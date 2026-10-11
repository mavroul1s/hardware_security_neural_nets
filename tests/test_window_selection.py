"""Window selector coordinate, objective, pairing and decision correctness only."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "notebooks"))
from paper_window_selection import window_means, select_box_pairs, oob_indices, summarize_pair
from paper_training_alignment import fit_simple_features


def test_window_means_match_direct_windows_and_center_translation():
    x = np.arange(4*190).reshape(4,190).astype(float)
    means = window_means(x)
    assert means.shape == (4,180)
    for center in (5,25,100,184):
        np.testing.assert_array_equal(means[:,center-5], x[:,center-5:center+6].mean(1))
    with pytest.raises(ValueError): window_means(x, 100)
    with pytest.raises(ValueError): window_means(x, -1)


def test_window_matrix_score_equals_box_feature_with_train_only_center():
    rng = np.random.default_rng(178)
    x = rng.normal(size=(450,190)) + np.arange(190)/9
    y = rng.normal(size=450)
    pairs, count, matrix = select_box_pairs(x,y,separation=30,diversity=10)
    assert count == len(np.triu_indices(140,k=30)[0])
    for pair in pairs.values():
        _, info, _ = fit_simple_features(x,y,pair)
        centered = x-x.mean(0)
        a,b = [centered[:,p-5:p+6].mean(1) for p in pair]
        direct = np.corrcoef(a*b,y)[0,1]
        np.testing.assert_allclose(matrix[pair[0]-25,pair[1]-25],direct,atol=1e-12)
        np.testing.assert_allclose(abs(direct),info['training_correlations']['box_product'],atol=1e-12)
    with pytest.raises(ValueError): select_box_pairs(x,y,margin=4)


def test_box_selector_uses_same_margin_constraints_and_deterministic_ties():
    rng = np.random.default_rng(24)
    x = rng.normal(size=(500,190)); a,b = rng.normal(size=(2,500))
    x[:,40:51]=a[:,None];x[:,115:126]=b[:,None];y=a*b
    pairs,count,matrix = select_box_pairs(x,y,separation=30,diversity=10)
    assert pairs['pair1'] == [45,120]
    assert count > 0
    assert all(25<=p<165 for pair in pairs.values() for p in pair)
    assert all(abs(p-q)>=10 for p in pairs['pair2'] for q in pairs['pair1'])
    assert pairs == select_box_pairs(x,y,separation=30,diversity=10)[0]


def test_oob_rows_exclude_all_duplicates_and_keep_label_pairing():
    ids=np.array([0,2,2,4,0,2],dtype=np.int32)
    np.testing.assert_array_equal(oob_indices(ids,6),[1,3,5])
    with pytest.raises(ValueError): oob_indices(np.array([6]),6)
    with pytest.raises(ValueError): oob_indices(np.array([1.]),6)


def test_paired_summary_preserves_draw_identity_and_negative_coefficients():
    b=np.r_[np.full(9,.09),np.full(11,-.2)]
    a=np.r_[np.full(11,.1),np.full(9,-.1)]
    s=summarize_pair(a,b)
    assert np.isclose(s['median_paired_difference'],.1)
    assert s['window_positive_draws']==11 and s['window_minimum']<0
    assert not np.isclose(s['median_paired_difference'],np.median(a)-np.median(b))
    with pytest.raises(ValueError): summarize_pair(a[:19],b[:19])
