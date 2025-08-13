from pathlib import Path
import typer

from .ocr import run_ocr_batch
from .clean import clean_batch
from .export_json import export_single, export_batch

app = typer.Typer(help="Provas pipeline CLI")

@app.command()
def ocr(
    base: Path = typer.Argument(Path("provas"), help="Base folder containing exam subfolders")
):
    """Run OCR over all tests that have full.md and images/."""
    run_ocr_batch(base)

@app.command()
def clean(
    base: Path = typer.Argument(Path("provas"), help="Base folder containinzg exam subfolders")
):
    """Normalize markdown (merge preambles, strip inline options)."""
    clean_batch(base)

@app.command(name="export")
def export_cmd(
    path: Path = typer.Argument(..., help="Path to a single exam folder (contains full_regex.md)")
):
    """Export JSON + validation for a specific test folder."""
    export_single(path / "full_regex.md")

@app.command(name="export-all")
def export_all_cmd(
    base: Path = typer.Argument(Path("provas"), help="Base folder containing exam subfolders")
):
    """Export JSON + validation for all test folders with full_regex.md."""
    export_batch(base)

if __name__ == "__main__":
    app()
