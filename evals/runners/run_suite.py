"""One candidate suite run -> evals/reports/candidate.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evals.runners.harness import ROOT, run_suite  # noqa: E402


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "evals/reports/candidate.json")
    result = run_suite()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result["scores"], indent=2))
    print(f"\ncandidate written -> {out}")


if __name__ == "__main__":
    main()
