"""Bootstrap salvaje por clúster studentizado con el error agrupado, sobre el diseño completo (ADR-024).

Con 33 departamentos la asintótica del error agrupado no se cumple, y la corrección estándar es el
bootstrap salvaje con la nula impuesta (Cameron, Gelbach y Miller, 2008). Su refinamiento asintótico viene
de studentizar cada réplica con **el mismo** estimador de varianza que el contraste observado, que aquí es
el agrupado por departamento (CRVE). La versión anterior studentizaba con el error homocedástico: el
coeficiente era el correcto y el estadístico no.

Todo se hace con los efectos fijos como variables ficticias explícitas. Con 33 departamentos y a lo sumo
veinte años el diseño cabe de sobra en memoria, y así los residuos de cada réplica son los del modelo
completo: una réplica con signos distintos por departamento deja de ser ortogonal a los efectos de año, y
trabajar en el espacio ya desmediado lo olvidaba.

Como el problema es lineal en todo, las réplicas se calculan juntas como matrices y la prueba con la nula
β = β₀ es lineal en β₀. Eso hace barato invertirla: el intervalo de confianza es el conjunto de β₀ que la
prueba no rechaza, y el TOST bootstrap son dos pruebas unilaterales con la nula en −m y en +m.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

# Pesos de las réplicas. Rademacher tiene 2^G combinaciones distintas, que con 33 clústeres sobran; Webb
# (2014) reparte seis puntos con media 0 y varianza 1 y se recomienda cuando hay pocos clústeres. Se
# publican los dos.
PESOS = {
    "rademacher": np.array([-1.0, 1.0]),
    "webb": np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)]),
}


@dataclass
class Diseno:
    """La ecuación como matrices: dependiente, regresores con ficticias y el clúster de cada fila."""

    y: np.ndarray
    X: np.ndarray
    nombres: list[str]
    grupos: np.ndarray  # código 0..G-1 del clúster de cada fila
    G: int
    # Ficticias de unidad: están anidadas en los clústeres y, como en Stata, no descuentan grados de
    # libertad en la corrección CR1.
    anidadas: int = 0

    @property
    def n(self) -> int:
        return int(self.X.shape[0])

    @property
    def k(self) -> int:
        return int(np.linalg.matrix_rank(self.X))


def diseno(
    df: pd.DataFrame,
    y: str,
    regresores: list[str],
    *,
    unidad: str = "dpto_ccdgo",
    tiempo: str = "anio",
    efectos_tiempo: bool = True,
) -> Diseno:
    """Regresores, constante y ficticias de unidad (y de año) en una sola matriz."""
    datos = df.dropna(subset=[y, *regresores, unidad, tiempo]).reset_index(drop=True)
    partes = [datos[regresores].to_numpy(dtype=float), np.ones((len(datos), 1))]
    nombres = [*regresores, "const"]
    ent = pd.get_dummies(datos[unidad].astype(str), drop_first=True, dtype=float)
    partes.append(ent.to_numpy())
    nombres += [f"u_{c}" for c in ent.columns]
    if efectos_tiempo:
        per = pd.get_dummies(datos[tiempo].astype(int), drop_first=True, dtype=float)
        partes.append(per.to_numpy())
        nombres += [f"t_{c}" for c in per.columns]
    codigos, _ = pd.factorize(datos[unidad])
    return Diseno(
        y=datos[y].to_numpy(dtype=float),
        X=np.column_stack(partes),
        nombres=nombres,
        grupos=np.asarray(codigos),
        G=int(codigos.max() + 1),
        anidadas=int(ent.shape[1]),
    )


def holm(p: np.ndarray | list[float]) -> np.ndarray:
    """p ajustados de Holm (1979): válidos bajo cualquier dependencia entre los contrastes.

    Se ordenan de menor a mayor, el k-ésimo se multiplica por (m − k + 1) y se impone monotonía.
    """
    p = np.asarray(p, dtype=float)
    m = p.size
    orden = np.argsort(p)
    ajustado = np.empty(m)
    acumulado = 0.0
    for rango, i in enumerate(orden):
        acumulado = max(acumulado, min(1.0, (m - rango) * p[i]))
        ajustado[i] = acumulado
    return ajustado


def _uno_caliente(grupos: np.ndarray, G: int) -> np.ndarray:
    H = np.zeros((grupos.size, G))
    H[np.arange(grupos.size), grupos] = 1.0
    return H


def _factor_cr1(n: int, k: int, G: int) -> float:
    """Corrección de muestra pequeña del CRVE (la de Stata): G/(G−1) · (N−1)/(N−K).

    K no cuenta los efectos de unidad, anidados en los clústeres. La constante se cancela en el p bootstrap
    y en el intervalo invertido, porque multiplica igual al estadístico observado y a cada réplica: solo
    mueve el error estándar que se reporta y el p analítico.
    """
    return G / (G - 1) * (n - 1) / max(n - k, 1)


def _pesos_de_replica(nombre: str, G: int, replicas: int, semilla: int) -> np.ndarray:
    if nombre not in PESOS:
        raise ValueError(f"pesos desconocidos: {nombre!r}; admite {sorted(PESOS)}")
    rng = np.random.default_rng(semilla)
    return rng.choice(PESOS[nombre], size=(G, replicas))


class _Particion:
    """FWL: lo que queda de los regresores contrastados tras proyectar fuera todo lo demás."""

    def __init__(self, d: Diseno, idx: list[int]):
        self.d = d
        self.idx = list(idx)
        resto = [j for j in range(d.X.shape[1]) if j not in self.idx]
        self.Q = d.X[:, resto]
        self.Qp = np.linalg.pinv(self.Q)
        self.Xt = self.anula(d.X[:, self.idx])  # N × q
        self.yt = self.anula(d.y)
        self.A = np.linalg.inv(self.Xt.T @ self.Xt)
        self.b = self.A @ (self.Xt.T @ self.yt)
        self.e = self.yt - self.Xt @ self.b
        self.H = _uno_caliente(d.grupos, d.G)
        self.c = _factor_cr1(d.n, d.k - d.anidadas, d.G)

    def anula(self, v: np.ndarray) -> np.ndarray:
        """M_Q v: el residuo de proyectar v sobre los regresores que no se contrastan."""
        return v - self.Q @ (self.Qp @ v)

    def vcov(self, e: np.ndarray) -> np.ndarray:
        """CRVE (CR1) de los coeficientes contrastados dado un vector de residuos."""
        S = self.H.T @ (self.Xt * e[:, None])  # G × q
        return self.c * self.A @ (S.T @ S) @ self.A


def crve(d: Diseno, idx: list[int]) -> dict:
    """Coeficientes y error agrupado CR1 de los regresores `idx`."""
    p = _Particion(d, idx)
    V = p.vcov(p.e)
    return {"coef": p.b, "vcov": V, "se": np.sqrt(np.diag(V))}


def wald_bootstrap(
    d: Diseno,
    idx: list[int],
    *,
    replicas: int = 999,
    semilla: int = 20260907,
    pesos: str = "rademacher",
) -> dict:
    """Prueba conjunta β[idx] = 0 con el Wald agrupado y su bootstrap salvaje con la nula impuesta.

    Devuelve el F analítico contra F(q, G − 1) y el p bootstrap del Wald. Con q = 1 el Wald es t² y la
    prueba es la simétrica de dos colas.
    """
    p = _Particion(d, idx)
    q = len(idx)
    V = p.vcov(p.e)
    Vi = np.linalg.pinv(V)
    wald = float(p.b @ Vi @ p.b)

    W = _pesos_de_replica(pesos, d.G, replicas, semilla)[d.grupos]  # N × B
    # Bajo la nula los regresores contrastados no entran: el residuo restringido es M_Q y.
    V_b = p.anula(p.yt[:, None] * W)  # M_Q (u_r ∘ w)
    b_b = p.A @ (p.Xt.T @ V_b)  # q × B
    E_b = V_b - p.Xt @ b_b
    walds = np.empty(replicas)
    for r in range(replicas):
        Vr = p.vcov(E_b[:, r])
        walds[r] = float(b_b[:, r] @ np.linalg.pinv(Vr) @ b_b[:, r])
    ok = np.isfinite(walds)
    p_boot = (np.sum(walds[ok] >= wald) + 1) / (ok.sum() + 1)
    F = wald / q
    return {
        "q": q,
        "F": F,
        "gl": [q, d.G - 1],
        "p_F": float(stats.f.sf(F, q, d.G - 1)),
        "p_bootstrap": float(p_boot),
        "pesos": pesos,
        "replicas": int(ok.sum()),
        "clusteres": d.G,
        "n": d.n,
    }


class BootstrapUnCoeficiente:
    """El bootstrap de un solo coeficiente, como función de la nula β = β₀.

    Todo es lineal en β₀: el residuo restringido es ỹ − β₀x̃, así que cada réplica se escribe como dos
    matrices fijas combinadas con β₀. Evaluar la prueba en otro β₀ cuesta una combinación lineal, y por eso
    se puede invertir.
    """

    def __init__(self, d: Diseno, j: int, *, replicas: int, semilla: int, pesos: str):
        p = _Particion(d, [j])
        self.p, self.d = p, d
        self.coef = float(p.b[0])
        self.se = float(np.sqrt(p.vcov(p.e)[0, 0]))
        x = p.Xt[:, 0]
        W = _pesos_de_replica(pesos, d.G, replicas, semilla)[d.grupos]
        P1 = p.anula(p.yt[:, None] * W)
        P2 = p.anula(x[:, None] * W)
        a = float(p.A[0, 0])
        self.n1 = a * (x @ P1)  # b* − β₀ = n1 − β₀ n2
        self.n2 = a * (x @ P2)
        h2 = p.H.T @ (x**2)
        F1 = p.H.T @ (x[:, None] * P1) - h2[:, None] * self.n1[None, :]
        F2 = p.H.T @ (x[:, None] * P2) - h2[:, None] * self.n2[None, :]
        self.F1, self.F2 = F1, F2
        self.escala = np.sqrt(p.c) * a
        self.replicas = replicas

    def t_replicas(self, beta0: float) -> np.ndarray:
        num = self.n1 - beta0 * self.n2
        S = self.F1 - beta0 * self.F2
        se = self.escala * np.sqrt(np.sum(S**2, axis=0))
        with np.errstate(invalid="ignore", divide="ignore"):
            return num / se

    def t_observado(self, beta0: float) -> float:
        return (self.coef - beta0) / self.se

    def p_simetrico(self, beta0: float) -> float:
        t = self.t_replicas(beta0)
        t = t[np.isfinite(t)]
        return float((np.sum(np.abs(t) >= abs(self.t_observado(beta0))) + 1) / (t.size + 1))

    def p_unilateral(self, beta0: float, lado: str) -> float:
        """`mayor`: H0 β ≤ β₀ contra β > β₀. `menor`: H0 β ≥ β₀ contra β < β₀."""
        t = self.t_replicas(beta0)
        t = t[np.isfinite(t)]
        obs = self.t_observado(beta0)
        cuenta = np.sum(t >= obs) if lado == "mayor" else np.sum(t <= obs)
        return float((cuenta + 1) / (t.size + 1))

    def intervalo(self, nivel: float = 0.95, *, ancho: float = 8.0, puntos: int = 801) -> list[float]:
        """El conjunto de β₀ que la prueba simétrica no rechaza al nivel pedido, por rejilla y bisección."""
        alfa = 1 - nivel
        rejilla = self.coef + self.se * np.linspace(-ancho, ancho, puntos)
        acepta = np.array([self.p_simetrico(b) > alfa for b in rejilla])
        if not acepta.any():
            return [float("nan"), float("nan")]
        i_lo, i_hi = int(np.argmax(acepta)), int(len(acepta) - 1 - np.argmax(acepta[::-1]))

        def biseccion(fuera: float, dentro: float) -> float:
            for _ in range(50):
                medio = (fuera + dentro) / 2
                if self.p_simetrico(medio) > alfa:
                    dentro = medio
                else:
                    fuera = medio
            return (fuera + dentro) / 2

        lo = rejilla[i_lo] if i_lo == 0 else biseccion(rejilla[i_lo - 1], rejilla[i_lo])
        hi = rejilla[i_hi] if i_hi == len(rejilla) - 1 else biseccion(rejilla[i_hi + 1], rejilla[i_hi])
        return [float(lo), float(hi)]

    def tost(self, margen: float) -> dict:
        """Dos unilaterales bootstrap: H0 β ≤ −m y H0 β ≥ +m, cada una con su nula impuesta."""
        p_inf = self.p_unilateral(-margen, "mayor")
        p_sup = self.p_unilateral(margen, "menor")
        p = max(p_inf, p_sup)
        return {"margen": float(margen), "p": p, "p_inferior": p_inf, "p_superior": p_sup, "equivale": bool(p < 0.05)}

    def margen_minimo(self, alfa: float = 0.05) -> float:
        """El margen más pequeño que el TOST bootstrap declara equivalente al nivel `alfa`.

        Es la cota que el diseño sostiene: descarta efectos mayores que este margen y ninguno menor. Se
        busca por bisección, porque el p del TOST baja cuando el margen crece.
        """
        bajo, alto = 0.0, abs(self.coef) + 20 * self.se
        if self.tost(alto)["p"] >= alfa:
            return float("nan")
        for _ in range(50):
            medio = (bajo + alto) / 2
            if self.tost(medio)["p"] < alfa:
                alto = medio
            else:
                bajo = medio
        return float(alto)
