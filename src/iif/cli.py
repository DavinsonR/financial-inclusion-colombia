"""CLI del proyecto: `uv run iif <comando>`."""

from __future__ import annotations

from pathlib import Path

import typer

from iif import config

app = typer.Typer(help="Inclusión financiera y crecimiento regional en Colombia", no_args_is_help=True)


@app.command()
def reproduce(
    xlsx: Path = typer.Option(config.LEGACY_XLSX, help="Panel legado (xlsx o parquet)"),
    out: Path = typer.Option(Path("docs/legacy/reproduccion.md"), help="Informe markdown"),
    mode: str = typer.Option("notebook", help="notebook | corrected"),
) -> None:
    """Corre el pipeline legado y escribe el informe con la tabla de discrepancias."""
    from iif.legacy.pipeline import run_legacy_pipeline, to_markdown

    res = run_legacy_pipeline(xlsx, mode=mode)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_markdown(res), encoding="utf-8")
    typer.echo(f"✓ {out}  (discrepancias: {res.ledger.n_discrepancias}, filas: {len(res.ledger.rows)})")


@app.command()
def scrub(
    xlsx: Path = typer.Argument(..., help="xlsx original"),
    notebook: Path = typer.Argument(..., help="ipynb original"),
    markdown: Path = typer.Argument(..., help="dump de resultados original"),
) -> None:
    """Limpia los tres artefactos legados y los deja en data/legacy, notebooks/legacy y docs/legacy."""
    from iif.data import scrub as sc
    from iif.data.dictionary import build_dictionary

    r1 = sc.scrub_xlsx(xlsx, config.LEGACY_XLSX)
    r2 = sc.scrub_notebook(notebook, config.REPO_ROOT / "notebooks" / "legacy" / "TESIS_CONSOLIDADO.ipynb")
    r3 = sc.scrub_markdown(markdown, config.DOCS_DIR / "legacy" / "RESULTADOS_CONSOLIDADO_2.md")
    dic = build_dictionary(config.LEGACY_PARQUET)
    dic.to_csv(config.DATA_LEGACY / "diccionario_panel_legacy.csv", index=False)
    sc.write_checksums([config.LEGACY_XLSX, config.LEGACY_PARQUET], config.DATA_LEGACY / "SHA256SUMS")
    hits = (
        sc.find_private_strings(config.DATA_LEGACY)
        + sc.find_private_strings(config.REPO_ROOT / "notebooks")
        + sc.find_private_strings(config.DOCS_DIR / "legacy")
    )
    typer.echo(
        f"xlsx {r1['rows']}x{r1['cols']} · notebook {r2['cells']} celdas ({r2['paths_replaced']} rutas) · md {r3['paths_masked']} líneas enmascaradas · diccionario {len(dic)} filas"
    )
    if hits:
        typer.echo("CADENAS PRIVADAS RESTANTES:\n" + "\n".join(hits))
        raise typer.Exit(code=1)
    typer.echo("✓ sin cadenas privadas")


@app.command()
def dictionary(out: Path = typer.Option(config.DATA_LEGACY / "diccionario_panel_legacy.csv")) -> None:
    from iif.data.dictionary import build_dictionary

    dic = build_dictionary(config.LEGACY_PARQUET)
    dic.to_csv(out, index=False)
    typer.echo(f"✓ {out} ({len(dic)} filas)")


@app.command()
def acquire(
    source: str = typer.Argument(
        ..., help="id de config/sources.yaml, o 'all', o 'small' (todo salvo kx2f y MinTIC)"
    ),
    force: bool = typer.Option(False, help="descargar aunque la fuente no haya cambiado"),
) -> None:
    """Descarga una fuente (o todas) y la registra en el manifiesto."""
    from iif.acquire import dane, mgn, soda
    from iif.acquire.sources import load_sources

    sources = load_sources()
    big = {"sfc-kx2f-xjdq", "mintic-n48w-gutb"}
    ids = (
        list(sources)
        if source == "all"
        else ([s for s in sources if s not in big] if source == "small" else [source])
    )
    for sid in ids:
        src = {"id": sid, **sources[sid]}
        try:
            if src["kind"] == "soda":
                recs = soda.fetch_soda(src, force=force)
                typer.echo(
                    f"✓ {sid}: {sum(r.row_count or 0 for r in recs)} filas en {len(recs)} partición(es)"
                    if recs
                    else f"= {sid}: sin cambios en la fuente"
                )
            elif src["kind"] == "http":
                rec = dane.fetch_file(src, force=force)
                typer.echo(
                    f"✓ {sid}: {rec.bytes / 1e6:.2f} MB, Last-Modified {rec.source_updated_at}"
                    if rec
                    else f"= {sid}: sin cambios"
                )
            elif src["kind"] == "arcgis":
                rec = mgn.fetch_layer(src, force=force)
                typer.echo(
                    f"✓ {sid}: {rec.row_count} rasgos, {rec.bytes / 1e6:.2f} MB"
                    if rec
                    else f"= {sid}: sin cambios"
                )
        except soda.SizeGateError as exc:
            typer.echo(f"! {sid}: {exc}")


