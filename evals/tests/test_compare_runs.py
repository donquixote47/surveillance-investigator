"""compare_runs.py scores two runs with the labels of the dataset they were made on (2026-11-16: it used seed7's
labels for every run, so a comparison of two seed8 runs came out as "0 shared alerts")."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals"))

import compare_runs  # noqa: E402

RUNS = ROOT / "evals" / "runs"
SEED7_RUN = RUNS / "20261110T1833-sonnet-v4"
SEED8_RUN = RUNS / "20261111T1326-seed8-generalisation"

pytestmark = pytest.mark.skipif(
    not (SEED7_RUN / "run.json").exists()
    or not (SEED8_RUN / "run.json").exists()
    or not (ROOT / "data" / "synthetic" / "seed8" / "labels" / "labels.parquet").exists(),
    reason="the committed runs or the seed8 labels are not present",
)


def test_a_seed8_run_is_scored_with_seed8_labels(capsys) -> None:
    assert compare_runs.dataset_of(SEED8_RUN) == "seed8"
    assert compare_runs.main([str(SEED8_RUN), str(SEED8_RUN)]) == 0
    out = capsys.readouterr().out
    assert "100 shared alerts on dataset `seed8`" in out
    assert "Paired changes (0 of 100 alerts proposed differently)" in out
    assert "| safe close rate | 86.8% | 86.8% |" in out


def test_runs_on_different_datasets_are_refused(capsys) -> None:
    assert compare_runs.main([str(SEED7_RUN), str(SEED8_RUN)]) == 2
    assert "different datasets (seed7, seed8)" in capsys.readouterr().err
