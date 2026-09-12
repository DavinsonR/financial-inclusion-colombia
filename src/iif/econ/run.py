"""Corre la batería completa y deja un solo JSON con todo lo que la página publica.

El orden importa y es el del argumento: primero la especificación base y el contraste que enseña de dónde
sale el coeficiente, después los diagnósticos que dicen si la inferencia vale, después los diseños que no
dependen de la exogeneidad del índice, y al final la robustez. Cada cifra publicada sale de este archivo,
no de un cuaderno (R-09).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from iif import config
from iif.econ import designs, diagnostics, power, robustness
from iif.econ.frame import estimation_sample, load_frame
from iif.econ.panel import by_dimension, in_changes, pooled_entity_only, residuals_wide, two_way_fe

Y = "crecimiento"
# El regresor de la especificación base. `REZAGO_INDICE` decide si se usa el índice del mismo año o el del
# anterior, y es la única fuente de verdad de esa elección: el texto publicado la cita desde aquí en vez de
# describirla por su cuenta, que es exactamente el error de B-049. Con el denominador rezagado de ADR-017,
# el contemporáneo da +0,00382 (p = 0,54) y el rezagado +0,00699 (p = 0,25): los dos son nulos y el segundo
# no cuesta ninguna observación, porque la muestra ya empieza en 2019 y el índice existe desde 2018.
REZAGO_INDICE = False
# `INDICE` es la serie; `X` es el regresor que entra en la ecuación base. Se separan porque la
# especificación en cambios, la exposición inicial y los índices de sensibilidad trabajan siempre sobre la
# serie sin rezagar, aunque la base decida rezagarla.
INDICE = "iif_compuesto"
X = f"{INDICE}_rezago" if REZAGO_INDICE else INDICE
CONTROLES = ["log_pib_rezago", "tasa_urbanizacion"]
ANIO_BASE = 2018
ANIO_EVENTO = 2020


def _limpia(objeto):
    """JSON no sabe de NaN ni de tipos de numpy."""
    if isinstance(objeto, dict):
        return {k: _limpia(v) for k, v in objeto.items()}
    if isinstance(objeto, list):
        return [_limpia(v) for v in objeto]
    if isinstance(objeto, (np.integer,)):
        return int(objeto)
    if isinstance(objeto, (np.floating, float)):
        valor = float(objeto)
        return None if not np.isfinite(valor) else valor
    if isinstance(objeto, (np.bool_,)):
        return bool(objeto)
    return objeto


def run(db: str | None = None, *, replicas: int = 999, placebos: int = 499) -> dict:
    marco = load_frame(db)
    muestra = estimation_sample(marco, Y, X, CONTROLES)

    base, res_base = two_way_fe(muestra, Y, X, CONTROLES, nombre="base: efectos de entidad y tiempo")
    dk, _ = two_way_fe(muestra, Y, X, CONTROLES, errores="driscoll-kraay", nombre="base con Driscoll-Kraay")
    solo_entidad, _ = pooled_entity_only(muestra, Y, X, CONTROLES)

    cambios_muestra = estimation_sample(marco, Y, f"d_{INDICE}", CONTROLES)
    cambios, _ = in_changes(cambios_muestra, Y, INDICE, CONTROLES)

    cce, _ = designs.cce_pooled(muestra, Y, X, CONTROLES)
    exposicion = designs.exposicion_inicial(marco, INDICE, ANIO_BASE)
    ss, datos_ss = designs.shift_share(muestra, Y, X, exposicion, CONTROLES)

    # El shift-share con efectos de tiempo identifica una pendiente diferencial de los departamentos mas
    # expuestos. Cualquier caracteristica inicial correlacionada con el indice —ingreso, urbanizacion—
    # produciria la misma pendiente si lo que hay es recuperacion desigual y no inclusion. Se contrasta
    # con esas exposiciones de placebo y con la carrera de caballos: el indice contra el ingreso, juntos.
    nacional = muestra.groupby("anio")[INDICE].mean()
    ss_placebos = []
    for variable, etiqueta in (
        ("log_pib", "ingreso inicial"),
        ("tasa_urbanizacion", "urbanizacion inicial"),
    ):
        exp_alt = designs.exposicion_inicial(marco, variable, ANIO_BASE)
        est_alt, _ = designs.shift_share(muestra, Y, X, exp_alt, CONTROLES, nacional=nacional)
        est_alt.nombre = f"placebo shift-share: {etiqueta} × adopcion"
        ss_placebos.append(est_alt.as_dict())
    carrera = _carrera_shift_share(
        muestra,
        exposicion,
        {
            "ingreso": designs.exposicion_inicial(marco, "log_pib", ANIO_BASE),
            "urbanizacion": designs.exposicion_inicial(marco, "tasa_urbanizacion", ANIO_BASE),
        },
        nacional,
    )

    vecinos = diagnostics.vecinos_desde_topojson(
        config.REPO_ROOT / "atlas" / "data" / "geo_departamentos.json"
    )
    espacial, res_slx = designs.slx(muestra, Y, X, vecinos, CONTROLES)

    resid = residuals_wide(res_base)
    cd = diagnostics.pesaran_cd(resid)
    niveles = marco.pivot_table(index="anio", columns="dpto_ccdgo", values=INDICE)
    raiz = diagnostics.cips(niveles)

    unidades = sorted(muestra["dpto_ccdgo"].unique())
    W = diagnostics.matriz_pesos(unidades, vecinos)
    moran_por_anio = _moran_por_anio(muestra, unidades, W, res_base, res_slx)

    eventos = designs.event_study(muestra, Y, X, exposicion, anio_evento=ANIO_EVENTO)
    wild = robustness.wild_cluster_bootstrap(muestra, Y, X, CONTROLES, replicas=replicas)
    placebo = robustness.placebo_permutacion(muestra, Y, X, CONTROLES, replicas=placebos)
    # El modo antiguo se conserva al lado: su nube es mucho mas estrecha porque destruye la correlacion
    # serial del regresor, y verlas juntas es lo que explica por que sus p no son comparables (B-054).
    placebo_anio = robustness.placebo_permutacion(
        muestra, Y, X, CONTROLES, replicas=placebos, modo="dentro_del_anio"
    )
    dimensiones = by_dimension(marco.dropna(subset=[Y, *CONTROLES]), Y, CONTROLES)

    sensibilidad = []
    for alterno, etiqueta in (("iif_sensibilidad_pca", "PCA"), ("iif_sensibilidad_sarma", "Sarma")):
        sub = estimation_sample(marco, Y, alterno, CONTROLES)
        if sub.empty:
            continue
        est, _ = two_way_fe(sub, Y, alterno, CONTROLES, nombre=f"índice alternativo: {etiqueta}")
        sensibilidad.append(est.as_dict())

    return _limpia(
        {
            "generado_en": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "especificacion": {
                "dependiente": Y,
                "regresor": X,
                "controles": CONTROLES,
                "efectos": "entidad y tiempo",
                "anio_base_exposicion": ANIO_BASE,
                "anio_evento": ANIO_EVENTO,
                "unidades": int(muestra["dpto_ccdgo"].nunique()),
                "periodos": sorted(int(a) for a in muestra["anio"].unique()),
                "n": int(len(muestra)),
            },
            "principales": [base.as_dict(), dk.as_dict(), solo_entidad.as_dict(), cambios.as_dict()],
            # Qué efectos descarta este diseño y cuáles no puede descartar (ADR-018). Sin esto, "no
            # predice" es una afirmación que la muestra no sostiene.
            "potencia": power.resumen(base, muestra, X, CONTROLES),
            "dimensiones": [d.as_dict() for d in dimensiones],
            "sensibilidad_indice": sensibilidad,
            "ventanas": _ventanas(muestra),
            "no_linealidad": _no_linealidad(muestra, replicas),
            "disenos": [cce.as_dict(), ss.as_dict(), espacial.as_dict()],
            "shift_share_contraste": {
                "placebos": ss_placebos,
                "carrera": carrera,
                "inferencia": _inferencia_del_shift_share(datos_ss, replicas, placebos),
            },
            "estudio_eventos": eventos.to_dict(orient="records"),
            "diagnosticos": {"pesaran_cd": cd, "cips": raiz, "moran_por_anio": moran_por_anio},
            "robustez": {
                "wild_cluster_bootstrap": wild,
                "placebo_permutacion": placebo,
                "placebo_permutacion_dentro_del_anio": placebo_anio,
                "jackknife": _jackknife(muestra),
            },
        }
    )


def _carrera_shift_share(
    muestra: pd.DataFrame, exp_indice: pd.Series, rivales: dict[str, pd.Series], nacional: pd.Series
) -> list[dict]:
    """El índice contra cada exposición rival en la misma ecuación, y contra todas a la vez.

    Antes solo se corría contra el ingreso inicial, que es el rival que pierde. La urbanización inicial es
    la que gana su propio placebo, así que es la que hay que meter dentro: con ella el índice pasa de
    p = 0,007 a p = 0,072. Correr la carrera únicamente contra el rival débil no es un contraste.
    """
    base = muestra.copy()
    base["adopcion"] = base["anio"].map(nacional)
    base["ss_indice"] = base["dpto_ccdgo"].map(exp_indice) * base["adopcion"]

    columnas = {}
    for etiqueta, serie in rivales.items():
        col = f"ss_{etiqueta}"
        base[col] = base["dpto_ccdgo"].map(serie) * base["adopcion"]
        columnas[etiqueta] = col

    combinaciones = [([e], f"carrera: índice contra {e} inicial") for e in columnas]
    if len(columnas) > 1:
        combinaciones.append((list(columnas), "carrera: índice contra todas las exposiciones"))

    salida = []
    for etiquetas, nombre in combinaciones:
        cols = [columnas[e] for e in etiquetas]
        datos = base.dropna(subset=["ss_indice", *cols])
        est, res = two_way_fe(datos, Y, "ss_indice", [*CONTROLES, *cols], nombre=nombre)
        fila = est.as_dict()
        fila["rivales"] = {
            e: {
                "coef": float(res.params[columnas[e]]),
                "se": float(res.std_errors[columnas[e]]),
                "p": float(res.pvalues[columnas[e]]),
            }
            for e in etiquetas
        }
        salida.append(fila)
    return salida


def _residuos_largos(res) -> pd.DataFrame:
    """Los residuos de una estimación como tabla unidad-año, que es lo que consume Moran."""
    r = res.resids.reset_index()
    r.columns = ["dpto_ccdgo", "anio", "e"]
    return r


def _moran_por_anio(muestra: pd.DataFrame, unidades: list[str], W, res_base, res_slx) -> list[dict]:
    """I de Moran por año sobre tres objetos: la dependiente cruda y los residuos de los dos modelos.

    La cruda dice si los vecinos crecen parecido, que es un hecho conocido sobre Colombia y no una propiedad
    del modelo. Lo que la batería necesita saber es si al modelo le queda dependencia espacial sin explicar,
    y eso solo lo dicen los residuos. Publicar la primera y afirmar con ella lo segundo fue B-048; van las
    tres columnas para que la diferencia se vea.
    """
    resid_base, resid_slx = _residuos_largos(res_base), _residuos_largos(res_slx)

    def serie(tabla: pd.DataFrame, columna: str) -> np.ndarray:
        return tabla.set_index("dpto_ccdgo").reindex(unidades)[columna].to_numpy(dtype=float)

    salida = []
    for anio, sub in muestra.groupby("anio"):
        fila = {"anio": int(anio), "crecimiento": diagnostics.moran_i(serie(sub, Y), W)}
        for etiqueta, tabla in (("residuos_base", resid_base), ("residuos_slx", resid_slx)):
            trozo = tabla[tabla["anio"] == anio]
            fila[etiqueta] = (
                diagnostics.moran_i(serie(trozo, "e"), W)
                if not trozo.empty
                else {"I": float("nan"), "p": float("nan"), "n": 0}
            )
        salida.append(fila)
    return salida


def _jackknife(muestra: pd.DataFrame) -> dict:
    """El coeficiente dejando fuera un departamento cada vez.

    Con 33 unidades una sola observación influyente puede mandar el resultado, y un nulo que dependiera de
    un departamento no sería un nulo. Es evidencia a favor del resultado y por eso se publica.
    """
    filas = []
    for unidad in sorted(muestra["dpto_ccdgo"].unique()):
        sub = muestra[muestra["dpto_ccdgo"] != unidad]
        est, _ = two_way_fe(sub, Y, X, CONTROLES)
        filas.append(
            {
                "fuera": unidad,
                "departamento": muestra.loc[muestra["dpto_ccdgo"] == unidad, "departamento"].iloc[0],
                "coef": est.coef,
                "p": est.p,
            }
        )
    coefs = [f["coef"] for f in filas]
    return {
        "minimo": float(min(coefs)),
        "maximo": float(max(coefs)),
        "ninguno_significativo": bool(all(f["p"] >= 0.05 for f in filas)),
        "por_departamento": filas,
    }


def _ventanas(muestra: pd.DataFrame) -> list[dict]:
    """El coeficiente en ventanas que quitan la pandemia o los años cuyo dato aún es provisional.

    2020 y 2021 son el choque asimétrico más grande del periodo y 2024 y 2025 llevan dato provisional o
    preliminar del DANE. Si el nulo dependiera de cualquiera de los cuatro, habría que decirlo.
    """
    cortes = [
        ("completa", muestra),
        ("sin 2020", muestra[muestra["anio"] != 2020]),
        ("sin 2020 y 2021", muestra[~muestra["anio"].isin([2020, 2021])]),
        ("sin 2025 preliminar", muestra[muestra["anio"] != 2025]),
        ("sin 2024 ni 2025", muestra[~muestra["anio"].isin([2024, 2025])]),
    ]
    salida = []
    for etiqueta, sub in cortes:
        if sub["anio"].nunique() < 3:
            continue
        est, _ = two_way_fe(sub, Y, X, CONTROLES, nombre=f"ventana: {etiqueta}")
        salida.append(est.as_dict())
    return salida


def _no_linealidad(muestra: pd.DataFrame, replicas: int) -> dict:
    """El término cuadrático, que ADR-016 prometió como heterogeneidad y nunca se estimó.

    La literatura de finanzas y crecimiento encuentra efectos que se agotan o se invierten con el nivel
    (Arcand, Berkes y Panizza, 2015). Una especificación lineal promedia eso a cero, así que el nulo no
    distingue entre "no hay efecto" y "hay dos efectos que se cancelan". Se publica con bootstrap salvaje
    porque con 33 clústeres el p agrupado no basta, y con la advertencia de que es un contraste más en una
    familia: su p no lleva descuento por comparaciones múltiples.
    """
    datos = muestra.copy()
    datos[f"{X}_cuadrado"] = datos[X] ** 2
    est, res = two_way_fe(datos, Y, X, [*CONTROLES, f"{X}_cuadrado"], nombre="con término cuadrático")
    boot = robustness.wild_cluster_bootstrap(
        datos, Y, f"{X}_cuadrado", [*CONTROLES, X], replicas=replicas
    )
    lineal, cuadratico = float(res.params[X]), float(res.params[f"{X}_cuadrado"])
    salida = est.as_dict()
    salida.update(
        {
            "coef_lineal": lineal,
            "p_lineal": float(res.pvalues[X]),
            "coef_cuadratico": cuadratico,
            "p_cuadratico": float(res.pvalues[f"{X}_cuadrado"]),
            "p_bootstrap_cuadratico": boot["p_bootstrap"],
            "vertice": float(-lineal / (2 * cuadratico)) if cuadratico != 0 else float("nan"),
            "nota": "un contraste más en la familia; su p no lleva descuento por comparaciones múltiples",
        }
    )
    if np.isfinite(salida["vertice"]):
        salida["fraccion_bajo_el_vertice"] = float((muestra[X] < salida["vertice"]).mean())
    return salida


def _inferencia_del_shift_share(datos_ss: pd.DataFrame, replicas: int, placebos: int) -> dict:
    """El bootstrap y el placebo aplicados al shift-share, que es el único coeficiente con señal.

    Hasta ahora la batería fuerte solo corría sobre el coeficiente nulo, donde no podía cambiar nada. Es al
    revés de como debería: la inferencia exigente se le pide al resultado que afirma algo.
    """
    wild = robustness.wild_cluster_bootstrap(datos_ss, Y, "shift_share", CONTROLES, replicas=replicas)
    placebo = robustness.placebo_permutacion(datos_ss, Y, "shift_share", CONTROLES, replicas=placebos)
    return {"wild_cluster_bootstrap": wild, "placebo_permutacion": placebo}


def write(salida: Path | None = None, db: str | None = None, **kwargs) -> Path:
    destino = salida or (config.REPO_ROOT / "data" / "processed" / "econ" / "resultados.json")
    destino.parent.mkdir(parents=True, exist_ok=True)
    resultados = run(db, **kwargs)
    destino.write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino


def tabla_principal(resultados: dict) -> pd.DataFrame:
    """Las columnas de la tabla 1, en el orden en que se leen."""
    filas = [
        {
            "Especificación": e["nombre"],
            "Coeficiente": e["coef"],
            "Error estándar": e["se"],
            "p": e["p"],
            "N": e["n"],
            "Departamentos": e["unidades"],
            "Errores": e["errores"],
        }
        for e in resultados["principales"]
    ]
    return pd.DataFrame(filas)
