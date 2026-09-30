#!/usr/bin/env python3
"""IE-06b: registry diff-justification lint — "never edit a threshold to turn
a red gate green", enforced instead of hoped.

Schema lint (IE-06, registry_lint.py) cannot see intent: flipping
`higher_better` to the other VALID enum value, loosening a threshold, or
downgrading `blocking: hard` all pass schema. This lint compares the registry
against a git base ref and classifies every change; a GATE-WEAKENING change
blocks unless the same change set carries a written justification that names
the metric.

Weakening kinds (each one is a way a red gate quietly turns green):
  threshold_loosened   threshold moved in the passing direction
                       (higher_better: lowered · lower_better: raised)
  direction_flipped    higher_better <-> lower_better
  blocking_downgraded  hard -> soft/monitor_only, or soft -> monitor_only
  noise_band_widened   regression band widened (regressions hide inside it)
  hard_row_removed     a `blocking: hard` metric deleted outright
  detects_emptied      failure-mode links removed (orphaning the metric)

Strengthening changes (tightening, upgrades, new rows) pass without ceremony —
the ratchet only binds in the weakening direction.

Justification mechanism: a markdown file under evals/justifications/ that is
ADDED or MODIFIED in the same diff, mentions the metric by name, and carries
at least 200 characters of text. The justification file rides the same PR as
the weakening, so review sees the claim and the reason together.

CLI (repo root):
  python evals/runners/registry_diff_lint.py --base origin/main \\
      [--registry evals/metrics/registry.yaml] [--justifications evals/justifications]
Exit 0 = no weakening, or every weakening justified (each is printed);
1 = unjustified weakening; 2 = error. Exit code never crosses a pipe.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Weakening:
    metric: str
    kind: str
    detail: str


def _rows_by_name(rows: object) -> dict[str, dict]:
    if not isinstance(rows, list):
        return {}
    return {r["name"]: r for r in rows if isinstance(r, dict) and r.get("name")}


BLOCKING_RANK = {"hard": 2, "soft": 1, "monitor_only": 0}


def compare_registries(old_rows: object, new_rows: object) -> list[Weakening]:
    """Pure classification: every gate-weakening change between two registries."""
    old, new = _rows_by_name(old_rows), _rows_by_name(new_rows)
    out: list[Weakening] = []

    for name, o in old.items():
        n = new.get(name)
        if n is None:
            if o.get("blocking") == "hard":
                out.append(Weakening(name, "hard_row_removed",
                                     "a hard-blocking metric was deleted"))
            continue

        o_dir, n_dir = o.get("direction"), n.get("direction")
        if o_dir != n_dir:
            out.append(Weakening(name, "direction_flipped", f"{o_dir} -> {n_dir}"))

        try:
            o_thr, n_thr = float(o.get("threshold")), float(n.get("threshold"))
        except (TypeError, ValueError):
            o_thr = n_thr = None
        if o_thr is not None and n_thr != o_thr and o_dir == n_dir:
            loosened = n_thr < o_thr if n_dir == "higher_better" else n_thr > o_thr
            if loosened:
                out.append(Weakening(name, "threshold_loosened", f"{o_thr} -> {n_thr}"))

        o_blk, n_blk = o.get("blocking"), n.get("blocking")
        if (o_blk in BLOCKING_RANK and n_blk in BLOCKING_RANK
                and BLOCKING_RANK[n_blk] < BLOCKING_RANK[o_blk]):
            out.append(Weakening(name, "blocking_downgraded", f"{o_blk} -> {n_blk}"))

        try:
            o_band, n_band = float(o.get("noise_band")), float(n.get("noise_band"))
            if n_band > o_band:
                out.append(Weakening(name, "noise_band_widened", f"{o_band} -> {n_band}"))
        except (TypeError, ValueError):
            pass

        if o.get("detects") and not n.get("detects"):
            out.append(Weakening(name, "detects_emptied",
                                 f"was {o.get('detects')} -> empty"))
    return out


# --- justification lookup ----------------------------------------------------

MIN_JUSTIFICATION_CHARS = 200


def justified(weak: Weakening, changed_justifications: dict[str, str]) -> str | None:
    """Return the justification file path if this weakening is justified."""
    for path, text in changed_justifications.items():
        if weak.metric in text and len(text.strip()) >= MIN_JUSTIFICATION_CHARS:
            return path
    return None


# --- git plumbing --------------------------------------------------------------

def _git(repo: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout


def registry_at_base(repo: Path, base: str, registry_rel: str) -> object | None:
    code, out = _git(repo, "show", f"{base}:{registry_rel}")
    if code != 0:
        return None  # registry didn't exist at base -> nothing to weaken
    return yaml.safe_load(out)


def changed_justification_files(repo: Path, base: str, just_dir: str) -> dict[str, str]:
    code, out = _git(repo, "diff", "--name-only", base, "--", just_dir)
    rels = set(out.splitlines()) if code == 0 else set()
    # git diff never lists untracked files; a justification added in the same
    # change set may not be staged yet when the lint runs locally.
    code, out = _git(repo, "ls-files", "--others", "--exclude-standard", "--", just_dir)
    if code == 0:
        rels |= set(out.splitlines())
    files: dict[str, str] = {}
    for rel in rels:
        p = repo / rel.strip()
        if p.is_file() and p.suffix in (".md", ".txt"):
            files[rel.strip()] = p.read_text(encoding="utf-8", errors="replace")
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True,
                    help="git ref to diff against (e.g. origin/main, HEAD~1)")
    ap.add_argument("--registry", default="evals/metrics/registry.yaml")
    ap.add_argument("--justifications", default="evals/justifications")
    ap.add_argument("--repo", default=".")
    a = ap.parse_args(argv)

    repo = Path(a.repo).resolve()
    reg_path = repo / a.registry
    if not reg_path.is_file():
        print(f"FAIL: registry not found: {reg_path}", file=sys.stderr)
        return 2
    try:
        new_rows = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"FAIL: cannot parse {reg_path}: {exc}", file=sys.stderr)
        return 2

    old_rows = registry_at_base(repo, a.base, a.registry)
    if old_rows is None:
        print(f"registry-diff-lint: no registry at {a.base} — nothing to weaken; OK")
        return 0

    weakenings = compare_registries(old_rows, new_rows)
    if not weakenings:
        print(f"registry-diff-lint: no gate-weakening changes vs {a.base}; OK")
        return 0

    just_files = changed_justification_files(repo, a.base, a.justifications)
    unjustified: list[Weakening] = []
    for w in weakenings:
        j = justified(w, just_files)
        if j:
            print(f"  JUSTIFIED  {w.metric}: {w.kind} ({w.detail}) — by {j}")
        else:
            unjustified.append(w)
            print(f"  UNJUSTIFIED {w.metric}: {w.kind} ({w.detail})")

    if unjustified:
        print(f"\nBLOCK: {len(unjustified)} gate-weakening change(s) without a "
              f"justification file.\nAdd a markdown file under {a.justifications}/ "
              f"in this same change, naming each metric and explaining why the "
              f"gate is being weakened (>= {MIN_JUSTIFICATION_CHARS} chars). "
              f"\"Never edit a threshold to turn a red gate green.\"",
              file=sys.stderr)
        return 1
    print("\nregistry-diff-lint: every weakening carries a justification; OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
