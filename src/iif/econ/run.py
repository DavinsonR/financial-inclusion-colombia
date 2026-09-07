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
from iif.econ import designs, diagnostics, robustness
from iif.econ.frame import estimation_sample, load_frame
from iif.econ.panel import by_dimension, in_changes, pooled_entity_only, residuals_wide, two_way_fe

Y = "crecimiento"
X = "iif_compuesto"
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

    cambios_muestra = estimation_sample(marco, Y, f"d_{X}", CONTROLES)
    cambios, _ = in_changes(cambios_muestra, Y, X, CONTROLES)

    cce, _ = designs.cce_pooled(muestra, Y, X, CONTROLES)
    exposicion = designs.exposicion_inicial(marco, X, ANIO_BASE)
    ss, _ = designs.shift_share(muestra, Y, X, exposicion, CONTROLES)

    # El shift-share con efectos de tiempo identifica una pendiente diferencial de los departamentos mas
    # expuestos. Cualquier caracteristica inicial correlacionada con el indice —ingreso, urbanizacion—
    # produciria la misma pendiente si lo que hay es recuperacion desigual y no inclusion. Se contrasta
    # con esas exposiciones de placebo y con la carrera de caballos: el indice contra el ingreso, juntos.
    nacional = muestra.groupby("anio")[X].mean()
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
        muestra, exposicion, designs.exposicion_inicial(marco, "log_pib", ANIO_BASE), nacional
    )

    vecinos = diagnostics.vecinos_desde_topojson(
        config.REPO_ROOT / "atlas" / "data" / "geo_departamentos.json"
    )
    espacial, _ = designs.slx(muestra, Y, X, vecinos, CONTROLES)

    resid = residuals_wide(res_base)
    cd = diagnostics.pesaran_cd(resid)
    niveles = marco.pivot_table(index="anio", columns="dpto_ccdgo", values=X)
    raiz = diagnostics.cips(niveles)

    unidades = sorted(muestra["dpto_ccdgo"].unique())
    W = diagnostics.matriz_pesos(unidades, vecinos)
    moran_por_anio = []
    for anio, sub in muestra.groupby("anio"):
        serie = sub.set_index("dpto_ccdgo").reindex(unidades)["crecimiento"].to_numpy()
        m = diagnostics.moran_i(serie, W)
        m["anio"] = int(anio)
        moran_por_anio.append(m)

    eventos = designs.event_study(muestra, Y, X, exposicion, anio_evento=ANIO_EVENTO)
    wild = robustness.wild_cluster_bootstrap(muestra, Y, X, CONTROLES, replicas=replicas)
    placebo = robustness.placebo_permutacion(muestra, Y, X, CONTROLES, replicas=placebos)
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
            "dimensiones": [d.as_dict() for d in dimensiones],
            "sensibilidad_indice": sensibilidad,
            "disenos": [cce.as_dict(), ss.as_dict(), espacial.as_dict()],
            "shift_share_contraste": {"placebos": ss_placebos, "carrera": carrera},
            "estudio_eventos": eventos.to_dict(orient="records"),
            "diagnosticos": {"pesaran_cd": cd, "cips": raiz, "moran_por_anio": moran_por_anio},
            "robustez": {"wild_cluster_bootstrap": wild, "placebo_permutacion": placebo},
        }
    )


def _carrera_shift_share(
    muestra: pd.DataFrame, exp_indice: pd.Series, exp_ingreso: pd.Series, nacional: pd.Series
) -> dict:
    """Las dos exposiciones en la misma ecuacion: cual de las dos pendientes diferenciales sobrevive."""
    datos = muestra.copy()
    datos["adopcion"] = datos["anio"].map(nacional)
    datos["ss_indice"] = datos["dpto_ccdgo"].map(exp_indice) * datos["adopcion"]
    datos["ss_ingreso"] = datos["dpto_ccdgo"].map(exp_ingreso) * datos["adopcion"]
    datos = datos.dropna(subset=["ss_indice", "ss_ingreso"])
    est, res = two_way_fe(
        datos,
        Y,
        "ss_indice",
        [*CONTROLES, "ss_ingreso"],
        nombre="carrera: indice e ingreso iniciales × adopcion",
    )
    salida = est.as_dict()
    salida["coef_ingreso"] = float(res.params["ss_ingreso"])
    salida["se_ingreso"] = float(res.std_errors["ss_ingreso"])
    salida["p_ingreso"] = float(res.pvalues["ss_ingreso"])
    return salida


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
