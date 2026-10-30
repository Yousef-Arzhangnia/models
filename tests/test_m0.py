"""M0: params.yaml loads, tracker records a run."""
import numpy as np

from u4.params import load, to_si
from u4 import tracker


def test_params_load_and_units():
    P = load()
    leaves = list(P.leaves())
    assert len(leaves) > 100
    for p in leaves:
        assert p.tag.startswith("[")
    assert np.isclose(P.si("today.laser.pulse_fwhm"), 1.3e-9)
    assert np.isclose(P.si("today.sample_light.peak_fluence"), 8.4e4)
    assert np.isclose(to_si(0.2, "1/cm"), 20.0)
    assert len(P.tbd()) > 10


def test_tracker_roundtrip(tmp_path):
    db = tmp_path / "s.sqlite"
    with tracker.Run(model="t", study="unit", milestone="M0", db=db, runs_dir=tmp_path) as run:
        run.progress(0.5, "half")
        run.check("trivial", True, 1, 1)
        run.result("x", 1.5, "MHz")
    rows = tracker.runs("t", db=db)
    assert rows[0]["status"] == "passed"
    assert tracker.run_checks(rows[0]["id"], db=db)[0]["passed"] == 1
    assert tracker.run_results(rows[0]["id"], db=db)[0]["value"] == 1.5


def test_tracker_stop(tmp_path):
    db = tmp_path / "s.sqlite"
    with tracker.Run(model="t", study="stop", db=db, runs_dir=tmp_path) as run:
        tracker.request_stop(run.id, db=db)
        import time; time.sleep(0.25)
        for i in range(5):
            run.progress(i / 5, "x")
            time.sleep(0.25)
    assert tracker.runs("t", db=db)[0]["status"] == "stopped"
