# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# --- Part 1: Fix Python's Path ---
# This adds the 'src' folder to Python's path so it can find your code.
try:
    src_path = Path(__file__).parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
except Exception as e:
    print(f"FATAL ERROR: Could not set up the system path. Error: {e}")
    sys.exit(1)

# --- Part 2: The Main Functions ---
def run_the_blocks_process():
    """Imports and runs the blocks_batch function."""
    try:
        from prova_principal.stp_01_blocks_fix_boundaries import blocks_batch
        base_directory = Path("provas")
        print("✅ Script started, running blocks_batch...")
        blocks_batch(base_directory)
        print("✅ Script finished.")
    except Exception as e:
        print(f"\n❌ An error occurred during the 'blocks' process: {e}")

def run_the_dedup_process():
    """Imports and runs the fix_batch function for deduplication."""
    try:
        from prova_principal.stp_02_blocks_fix_dedup import fix_batch
        base_directory = Path("provas")
        print("✅ Script started, running fix_batch (deduplication)...")
        fix_batch(base_directory)
        print("✅ Script finished.")
    except Exception as e:
        print(f"\n❌ An error occurred during the 'dedup' process: {e}")

def run_the_missing_process():
    """Imports and runs the fix_missing_batch function."""
    try:
        from prova_principal.stp_03_blocks_fix_missing import fix_missing_batch
        base_directory = Path("provas")
        print("✅ Script started, running fix_missing_batch...")
        fix_missing_batch(base_directory)
        print("✅ Script finished.")
    except Exception as e:
        print(f"\n❌ An error occurred during the 'missing' process: {e}")

def run_the_audit_process():
    """Imports and runs the final_audit_batch function."""
    try:
        from prova_principal.stp_04_blocks_fix_audit import final_audit_batch
        base_directory = Path("provas")
        print("✅ Script started, running final_audit_batch...")
        final_audit_batch(base_directory)
        print("✅ Script finished.")
    except Exception as e:
        print(f"\n❌ An error occurred during the 'audit' process: {e}")

def run_the_finalize_process():
    """Imports and runs the finalize_batch_from_audit function."""
    try:
        from prova_principal.stp_05_block_fix_llm import finalize_batch_from_audit
        base_directory = Path("provas")
        print("✅ Script started, running finalize_batch_from_audit...")
        finalize_batch_from_audit(base_directory)
        print("✅ Script finished.")
    except Exception as e:
        print(f"\n❌ An error occurred during the 'finalize' process: {e}")

def run_the_json_process():
    """Imports and runs the run function to generate final JSON."""
    try:
        from prova_principal.stp_06_blocks_final_json import run
        base_directory = Path("provas")
        print("✅ Script started, running final JSON generation...")
        run(base_directory)
        print("✅ Script finished.")
    except Exception as e:
        print(f"\n❌ An error occurred during the 'json' process: {e}")


# --- Part 3: Run the Code ---
# This is the entry point of the script.
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_this.py [command]")
        print("Commands: blocks, dedup, missing, audit, finalize, json")
        sys.exit(1)

    command = sys.argv[1]

    if command == "blocks":
        run_the_blocks_process()
    elif command == "dedup":
        run_the_dedup_process()
    elif command == "missing":
        run_the_missing_process()
    elif command == "audit":
        run_the_audit_process()
    elif command == "finalize":
        run_the_finalize_process()
    elif command == "json":
        run_the_json_process()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: blocks, dedup, missing, audit, finalize, json")
