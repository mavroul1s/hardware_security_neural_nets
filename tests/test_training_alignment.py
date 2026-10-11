"""Synthetic checks verify coordinates and estimators, never physical efficacy."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"notebooks"))
from paper_alignment import shifted, estimate_offsets
from paper_training_alignment import (safe_template, align_training_once, offsets_batched,
    interior_selection, fit_simple_features, extract_simple, FEATURES)
from paper_selection_audit import correlation


def test_training_alignment_sign_original_rows_and_batch_invariance():
    rng=np.random.default_rng(41)
    waveform=rng.normal(size=180);waveform[:20]=0;waveform[-20:]=0
    x=np.tile(waveform,(51,1));d=np.tile(np.arange(-8,9,dtype=np.int16),3)
    observed=shifted(x,d)
    aligned,offsets,raw,refined=align_training_once(observed,bound=10,batch_size=7)
    np.testing.assert_array_equal(offsets,offsets_batched(observed,raw,10,13))
    np.testing.assert_array_equal(aligned,shifted(observed,-offsets))
    # Direct score minimum is the algorithm's definition; true synthetic shifts need not be recovered.
    expected,scores=estimate_offsets(observed,raw,"gaussian_template",10)
    np.testing.assert_array_equal(offsets,expected)
    assert scores.shape==(51,21) and refined["mean"].shape==(180,)


def test_template_floor_and_selection_ignore_padded_edges():
    rng=np.random.default_rng(44);x=rng.normal(size=(600,160));y=x[:,40]*x[:,105]
    alt=x.copy();alt[:,:10]=1e9*rng.normal(size=(600,10));alt[:,-10:]=1e9
    assert safe_template(x)["variance_floor"]==safe_template(alt)["variance_floor"]
    pairs,count,c=interior_selection(x,y,margin=25,separation=30,diversity=10)
    other,n,cc=interior_selection(alt,y,margin=25,separation=30,diversity=10)
    assert pairs==other and n==count and pairs["pair1"]==[40,105]
    np.testing.assert_array_equal(c,cc)
    assert c.shape==(110,110)


def test_feature_fit_direct_reference_and_rank_one_covariance_optimum():
    rng=np.random.default_rng(45);x=rng.normal(size=(1000,160));y=x[:,40]*x[:,105]+rng.normal(size=1000)*.2
    pair=[40,105];weights,info,c=fit_simple_features(x,y,pair,radius=2)
    p=((x[:,38:43]-x[:,38:43].mean(0))[:,:,None]*(x[:,103:108]-x[:,103:108].mean(0))[:,None,:]).reshape(len(x),-1)
    actual=extract_simple(x,x.mean(0),pair,np.zeros(len(x),dtype=np.int16),weights,radius=2)
    np.testing.assert_allclose(actual,np.column_stack([p@weights[n] for n in FEATURES]),atol=1e-12)
    assert np.isclose(weights["covariance_rank1"]@c,np.linalg.svd(c.reshape(5,5),compute_uv=False)[0])
    assert np.linalg.matrix_rank(weights["covariance_rank1"].reshape(5,5),tol=1e-10)==1
    for j,n in enumerate(FEATURES):assert np.isclose(info["training_correlations"][n],correlation(actual[:,j],y))


def test_shifted_extraction_matches_training_coordinates_and_padding_exclusion():
    rng=np.random.default_rng(46);x=rng.normal(size=(100,150));y=x[:,25]*x[:,120]
    pair=[25,120];weights,_,_=fit_simple_features(x,y,pair)
    d=rng.integers(-10,11,len(x),dtype=np.int16);observed=shifted(x,d)
    expected=extract_simple(x,x.mean(0),pair,np.zeros(len(x),dtype=np.int16),weights)
    actual=extract_simple(observed,x.mean(0),pair,d,weights)
    np.testing.assert_allclose(actual,expected,atol=1e-12)
    with pytest.raises(ValueError):extract_simple(x,x.mean(0),[3,120],d,weights)
    with pytest.raises(ValueError):offsets_batched(x,safe_template(x),batch_size=0)
    with pytest.raises(ValueError):interior_selection(x,y,margin=60)
    with pytest.raises(ValueError):fit_simple_features(x,np.ones(len(x)),pair)
