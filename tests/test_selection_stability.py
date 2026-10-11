"""Paired sampling and selection sensitivity correctness; synthetic data only."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"notebooks"))
from paper_selection_stability import paired_training_draws,location_summary,sensitivity_summary
from paper_training_alignment import interior_selection,fit_simple_features,extract_simple


def test_paired_draws_preserve_pairing_size_duplicates_and_rng():
    draws,state=paired_training_draws(500,20)
    other,s=paired_training_draws(500,20)
    np.testing.assert_array_equal(draws,other);assert state==s
    assert draws.shape==(20,500) and draws.min()>=0 and draws.max()<500
    assert all(len(np.unique(row))<500 for row in draws)
    trace_ids=np.arange(500)*13;label_ids=trace_ids+7
    np.testing.assert_array_equal(label_ids[draws]-trace_ids[draws],np.full(draws.shape,7))
    with pytest.raises(ValueError):paired_training_draws(1)


def test_location_matches_report_swaps_and_tolerance_boundary():
    references=np.array([[30,90],[55,120]])
    pairs=np.array([references,references[::-1],[[35,95],[61,126]]])
    summary=location_summary(pairs,references,5)
    assert summary["ordered_hits"]==[2,1] and summary["either_family_hits"]==[3,2]
    assert summary["ordered_median_max_point_distance"]==[5.,6.]
    with pytest.raises(ValueError):location_summary(np.zeros((3,2)),references,5)


def test_sensitivity_threshold_is_joint_and_retains_negative_draws():
    yes=np.array([.07]*16+[-.01]*4)
    assert sensitivity_summary(yes)["support"]
    fail=np.array([.07]*15+[-.01]*5)
    summary=sensitivity_summary(fail)
    assert not summary["support"] and summary["minimum"]==-.01 and summary["positive_draws"]==15
    assert not sensitivity_summary(np.full(20,.049))["support"]
    assert not sensitivity_summary(np.zeros(20))["support"]
    with pytest.raises(ValueError):sensitivity_summary([float("nan")])


def test_duplicate_draw_selection_and_fit_match_explicit_original_subset():
    rng=np.random.default_rng(82);x=rng.normal(size=(700,180));y=x[:,45]*x[:,120]+.1*rng.normal(size=700)
    ids,_=paired_training_draws(len(x),1);ids=ids[0]
    pairs,count,matrix=interior_selection(x[ids],y[ids],margin=25,separation=30,diversity=10)
    assert pairs["pair1"]==[45,120]
    center=x[ids].mean(0)
    a=x[ids,45]-center[45];b=x[ids,120]-center[120]
    np.testing.assert_allclose(matrix[20,95],np.corrcoef(a*b,y[ids])[0,1],atol=1e-12)
    weights,info,_=fit_simple_features(x[ids],y[ids],pairs["pair1"])
    products=extract_simple(x[ids],center,pairs["pair1"],np.zeros(len(ids),dtype=np.int16),weights)
    assert np.isclose(np.corrcoef(products[:,2],y[ids])[0,1],info["training_correlations"]["covariance_rank1"])
