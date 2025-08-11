from pathlib import Path
import typer
from ocr import run_ocr_batch
from clean import clean_batch
from export_json import export_single, export_batch

app = typer.Typer(help="Provas pipeline CLI")

@app.command()
def ocr(base: str = "provas"):
    """Run OCR over all tests that have full.md and images/."""
    run_ocr_batch(Path(base))

@app.command()
def clean(base: str = "provas"):
    """Normalize markdown (merge preambles, strip inline options)."""
    clean_batch(Path(base))

@app.command()
def export(path: str):
    """Export JSON + validation for a specific test folder (expects full_regex.md)."""
    export_single(Path(path) / "full_regex.md")

@app.command()
def export_all(base: str = "provas"):
    """Export JSON + validation for all test folders with full_regex.md."""
    export_batch(Path(base))

if __name__ == "__main__":
    app()
