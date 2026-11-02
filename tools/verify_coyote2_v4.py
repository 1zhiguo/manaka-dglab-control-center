"""Run the source controller against the loopback-only Coyote 2.0 APP."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from manaka_devices.coyote2_validation import run_validation
if __name__ == "__main__":
    destination = sys.argv[1] if len(sys.argv) > 1 else ROOT / "build/coyote2-validation/source.json"
    raise SystemExit(run_validation(destination))
