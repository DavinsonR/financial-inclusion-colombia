"""De dónde sale el ancla nacional y qué hay que saber de ella (ADR-021 decisión 4).

Por orden de preferencia: Banrep (EME), MinHacienda (MFMP) y FMI (WEO). Solo el WEO tiene
API abierta y multianual, así que es el que se descarga; los otros dos se transcriben a mano
en `config/forecast.yaml` (la EME, del Excel de Banrep: ADR-021, adenda 1).

**El WEO sale de la API SDMX del FMI y se fecha por su publicación (B-091).** Hasta
septiembre de 2026 salía de DBnomics, que dejó de actualizarlo en abril de 2025, y se
fechaba por el día en que DBnomics lo indexó: re-correr no renovaba nada y la fecha no era
la del emisor.

**Advertencia sobre el WEO que conviene no perder.** En sus últimos años la senda converge a un
valor de mediano plazo que se repite (en el WEO de abril de 2026: 2,62 % en 2028, 2,74 % en 2029
y 2,76 % en 2030 y 2031): ese tramo no es un pronóstico año a año. ADR-021 fija el punto de equilibrio del
anclaje en unos 3,5 puntos de error del consenso, y una constante de mediano plazo puede
alejarse de eso sin avisar.

**Un ancla también caduca.** Si su fecha de corte tiene más de `ANTIGUEDAD_MAXIMA_MESES`,
`cargar` emite un aviso visible y `vigencia` lo deja escrito en `resultados.json`
(`ancla.antiguedad_meses`, `ancla.vencida`, `ancla.aviso`). No falla: un ancla vieja con su
edad a la vista es preferible a no publicar, pero nadie debe poder leer el mapa sin saberlo.
La solución no es tocar este módulo, es transcribir la EME vigente en `config/forecast.yaml`.
"""

from __future__ import annotations

import json
import math
import urllib.request
import warnings
from datetime import date
from pathlib import Path

from iif import config
from iif.forecast.reconcile import Ancla

# Crecimiento real del PIB de Colombia en el WEO, desde la API SDMX del propio FMI. Una serie y
# una llamada por corrida: no es la descarga masiva automatizada que los términos del FMI vedan.
URL_WEO = ("https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO/COL.NGDP_RPCH.A"
           "?startPeriod={desde}&endPeriod={hasta}")
PAGINA_WEO = "https://data.imf.org/en/datasets/IMF.RES:WEO"
CONFIG_FORECAST = config.CONFIG_DIR / "forecast.yaml"
# Más de seis meses es más de dos ediciones del Informe de Política Monetaria y de dos EME con
# pregunta por el PIB (enero, abril, julio y octubre):
# el consenso ya se ha revisado y el ancla no lo dice.
ANTIGUEDAD_MAXIMA_MESES = 6
DIAS_POR_MES = 365.25 / 12


class AnclaVencida(UserWarning):
    """La fecha de corte del ancla supera la antigüedad máxima."""


def antiguedad_meses(fecha_corte: str, hoy: date | None = None) -> float | None:
    """Meses entre la fecha de corte del ancla y hoy; `None` si la fecha no se puede leer."""
    try:
        corte = date.fromisoformat(str(fecha_corte)[:10])
    except ValueError:
        return None
    return ((hoy or date.today()) - corte).days / DIAS_POR_MES


def vigencia(ancla: Ancla, hoy: date | None = None) -> dict:
    """Edad del ancla y, si pasa del máximo, el aviso que viaja con ella a `resultados.json`."""
    meses = antiguedad_meses(ancla.fecha_corte, hoy)
    vencida = meses is None or meses > ANTIGUEDAD_MAXIMA_MESES
    aviso = None
    if vencida:
        edad = "de fecha ilegible" if meses is None else f"con {meses:.0f} meses de antigüedad"
        aviso = (f"El ancla ({ancla.fuente}, corte {ancla.fecha_corte}) está {edad}; el máximo es "
                 f"{ANTIGUEDAD_MAXIMA_MESES}. Transcribe en config/forecast.yaml la última EME "
                 "con PIB (enero, abril, julio u octubre).")
    return {"antiguedad_meses": None if meses is None else round(meses, 1),
            "antiguedad_maxima_meses": ANTIGUEDAD_MAXIMA_MESES,
            "vencida": vencida, "aviso": aviso}


