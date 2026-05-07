from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler(LOGS / "pipeline.log"), logging.StreamHandler()],
)
log = logging.getLogger("orchestrator")


STAGES = [
    ("profiling",  SCRIPTS / "data_profiling.py",                 False),
    ("cleaning",   SCRIPTS / "data_cleaning.py",                  True),
    ("features",   SCRIPTS / "feature_engineering.py",            True),
    ("diagram",    SCRIPTS / "generate_architecture_diagram.py",  False),
    ("quality",    SCRIPTS / "quality_checks.py",                 False),  # we tolerate non-critical fails
    ("analysis",   SCRIPTS / "analysis.py",                       True),
]


def run_stage(name: str, path: Path, must_succeed: bool) -> int:
    log.info("=" * 70)
    log.info(f"STAGE: {name}  →  {path.name}")
    log.info("=" * 70)
    t0 = time.time()
    rc = subprocess.call([sys.executable, str(path)])
    dt = time.time() - t0
    if rc == 0:
        log.info(f"✓ {name} completed in {dt:.1f}s")
    else:
        msg = f"✗ {name} failed (exit={rc}, {dt:.1f}s)"
        if must_succeed:
            log.error(msg + "  — pipeline aborting")
            return rc
        else:
            log.warning(msg + "  — non-blocking, continuing")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip", action="append", default=[], help="stage name to skip")
    ap.add_argument("--only", help="run only this stage")
    args = ap.parse_args()

    log.info("ABC Phones credit pipeline — starting")
    overall_t0 = time.time()

    stages = STAGES
    if args.only:
        stages = [s for s in STAGES if s[0] == args.only]
        if not stages:
            log.error(f"unknown stage: {args.only}")
            return 2
    elif args.skip:
        stages = [s for s in STAGES if s[0] not in args.skip]

    for name, path, must in stages:
        rc = run_stage(name, path, must)
        if rc != 0 and must:
            return rc

    log.info(f"Pipeline finished in {time.time() - overall_t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
