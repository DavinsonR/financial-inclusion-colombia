"""Lo que sostiene o tumba el coeficiente: inferencia con pocos clústeres y un placebo.

Con 33 departamentos, el error estándar agrupado descansa en una asintótica que no se cumple. Las dos
piezas de aquí atacan ese problema desde lados distintos: el bootstrap salvaje corrige la inferencia bajo
la nula, y el placebo por permutación construye la distribución del coeficiente cuando por diseño no hay
nada que encontrar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from iif.econ import inference
from iif.econ.panel import two_way_fe


def demean_two_way(
    datos: pd.DataFrame, cols: list[str], unidad: str, tiempo: str, *, tol: float = 1e-10, max_iter: int = 500
) -> np.ndarray:
    """Doble desviación respecto a medias de unidad y de tiempo, por proyecciones alternadas.

    En un panel balanceado basta restar una vez cada media; en uno desbalanceado —y este pierde tres
    filas— las dos proyecciones no conmutan y hay que alternarlas hasta que converjan. Sin esto el
    coeficiente del bootstrap no coincide con el del estimador, y la prueba compara dos cosas distintas.
    """
    X = np.array(datos[cols].to_numpy(dtype=float), copy=True)
    u = datos[unidad].to_numpy()
    t = datos[tiempo].to_numpy()
    grupos_u = {v: (u == v) for v in np.unique(u)}
    grupos_t = {v: (t == v) for v in np.unique(t)}
    for _ in range(max_iter):
        anterior = X.copy()
        for m in grupos_u.values():
            X[m] -= X[m].mean(axis=0)
        for m in grupos_t.values():
            X[m] -= X[m].mean(axis=0)
        if np.max(np.abs(X - anterior)) < tol:
            break
    return X


def wild_cluster_bootstrap(
    df: pd.DataFrame,
    y: str,
    x: str,
    controls: list[str] | None = None,
    *,
    replicas: int = 999,
    semilla: int = 20260907,
    unidad: str = "dpto_ccdgo",
    tiempo: str = "anio",
    pesos: str = "rademacher",
    invertir: bool = False,
    margenes: tuple[float, ...] = (),
    efectos_tiempo: bool = True,
) -> dict:
    """Bootstrap salvaje por clúster con la nula impuesta, studentizado con el CRVE (ADR-024).

    Se estima el modelo restringido —sin la variable de interés— y cada réplica reasigna al residuo de
    cada **departamento entero** un peso de media cero (Rademacher o Webb). El estadístico de cada réplica
    se studentiza con el error agrupado, igual que el observado: es lo que da al procedimiento el
    refinamiento asintótico que justifica usarlo con 33 clústeres (Cameron, Gelbach y Miller, 2008). La
    versión anterior studentizaba con el error homocedástico y no lo tenía.

    Con `invertir`, añade el intervalo del 95 % por inversión de la prueba; con `margenes`, el TOST
    bootstrap en cada margen (en unidades del regresor).
    """

    controls = list(controls or [])
    d = inference.diseno(df, y, [x, *controls], unidad=unidad, tiempo=tiempo, efectos_tiempo=efectos_tiempo)
    boot = inference.BootstrapUnCoeficiente(d, 0, replicas=replicas, semilla=semilla, pesos=pesos)
    salida = {
        "coef": boot.coef,
        "se_crve": boot.se,
        "t_observado": boot.t_observado(0.0),
        "p_bootstrap": boot.p_simetrico(0.0),
        "pesos": pesos,
        "studentizacion": "CRVE (CR1)",
        "replicas": int(replicas),
        "clusteres": int(d.G),
        "n": int(d.n),
    }
    if invertir:
        salida["ic95_bootstrap"] = boot.intervalo(0.95)
        salida["ic90_bootstrap"] = boot.intervalo(0.90)
    if margenes:
        salida["tost_bootstrap"] = [boot.tost(m) for m in margenes]
        salida["margen_minimo_bootstrap"] = boot.margen_minimo()
    return salida


def placebo_permutacion(
    df: pd.DataFrame,
    y: str,
    x: str,
    controls: list[str] | None = None,
    *,
    replicas: int = 499,
    semilla: int = 20260907,
    modo: str = "trayectoria",
    unidad: str = "dpto_ccdgo",
) -> dict:
    """Placebo: se reasigna el índice a departamentos que no son el suyo.

    Hay dos formas de barajar y no son intercambiables. `dentro_del_anio` permuta los valores entre
    departamentos dentro de cada año por separado; conserva la trayectoria nacional, pero al romper también
    la correlación serial del regresor dentro de cada departamento produce un regresor placebo mucho más
    ruidoso que el real, y por tanto una nube de coeficientes demasiado estrecha: su desviación queda muy por
    debajo del error estándar agrupado y el placebo rechaza donde el estimador no rechaza.

    `trayectoria` permuta la **serie completa** de cada departamento, que es la nula que interesa —la
    asignación territorial del índice es aleatoria— y conserva tanto la trayectoria nacional como la
    estructura serial de cada unidad. Es el modo por defecto; el otro se publica al lado como diagnóstico
    de cuánta variación destruye cada uno.
    """
    controls = list(controls or [])
    datos = df.dropna(subset=[y, x, *controls]).reset_index(drop=True)
    verdadero, _ = two_way_fe(datos, y, x, controls)
    rng = np.random.default_rng(semilla)
    coefs = np.empty(replicas)

    if modo == "trayectoria":
        claves = np.sort(datos[unidad].unique())
        # La serie de cada unidad, indexada por año, para poder reasignarla entera a otra unidad.
        series = {u: datos.loc[datos[unidad] == u, ["anio", x]].set_index("anio")[x] for u in claves}
    elif modo != "dentro_del_anio":
        raise ValueError(f"modo de placebo desconocido: {modo!r}")

    for k in range(replicas):
        barajado = datos.copy()
        if modo == "trayectoria":
            destino = dict(zip(claves, rng.permutation(claves), strict=True))
            barajado[x] = [
                series[destino[u]].get(a, np.nan)
                for u, a in zip(barajado[unidad], barajado["anio"], strict=True)
            ]
            barajado = barajado.dropna(subset=[x])
        else:
            barajado[x] = barajado.groupby("anio", sort=False)[x].transform(
                lambda s: s.to_numpy()[rng.permutation(len(s))]
            )
        est, _ = two_way_fe(barajado, y, x, controls)
        coefs[k] = est.coef

    p = (np.sum(np.abs(coefs) >= abs(verdadero.coef)) + 1) / (replicas + 1)
    return {
        "modo": modo,
        "coef_verdadero": verdadero.coef,
        "p_placebo": float(p),
        "media_placebos": float(np.mean(coefs)),
        "de_placebos": float(np.std(coefs, ddof=1)),
        "percentil_95": float(np.percentile(np.abs(coefs), 95)),
        "replicas": int(replicas),
    }
