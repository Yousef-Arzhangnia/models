"""Command line: python -m u4 run <study> | run m1 | list | checks."""
from __future__ import annotations

import argparse
import sys
import time

from .params import load
from .tracker import Run, mark_stale


def main(argv=None) -> int:
    from .studies import load_all
    reg = load_all()
    ap = argparse.ArgumentParser(prog="python -m u4", description="Upgrade 4 models: run studies through the tracker.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run a study (or 'm1' for all M1 studies)")
    r.add_argument("study")
    r.add_argument("--steps", type=int, default=30, help="demo only: number of steps")
    r.add_argument("--dt", type=float, default=1.0, help="demo only: seconds per step")
    sub.add_parser("list", help="list studies")
    args = ap.parse_args(argv)

    if args.cmd == "list":
        for name, s in reg.items():
            print(f"{name:16s} model {s['model']:6s} {s['milestone']}  {s['title']}")
        return 0

    names = [args.study]
    if args.study.lower() == "m1":
        from .studies.m1 import M1_STUDIES
        names = M1_STUDIES
    try:
        mark_stale()
    except Exception:
        pass
    P = load()
    status = 0
    for name in names:
        if name not in reg:
            print(f"unknown study '{name}'. Use: python -m u4 list")
            return 2
        s = reg[name]
        t0 = time.time()
        params = {"params_file": str(P.source), "params_version": P.value("meta.params_version")}
        with Run(model=s["model"], study=name, milestone=s["milestone"], params=params) as run:
            kwargs = dict(steps=args.steps, dt=args.dt) if name == "demo" else {}
            s["fn"](P, run, **kwargs)
        from .tracker import query
        row = query("SELECT status FROM runs WHERE id=?", (run.id,))
        st = row[0]["status"] if row else "?"
        print(f"{name:16s} {st:8s} {time.time()-t0:6.1f} s   run {run.id}")
        if st not in ("passed",):
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
