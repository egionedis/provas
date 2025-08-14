# src/cli.py
from pathlib import Path
import typer

app = typer.Typer(no_args_is_help=True, help="Prova Principal CLI")
DEFAULT_BASE = Path("provas")

@app.command("blocks")
def blocks_cmd(
    base: Path = typer.Option(
        DEFAULT_BASE, "--base", "-b",
        help="Base folder with exam subfolders (e.g. ./provas or a single ./provas/unicamp_2024)",
    )
):
    """Split each exam's full.md into '----' blocks and attach shared preambles."""
    from .prova_principal.blocks_fix_boundaries import blocks_batch
    blocks_batch(base)

if __name__ == "__main__":
    app()