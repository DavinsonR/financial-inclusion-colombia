"""Corre la batería completa y deja un solo JSON con todo lo que la página publica.

El orden importa y es el del argumento: primero la especificación base y el contraste que enseña de dónde
sale el coeficiente, después los diagnósticos que dicen si la inferencia vale, después los diseños
complementarios, y al final la robustez y los contrastes que pidió el referee (ADR-024). Cada cifra
publicada sale de este archivo, no de un cuaderno (R-09).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from iif import config
from iif.econ import denominador, designs, diagnostics, inference, power, robustness
from iif.econ.frame import discrepancia_va, estimation_sample, load_frame, load_serie_larga
from iif.econ.panel import by_dimension, in_changes, pooled_entity_only, residuals_wide, two_way_fe
from iif.index.build import load_contract

Y = "crecimiento"
# El regresor de la especificación base. `REZAGO_INDICE` decide si se usa el índice del mismo año o el del
# anterior, y es la única fuente de verdad de esa elección: el texto publicado la cita desde aquí en vez de
# describirla por su cuenta, que es exactamente el error de B-069. Con el denominador rezagado de ADR-017,
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
# Año de referencia del estudio de eventos y del contraste de tendencias previas: el último antes del choque.
ANIO_REFERENCIA = 2019
# Las condiciones iniciales que sustituyen al rezago del ingreso en la fila sin sesgo de Nickell (ADR-024).
CONDICIONES_INICIALES = {"log_pib_2018": "log_pib", "urbanizacion_2018": "tasa_urbanizacion"}


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


def _p_t(coef: float, se: float, unidades: int) -> float:
    """p de dos colas contra t(G − 1), la referencia con errores agrupados (ADR-024)."""
    if not (np.isfinite(se) and se > 0):
        return float("nan")
    return float(2 * stats.t.sf(abs(coef / se), unidades - 1))


def _fila(est, clave: str, datos: pd.DataFrame, y: str, x: str, controles: list[str], replicas: int, **kw) -> dict:
    """Una estimación como fila publicable: con su clave, su p contra t(G − 1) y su bootstrap."""
    fila = est.as_dict()
    fila["clave"] = clave
    fila["p_t_g1"] = _p_t(est.coef, est.se, est.unidades)
    boot = robustness.wild_cluster_bootstrap(datos, y, x, controles, replicas=replicas, **kw)
    fila["p_bootstrap"] = boot["p_bootstrap"]
    return fila


def _con_condiciones_iniciales(marco: pd.DataFrame, muestra: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Cada condición de 2018 × cada año de la muestra salvo el primero (el resto lo absorben los efectos)."""
    datos = muestra.copy()
    columnas = []
    anios = sorted(datos["anio"].unique())[1:]
    for nombre, variable in CONDICIONES_INICIALES.items():
        inicial = designs.exposicion_inicial(marco, variable, ANIO_BASE)
        valor = datos["dpto_ccdgo"].map(inicial)
        for a in anios:
            col = f"{nombre}_x_{a}"
            datos[col] = valor * (datos["anio"] == a).astype(float)
            columnas.append(col)
    return datos.dropna(subset=columnas).reset_index(drop=True), columnas


