# smoke_import.py — minimal validator.
# Imports just the first 3 cells from the layout to confirm the
# import-and-spawn loop works end-to-end before kicking off a full
# 568-cell run that takes 5-10 minutes.
#
# Usage:
#   pwsh pipeline\ue-import\run_import.ps1 -Smoke
# Or directly:
#   UnrealEditor-Cmd ... -script="pipeline\ue-import\smoke_import.py"
import os
os.environ["AC_LAYOUT_LIMIT"] = "3"
# Then delegate to the real script.
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    "import_academy",
    str(Path(__file__).resolve().parent / "import_academy.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.exit(m.main() or 0)
