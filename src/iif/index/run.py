"""Orquestación: lee los paneles del warehouse, construye el índice y escribe Parquet en data/processed/."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import duckdb
import pandas as pd
import yaml

from iif import config
from iif.index.build import build_index, load_contract

NIVELES = {
    "departamento": dict(
        tabla="marts.mart_panel_departamento_anual",
        id_cols=("dpto_ccdgo", "anio"),
        col_producto="pib_corriente_mm",
    ),
    "municipio": dict(
        tabla="marts.mart_panel_municipio_anual",
        id_cols=("mpio_ccdgo", "anio"),
        col_producto="va_corriente_mm",
    ),
}


def _con(db: Path | None = None) -> duckdb.DuckDBPyConnection:
    path = db or config.DUCKDB_PATH
    if not path.exists():
        raise FileNotFoundError(f"no existe {path}; corre `make dbt-build` antes de construir el índice")
    return duckdb.connect(str(path), read_only=True)


def build_level(
    nivel: str, *, db: Path | None = None, contract: dict | None = None, congelados: dict | None = None
):
    spec = NIVELES[nivel]
    contract = contract or load_contract()
    with _con(db) as con:
        panel = con.sql(f"select * from {spec['tabla']}").df()
        unidades = dict(con.sql("select variable_id, unidad from seeds.dim_variable").df().values)
    return panel, build_index(
        panel,
        unidades,
        contract=contract,
        id_cols=spec["id_cols"],
        col_producto=spec["col_producto"],
        pesos_congelados=congelados,
    )


def run(*, recalibrar: bool = False, out_dir: Path | None = None, db: Path | None = None) -> dict[str, Path]:
    """Construye el índice en los dos niveles. Con `recalibrar` reestima y reescribe los pesos congelados.

    Los pesos se calibran una sola vez, sobre el panel departamental, y se aplican también al municipal:
    así el índice de un municipio y el de su departamento están en la misma escala y son comparables.
    """
    out_dir = out_dir or config.DATA_PROCESSED
    out_dir.mkdir(parents=True, exist_ok=True)
    contract = load_contract()
    congelados = contract.get("pesos_congelados") or None
    # Recalibrar significa volver a estimar, así que la primera pasada tiene que ir SIN los pesos viejos:
    # pasándolos, `build_index` los reutiliza y `res_dep.fits` devuelve exactamente lo que ya había, de modo
    # que la orden se cumplía escribiendo de nuevo los mismos números (B-053).
    if recalibrar:
        congelados = None

    panel_dep, res_dep = build_level("departamento", db=db, contract=contract, congelados=congelados)
    if recalibrar or not congelados:
        congelados = {d: asdict(f) for d, f in res_dep.fits.items()}
        ruta = config.CONFIG_DIR / "index.yaml"
        doc = config.load_yaml(ruta)
        doc["pesos_congelados"] = congelados
        ruta.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")

    escritos: dict[str, Path] = {}
    for nivel in NIVELES:
        panel, res = build_level(nivel, db=db, contract=contract, congelados=congelados)
        salida = out_dir / f"indice_{nivel}_anual.parquet"
        ids = list(NIVELES[nivel]["id_cols"])
        scores = res.scores.merge(res.sensibilidad, on=ids, how="left")
        # Las variables normalizadas viajan con el índice: son lo que el atlas muestra cuando se pide
        # el desglose por variable, y publicarlas hace auditable de qué está hecho cada subíndice.
        variables = [v for f in res.fits.values() for v in f.variables]
        scores = scores.merge(res.normalizado[ids + variables], on=ids, how="left")
        scores.to_parquet(salida, index=False)
        escritos[nivel] = salida
    res_dep.implicitos.to_csv(out_dir / "indice_pesos_implicitos.csv", index=False)
    pd.DataFrame(
        [
            dict(
                dimension=d,
                metodo=f.metodo,
                n_variables=len(f.variables),
                kmo=f.kmo,
                bartlett_chi2=f.bartlett_chi2,
                bartlett_p=f.bartlett_p,
                varianza_explicada=f.varianza_explicada,
            )
            for d, f in res_dep.fits.items()
        ]
    ).to_csv(out_dir / "indice_diagnosticos.csv", index=False)
    res_dep.correlacion_rangos.to_csv(out_dir / "indice_correlacion_rangos.csv")
    escritos["pesos_implicitos"] = out_dir / "indice_pesos_implicitos.csv"
    escritos["diagnosticos"] = out_dir / "indice_diagnosticos.csv"
    return escritos