def run(db: str | None = None, *, replicas: int = 999, placebos: int = 499) -> dict:
    marco = load_frame(db)
    muestra = estimation_sample(marco, Y, X, CONTROLES)

    base, res_base = two_way_fe(muestra, Y, X, CONTROLES, nombre="base: efectos de entidad y tiempo")
    dk, _ = two_way_fe(muestra, Y, X, CONTROLES, errores="driscoll-kraay", nombre="base con Driscoll-Kraay")
    solo_entidad, _ = pooled_entity_only(muestra, Y, X, CONTROLES)

    cambios_muestra = estimation_sample(marco, Y, f"d_{INDICE}", CONTROLES)
    cambios, _ = in_changes(cambios_muestra, Y, INDICE, CONTROLES)

    # --- Inferencia del coeficiente base (ADR-024, punto 1) -------------------------------------------
    escala = power.escala_del_regresor(muestra, X, CONTROLES)
    margenes = power.margenes_en_unidades(escala["de_identificante"])
    wild = robustness.wild_cluster_bootstrap(
        muestra, Y, X, CONTROLES, replicas=replicas, invertir=True, margenes=margenes
    )
    wild_webb = robustness.wild_cluster_bootstrap(
        muestra, Y, X, CONTROLES, replicas=replicas, invertir=True, margenes=margenes, pesos="webb"
    )
    potencia = power.resumen(base, muestra, X, CONTROLES, bootstrap=wild)
    potencia["bootstrap_webb"] = power.resumen(base, muestra, X, CONTROLES, bootstrap=wild_webb)["bootstrap"]

    # --- Filas principales (ADR-024, puntos 3 y 6) -----------------------------------------------------
    indices_denominador = denominador.indices(db)
    marco_den = marco.merge(indices_denominador, on=["dpto_ccdgo", "anio"], how="left")
    muestra_fija = estimation_sample(marco_den, Y, "iif_fijo", CONTROLES)
    fijo, _ = two_way_fe(muestra_fija, Y, "iif_fijo", CONTROLES, nombre="coprincipal: denominador fijo (2018)")

    muestra_ci, cols_ci = _con_condiciones_iniciales(marco, estimation_sample(marco, Y, X, ["tasa_urbanizacion"]))
    sin_nickell, _ = two_way_fe(
        muestra_ci, Y, X, ["tasa_urbanizacion", *cols_ci],
        nombre="sin Nickell: condiciones iniciales de 2018 × año en lugar del rezago del ingreso",
    )
    sin_nickell.controles = ["tasa_urbanizacion", "log_pib_2018 × año", "urbanizacion_2018 × año"]
    sin_nickell.coeficientes = {k: v for k, v in sin_nickell.coeficientes.items() if k in (X, "const")}
    muestra_sc = estimation_sample(marco, Y, X, [])
    sin_controles, _ = two_way_fe(muestra_sc, Y, X, [], nombre="sin controles")

    principales = [
        _fila(base, "base", muestra, Y, X, CONTROLES, replicas),
        _fila(fijo, "denominador_fijo", muestra_fija, Y, "iif_fijo", CONTROLES, replicas),
        _fila(solo_entidad, "solo_entidad", muestra, Y, X, CONTROLES, replicas, efectos_tiempo=False),
        _fila(cambios, "cambios", cambios_muestra, Y, f"d_{INDICE}", CONTROLES, replicas),
        _fila(sin_nickell, "condiciones_iniciales", muestra_ci, Y, X, ["tasa_urbanizacion", *cols_ci], replicas),
        _fila(sin_controles, "sin_controles", muestra_sc, Y, X, [], replicas),
    ]

    cce, _ = designs.cce_pooled(muestra, Y, X, CONTROLES)
    exposicion = designs.exposicion_inicial(marco, INDICE, ANIO_BASE)
    ss, datos_ss = designs.exposicion_por_adopcion(muestra, Y, X, exposicion, CONTROLES)

    # El diseño de exposición inicial con efectos de tiempo identifica una pendiente diferencial de los
    # departamentos más expuestos. Cualquier característica inicial correlacionada con el índice —ingreso,
    # urbanización— produciría la misma pendiente si lo que hay es recuperación desigual y no inclusión. Se
    # contrasta con esas exposiciones de placebo y con la carrera de caballos.
    nacional = muestra.groupby("anio")[INDICE].mean()
    ss_placebos = []
    for variable, etiqueta in (
        ("log_pib", "ingreso inicial"),
        ("tasa_urbanizacion", "urbanizacion inicial"),
    ):
        exp_alt = designs.exposicion_inicial(marco, variable, ANIO_BASE)
        est_alt, _ = designs.exposicion_por_adopcion(muestra, Y, X, exp_alt, CONTROLES, nacional=nacional)
        est_alt.nombre = f"placebo de exposición inicial: {etiqueta} × adopción"
        ss_placebos.append(est_alt.as_dict())
    carrera = _carrera_exposicion(
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
    placebo = robustness.placebo_permutacion(muestra, Y, X, CONTROLES, replicas=placebos)
    # El modo antiguo se conserva al lado: su nube es mucho mas estrecha porque destruye la correlacion
    # serial del regresor, y verlas juntas es lo que explica por que sus p no son comparables (B-074).
    placebo_anio = robustness.placebo_permutacion(
        muestra, Y, X, CONTROLES, replicas=placebos, modo="dentro_del_anio"
    )
    dimensiones = by_dimension(marco.dropna(subset=[Y, *CONTROLES]), Y, CONTROLES)

    sensibilidad = []
    for alterno, etiqueta in (("iif_sensibilidad_pca", "PCA"), ("iif_sensibilidad_sarma", "distancia tipo Sarma")):
        sub = estimation_sample(marco, Y, alterno, CONTROLES)
        if sub.empty:
            continue
        est, _ = two_way_fe(sub, Y, alterno, CONTROLES, nombre=f"índice alternativo: {etiqueta}")
        sensibilidad.append(est.as_dict())

    no_linealidad = _no_linealidad(muestra, replicas)
    larga = load_serie_larga(db)

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
                "anio_referencia": ANIO_REFERENCIA,
                "unidades": int(muestra["dpto_ccdgo"].nunique()),
                "periodos": sorted(int(a) for a in muestra["anio"].unique()),
                "n": int(len(muestra)),
            },
            "principales": principales,
            # Driscoll-Kraay con T = 7 no es creíble como inferencia (ADR-024): se sigue calculando y se
            # publica como nota, no como fila de igual rango.
            "notas": {"driscoll_kraay": dk.as_dict()},
            # Qué efectos descarta este diseño y cuáles no puede descartar (ADR-018, ADR-024).
            "potencia": potencia,
            "dimensiones": [d.as_dict() for d in dimensiones],
            "unidades_naturales": _unidades_naturales(dimensiones),
            "sensibilidad_indice": sensibilidad,
            "ventanas": _ventanas(muestra),
            "no_linealidad": no_linealidad,
            "disenos": [cce.as_dict(), ss.as_dict(), espacial.as_dict()],
            "exposicion_inicial_contraste": {
                "placebos": ss_placebos,
                "carrera": carrera,
                "inferencia": _inferencia_de_la_exposicion(datos_ss, replicas, placebos),
            },
            "estudio_eventos": eventos.to_dict(orient="records"),
            "tendencias_previas": _tendencias_previas(marco, larga, exposicion, replicas),
            "dependiente_sin_bk": _dependiente_limpia(marco, replicas, db),
            "causalidad_inversa": _causalidad_inversa(marco_den, replicas),
            "denominador": _denominador(marco_den, replicas),
            "aronow_samii": _aronow_samii(muestra, marco),
            "familia_holm": _familia_holm(base, dimensiones, ss, eventos, no_linealidad, len(exposicion)),
            "convergencia": _convergencia(larga),
            "diagnosticos": {"pesaran_cd": cd, "cips": raiz, "moran_por_anio": moran_por_anio},
            "robustez": {
                "wild_cluster_bootstrap": wild,
                "wild_cluster_bootstrap_webb": wild_webb,
                "placebo_permutacion": placebo,
                "placebo_permutacion_dentro_del_anio": placebo_anio,
                "jackknife": _jackknife(muestra),
            },
        }
    )


