"""
Utility script: run the detection loop once for one or more users.

Intended usage (from project root):

    DB_URL="postgresql://user:pass@host:5432/db" \\
      ./venv/bin/python backend/app/engine/run_loop_once.py --user-id 1

Notes:
- We treat DB_URL as a shorthand for DATABASE_URL for convenience when running
  this script from the shell.
- If DATABASE_URL is already set (e.g. via .env), it wins.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List

# Ensure backend/ is on sys.path so `import app...` works when invoked from repo root.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Bridge DB_URL -> DATABASE_URL before the SQLAlchemy engine is created.
if "DB_URL" in os.environ and not os.environ.get("DATABASE_URL"):
    _raw = os.environ["DB_URL"]
    # Normalize legacy postgres:// URLs for SQLAlchemy
    if _raw.startswith("postgres://"):
        _raw = "postgresql://" + _raw[len("postgres://") :]
    os.environ["DATABASE_URL"] = _raw

from app.core.database import SessionLocal  # noqa: E402
from app.engine.loop_runner import run_loop  # noqa: E402


log = logging.getLogger(__name__)


def _parse_user_ids(args: argparse.Namespace) -> List[int]:
    if getattr(args, "user_id", None) is not None:
        return [args.user_id]

    if getattr(args, "user_ids", None):
        raw = args.user_ids
    else:
        # Fallback to env var; reuse SCHEDULER_USER_IDS if already configured.
        raw = os.getenv("LOOP_USER_IDS") or os.getenv("SCHEDULER_USER_IDS") or "1"

    ids: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            log.warning("Ignoring non-numeric user id value: %r", part)
    if not ids:
        ids = [1]
    return ids


def main() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Run the health loop once for one or more users.")
    parser.add_argument("--user-id", type=int, help="Single user id to run the loop for.")
    parser.add_argument(
        "--user-ids",
        type=str,
        help="Comma-separated list of user ids (e.g. '1,2,3'). Overrides --user-id.",
    )
    args = parser.parse_args()

    user_ids = _parse_user_ids(args)

    db = SessionLocal()
    try:
        for uid in user_ids:
            try:
                log.info("Running loop for user_id=%s", uid)
                result = run_loop(db=db, user_id=uid)
                log.info("Loop result user_id=%s: created=%s suppressed=%s", uid, result.get("created"), result.get("suppressed"))
            except Exception:  # noqa: BLE001
                log.exception("Loop failed for user_id=%s", uid)
    finally:
        db.close()


if __name__ == "__main__":
    main()


