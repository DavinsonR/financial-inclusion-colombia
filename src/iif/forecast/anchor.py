"""De dónde sale el ancla nacional y qué hay que saber de ella (ADR-021 decisión 4).

Por orden de preferencia: Banrep (EME), MinHacienda (MFMP) y FMI (WEO). Solo el WEO tiene
API abierta y multianual, así que es el que se descarga; los otros dos se cargan a mano
desde `config/forecast.yaml` cuando el autor los transcriba de sus PDF.

**Advertencia sobre el WEO que conviene no perder.** Su senda para Colombia repite el mismo
número de 2027 en adelante (2,76 % hasta 2030): es el valor de convergencia de mediano
plazo del Fondo, no un pronóstico año a año. A horizonte 1 el ancla es informativa; a
horizontes 2 y 3 es, en la práctica, una constante. ADR-021 fija el punto de equilibrio del
anclaje en unos 3,5 puntos de error del consenso, y una constante de mediano plazo puede
alejarse de eso sin avisar.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from iif import config
from iif.forecast.reconcile import Ancla

SERIE_WEO = "IMF/WEO:latest/COL.NGDP_RPCH"
URL_DBNOMICS = "https://api.db.nomics.world/v22/series/{sid}?observations=1"
CONFIG_FORECAST = config.CONFIG_DIR / "forecast.yaml"


def desde_weo(anios: list[int], timeout: int = 40) -> Ancla:
    """Baja la senda de crecimiento real del WEO para Colombia."""
    url = URL_DBNOMICS.format(sid=SERIE_WEO)
    peticion = urllib.request.Request(url, headers={"User-Agent": "iif-forecast/0.1"})
    with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
        bruto = json.load(respuesta)

    docs = bruto.get("series", {}).get("docs", [])
    if not docs:
        raise RuntimeError(f"el WEO no devolvió datos para {SERIE_WEO}")
    doc = docs[0]
    senda = {int(p): float(v) for p, v in zip(doc["period"], doc["value"], strict=False)
             if v is not None}

    faltan = [a for a in anios if a not in senda]
    if faltan:
        raise KeyError(f"el WEO no cubre {faltan}")
    corte = doc.get("indexed_at", doc.get("updated_at", "desconocida"))
    return Ancla(fuente="FMI, World Economic Outlook (via DBnomics)",
                 fecha_corte=str(corte)[:10],
                 crecimiento={a: senda[a] for a in anios})


def desde_config(anios: list[int], escenario: str = "central",
                 ruta: Path | None = None) -> Ancla:
    """Lee un ancla transcrita a mano en `config/forecast.yaml`.

    Es la vía para la EME de Banrep y para el MFMP, que solo publican PDF. El bloque tiene
    que declarar fuente y fecha de corte: sin eso no se carga.
    """
    ruta = ruta or CONFIG_FORECAST
    cfg = config.load_yaml(ruta)
    anclas = cfg.get("anclas", {})
    if escenario not in anclas:
        raise KeyError(f"{ruta.name} no define el escenario '{escenario}'")
    bloque = anclas[escenario]
    for campo in ("fuente", "fecha_corte", "crecimiento"):
        if campo not in bloque:
            raise KeyError(f"el ancla '{escenario}' no declara '{campo}'")
    senda = {int(k): float(v) for k, v in bloque["crecimiento"].items()}
    faltan = [a for a in anios if a not in senda]
    if faltan:
        raise KeyError(f"el ancla '{escenario}' no cubre {faltan}")
    return Ancla(fuente=str(bloque["fuente"]), fecha_corte=str(bloque["fecha_corte"]),
                 crecimiento={a: senda[a] for a in anios}, escenario=escenario)


def cargar(anios: list[int], escenario: str = "central", *, sin_red: bool = False) -> Ancla:
    """El ancla del escenario pedido: primero `config/forecast.yaml`, si no el WEO.

    El orden es deliberado. Un ancla transcrita de Banrep es preferible a la del WEO
    (ADR-021), y el WEO queda como red de seguridad para que el módulo corra sin que nadie
    tenga que transcribir nada.
    """
    if CONFIG_FORECAST.exists():
        try:
            return desde_config(anios, escenario)
        except (KeyError, ValueError):
            if escenario != "central":
                raise
    if sin_red:
        raise RuntimeError("no hay ancla en config/forecast.yaml y se pidió no usar la red")
    return desde_weo(anios)
