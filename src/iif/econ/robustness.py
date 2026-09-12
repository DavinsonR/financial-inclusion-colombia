"""Lo que sostiene o tumba el coeficiente: inferencia con pocos clústeres y un placebo.

Con 33 departamentos, el error estándar agrupado descansa en una asintótica que no se cumple. Las dos
piezas de aquí atacan ese problema desde lados distintos: el bootstrap salvaje corrige la inferencia bajo
la nula, y el placebo por permutación construye la distribución del coeficiente cuando por diseño no hay
nada que encontrar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

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
) -> dict:
    """Bootstrap salvaje por clúster con la nula impuesta (Cameron, Gelbach y Miller, 2008).

    Se estima el modelo restringido —sin la variable de interés—, y cada réplica reasigna al residuo de
    cada **departamento entero** un signo de Rademacher. Imponer la nula es lo que da al procedimiento su
    buen comportamiento con pocos clústeres; remuestrear sin imponerla devuelve intervalos demasiado
    estrechos, que es el error que este bootstrap existe para no cometer.
    """
    controls = list(controls or [])
    cols = [y, x, *controls]
    datos = df.dropna(subset=[*cols, unidad, tiempo]).reset_index(drop=True)
    Z = demean_two_way(datos, cols, unidad, tiempo)
    yv, Xv = Z[:, 0], Z[:, 1:]

    def beta_de(objetivo: np.ndarray) -> np.ndarray:
        return np.linalg.lstsq(Xv, objetivo, rcond=None)[0]

    b = beta_de(yv)
    resid = yv - Xv @ b
    gl = max(len(yv) - Xv.shape[1], 1)
    xtx_inv = np.linalg.pinv(Xv.T @ Xv)
    se = float(np.sqrt(float(resid @ resid) / gl * xtx_inv[0, 0]))
    t_obs = float(b[0] / se) if se > 0 else float("nan")

    # modelo restringido: se quita la variable de interés y se guarda su residuo
    X_r = Xv[:, 1:] if Xv.shape[1] > 1 else np.zeros((len(yv), 0))
    if X_r.shape[1]:
        b_r = np.linalg.lstsq(X_r, yv, rcond=None)[0]
        resid_r = yv - X_r @ b_r
        ajuste_r = X_r @ b_r
    else:
        resid_r, ajuste_r = yv.copy(), np.zeros_like(yv)

    grupos = datos[unidad].to_numpy()
    claves = np.unique(grupos)
    rng = np.random.default_rng(semilla)
    ts = np.empty(replicas)
    for k in range(replicas):
        signos = rng.choice([-1.0, 1.0], size=claves.size)
        peso = np.ones_like(yv)
        for s, clave in zip(signos, claves, strict=True):
            peso[grupos == clave] = s
        y_b = ajuste_r + resid_r * peso
        b_b = beta_de(y_b)
        r_b = y_b - Xv @ b_b
        se_b = float(np.sqrt(float(r_b @ r_b) / gl * xtx_inv[0, 0]))
        ts[k] = b_b[0] / se_b if se_b > 0 else np.nan

    validos = ts[np.isfinite(ts)]
    p = (np.sum(np.abs(validos) >= abs(t_obs)) + 1) / (validos.size + 1)
    return {
        "coef": float(b[0]),
        "t_observado": t_obs,
        "p_bootstrap": float(p),
        "replicas": int(validos.size),
        "clusteres": int(claves.size),
        "n": int(len(yv)),
    }


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
