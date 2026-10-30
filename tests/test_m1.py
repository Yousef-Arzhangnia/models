"""M1 verification checks. Internal checks must pass; external checks are reported, not asserted."""
import pytest

from u4.models import absorption, electronics, laser, noise, sphere_pa, transducer, water
from u4.params import load

MODULES = {"1": sphere_pa, "5": laser, "7": absorption, "8": water, "10": transducer, "11": electronics, "12": noise}
P = load()


@pytest.mark.parametrize("model", list(MODULES))
def test_model_checks(model):
    checks = MODULES[model].checks(P)
    assert checks, "every model has at least one check"
    failed = [c for c in checks if c.kind == "internal" and not c.passed]
    assert not failed, "; ".join(f"{c.name}: expected {c.expected}, got {c.obtained}" for c in failed)


def test_chain_runs_both_presets():
    from u4.models import chain
    for preset in ("today", "upgrade1"):
        for d in P.si("cell.test_diameters"):
            r = chain.simulate(P, preset, d)
            assert r.info["snr_bp"] == r.info["snr_bp"]  # not NaN
            assert r.v_dig.size > 100


def test_upgrade1_gaps_unmoved():
    from u4.studies.m1 import _chain_checks
    from u4.models import chain
    res = {(p, d): chain.simulate(P, p, d) for p in ("today", "upgrade1") for d in P.si("cell.test_diameters")}
    internal = [c for c in _chain_checks(P, res) if c.kind == "internal"]
    assert internal and all(c.passed for c in internal)
