"""Del warehouse al navegador: geometría en TopoJSON y series columnares en JSON (ADR-005).

El atlas es una página estática: no hay API detrás. Todo lo que el mapa puede mostrar tiene que caber en
`atlas/data/` dentro del presupuesto de `config/atlas.yaml`, así que el formato está pensado para pesar
poco: la geometría lleva solo la clave, y las series viajan como matrices de año por unidad con los
valores redondeados a los decimales que cada indicador necesita.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from iif import config

NIVELES = {
    "departamento": dict(
        tabla="marts.mart_indice_departamento_anual",
        clave="dpto_ccdgo",
        nombre="departamento",
        extra=("region",),
    ),
    "municipio": dict(
        tabla="marts.mart_indice_municipio_anual",
        clave="mpio_ccdgo",
        nombre="municipio",
        extra=("dpto_ccdgo", "mpio_tipo", "es_capital"),
    ),
}


def load_contract(path: Path | None = None) -> dict:
    return config.load_yaml(path or config.CONFIG_DIR / "atlas.yaml")


MINUSCULAS = {"de", "del", "la", "las", "los", "el", "y", "e", "en"}


def _titular(nombre: str) -> str:
    """El nombre como se escribe, no como lo guarda la fuente.

    La SFC y el DANE traen los municipios en mayúsculas ("VILLA DE SAN DIEGO DE UBATÉ"), que en un mapa
    ocupa un tercio más de ancho y se lee peor. Se baja a capitalización normal dejando quietas las
    abreviaturas con punto (D.C.) y los enlaces que en español van en minúscula.
    """
    if nombre != nombre.upper():
        return nombre
    palabras = nombre.split(" ")
    salida = []
    for i, palabra in enumerate(palabras):
        if "." in palabra or palabra in {"-", "("}:
            salida.append(palabra)
        elif i and palabra.lower().strip(",") in MINUSCULAS:
            salida.append(palabra.lower())
        else:
            salida.append(palabra.capitalize())
    return " ".join(salida)


def _escalar(valor: object) -> object:
    """Un acompañante de la unidad, tal cual lo entiende JavaScript.

    Los códigos DIVIPOLA van a texto porque llevan ceros a la izquierda y un número los perdería. Un booleano,
    en cambio, tiene que llegar como booleano: `str(True)` produce `"True"`, y en el navegador `"True"` no es
    ni `true` ni `"true"`, así que la comparación falla en silencio y la capa que dependa de ella no se dibuja.
    """
    if valor is None or (not isinstance(valor, bool) and pd.isna(valor)):
        return None
    if isinstance(valor, (bool, np.bool_)):
        return bool(valor)
    return str(valor)


def _limpiar(rasgo: dict, tolerancia: float) -> tuple[dict, int]:
    """Ordena los anillos como los espera TopoJSON y descarta las islas por debajo de la resolución.

    Dos motivos, los dos medidos sobre estos datos (B-039):
    - **El giro.** TopoJSON y la geometría esférica de d3 esperan el anillo exterior en sentido horario,
      que es justo el contrario de lo que pide RFC 7946 para GeoJSON. Con el giro de RFC, d3 interpreta
      cada anillo como el complemento del polígono: `d3.geoArea` de Bogotá daba 12,566, es decir 4π, la
      esfera entera. El mapa salía como un rectángulo de color con el país reducido a una mancha.
    - **Las islas diminutas.** Una isla más pequeña que la tolerancia de simplificación colapsa a un anillo
      de área cero, que produce el mismo efecto. Bolívar tiene 51 polígonos y una de sus islas caía ahí.
    Se descartan las islas de área menor que el cuadrado de la tolerancia: a la escala del atlas no ocupan
    ni un píxel, y el exportador informa cuántas para que la pérdida sea explícita, no silenciosa.
    """
    from shapely.geometry import MultiPolygon, mapping, shape
    from shapely.geometry.polygon import orient

    geom = rasgo.get("geometry")
    if not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
        return rasgo, 0
    figura = shape(geom)
    minima = tolerancia**2
    partes = [figura] if figura.geom_type == "Polygon" else list(figura.geoms)
    grandes = [g for g in partes if g.area >= minima]
    descartadas = len(partes) - len(grandes)
    if not grandes:  # nunca se deja una unidad sin geometría: se conserva su polígono mayor
        grandes = [max(partes, key=lambda g: g.area)]
        descartadas = len(partes) - 1
    orientados = [orient(g, sign=-1.0) for g in grandes]
    figura = orientados[0] if len(orientados) == 1 else MultiPolygon(orientados)
    return {**rasgo, "geometry": mapping(figura)}, descartadas


def build_topojson(spec: dict) -> tuple[str, int]:
    """GeoJSON del MGN a TopoJSON con solo la clave como propiedad. Devuelve (json, número de unidades)."""
    import topojson as tp

    fc = json.loads((config.REPO_ROOT / spec["origen"]).read_text(encoding="utf-8"))
    clave = spec["clave"]
    for ft in fc["features"]:
        props = ft["properties"]
        valor = props.get(clave) or props.get(clave.upper())
        if valor is None:
            raise KeyError(f"un rasgo no trae la clave {clave!r}: {sorted(props)[:6]}")
        ft["properties"] = {"id": valor}
    tolerancia = float(spec["simplificacion"])
    limpios = [_limpiar(ft, tolerancia) for ft in fc["features"]]
    descartadas = sum(d for _, d in limpios)
    fc["features"] = [ft for ft, _ in limpios]
    n = len(fc["features"])
    topo = tp.Topology(
        fc,
        prequantize=spec["cuantizacion"],
        toposimplify=spec["simplificacion"],
        # `winding_order` deja los anillos como manda RFC 7946 y `prevent_oversimplify` impide que una isla
        # pequeña colapse: un anillo degenerado o con el giro invertido se dibuja como el complemento de la
        # esfera y tapa el mapa entero (B-039).
        winding_order="CW_CCW",
        prevent_oversimplify=True,
    )
    texto = topo.to_json()
    # La simplificación conserva la topología, pero se comprueba: un municipio que desaparece del mapa
    # sin que nadie lo note es peor que un mapa más pesado.
    objetos = json.loads(texto)["objects"]
    geoms = next(iter(objetos.values()))["geometries"]
    if len(geoms) != n:
        raise ValueError(f"la simplificación dejó {len(geoms)} unidades de {n}")
    return texto, n, descartadas


def series_frame(nivel: str, indicadores: list[dict], con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    spec = NIVELES[nivel]
    cols = [spec["clave"], spec["nombre"], "anio", *spec["extra"], *[i["id"] for i in indicadores]]
    disponibles = {r[0] for r in con.sql(f"describe {spec['tabla']}").fetchall()}
    faltan = [c for c in cols if c not in disponibles]
    if faltan:
        raise KeyError(f"{spec['tabla']} no tiene las columnas {faltan}")
    return con.sql(f"select {', '.join(cols)} from {spec['tabla']} order by 1, 3").df()


def build_series(nivel: str, indicadores: list[dict], df: pd.DataFrame) -> dict:
    """Series como matriz año por unidad. Un nulo es un dato no observado, nunca un cero (R-13)."""
    spec = NIVELES[nivel]
    ids = sorted(df[spec["clave"]].dropna().unique().tolist())
    anios = sorted(int(a) for a in df["anio"].dropna().unique())
    pos = {v: i for i, v in enumerate(ids)}
    meta = df.drop_duplicates(subset=[spec["clave"]]).set_index(spec["clave"])
    salida = {
        "nivel": nivel,
        "ids": ids,
        "anios": anios,
        "nombres": [_titular(str(meta[spec["nombre"]].get(i, ""))) for i in ids],
        "series": {},
    }
    for campo in spec["extra"]:
        salida[campo] = [_escalar(meta[campo].get(i)) for i in ids]

    for ind in indicadores:
        matriz = []
        for anio in anios:
            fila: list[float | None] = [None] * len(ids)
            sub = df[df["anio"] == anio]
            for clave, valor in zip(sub[spec["clave"]], sub[ind["id"]], strict=True):
                if pd.notna(valor) and clave in pos:
                    fila[pos[clave]] = round(float(valor), ind["decimales"])
            matriz.append(fila)
        salida["series"][ind["id"]] = matriz
    return salida


def export_atlas(*, out_dir: Path | None = None, db: Path | None = None) -> dict[str, Path]:
    out_dir = out_dir or (config.REPO_ROOT / "atlas" / "data")
    out_dir.mkdir(parents=True, exist_ok=True)
    contrato = load_contract()
    ruta_db = db or (config.REPO_ROOT / "db" / "iif.duckdb")
    if not ruta_db.exists():
        raise FileNotFoundError(f"no existe {ruta_db}; corre `make dbt-build` y `make index` antes")

    escritos: dict[str, Path] = {}
    unidades: dict[str, int] = {}
    islas_descartadas: dict[str, int] = {}
    for nombre, spec in contrato["geometria"].items():
        texto, n, descartadas = build_topojson(spec)
        islas_descartadas[nombre] = descartadas
        destino = out_dir / f"geo_{nombre}.json"
        destino.write_text(texto, encoding="utf-8")
        escritos[f"geo_{nombre}"] = destino
        unidades[nombre] = n

    meta_indicadores = {}
    with duckdb.connect(str(ruta_db), read_only=True) as con:
        for nivel, indicadores in contrato["indicadores"].items():
            df = series_frame(nivel, indicadores, con)
            datos = build_series(nivel, indicadores, df)
            destino = out_dir / f"series_{nivel}.json"
            destino.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            escritos[f"series_{nivel}"] = destino
            meta_indicadores[nivel] = indicadores

    meta = {
        "version": contrato["version"],
        "generado_en": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "indicadores": meta_indicadores,
        "unidades": unidades,
        "islas_descartadas": islas_descartadas,
        "fuente": "Superintendencia Financiera (CC BY-SA 4.0), DANE, MinTIC y MEN. Índice: ADR-015.",
        "nota": "Un valor ausente es una unidad no observada, no un cero.",
        "nota_geometria": (
            "Se descartan las islas menores que la tolerancia de simplificación; `islas_descartadas` "
            "dice cuántas por nivel. Ninguna unidad se queda sin geometría."
        ),
    }
    destino = out_dir / "atlas_meta.json"
    destino.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    escritos["meta"] = destino

    total = sum(p.stat().st_size for p in escritos.values()) / 1e6
    tope = float(contrato["presupuesto_mb"])
    if total > tope:
        detalle = ", ".join(f"{k} {p.stat().st_size / 1e6:.2f} MB" for k, p in escritos.items())
        raise ValueError(f"el atlas pesa {total:.2f} MB y el tope es {tope} MB: {detalle}")
    return escritos
