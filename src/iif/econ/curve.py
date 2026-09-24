"""La curva de especificación: todas las decisiones defendibles, estimadas, y cuántas dan significativo.

Una batería contra la correlación espuria responde «este coeficiente concreto no sobrevive». La curva
responde algo más incómodo y más útil: de todas las especificaciones que el proyecto podría haber
defendido, ¿cuántas habrían dado un resultado? Y, sobre todo, ¿cuánto cambia esa proporción al poner los
efectos de tiempo?

El contraste es el argumento central del trabajo convertido en un número que se puede enseñar: sin efectos
de tiempo, más de la mitad de las especificaciones «encuentra» algo; con ellos, la proporción cae a lo que
el azar produce al probar ochenta hipótesis correlacionadas al 5 %. Es una lectura en el espíritu del
análisis multiverso y de la curva de especificación (Simonsohn, Simmons y Nelson, 2020).

Ninguna cifra de aquí se calcula en una página: `uv run iif curva` escribe el JSON y la página lo lee (R-09).
"""

from __future__ import annotations

import itertools
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from iif import config
from iif.econ.frame import estimation_sample, load_frame
from iif.econ.panel import two_way_fe
from iif.econ.power import escala_del_regresor

Y = "crecimiento"

# Cada eje es una decisión que el autor podría haber tomado de otra forma sin dejar de ser defendible.
REGRESORES = {
    "índice compuesto": "iif_compuesto",
    "compuesto rezagado": "iif_compuesto_rezago",
    "cambio del compuesto": "d_iif_compuesto",
    "acceso": "iif_acceso",
    "uso": "iif_uso",
    "profundidad": "iif_profundidad",
    "índice por PCA": "iif_sensibilidad_pca",
    "índice de Sarma": "iif_sensibilidad_sarma",
}

CONTROLES = {
    "convergencia y urbanización": ["log_pib_rezago", "tasa_urbanizacion"],
    "solo urbanización": ["tasa_urbanizacion"],
}

MUESTRAS = {
    "completa": lambda d: d,
    "sin 2020": lambda d: d[d["anio"] != 2020],
    "sin 2020 y 2021": lambda d: d[~d["anio"].isin([2020, 2021])],
    "sin 2025 preliminar": lambda d: d[d["anio"] != 2025],
    "sin Bogotá": lambda d: d[d["dpto_ccdgo"] != "11"],
}

EFECTOS = {"entidad y tiempo": True, "solo entidad": False}

MIN_FILAS = 40
MIN_UNIDADES = 10


def estimar_rejilla(db: str | None = None) -> pd.DataFrame:
    """Una fila por especificación, con su coeficiente y su p."""
    marco = load_frame(db)
    filas = []
    combinaciones = itertools.product(
        REGRESORES.items(), CONTROLES.items(), MUESTRAS.items(), EFECTOS.items()
    )
    for (reg_nom, reg_col), (ctl_nom, ctl), (mue_nom, corte), (efe_nom, con_tiempo) in combinaciones:
        if reg_col not in marco.columns:
            continue
        muestra = estimation_sample(corte(marco), Y, reg_col, ctl)
        if len(muestra) < MIN_FILAS or muestra["dpto_ccdgo"].nunique() < MIN_UNIDADES:
            continue
        try:
            est, _ = two_way_fe(muestra, Y, reg_col, ctl, time_effects=con_tiempo)
        except Exception:
            # Una combinación que el estimador no puede resolver (rango incompleto, efecto absorbido) no
            # es un resultado: se omite y se cuenta, en vez de colarse como un cero.
            filas.append({"regresor": reg_nom, "controles": ctl_nom, "muestra": mue_nom,
                          "efectos": efe_nom, "estimable": False})
            continue
        # Los ocho regresores no están en la misma escala: el índice de Sarma es una distancia en [0, 1] y
        # los demás son estandarizados, así que sus coeficientes crudos no se pueden poner en el mismo eje.
        # Cada uno se expresa en puntos porcentuales de crecimiento por desviación típica IDENTIFICANTE de
        # ese regresor, que es la unidad en la que sí son comparables (ADR-018).
        sd = escala_del_regresor(muestra, reg_col, ctl)["de_identificante"]
        factor = sd * 100 if sd > 0 else float("nan")
        coef_pp, bajo_pp, alto_pp = (
            float(est.coef * factor),
            float(est.ic_bajo * factor),
            float(est.ic_alto * factor),
        )
        filas.append(
            {
                "regresor": reg_nom,
                "controles": ctl_nom,
                "muestra": mue_nom,
                "efectos": efe_nom,
                "estimable": True,
                "coef": round(float(est.coef), 6),
                "se": round(float(est.se), 6),
                "p": round(float(est.p), 5),
                "ic_bajo": round(float(est.ic_bajo), 6),
                "ic_alto": round(float(est.ic_alto), 6),
                "de_identificante": round(float(sd), 6),
                "coef_pp": round(coef_pp, 4),
                "ic_bajo_pp": round(bajo_pp, 4),
                "ic_alto_pp": round(alto_pp, 4),
                "n": int(est.n),
                "unidades": int(est.unidades),
                "significativa": bool(est.p < 0.05),
            }
        )
    return pd.DataFrame(filas)


def resumir(rejilla: pd.DataFrame) -> dict:
    """Cuántas dan significativo en cada régimen de efectos: es el resultado de la página."""
    vivas = rejilla[rejilla["estimable"]]
    salida = {}
    for efectos, sub in vivas.groupby("efectos"):
        salida[efectos] = {
            "especificaciones": int(len(sub)),
            "significativas": int(sub["significativa"].sum()),
            "fraccion": round(float(sub["significativa"].mean()), 4),
            "mediana": round(float(sub["coef"].median()), 6),
            "minimo": round(float(sub["coef"].min()), 6),
            "maximo": round(float(sub["coef"].max()), 6),
            "mediana_pp": round(float(sub["coef_pp"].median()), 4),
            "minimo_pp": round(float(sub["coef_pp"].min()), 4),
            "maximo_pp": round(float(sub["coef_pp"].max()), 4),
        }
    return salida


def run(db: str | None = None) -> dict:
    rejilla = estimar_rejilla(db)
    vivas = rejilla[rejilla["estimable"]]
    return {
        "generado_en": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ejes": {
            "regresor": list(REGRESORES),
            "controles": list(CONTROLES),
            "muestra": list(MUESTRAS),
            "efectos": list(EFECTOS),
        },
        "total": int(len(rejilla)),
        "no_estimables": int((~rejilla["estimable"]).sum()),
        "resumen": resumir(rejilla),
        "especificaciones": vivas.drop(columns=["estimable"]).to_dict(orient="records"),
    }


def write(salida: Path | None = None, db: str | None = None) -> Path:
    destino = salida or (config.DATA_PROCESSED / "econ" / "curva_especificacion.json")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(run(db), ensure_ascii=False, indent=1), encoding="utf-8")
    return destino