def _carrera_exposicion(
    muestra: pd.DataFrame, exp_indice: pd.Series, rivales: dict[str, pd.Series], nacional: pd.Series
) -> list[dict]:
    """El índice contra cada exposición rival en la misma ecuación, y contra todas a la vez.

    Antes solo se corría contra el ingreso inicial, que es el rival que pierde. La urbanización inicial es
    la que gana su propio placebo, así que es la que hay que meter dentro. Correr la carrera únicamente
    contra el rival débil no es un contraste.
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
    y eso solo lo dicen los residuos. Publicar la primera y afirmar con ella lo segundo fue B-068; van las
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
    porque con 33 clústeres el p agrupado no basta, y entra en la familia de Holm (ADR-024).
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
            "se_cuadratico": float(res.std_errors[f"{X}_cuadrado"]),
            "p_cuadratico": float(res.pvalues[f"{X}_cuadrado"]),
            "p_bootstrap_cuadratico": boot["p_bootstrap"],
            "vertice": float(-lineal / (2 * cuadratico)) if cuadratico != 0 else float("nan"),
            "nota": "un contraste más en la familia; su p ajustado por Holm está en familia_holm",
        }
    )
    if np.isfinite(salida["vertice"]):
        salida["fraccion_bajo_el_vertice"] = float((muestra[X] < salida["vertice"]).mean())
    return salida


def _inferencia_de_la_exposicion(datos_ss: pd.DataFrame, replicas: int, placebos: int) -> dict:
    """El bootstrap y el placebo aplicados al diseño de exposición inicial, el único coeficiente con señal.

    La inferencia exigente se le pide al resultado que afirma algo, no solo al nulo.
    """
    wild = robustness.wild_cluster_bootstrap(datos_ss, Y, "shift_share", CONTROLES, replicas=replicas)
    wild_webb = robustness.wild_cluster_bootstrap(
        datos_ss, Y, "shift_share", CONTROLES, replicas=replicas, pesos="webb"
    )
    placebo = robustness.placebo_permutacion(datos_ss, Y, "shift_share", CONTROLES, replicas=placebos)
    return {"wild_cluster_bootstrap": wild, "wild_cluster_bootstrap_webb": wild_webb, "placebo_permutacion": placebo}


def _tendencias_previas(marco: pd.DataFrame, larga: pd.DataFrame, exposicion: pd.Series, replicas: int) -> dict:
    """Estudio de eventos 2006–2025 con la prueba conjunta de los coeficientes previos (ADR-024, A2).

    La dependiente principal es el crecimiento del PIB real total, que es la serie que el DANE publica
    completa desde 2005; al lado va el per cápita con la población implícita. Cada una se repite con la
    urbanización de 2018 × año dentro, que es la condición inicial que gana el placebo de la exposición.
    """
    urbanizacion = designs.exposicion_inicial(marco, "tasa_urbanizacion", ANIO_BASE)
    salida = {}
    for dep in ("crecimiento_pib_total", "crecimiento_pib_pc"):
        for etiqueta, controles in (("sin_controles", None), ("con_urbanizacion_2018", {"urb2018": urbanizacion})):
            salida[f"{dep}__{etiqueta}"] = designs.tendencias_previas(
                larga, dep, exposicion, anio_referencia=ANIO_REFERENCIA, anio_evento=ANIO_EVENTO,
                controles_iniciales=controles, replicas=replicas,
            )
    return salida


def _dependiente_limpia(marco: pd.DataFrame, replicas: int, db: str | None) -> dict:
    """La base con el valor agregado sin minería (B) ni actividades financieras (K) (ADR-024, A4)."""
    from iif.econ.frame import SIN_SECCIONES

    filas = []
    for columna, fuera in SIN_SECCIONES.items():
        datos = estimation_sample(marco, columna, X, CONTROLES)
        est, _ = two_way_fe(datos, columna, X, CONTROLES, nombre=f"dependiente sin {' ni '.join(fuera)}")
        fila = _fila(est, columna, datos, columna, X, CONTROLES, replicas)
        fila["secciones_fuera"] = list(fuera)
        filas.append(fila)
    return {"filas": filas, "no_aditividad": discrepancia_va(db)}


def _causalidad_inversa(marco: pd.DataFrame, replicas: int) -> dict:
    """Adelanto del índice y Granger inverso (ADR-024, A6).

    Si el crédito responde al crecimiento esperado, el índice de mañana "explica" el crecimiento de hoy, y
    el crecimiento de ayer explica el cambio del índice de hoy. Ninguno de los dos prueba causalidad; los
    dos dicen si el orden temporal que la base supone es el que los datos muestran.
    """
    adelanto_x = f"{INDICE}_adelanto"
    d1 = estimation_sample(marco, Y, adelanto_x, CONTROLES)
    adelanto, _ = two_way_fe(d1, Y, adelanto_x, CONTROLES, nombre="adelanto: crecimiento_t sobre índice_t+1")
    d2 = estimation_sample(marco, Y, adelanto_x, [*CONTROLES, INDICE])
    adelanto_con, _ = two_way_fe(
        d2, Y, adelanto_x, [*CONTROLES, INDICE], nombre="adelanto con el índice contemporáneo dentro"
    )
    d3 = estimation_sample(marco, f"d_{INDICE}", "crecimiento_rezago", [])
    granger, _ = two_way_fe(
        d3, f"d_{INDICE}", "crecimiento_rezago", [], nombre="Granger inverso: Δíndice_t sobre crecimiento_t−1"
    )
    # Con el denominador rezagado, el índice de t lleva el producto de t − 1 abajo: Δíndice_t contiene
    # mecánicamente el crecimiento de t − 1 con signo negativo. El Granger inverso se repite con el índice
    # de denominador fijo, que no lo contiene.
    marco_f = marco.sort_values(["dpto_ccdgo", "anio"]).copy()
    marco_f["d_iif_fijo"] = marco_f.groupby("dpto_ccdgo", sort=False)["iif_fijo"].diff()
    d4 = estimation_sample(marco_f, "d_iif_fijo", "crecimiento_rezago", [])
    granger_fijo, _ = two_way_fe(
        d4, "d_iif_fijo", "crecimiento_rezago", [],
        nombre="Granger inverso con el índice de denominador fijo",
    )
    return {
        "granger_inverso_denominador_fijo": _fila(
            granger_fijo, "granger_inverso_denominador_fijo", d4, "d_iif_fijo", "crecimiento_rezago", [], replicas
        ),
        "adelanto": _fila(adelanto, "adelanto", d1, Y, adelanto_x, CONTROLES, replicas),
        "adelanto_con_contemporaneo": _fila(
            adelanto_con, "adelanto_con_contemporaneo", d2, Y, adelanto_x, [*CONTROLES, INDICE], replicas
        ),
        "granger_inverso": _fila(granger, "granger_inverso", d3, f"d_{INDICE}", "crecimiento_rezago", [], replicas),
    }


def _denominador(marco_den: pd.DataFrame, replicas: int) -> dict:
    """El índice real y el placebo de solo-denominador con cada denominador (ADR-017, ADR-024 A7).

    El placebo se estima con los controles de la base y sin ellos: con el rezago del ingreso dentro, un
    placebo que es 1 / producto rezagado es casi colineal con el control, y los dos números juntos dicen
    cuánto del resultado es esa colinealidad.
    """
    filas = []
    ventanas = {"completa": marco_den, "sin 2020 y 2021": marco_den[~marco_den["anio"].isin([2020, 2021])]}
    for modo in denominador.MODOS:
        for tipo in ("iif", "placebo"):
            col = f"{tipo}_{modo}"
            for ventana, datos_v in ventanas.items():
                for con_controles in (True, False):
                    ctl = CONTROLES if con_controles else []
                    datos = estimation_sample(datos_v, Y, col, ctl)
                    fila = {"indice": tipo, "denominador": modo, "ventana": ventana, "controles": list(ctl)}
                    dentro = datos.groupby("dpto_ccdgo")[col].std(ddof=0).max() if len(datos) else 0.0
                    if datos.empty or not dentro > 1e-12:
                        fila.update({"estimable": False, "motivo": "sin variación dentro de la unidad"})
                        filas.append(fila)
                        continue
                    est, _ = two_way_fe(datos, Y, col, ctl)
                    fila.update(
                        {
                            "estimable": True,
                            "coef": est.coef,
                            "se": est.se,
                            "p": est.p,
                            "p_t_g1": _p_t(est.coef, est.se, est.unidades),
                            "n": est.n,
                        }
                    )
                    filas.append(fila)
    return {
        "placebo": "todos los numeradores congelados en su valor de 2018; el índice solo se mueve por sus denominadores",
        "filas": filas,
    }


def _aronow_samii(muestra: pd.DataFrame, marco: pd.DataFrame) -> dict:
    """Qué departamentos identifican el coeficiente y cuánto pesan en la población (ADR-024, A8)."""
    pesos = power.pesos_aronow_samii(muestra, X, CONTROLES)
    poblacion = marco.loc[marco["anio"] == ANIO_BASE].set_index("dpto_ccdgo")["poblacion_total"].astype(float)
    nombres = marco.drop_duplicates("dpto_ccdgo").set_index("dpto_ccdgo")["departamento"]
    tabla = pd.DataFrame({"peso": pesos})
    tabla["participacion_poblacion"] = poblacion.reindex(tabla.index) / poblacion.reindex(tabla.index).sum()
    tabla["departamento"] = nombres.reindex(tabla.index)
    tabla = tabla.sort_values("peso", ascending=False)

    ponderada_datos = muestra.copy()
    ponderada_datos["poblacion_2018"] = ponderada_datos["dpto_ccdgo"].map(poblacion)
    ponderada, _ = two_way_fe(
        ponderada_datos, Y, X, CONTROLES, pesos="poblacion_2018", nombre="base ponderada por población de 2018"
    )
    return {
        "por_departamento": [
            {"dpto_ccdgo": k, "departamento": f["departamento"], "peso": f["peso"],
             "participacion_poblacion": f["participacion_poblacion"]}
            for k, f in tabla.iterrows()
        ],
        "top5_peso": float(tabla["peso"].head(5).sum()),
        "top5_participacion_poblacion": float(tabla["participacion_poblacion"].head(5).sum()),
        # Unidades efectivas: 1 / Σ w². Con pesos iguales serían 33.
        "unidades_efectivas": float(1 / (tabla["peso"] ** 2).sum()),
        # Correlación entre lo que cada departamento aporta a la identificación y lo que pesa en la población.
        "correlacion_peso_poblacion": float(tabla["peso"].corr(tabla["participacion_poblacion"])),
        "ponderada_por_poblacion": {**ponderada.as_dict(), "p_t_g1": _p_t(ponderada.coef, ponderada.se, ponderada.unidades)},
    }


def _familia_holm(base, dimensiones, ss, eventos: pd.DataFrame, no_linealidad: dict, g_eventos: int) -> dict:
    """Holm sobre la familia de contrastes que el texto lee (ADR-024, A9).

    Doce contrastes: la base, las tres dimensiones, la exposición inicial, los seis años posteriores del
    estudio de eventos y el término cuadrático. Holm es válido bajo cualquier dependencia entre ellos; los p
    de partida son contra t(G − 1).
    """
    filas = [{"contraste": "base", "coef": base.coef, "se": base.se, "unidades": base.unidades}]
    filas += [
        {"contraste": d.nombre, "coef": d.coef, "se": d.se, "unidades": d.unidades} for d in dimensiones
    ]
    filas.append({"contraste": "exposición inicial", "coef": ss.coef, "se": ss.se, "unidades": ss.unidades})
    for _, e in eventos[~eventos["referencia"]].iterrows():
        if int(e["anio"]) >= ANIO_EVENTO:
            filas.append(
                {"contraste": f"estudio de eventos {int(e['anio'])}", "coef": float(e["coef"]),
                 "se": float(e["se"]), "unidades": g_eventos}
            )
    filas.append(
        {"contraste": "término cuadrático", "coef": no_linealidad["coef_cuadratico"],
         "se": no_linealidad["se_cuadratico"], "unidades": no_linealidad["unidades"]}
    )
    for f in filas:
        f["p"] = _p_t(f["coef"], f["se"], f["unidades"])
    m = len(filas)
    ajustado = inference.holm([f["p"] for f in filas])
    for f, a in zip(filas, ajustado, strict=True):
        f["p_holm"] = float(a)
        f["rechaza_holm_5"] = bool(a < 0.05)
    return {
        "metodo": "Holm (1979) sobre p de t(G − 1); Romano-Wolf no se estima (ADR-024, punto 8)",
        "contrastes": m,
        "filas": filas,
        "rechazos_holm_5": int(sum(f["rechaza_holm_5"] for f in filas)),
        "rechazos_sin_ajuste_5": int(sum(f["p"] < 0.05 for f in filas)),
    }


def _unidades_naturales(dimensiones) -> dict:
    """El β de acceso en puntos porcentuales por cada 10 corresponsales activos por 10.000 habitantes.

    La dimensión de acceso es una sola variable estandarizada con la media y la desviación congeladas en
    `config/index.yaml` (R-15): una unidad del subíndice es una desviación de corresponsales por 10.000
    habitantes en la ventana de calibración.
    """
    acceso = next(d for d in dimensiones if d.nombre.endswith("acceso"))
    congelados = load_contract()["pesos_congelados"]["acceso"]
    variable = congelados["variables"][0]
    desviacion = float(congelados["desviacion"][variable])
    carga = float(congelados["cargas"][variable])
    factor = 10 / desviacion * carga * 100
    return {
        "variable": variable,
        "desviacion_calibracion_por_10k": desviacion,
        "coef_acceso": acceso.coef,
        "pp_por_10_corresponsales_por_10k": acceso.coef * factor,
        "ic95_pp_por_10_corresponsales_por_10k": sorted([acceso.ic_bajo * factor, acceso.ic_alto * factor]),
        "p": acceso.p,
    }


def _convergencia(larga: pd.DataFrame) -> dict:
    """Sigma-convergencia y beta-convergencia incondicional, 2005–2025 (ADR-024, punto 11).

    La sigma es la dispersión del log del PIB real per cápita entre departamentos año a año. La beta es el
    corte transversal clásico: crecimiento medio anual del periodo sobre el log del nivel inicial, 33
    observaciones, con errores robustos (HC1). No es una estimación causal de nada; es el hecho estilizado
    contra el que se lee el término de convergencia condicional del panel.
    """
    sigma = (
        larga.groupby("anio")["log_pib_real_pc"].std(ddof=1).reset_index().rename(columns={"log_pib_real_pc": "de"})
    )
    anios = sorted(larga["anio"].unique())
    a0, a1 = int(anios[0]), int(anios[-1])
    ancho = larga.pivot_table(index="dpto_ccdgo", columns="anio", values="log_pib_real_pc")
    corte = pd.DataFrame({"inicial": ancho[a0], "final": ancho[a1]}).dropna()
    T = a1 - a0
    corte["g"] = (corte["final"] - corte["inicial"]) / T
    Xc = np.column_stack([np.ones(len(corte)), corte["inicial"].to_numpy()])
    yc = corte["g"].to_numpy()
    b, *_ = np.linalg.lstsq(Xc, yc, rcond=None)
    e = yc - Xc @ b
    n, k = Xc.shape
    xtx_inv = np.linalg.inv(Xc.T @ Xc)
    V = xtx_inv @ (Xc.T * e**2) @ Xc @ xtx_inv * n / (n - k)
    se = float(np.sqrt(V[1, 1]))
    beta = float(b[1])
    velocidad = float(-np.log(1 + beta * T) / T) if 1 + beta * T > 0 else float("nan")
    return {
        "sigma": [{"anio": int(r.anio), "de": float(r.de)} for r in sigma.itertuples()],
        "beta_incondicional": {
            "desde": a0,
            "hasta": a1,
            "coef": beta,
            "se_hc1": se,
            "p": float(2 * stats.t.sf(abs(beta / se), n - k)),
            "n": int(n),
            "velocidad_anual": velocidad,
            "r2": float(1 - (e @ e) / ((yc - yc.mean()) @ (yc - yc.mean()))),
        },
    }


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
