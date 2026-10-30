"""Run tracker: every study reports here, the board reads only this database.

Usage
-----
    from u4.tracker import Run
    with Run(model="1", study="sphere_gap_check", milestone="M1", params=p) as run:
        run.progress(0.5, "d = 7 um")
        run.check("gap 1 within 0.5 % of 1.43 c/d", passed=True, expected="1.4303", obtained="1.4301")
        run.result("first_gap_MHz", 184.7, unit="MHz", tag="[C]")
        run.figure(fig, name="spectrum")

The database is SQLite in WAL mode, so several runs can write while the board reads.
Every write is wrapped so that a tracker failure never stops a simulation.
"""
from __future__ import annotations

import json
import sqlite3
import time
import traceback
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .paths import DB_FILE, RUNS_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY, model TEXT, milestone TEXT, study TEXT, params TEXT,
    started REAL, ended REAL, status TEXT, progress REAL, message TEXT,
    log_path TEXT, stop_requested INTEGER DEFAULT 0, error TEXT
);
CREATE TABLE IF NOT EXISTS checks (
    run_id TEXT, model TEXT, name TEXT, expected TEXT, obtained TEXT, passed INTEGER,
    kind TEXT, note TEXT, t REAL
);
CREATE TABLE IF NOT EXISTS results (
    run_id TEXT, model TEXT, key TEXT, value REAL, unit TEXT, tag TEXT, text TEXT, t REAL
);
CREATE TABLE IF NOT EXISTS artefacts (
    run_id TEXT, model TEXT, name TEXT, kind TEXT, path TEXT, path2 TEXT, t REAL
);
CREATE INDEX IF NOT EXISTS ix_runs_model ON runs(model);
CREATE INDEX IF NOT EXISTS ix_checks_run ON checks(run_id);
CREATE INDEX IF NOT EXISTS ix_results_run ON results(run_id);
CREATE INDEX IF NOT EXISTS ix_art_run ON artefacts(run_id);
"""


class StopRequested(Exception):
    """Raised inside a run when the board's stop button was pressed."""


def connect(db: Path | None = None) -> sqlite3.Connection:
    db = Path(db or DB_FILE)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db, timeout=5.0, isolation_level=None)
    try:
        con.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:  # some network or virtual file systems refuse WAL
        con.execute("PRAGMA journal_mode=DELETE")
    con.execute("PRAGMA busy_timeout=5000")
    con.executescript(SCHEMA)
    con.row_factory = sqlite3.Row
    return con


@contextmanager
def _db(db: Path | None = None):
    con = connect(db)
    try:
        yield con
    finally:
        con.close()


def _jsonable(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        if isinstance(obj, dict):
            return {str(k): _jsonable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_jsonable(v) for v in obj]
        try:
            return float(obj)
        except Exception:
            return str(obj)


class Run:
    """Context manager that records one study run."""

    def __init__(self, model: str, study: str, milestone: str = "M1", params: dict | None = None,
                 db: Path | None = None, runs_dir: Path | None = None):
        self.id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.model, self.study, self.milestone = str(model), study, milestone
        self.params = params or {}
        self.db = Path(db or DB_FILE)
        self.dir = Path(runs_dir or RUNS_DIR) / self.id
        self.log_path = self.dir / "log.txt"
        self._checks: list[dict] = []
        self._last_write = 0.0

    # -- lifecycle ------------------------------------------------------------------------
    def __enter__(self) -> "Run":
        self.dir.mkdir(parents=True, exist_ok=True)
        self.t0 = time.time()
        self._safe(lambda c: c.execute(
            "INSERT INTO runs (id, model, milestone, study, params, started, status, progress, message, log_path)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (self.id, self.model, self.milestone, self.study, json.dumps(_jsonable(self.params)),
             self.t0, "running", 0.0, "started", str(self.log_path))))
        self.log(f"run {self.id} started: model {self.model}, study {self.study}")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is StopRequested:
            status, err = "stopped", "stopped from the board"
        elif exc_type is not None:
            status, err = "error", "".join(traceback.format_exception(exc_type, exc, tb))[-4000:]
        else:
            internal_fail = any((not c["passed"]) and c["kind"] == "internal" for c in self._checks)
            status, err = ("failed" if internal_fail else "passed"), None
        self.log(f"run finished: {status}")
        self._safe(lambda c: c.execute(
            "UPDATE runs SET ended=?, status=?, progress=?, message=?, error=? WHERE id=?",
            (time.time(), status, 1.0 if status in ("passed", "failed") else None,
             status if err is None else err.splitlines()[-1][:200], err, self.id)))
        return exc_type is StopRequested  # swallow stop requests, re-raise real errors

    # -- reporting ------------------------------------------------------------------------
    def progress(self, fraction: float, message: str = "") -> None:
        """Update progress (0 to 1). Throttled to one DB write per 0.2 s. Checks the stop flag."""
        now = time.time()
        if message:
            self.log(message)
        if now - self._last_write > 0.2 or fraction >= 1.0:
            self._last_write = now
            self._safe(lambda c: c.execute("UPDATE runs SET progress=?, message=? WHERE id=?",
                                           (float(max(0.0, min(1.0, fraction))), message, self.id)))
            if self.stop_requested():
                raise StopRequested()

    def stop_requested(self) -> bool:
        row = self._safe(lambda c: c.execute("SELECT stop_requested FROM runs WHERE id=?", (self.id,)).fetchone())
        return bool(row and row[0])

    def check(self, name: str, passed: bool, expected: Any = "", obtained: Any = "", kind: str = "internal",
              note: str = "", value: Any = None) -> bool:
        """Record a verification check. kind: internal (implementation must pass) or external
        (agreement with literature or bench data; a failure needs a decision, not a code fix)."""
        if value is not None and obtained == "":
            obtained = value
        rec = dict(name=name, expected=str(expected), obtained=str(obtained), passed=bool(passed), kind=kind, note=note)
        self._checks.append(rec)
        self.log(f"check [{'PASS' if passed else 'FAIL'}] {name}: expected {expected}, obtained {obtained}")
        self._safe(lambda c: c.execute(
            "INSERT INTO checks (run_id, model, name, expected, obtained, passed, kind, note, t) VALUES (?,?,?,?,?,?,?,?,?)",
            (self.id, self.model, name, str(expected), str(obtained), int(bool(passed)), kind, note, time.time())))
        return bool(passed)

    def checks(self, items: Iterable) -> None:
        for c in items:
            self.check(c.name, c.passed, c.expected, c.obtained, c.kind, c.note)

    def result(self, key: str, value: Any, unit: str = "", tag: str = "[C]", text: str = "") -> None:
        num = None
        try:
            num = float(value)
        except (TypeError, ValueError):
            text = text or str(value)
        self.log(f"result {key} = {value} {unit} {tag}")
        self._safe(lambda c: c.execute(
            "INSERT INTO results (run_id, model, key, value, unit, tag, text, t) VALUES (?,?,?,?,?,?,?,?)",
            (self.id, self.model, key, num, unit, tag, text, time.time())))

    def figure(self, fig, name: str) -> Path | None:
        """Save a matplotlib figure as PNG and SVG in the run folder and register it."""
        try:
            png, svg = self.dir / f"{name}.png", self.dir / f"{name}.svg"
            fig.savefig(png, dpi=150, bbox_inches="tight")
            fig.savefig(svg, bbox_inches="tight")
        except Exception as e:  # never stop a run because a figure failed
            self.log(f"figure {name} not saved: {e}")
            return None
        self._safe(lambda c: c.execute(
            "INSERT INTO artefacts (run_id, model, name, kind, path, path2, t) VALUES (?,?,?,?,?,?,?)",
            (self.id, self.model, name, "figure", str(png), str(svg), time.time())))
        return png

    def data(self, df, name: str) -> Path | None:
        """Save a pandas DataFrame as CSV (used by the pages' history overlay)."""
        try:
            path = self.dir / f"{name}.csv"
            df.to_csv(path, index=False)
        except Exception as e:
            self.log(f"data {name} not saved: {e}")
            return None
        self._safe(lambda c: c.execute(
            "INSERT INTO artefacts (run_id, model, name, kind, path, path2, t) VALUES (?,?,?,?,?,?,?)",
            (self.id, self.model, name, "data", str(path), "", time.time())))
        return path

    def log(self, msg: str) -> None:
        try:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now().strftime('%H:%M:%S')}  {msg}\n")
        except Exception:
            pass

    def _safe(self, fn):
        for attempt in range(3):
            try:
                with _db(self.db) as con:
                    return fn(con)
            except sqlite3.OperationalError:
                time.sleep(0.05 * (attempt + 1))
            except Exception:
                return None
        return None


