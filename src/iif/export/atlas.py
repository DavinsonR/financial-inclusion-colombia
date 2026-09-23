"""Del warehouse al navegador: geometría en TopoJSON y series columnares en JSON (ADR-005).

El atlas es una página estática: no hay API detrás. Todo lo que el mapa puede mostrar tiene que caber en
`atlas/data/` dentro del presupuesto de `config/atlas.yaml`, así que el formato está pensado para pesar
poco: la geometría lleva solo la clave, y las series viajan como matrices de año por unidad con los
valores redondeados a los decimales que cada indicador necesita.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
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


def build_topojson(spec: dict) -> tuple[str, int, int]:
    """GeoJSON del MGN a TopoJSON con solo la clave como propiedad.

    Devuelve (json, número de unidades, número de islas descartadas).
    """
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
    del_warehouse = [i["id"] for i in indicadores if i.get("grupo") != "proyeccion"]
    cols = [spec["clave"], spec["nombre"], "anio", *spec["extra"], *del_warehouse]
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
        if ind.get("grupo") == "proyeccion":
            continue       # no sale del warehouse; lo pega `adjuntar_proyeccion`
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


CAMPOS_PROYECCION = {
    "crecimiento_pib_real_proy": ("reconciliado", "crecimiento_pct"),
    "crecimiento_pib_real_pc_proy": ("reconciliado", "per_capita_crecimiento_pct"),
    "crecimiento_pib_real_proy_sin_anclar": ("sin_anclar", "crecimiento_pct"),
}
INDICADOR_INCERTIDUMBRE = "intervalo_ancho_proy"


class ProyeccionIncompleta(ValueError):
    """La capa de proyección no viaja sin su capa de incertidumbre (ADR-022 decisión 6)."""


def adjuntar_proyeccion(datos: dict, indicadores: list[dict], ruta: Path) -> dict:
    """Añade los años proyectados y sus indicadores a una serie ya construida.

    La proyección no sale del warehouse: 2026, 2027 y 2028 no existen en ningún mart. Se
    lee del JSON que produce `uv run iif forecast` y se pega al final de la matriz, con los
    años nuevos marcados en `anios_proyectados` para que el navegador sepa dónde termina el
    dato y empieza el pronóstico.

    Los indicadores observados reciben `None` en los años proyectados, y los de proyección
    reciben `None` en los observados. Un hueco aquí es una fila que nadie midió, nunca un
    cero, igual que en el resto del atlas (R-13).
    """
    proy = [i for i in indicadores if i.get("grupo") == "proyeccion"]
    if not proy:
        return datos
    if not ruta.exists():
        raise FileNotFoundError(
            f"falta {ruta}; corre `uv run iif forecast` o quita el grupo `proyeccion` de atlas.yaml")

    if not any(i["id"] == INDICADOR_INCERTIDUMBRE for i in proy):
        raise ProyeccionIncompleta(
            "el grupo `proyeccion` no declara `intervalo_ancho_proy`. Un mapa de calor de un "
            "pronóstico puntual sin su intervalo comunica una precisión que el modelo no tiene "
            "(ADR-022 decisión 6).")

    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    anios_proy = [int(a) for a in contenido["horizonte"]]
    deps = contenido["departamentos"]
    ids = datos["ids"]

    solapan = sorted(set(anios_proy) & set(datos["anios"]))
    if solapan:
        raise ProyeccionIncompleta(f"los años {solapan} ya existen como observados")

    n_obs = len(datos["anios"])
    datos["anios"] = datos["anios"] + anios_proy
    datos["anios_proyectados"] = anios_proy
    datos["proyeccion"] = {
        "ancla": contenido["ancla"],
        "nivel_intervalo": contenido["nivel_intervalo"],
        "vintage": contenido["vintage"]["sha256"][:12],
        "backtest": contenido["puerta_de_calidad"],
    }

    for ind in indicadores:
        if ind.get("grupo") != "proyeccion":
            datos["series"][ind["id"]] += [[None] * len(ids) for _ in anios_proy]

    for ind in proy:
        matriz = [[None] * len(ids) for _ in range(n_obs)]
        for k in range(len(anios_proy)):
            fila: list[float | None] = [None] * len(ids)
            for j, clave in enumerate(ids):
                bloque_dep = deps.get(clave)
                if bloque_dep is None:
                    continue
                if ind["id"] == INDICADOR_INCERTIDUMBRE:
                    valores = bloque_dep.get("intervalo_ancho_pp")
                else:
                    rama, campo = CAMPOS_PROYECCION[ind["id"]]
                    valores = bloque_dep.get(rama, {}).get(campo)
                if valores and valores[k] is not None:
                    fila[j] = round(float(valores[k]), ind["decimales"])
            matriz.append(fila)
        datos["series"][ind["id"]] = matriz

    faltantes = sum(1 for fila in datos["series"][INDICADOR_INCERTIDUMBRE][n_obs:]
                    for v in fila if v is None)
    if faltantes:
        raise ProyeccionIncompleta(
            f"{faltantes} celdas proyectadas sin ancho de intervalo. No se publica (ADR-022).")
    return datos


def export_atlas(*, out_dir: Path | None = None, db: Path | None = None) -> dict[str, Path]:
    out_dir = out_dir or (config.REPO_ROOT / "atlas" / "data")
    out_dir.mkdir(parents=True, exist_ok=True)
    contrato = load_contract()
    ruta_db = db or config.DUCKDB_PATH
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
            spec_proy = contrato.get("proyeccion")
            if spec_proy and spec_proy.get("nivel") == nivel:
                datos = adjuntar_proyeccion(
                    datos, indicadores, config.REPO_ROOT / spec_proy["origen"])
            destino = out_dir / f"series_{nivel}.json"
            destino.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            escritos[f"series_{nivel}"] = destino
            meta_indicadores[nivel] = indicadores

    meta = {
        "version": contrato["version"],
        "generado_en": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
