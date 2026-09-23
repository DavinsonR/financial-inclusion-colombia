"""Corre la capa de proyección y deja un solo JSON con todo lo que el atlas publica.

El orden es el de las decisiones: primero el backtest, que es la puerta —si la combinación
no le gana al ingenuo, nada se publica (ADR-020)—, después el pronóstico 2026–2028 sin
anclar, después el anclado y reconciliado (ADR-021), y al final los intervalos, que viajan
siempre (ADR-022). Cada cifra publicada sale de este archivo (R-09).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from iif import config
from iif.forecast import anchor, backtest, frame, models, reconcile

HORIZONTE = [2026, 2027, 2028]
NIVEL_INTERVALO = 0.80
DESTINO = config.DATA_PROCESSED / "forecast" / "resultados.json"


def _limpia(objeto):
    """JSON no sabe de NaN ni de tipos de numpy."""
    if isinstance(objeto, dict):
        return {k: _limpia(v) for k, v in objeto.items()}
    if isinstance(objeto, (list, tuple)):
        return [_limpia(v) for v in objeto]
    if isinstance(objeto, np.integer):
        return int(objeto)
    if isinstance(objeto, (np.floating, float)):
        valor = float(objeto)
        return None if not np.isfinite(valor) else round(valor, 6)
    if isinstance(objeto, np.bool_):
        return bool(objeto)
    return objeto


def pronosticar(marco: frame.Marco, anios: list[int] | None = None):
    """Pronóstico combinado por departamento, en logaritmos.

    Devuelve tres matrices año × departamento: media, varianza y el conteo de
    especificaciones que convergieron, que es lo que hace auditable la combinación.
    """
    anios = anios or HORIZONTE
    h = len(anios)
    media, varianza, vivas = {}, {}, {}
    for cod in marco.departamentos:
        serie = marco.log_pib[cod]
        partes = {n: models.predecir(n, serie, h) for n in models.ESPECIFICACIONES}
        combinado = models.combinar(partes)
        media[cod] = combinado.media
        varianza[cod] = combinado.varianza
        vivas[cod] = sum(1 for p in partes.values() if np.all(np.isfinite(p.media)))
    idx = pd.Index(anios, name="anio")
    return (pd.DataFrame(media, index=idx), pd.DataFrame(varianza, index=idx),
            pd.Series(vivas, name="especificaciones_convergidas"))


def _crecimiento(niveles: pd.DataFrame, ultimo_observado: pd.Series) -> pd.DataFrame:
    """De niveles a crecimiento anual en porcentaje, encadenando desde el último dato."""
    completo = pd.concat([ultimo_observado.to_frame().T, niveles])
    return (completo.pct_change().dropna() * 100)


def construir(marco: frame.Marco | None = None, anios: list[int] | None = None,
              escenario: str = "central", sin_red: bool = False) -> dict:
    """Todo el contenido publicable, como diccionario."""
    marco = marco or frame.load_frame()
    anios = anios or HORIZONTE

    # 1. La puerta de calidad. Si esto falla, no hay nada que publicar.
    detalle = backtest.rolling_origin(marco)
    veredictos = backtest.evaluar(detalle)
    aprobado = backtest.exigir_aprobacion(veredictos, "combinacion")

    # 2. Pronóstico sin anclar.
    media_log, var_log, vivas = pronosticar(marco, anios)
    niveles = np.exp(media_log)
    ultimo = marco.pib_nivel.iloc[-1]

    # 3. Anclado y reconciliado (ADR-021).
    ancla = anchor.cargar(anios, escenario=escenario, sin_red=sin_red)
    objetivo = ancla.niveles(float(marco.nacional.iloc[-1]),
                             int(marco.nacional.index[-1]), anios)
    reconciliado = reconcile.reconciliar(niveles, objetivo, metodo="proporcional")

    # 4. Per cápita: división, no modelo (ADR-019 decisión 2).
    pob = frame.poblacion()
    pob_horizonte = pob.reindex(index=anios, columns=marco.departamentos)
    per_capita = reconciliado / pob_horizonte * 1e9 if not pob_horizonte.isna().all().all() else None

    # 5. Intervalos, que viajan siempre (ADR-022).
    z_bajo, z_alto = models.Pronostico(media_log.to_numpy(), var_log.to_numpy()).intervalo(NIVEL_INTERVALO)
    ancho_pp = pd.DataFrame(z_alto - z_bajo, index=media_log.index,
                            columns=media_log.columns) * 100

    coherencia = reconcile.coherencia(marco.pib_nivel, marco.nacional)

    return {
        "generado_en": datetime.now(UTC).isoformat(timespec="seconds"),
        "vintage": marco.vintage.as_dict(),
        "horizonte": anios,
        "nivel_intervalo": NIVEL_INTERVALO,
        "ancla": ancla.as_dict(),
        "puerta_de_calidad": {
            "modelo_publicado": aprobado.modelo,
            "mae": aprobado.mae,
            "ganancia_sobre_ingenuo_pct": aprobado.ganancia_pct,
            "dm_p": aprobado.dm_p,
            "cobertura": aprobado.cobertura,
            "n_pares": aprobado.n,
        },
        "backtest": {
            "completo": [v.as_dict() for v in veredictos],
            "por_regimen": backtest.por_regimen(detalle),
        },
        "coherencia_jerarquica_pct": {str(a): float(v) for a, v in coherencia.items()},
        "departamentos": {
            cod: {
                "nombre": marco.nombres.get(cod, cod),
                "especificaciones_convergidas": int(vivas[cod]),
                "sin_anclar": {
                    "nivel": [float(niveles.loc[a, cod]) for a in anios],
                    "crecimiento_pct": [float(v) for v in
                                        _crecimiento(niveles, ultimo)[cod].to_numpy()],
                },
                "reconciliado": {
                    "nivel": [float(reconciliado.loc[a, cod]) for a in anios],
                    "crecimiento_pct": [float(v) for v in
                                        _crecimiento(reconciliado, ultimo)[cod].to_numpy()],
                    "per_capita": ([float(per_capita.loc[a, cod]) for a in anios]
                                   if per_capita is not None else None),
                },
                "intervalo_ancho_pp": [float(ancho_pp.loc[a, cod]) for a in anios],
            }
            for cod in marco.departamentos
        },
    }


def write(destino: Path | None = None, **kwargs) -> Path:
    destino = destino or DESTINO
    destino.parent.mkdir(parents=True, exist_ok=True)
    contenido = _limpia(construir(**kwargs))
    destino.write_text(json.dumps(contenido, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino
