# src/provas/cli.py
from pathlib import Path
import typer

app = typer.Typer(help="Provas pipeline CLI")

@app.command()
def ocr(base: Path = typer.Argument(Path("provas"))):
    from .ocr import run_ocr_batch
    run_ocr_batch(base)

@app.command()
def clean(base: Path = typer.Argument(Path("provas"))):
    from .clean import clean_batch
    clean_batch(base)

@app.command(name="export")
def export_cmd(path: Path = typer.Argument(...)):
    from .export_json import export_single
    export_single(path / "full_regex.md")

@app.command(name="export-all")
def export_all_cmd(base: Path = typer.Argument(Path("provas"))):
    from .export_json import export_batch
    export_batch(base)

@app.command()
def blocks(base: Path = typer.Argument(Path("provas"))):
    """Split full.md into '----' blocks, attach shared preambles, keep duplicates."""
    from .blocks import blocks_batch
    blocks_batch(base)