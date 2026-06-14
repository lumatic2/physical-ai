"""Single-source sync for the twin's data JSONs.

Canonical copies live here (03/ root) — this is where the Python tooling reads/writes
them (render_twin.py, smoke_twin.py, the record_*.py generators). The deployed app fetches
its own copies from web/. Run this instead of the old manual `cp` so the two never drift.

  python sync_web.py           # copy every 03/*.json -> web/*.json (idempotent)
  python sync_web.py --check    # exit 1 if any web/ copy is missing or stale (no write)

The mirror set is auto-discovered (all top-level *.json), so adding a new trajectory can't
be forgotten. deploy_vercel.py runs the copy at startup, so production can never ship a
stale copy — that is the "sync omission impossible" guarantee.
"""
import sys, filecmp, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB = HERE / "web"
check = "--check" in sys.argv

srcs = sorted(HERE.glob("*.json"))
stale = []
for src in srcs:
    dst = WEB / src.name
    if dst.exists() and filecmp.cmp(src, dst, shallow=False):
        continue
    stale.append(src.name)
    if not check:
        shutil.copy2(src, dst)
        print(f"  synced  {src.name}")

if check:
    if stale:
        print("STALE — web/ out of sync (run `python sync_web.py`):")
        for n in stale:
            print(f"  - {n}")
        sys.exit(1)
    print(f"OK — web/ in sync ({len(srcs)} files)")
else:
    print(f"sync done: {len(stale)} updated, {len(srcs) - len(stale)} already current")
