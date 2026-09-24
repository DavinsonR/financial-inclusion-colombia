"""Construcción del índice: normalizar, estandarizar, un componente por dimensión y promediar (ADR-015)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from iif import config

# R-17 y ADR-015 (adenda): por debajo de este KMO las variables no comparten varianza común y el
# primer componente no resume nada. El contrato puede declararlo como `kmo_minimo`.
KMO_MINIMO = 0.5


@dataclass
class DimensionFit:
    """Parámetros congelados de una dimensión: cómo estandarizar y cómo combinar."""

    dimension: str
    metodo: str
    variables: list[str]
    media: dict[str, float]
    desviacion: dict[str, float]
    cargas: dict[str, float]
    varianza_explicada: float | None = None
    kmo: float | None = None
    bartlett_chi2: float | None = None
    bartlett_p: float | None = None


@dataclass
class IndexResult:
    scores: pd.DataFrame
    fits: dict[str, DimensionFit]
    implicitos: pd.DataFrame
    sensibilidad: pd.DataFrame
    correlacion_rangos: pd.DataFrame
    correlacion_rangos_detalle: pd.DataFrame = field(repr=False, default_factory=pd.DataFrame)
    varianza_intra: pd.DataFrame = field(repr=False, default_factory=pd.DataFrame)
    techo_sarma: dict[str, float] = field(default_factory=dict)
    normalizado: pd.DataFrame = field(repr=False, default_factory=pd.DataFrame)


def load_contract(path: Path | None = None) -> dict:
    return config.load_yaml(path or config.CONFIG_DIR / "index.yaml")


def contract_variables(contract: dict) -> list[str]:
    return [v["variable_id"] for d in contract["dimensiones"].values() for v in d["variables"]]


def denominador_de_producto(
    panel: pd.DataFrame, contract: dict, id_cols: tuple[str, ...], col_producto: str
) -> tuple[pd.Series, str]:
    """El producto que va al denominador de los montos (ADR-017).

    El mismo producto está en el denominador del índice y en el numerador de la dependiente: si el producto
    cae, el índice sube por aritmética y el crecimiento baja por definición. Un año de separación rompe esa
    simultaneidad sin renunciar a la lectura de profundidad financiera; el modo `fijo` la rompe del todo, a
    cambio de dejar de medir profundidad relativa al tamaño actual de la economía (B-070).
    """
    modo = str(contract.get("denominador") or "contemporaneo").lower()
    unidad, tiempo = id_cols[0], id_cols[1]
    producto = pd.to_numeric(panel[col_producto], errors="coerce")

    if modo == "contemporaneo":
        return producto, modo
    if modo == "rezagado":
        # El mart trae el rezago calculado sobre la serie completa del DANE, así que el primer año del
        # panel también tiene denominador. Si no estuviera, se calcula aquí y ese primer año se queda sin
        # índice, que es preferible a inventarlo (R-13).
        precalculado = f"{col_producto}_rezago"
        if precalculado in panel.columns:
            return pd.to_numeric(panel[precalculado], errors="coerce"), modo
        orden = panel.sort_values([unidad, tiempo]).index
        rezagado = producto.loc[orden].groupby(panel.loc[orden, unidad], sort=False).shift(1)
        return rezagado.reindex(panel.index), modo
    if modo == "fijo":
        anio_base = contract["calibracion"]["anio_desde"]
        base = pd.to_numeric(
            panel.loc[panel[tiempo] == anio_base].set_index(unidad)[col_producto], errors="coerce"
        )
        return panel[unidad].map(base[~base.index.duplicated()]), modo
    raise ValueError(f"denominador desconocido: {modo!r}; admite contemporaneo, rezagado o fijo")


def normalize_panel(
    panel: pd.DataFrame,
    contract: dict,
    unidades: dict[str, str],
    *,
    col_poblacion: str = "poblacion_total",
    col_producto: str = "pib_corriente_mm",
    id_cols: tuple[str, ...] = ("dpto_ccdgo", "anio"),
) -> pd.DataFrame:
    """Conteos por 10.000 habitantes y montos como porcentaje del producto (ADR-015, punto 1).

    `unidades` mapea cada variable a 'count' o 'cop' (viene de dim_variable). El producto llega en miles de
    millones de pesos, de ahí el factor 1e9. Cuál producto —contemporáneo, rezagado o fijo— lo decide
    `config/index.yaml` (ADR-017), nunca una constante escondida aquí.
    """
    reglas = contract["normalizacion"]
    out = panel.copy()
    poblacion = pd.to_numeric(out[col_poblacion], errors="coerce")
    serie_producto, _modo = denominador_de_producto(out, contract, id_cols, col_producto)
    producto = serie_producto * 1e9
    for v in contract_variables(contract):
        if v not in out.columns:
            raise KeyError(f"el panel no trae la variable {v!r} que exige config/index.yaml")
        unidad = unidades.get(v)
        if unidad is None:
            raise KeyError(f"no se conoce la unidad de {v!r}; debe venir de dim_variable")
        regla = reglas[unidad]
        valor = pd.to_numeric(out[v], errors="coerce")
        if regla == "por_10k_habitantes":
            out[v] = valor / poblacion.replace(0, np.nan) * 10_000
        elif regla == "pct_producto":
            out[v] = valor / producto.replace(0, np.nan) * 100
        else:
            raise ValueError(f"regla de normalización desconocida: {regla!r}")
    return out


def _kmo(corr: np.ndarray) -> float:
    """Kaiser-Meyer-Olkin sobre la matriz de correlación: proporción de correlación no parcial."""
    inv = np.linalg.pinv(corr)
    d = np.sqrt(np.diag(inv))
    parcial = -inv / np.outer(d, d)
    np.fill_diagonal(parcial, 0.0)
    c = corr.copy()
    np.fill_diagonal(c, 0.0)
    return float((c**2).sum() / ((c**2).sum() + (parcial**2).sum()))


def _bartlett(corr: np.ndarray, n: int) -> tuple[float, float]:
    """Prueba de esfericidad: ¿la matriz de correlación difiere de la identidad?"""
    from scipy import stats

    p = corr.shape[0]
    det = np.linalg.det(corr)
    det = max(det, 1e-300)
    chi2 = -((n - 1) - (2 * p + 5) / 6) * np.log(det)
    gl = p * (p - 1) / 2
    return float(chi2), float(stats.chi2.sf(chi2, gl))


def fit_dimension(
    calib: pd.DataFrame, dimension: str, spec: dict, *, min_obs: int = 20, kmo_minimo: float | None = None
) -> DimensionFit:
    """Estima media, desviación y cargas de una dimensión sobre la ventana de calibración.

    Con `kmo_minimo`, el PCA se niega a estimarse si el KMO medido no llega (R-17): el supuesto se mide
    antes de usar el método. La sensibilidad lo llama sin umbral a propósito, porque su papel es
    enseñar lo que da el método que los datos no sostienen.
    """
    variables = [v["variable_id"] for v in spec["variables"]]
    signos = {v["variable_id"]: v.get("signo_esperado", 1) for v in spec["variables"]}
    x = calib[variables].apply(pd.to_numeric, errors="coerce").dropna()
    if len(x) < min_obs:
        raise ValueError(
            f"{dimension}: solo {len(x)} observaciones completas en la calibración, se exigen {min_obs}"
        )
    media = x.mean()
    desv = x.std(ddof=1).replace(0, np.nan)
    if desv.isna().any():
        raise ValueError(
            f"{dimension}: variables sin variación en la calibración: {list(desv[desv.isna()].index)}"
        )
    z = (x - media) / desv

    if spec["metodo"] == "pesos_iguales":
        # Cada variable pesa 1/k dentro de la dimensión. No exige estructura factorial y no puede dar un
        # peso negativo a una variable que debe sumar (ADR-015, adenda).
        corr = np.corrcoef(z.to_numpy(), rowvar=False)
        chi2, p_val = _bartlett(corr, len(z))
        cargas = {v: float(signos[v]) / len(variables) for v in variables}
        return DimensionFit(
            dimension,
            "pesos_iguales",
            variables,
            media.to_dict(),
            desv.to_dict(),
            cargas,
            kmo=_kmo(corr),
            bartlett_chi2=chi2,
            bartlett_p=p_val,
        )

    if spec["metodo"] == "variable_unica":
        if len(variables) != 1:
            raise ValueError(f"{dimension}: el método variable_unica exige exactamente una variable")
        v = variables[0]
        return DimensionFit(
            dimension, "variable_unica", variables, media.to_dict(), desv.to_dict(), {v: float(signos[v])}
        )

    corr = np.corrcoef(z.to_numpy(), rowvar=False)
    kmo = _kmo(corr)
    if kmo_minimo is not None and kmo < kmo_minimo:
        raise ValueError(
            f"{dimension}: KMO {kmo:.3f} < {kmo_minimo}; el PCA no se sostiene (R-17), usa pesos_iguales"
        )
    chi2, p_val = _bartlett(corr, len(z))
    # Componente principal: primer vector propio de la matriz de correlación de las estandarizadas.
    valores, vectores = np.linalg.eigh(corr)
    orden = np.argsort(valores)[::-1]
    valores, vectores = valores[orden], vectores[:, orden]
    carga = vectores[:, 0]
    # Orientación: el signo del componente es arbitrario, así que se fija con el signo esperado de la
    # variable de mayor carga absoluta. Sin esto el índice podría salir invertido de una corrida a otra.
    ancla = int(np.argmax(np.abs(carga)))
    if np.sign(carga[ancla]) != np.sign(signos[variables[ancla]]):
        carga = -carga
    # Se escala para que el score tenga varianza 1 en la calibración.
    carga = carga / np.sqrt(valores[0])
    return DimensionFit(
        dimension,
        "pca",
        variables,
        media.to_dict(),
        desv.to_dict(),
        dict(zip(variables, carga.astype(float), strict=True)),
        varianza_explicada=float(valores[0] / valores.sum()),
        kmo=kmo,
        bartlett_chi2=chi2,
        bartlett_p=p_val,
    )


def apply_dimension(panel: pd.DataFrame, fit: DimensionFit) -> pd.Series:
    z = pd.DataFrame(
        {
            v: (pd.to_numeric(panel[v], errors="coerce") - fit.media[v]) / fit.desviacion[v]
            for v in fit.variables
        }
    )
    return sum(z[v] * fit.cargas[v] for v in fit.variables)


def pesos_implicitos(fits: dict[str, DimensionFit], pesos_dim: dict[str, float]) -> pd.DataFrame:
    """Peso de cada variable en el compuesto, en la escala estandarizada y en la original (ADR-015, punto 7).

    En la escala original el peso es el de la estandarizada dividido por la desviación de la variable: es
    cuánto mueve el índice un cambio de una unidad de la variable tal como se mide.
    """
    filas = []
    for dim, fit in fits.items():
        w_dim = pesos_dim[dim]
        for v in fit.variables:
            filas.append(
                {
                    "dimension": dim,
                    "variable_id": v,
                    "peso_estandarizado": w_dim * fit.cargas[v],
                    "peso_escala_original": w_dim * fit.cargas[v] / fit.desviacion[v],
                    "desviacion_calibracion": fit.desviacion[v],
                }
            )
    return pd.DataFrame(filas).sort_values(["dimension", "variable_id"]).reset_index(drop=True)


def techo_sarma(z: pd.DataFrame, en_calibracion: pd.Series) -> pd.Series:
    """El techo de la distancia tipo Sarma: máximo de las z recortadas en 0, en la ventana de calibración."""
    techo = z.clip(lower=0).loc[np.asarray(en_calibracion, dtype=bool)].max().replace(0, np.nan)
    if techo.isna().any():
        raise ValueError(
            f"distancia tipo Sarma: sin techo en la calibración para {list(techo[techo.isna()].index)}"
        )
    return techo


def _sarma(z: pd.DataFrame, techo: pd.Series) -> pd.Series:
    """Distancia tipo Sarma: 1 menos la distancia euclídea normalizada al vector ideal (ADR-025).

    No es el índice de Sarma (2008) tal cual, y por eso se rotula «tipo Sarma»:

    - El suelo de cada variable es la media de la calibración (z = 0): lo que queda por debajo se recorta
      a 0, así que la distancia no distingue entre dos unidades que están, ambas, bajo la media.
    - El techo es el máximo de las z recortadas **en la ventana de calibración**, congelado como las
      medias y las desviaciones: añadir un año no mueve el techo ni, por tanto, los años anteriores. Lo
      que supera ese techo cuenta como haber llegado al ideal (se recorta a 1).
    - Un faltante sigue faltante (R-13): la fila sin alguna de las variables se queda sin valor, igual
      que el compuesto. Rellenar con cero la ponía a la máxima distancia del ideal en esa variable.
    """
    x = z.clip(lower=0).div(techo.reindex(z.columns), axis=1).clip(upper=1)
    k = x.shape[1]
    distancia = np.sqrt(((1 - x) ** 2).sum(axis=1, min_count=k)) / np.sqrt(k)
    # `min_count` ya deja NaN la suma de una fila incompleta; la máscara lo hace explícito.
    return (1 - distancia).where(x.notna().all(axis=1))


def correlacion_rangos_detalle(
    comp: pd.DataFrame, columnas: list[str], id_cols: tuple[str, ...]
) -> pd.DataFrame:
    """Spearman entre versiones del índice: agrupada, dentro de cada año y en cambios.

    La agrupada mezcla años y unidades, y la tendencia común la infla: si todas las versiones suben con
    el tiempo, ordenan igual los años aunque no ordenen igual a las unidades. Lo que importa para un panel
    con efectos de año es la correlación **dentro de cada año** (se publica la media y el mínimo, con el
    año del mínimo) y la de los **cambios** anuales de cada unidad, que es la variación que deja un efecto
    fijo de unidad.
    """
    unidad, tiempo = id_cols[0], id_cols[1]
    ordenado = comp.sort_values([unidad, tiempo]).reset_index(drop=True)
    cambios = ordenado.groupby(unidad)[columnas].diff()
    # Un cambio solo es tal entre años consecutivos: un hueco de dos años no es un cambio anual.
    cambios = cambios[ordenado.groupby(unidad)[tiempo].diff() == 1]
    filas = []
    for i, a in enumerate(columnas):
        for b in columnas[i + 1 :]:
            por_anio = {
                int(anio): g[a].corr(g[b], method="spearman")
                for anio, g in ordenado.dropna(subset=[a, b]).groupby(tiempo)
                if len(g) > 2
            }
            por_anio = pd.Series(por_anio, dtype=float).dropna()
            par_cambios = cambios[[a, b]].dropna()
            filas.append(
                dict(
                    version_a=a,
                    version_b=b,
                    agrupada=float(ordenado[a].corr(ordenado[b], method="spearman")),
                    por_anio_media=float(por_anio.mean()) if len(por_anio) else np.nan,
                    por_anio_minimo=float(por_anio.min()) if len(por_anio) else np.nan,
                    anio_del_minimo=int(por_anio.idxmin()) if len(por_anio) else None,
                    n_anios=int(len(por_anio)),
                    cambios=float(par_cambios[a].corr(par_cambios[b], method="spearman")),
                    n_cambios=int(len(par_cambios)),
                )
            )
    return pd.DataFrame(filas)


def _quitar_dos_vias(
    df: pd.DataFrame, columnas: list[str], unidad: str, tiempo: str, tol: float = 1e-12, max_iter: int = 1000
) -> pd.DataFrame:
    """Residuo de efectos fijos de unidad y de año, por proyecciones alternadas.

    En un panel balanceado basta una pasada (x − media de unidad − media de año + media global); con
    huecos, como los de Vaupés y Guainía, la pasada única no es la proyección y hay que iterar hasta que
    las medias por unidad y por año sean cero a la vez.
    """
    r = df[columnas].astype(float).copy()
    for _ in range(max_iter):
        r = r - r.groupby(df[unidad]).transform("mean")
        r = r - r.groupby(df[tiempo]).transform("mean")
        if float(r.groupby(df[unidad]).mean().abs().to_numpy().max()) < tol:
            break
    return r


def participacion_varianza_intra(
    scores: pd.DataFrame, pesos_dim: dict[str, float], id_cols: tuple[str, ...]
) -> pd.DataFrame:
    """Qué parte de la varianza intra (efectos fijos de unidad y de año) del compuesto aporta cada dimensión.

    Tras los efectos fijos, el compuesto residual es la suma ponderada de las dimensiones residuales, así
    que su varianza se reparte exactamente: participación_d = w_d · Cov(D̃_d, C̃) / Var(C̃), y las tres
    suman uno. Es la cifra detrás de la frase de la guía (§9) según la cual, tras los efectos fijos, el
    índice mide en la práctica corresponsales por habitante. `participacion_propia` es solo el término de
    varianza, w_d² · Var(D̃_d) / Var(C̃); la diferencia con la anterior son las covarianzas.
    """
    unidad, tiempo = id_cols[0], id_cols[1]
    dims = [f"iif_{d}" for d in pesos_dim]
    muestra = scores.dropna(subset=["iif_compuesto", *dims]).reset_index(drop=True)
    resid = _quitar_dos_vias(muestra, ["iif_compuesto", *dims], unidad, tiempo)
    c = resid["iif_compuesto"] - resid["iif_compuesto"].mean()
    var_total = float(muestra["iif_compuesto"].var(ddof=0))
    var_c = float((c**2).mean())
    if var_c <= 1e-12 * max(var_total, 1.0):
        # Sin variación intra no hay nada que repartir, y dividir por un residuo numérico inventaría
        # participaciones.
        var_c = 0.0
    filas = []
    for d, w in pesos_dim.items():
        x = resid[f"iif_{d}"] - resid[f"iif_{d}"].mean()
        var_d = float((x**2).mean())
        filas.append(
            dict(
                dimension=d,
                peso=float(w),
                varianza_intra_dimension=var_d,
                participacion=float(w * (x * c).mean() / var_c) if var_c > 0 else np.nan,
                participacion_propia=float(w**2 * var_d / var_c) if var_c > 0 else np.nan,
                varianza_intra_compuesto=var_c,
                fraccion_intra_de_la_total=var_c / var_total if var_total > 0 else np.nan,
                n_obs=int(len(muestra)),
            )
        )
    return pd.DataFrame(filas)


def build_index(
    panel: pd.DataFrame,
    unidades: dict[str, str],
    *,
    contract: dict | None = None,
    id_cols: tuple[str, ...] = ("dpto_ccdgo", "anio"),
    col_poblacion: str = "poblacion_total",
    col_producto: str = "pib_corriente_mm",
    pesos_congelados: dict | None = None,
    techo_congelado: dict[str, float] | None = None,
) -> IndexResult:
    """Calcula subíndices y compuesto. Con `pesos_congelados` reproduce exactamente una corrida anterior.

    `techo_congelado` es el techo de la distancia tipo Sarma calibrado en otro panel: el municipal usa el
    del departamental, igual que usa sus medias y desviaciones (ADR-025).
    """
    contract = contract or load_contract()
    norm = normalize_panel(
        panel,
        contract,
        unidades,
        col_poblacion=col_poblacion,
        col_producto=col_producto,
        id_cols=id_cols,
    )

    if pesos_congelados:
        fits = {d: DimensionFit(**f) for d, f in pesos_congelados.items()}
    else:
        c = contract["calibracion"]
        calib = norm[(norm["anio"] >= c["anio_desde"]) & (norm["anio"] <= c["anio_hasta"])]
        kmo_minimo = float(contract.get("kmo_minimo", KMO_MINIMO))
        fits = {
            dim: fit_dimension(calib, dim, spec, kmo_minimo=kmo_minimo)
            for dim, spec in contract["dimensiones"].items()
        }

    pesos_dim = contract["compuesto"]["pesos"]
    implicitos = pesos_implicitos(fits, pesos_dim)
    negativos = implicitos[implicitos["peso_estandarizado"] < 0]
    if not negativos.empty:
        # R-17: el índice publica sus pesos implícitos y ninguno puede ser negativo. Se comprueba
        # aquí, antes de puntuar, y también con pesos congelados, que llegan de un YAML editable.
        raise ValueError(
            "pesos implícitos negativos (R-17): "
            + ", ".join(f"{r.variable_id}={r.peso_estandarizado:.4f}" for r in negativos.itertuples())
        )
    scores = norm[list(id_cols)].copy()
    for dim, fit in fits.items():
        scores[f"iif_{dim}"] = apply_dimension(norm, fit)
    scores["dimensiones_observadas"] = sum(scores[f"iif_{d}"].notna().astype(int) for d in fits)
    # El compuesto exige las tres dimensiones: una unidad sin crédito de vivienda observado no tiene
    # profundidad, y rellenarla con cero sería inventar un dato (R-13).
    scores["iif_compuesto"] = sum(scores[f"iif_{d}"] * w for d, w in pesos_dim.items())

    # Sensibilidad: el primer componente principal por dimensión, que es el método que los datos no
    # sostienen (KMO por debajo de 0,5; ADR-015 adenda), y la distancia tipo Sarma (ADR-025).
    cal = contract["calibracion"]
    calib_sens = norm[(norm["anio"] >= cal["anio_desde"]) & (norm["anio"] <= cal["anio_hasta"])]
    sens = norm[list(id_cols)].copy()
    for dim, spec in contract["dimensiones"].items():
        if len(spec["variables"]) == 1:
            sens[f"pca_{dim}"] = apply_dimension(norm, fits[dim])
        else:
            sens[f"pca_{dim}"] = apply_dimension(
                norm, fit_dimension(calib_sens, dim, {**spec, "metodo": "pca"})
            )
    sens["iif_pca"] = sum(sens[f"pca_{d}"] * w for d, w in pesos_dim.items())
    todas = [v for f in fits.values() for v in f.variables]
    z_todas = pd.DataFrame(
        {
            v: (
                pd.to_numeric(norm[v], errors="coerce")
                - next(f.media[v] for f in fits.values() if v in f.media)
            )
            / next(f.desviacion[v] for f in fits.values() if v in f.desviacion)
            for v in todas
        }
    )
    if techo_congelado is None:
        en_calibracion = (norm["anio"] >= cal["anio_desde"]) & (norm["anio"] <= cal["anio_hasta"])
        techo = techo_sarma(z_todas, en_calibracion)
    else:
        techo = pd.Series(techo_congelado, dtype=float)
    sens["iif_sarma"] = _sarma(z_todas, techo)

    comp = scores[[*id_cols, "iif_compuesto"]].merge(
        sens[[*id_cols, "iif_pca", "iif_sarma"]], on=list(id_cols)
    )
    versiones = ["iif_compuesto", "iif_pca", "iif_sarma"]
    corr = comp[versiones].corr(method="spearman")
    return IndexResult(
        scores=scores,
        fits=fits,
        implicitos=implicitos,
        sensibilidad=sens,
        correlacion_rangos=corr,
        correlacion_rangos_detalle=correlacion_rangos_detalle(comp, versiones, id_cols),
        varianza_intra=participacion_varianza_intra(scores, pesos_dim, id_cols),
        techo_sarma=techo.to_dict(),
        normalizado=norm,
    )