@app.command()
def parse(
    what: str = typer.Argument("dane", help="dane: anexos XLSX del DANE → data/interim/dane/*.parquet"),
) -> None:
    """Convierte las descargas crudas en tablas tidy validadas con pandera."""
    if what == "dane":
        from iif.parse.dane import parse_all
    elif what == "mgn":
        from iif.parse.mgn import parse_all
    else:
        raise typer.BadParameter(what)
    written = parse_all()
    for name, path in written.items():
        typer.echo(f"✓ {name}: {path.relative_to(config.REPO_ROOT)}")


@app.command()
def crosswalk(
    action: str = typer.Argument(
        ..., help="derive-blocks: mapa tipo → columnas; geo-report: cobertura DIVIPOLA"
    ),
    fuente: str = typer.Option("ptgf", help="ptgf | kx2f | all"),
) -> None:
    """Mapas derivados de las tablas de la SFC (ADR-007, ADR-008)."""
    from iif import crosswalk as cw

    fuentes = list(cw.FUENTES) if fuente == "all" else [fuente]
    if action == "derive-blocks":
        res = cw.write_blocks(fuentes)
        for f in fuentes:
            sub = res[res.fuente == f]
            typer.echo(f"✓ {f}: {sub.tipo_id.nunique()} bloques, {len(sub)} pares bloque-columna")
    elif action == "geo-report":
        out = config.DATA_INTERIM / "sfc"
        out.mkdir(parents=True, exist_ok=True)
        for f in fuentes:
            cov, names = cw.geo_report(f)
            cov.to_csv(out / f"cobertura_geo_{f}.csv", index=False)
            names.to_csv(out / f"nombres_no_coincidentes_{f}.csv", index=False)
            typer.echo(
                f"✓ {f}: cobertura mínima {cov.cobertura.min():.4f} en {len(cov)} cortes; "
                f"{len(names)} nombres distintos al DANE ({int((~names.en_dane_o_mgn).sum())} sin código conocido)"
            )
    else:
        raise typer.BadParameter(action)


@app.command()
def index(
    recalibrar: bool = typer.Option(
        False, help="reestima los pesos y los vuelve a congelar en config/index.yaml (decisión de valor)"
    ),
) -> None:
    """Construye el índice de inclusión financiera en los dos niveles (ADR-015)."""
    from iif.index.run import run

    escritos = run(recalibrar=recalibrar)
    for nombre, ruta in escritos.items():
        typer.echo(f"✓ {nombre}: {ruta.relative_to(config.REPO_ROOT)}")


@app.command()
def atlas() -> None:
    """Exporta la geometría y las series que consume el atlas (ADR-005)."""
    from iif.export.atlas import export_atlas

    escritos = export_atlas()
    total = 0.0
    for nombre, ruta in escritos.items():
        mb = ruta.stat().st_size / 1e6
        total += mb
        typer.echo(f"✓ {nombre}: {ruta.relative_to(config.REPO_ROOT)} ({mb:.2f} MB)")
    typer.echo(f"  total {total:.2f} MB")


@app.command()
def manifest(action: str = typer.Argument("verify")) -> None:
    """verify: comprueba que cada archivo del manifiesto existe y su sha256 coincide."""
    from iif.acquire.manifest import read_records, verify_manifest

    if action == "verify":
        problems = verify_manifest()
        typer.echo(f"{len(read_records())} registros · {len(problems)} problemas")
        for p in problems:
            typer.echo("  - " + p)
        raise typer.Exit(code=1 if problems else 0)
    raise typer.BadParameter(action)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
