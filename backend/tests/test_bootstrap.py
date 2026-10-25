"""Bootstrap CI helper used in eval summaries."""

from hea.eval_agent import bootstrap_ci


def test_bootstrap_ci_bounds_contain_mean():
    vals = [1.0] * 20 + [0.0] * 5
    mean, lo, hi = bootstrap_ci(vals, n=500, seed=1)
    assert 0.7 < mean < 0.9
    assert lo <= mean <= hi