def _avisar_si_vencida(ancla: Ancla) -> Ancla:
    estado = vigencia(ancla)
    if estado["vencida"]:
        warnings.warn(estado["aviso"], AnclaVencida, stacklevel=3)
    return ancla


def senda_weo(bruto: dict) -> tuple[dict[int, float], str]:
    """Senda y fecha de publicación a partir de una respuesta SDMX-JSON del WEO.

    La fecha es el `PUBLICATION_DATE` del conjunto: el día en que el FMI publicó esa edición,
    no el de ninguna copia. Sin ella el ancla no se puede fechar y se rechaza.
    """
    estructura = bruto["structure"]
    periodos = [v["id"] for v in estructura["dimensions"]["observation"][0]["values"]]
    series = bruto["dataSets"][0]["series"]
    if not series:
        raise RuntimeError("el WEO no devolvió la serie de Colombia")
    obs = next(iter(series.values()))["observations"]
    # La clave de cada observación es el índice del período, no su posición en el diccionario.
    senda = {}
    for i, v in obs.items():
        if v and v[0] is not None and math.isfinite(float(v[0])):
            senda[int(periodos[int(i)])] = float(v[0])

    fecha = None
    for atributo in estructura.get("attributes", {}).get("dataSet", []):
        if atributo["id"] == "PUBLICATION_DATE" and atributo.get("values"):
            valor = atributo["values"][0]
            fecha = valor.get("id") or valor.get("name") or valor.get("value")
    try:
        date.fromisoformat(str(fecha)[:10])
    except ValueError:
        fecha = None
    if not fecha:
        raise RuntimeError("el WEO no trae un PUBLICATION_DATE legible: sin fecha no hay ancla")
    return senda, str(fecha)[:10]


def desde_weo(anios: list[int], timeout: int = 40) -> Ancla:
    """Baja la senda de crecimiento real del WEO vigente para Colombia, de la API del FMI."""
    url = URL_WEO.format(desde=min(anios), hasta=max(anios))
    peticion = urllib.request.Request(url, headers={"User-Agent": "iif-forecast/0.1",
                                                    "Accept": "application/json"})
    with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
        bruto = json.load(respuesta)

    senda, publicado = senda_weo(bruto)
    faltan = [a for a in anios if a not in senda]
    if faltan:
        raise KeyError(f"el WEO no cubre {faltan}")
    # La cita que piden los términos de datos del FMI: base, edición y enlace (B-092).
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
    edicion = date.fromisoformat(publicado)
    fuente = (f"Fondo Monetario Internacional, World Economic Outlook Database, "
              f"{meses[edicion.month - 1]} de {edicion.year}, {PAGINA_WEO}, "
              f"consultada el {date.today().isoformat()}")
    return Ancla(fuente=fuente,
                 fecha_corte=publicado,
                 crecimiento={a: round(senda[a], 2) for a in anios})


def desde_config(anios: list[int], escenario: str = "central",
                 ruta: Path | None = None) -> Ancla:
    """Lee un ancla transcrita a mano en `config/forecast.yaml`.

    Es la vía para la EME de Banrep (Excel mensual `res_inf_<mes><año>.xlsx`, hoja PIB) y para
    el MFMP (PDF), que no tienen API. El bloque tiene que declarar fuente y fecha de corte: sin
    eso no se carga.
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
            return _avisar_si_vencida(desde_config(anios, escenario))
        except (KeyError, ValueError):
            if escenario != "central":
                raise
    if sin_red:
        raise RuntimeError("no hay ancla en config/forecast.yaml y se pidió no usar la red")
    return _avisar_si_vencida(desde_weo(anios))
