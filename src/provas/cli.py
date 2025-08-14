# src/provas/cli.py
from pathlib import Path
import typer

app = typer.Typer(help="Provas pipeline CLI")

@app.command()
def ocr(base: Path = typer.Argument(Path("provas"))):
    from .ocr import run_ocr_batch
    run_ocr_batch(base)

@app.command(name="export")
def export_cmd(path: Path = typer.Argument(...)):
    from .export_json import export_single
    export_single(path / "full_regex.md")

@app.command(name="export-all")
def export_all_cmd(base: Path = typer.Argument(Path("provas"))):
    from .export_json import export_batch
    export_batch(base)



@app.command(name="blocks")
def blocks(base: Path = typer.Argument(Path("provas"))):
    """Split full.md into '----' blocks, attach shared preambles, keep duplicates."""
    from .blocks_fix_boundaries import blocks_batch
    blocks_batch(base)

@app.command(name="fix-dedup")
def fix(base: Path = typer.Argument(Path("provas"))):
    from .blocks_fix_dedup import fix_batch
    fix_batch(base)

@app.command(name="fix-missing")
def fix_missing_cmd(base: Path = typer.Argument(Path("provas"))):
    from .block_fix_missing import fix_missing_batch
    fix_missing_batch(base)

@app.command(name="final-audit")
def final_audit_cmd(base: Path = typer.Argument(Path("provas"))):
    """Aggregate summaries and run a final quality audit."""
    from .block_fix_audit import final_audit_batch
    final_audit_batch(base)


@app.command(name="finalize")
def finalize_cmd(base: Path = typer.Argument(Path("provas"))):
    from .block_fix_audit_llm import finalize_batch_from_audit
    finalize_batch_from_audit(base)


@app.command(name="blocks-json")
def blocks_json_cmd(base: Path = typer.Argument(Path("provas"))):
    from .blocks_json import run
    run(base)