# -- read side (board and pages) ----------------------------------------------------------
def query(sql: str, args: tuple = (), db: Path | None = None) -> list[dict]:
    try:
        with _db(db) as con:
            return [dict(r) for r in con.execute(sql, args).fetchall()]
    except Exception:
        return []


def request_stop(run_id: str, db: Path | None = None) -> None:
    with _db(db) as con:
        con.execute("UPDATE runs SET stop_requested=1 WHERE id=?", (run_id,))


def mark_stale(max_age_s: float = 6 * 3600, db: Path | None = None) -> None:
    """Runs still 'running' long after start (killed process) are marked as error."""
    with _db(db) as con:
        con.execute("UPDATE runs SET status='error', message='no end recorded (process killed?)' "
                    "WHERE status='running' AND started < ?", (time.time() - max_age_s,))


def runs(model: str | None = None, limit: int = 200, db: Path | None = None) -> list[dict]:
    if model is None:
        return query("SELECT * FROM runs ORDER BY started DESC LIMIT ?", (limit,), db)
    return query("SELECT * FROM runs WHERE model=? ORDER BY started DESC LIMIT ?", (str(model), limit), db)


def active_runs(db: Path | None = None) -> list[dict]:
    return query("SELECT * FROM runs WHERE status='running' ORDER BY started", (), db)


def run_checks(run_id: str, db: Path | None = None) -> list[dict]:
    return query("SELECT * FROM checks WHERE run_id=? ORDER BY t", (run_id,), db)


def run_results(run_id: str, db: Path | None = None) -> list[dict]:
    return query("SELECT * FROM results WHERE run_id=? ORDER BY t", (run_id,), db)


def run_artefacts(run_id: str, kind: str | None = None, db: Path | None = None) -> list[dict]:
    if kind:
        return query("SELECT * FROM artefacts WHERE run_id=? AND kind=? ORDER BY t", (run_id, kind), db)
    return query("SELECT * FROM artefacts WHERE run_id=? ORDER BY t", (run_id,), db)


def recent_figures(n: int = 6, db: Path | None = None) -> list[dict]:
    return query("SELECT a.*, r.study FROM artefacts a JOIN runs r ON a.run_id=r.id "
                 "WHERE a.kind='figure' ORDER BY a.t DESC LIMIT ?", (n,), db)


def latest_finished(model: str, db: Path | None = None) -> dict | None:
    rows = query("SELECT * FROM runs WHERE model=? AND status IN ('passed','failed','error','stopped') "
                 "ORDER BY started DESC LIMIT 1", (str(model),), db)
    return rows[0] if rows else None


def tail_log(path: str, n: int = 10) -> list[str]:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.readlines()[-n:]
    except Exception:
        return []
