import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"notebooks"))
from paper_precision_replication import cluster_moments,moment_difference,cluster_bootstrap
from paper_selection_audit import fresh_rows


def test_cluster_sufficient_statistics_match_actual_duplicated_rows():
    rng=np.random.default_rng(25);a,b,y=rng.normal(size=(3,91));indices=np.arange(91)*7
    blocks,moments=cluster_moments(a,b,y,indices,100)
    choices=np.array([0,0,2,4,5])
    rows=np.concatenate([np.flatnonzero(indices//100==blocks[c]) for c in choices])
    expected=np.corrcoef(a[rows],y[rows])[0,1]-np.corrcoef(b[rows],y[rows])[0,1]
    assert moment_difference(moments[choices].sum(0))==pytest.approx(expected,abs=1e-12)


def test_cluster_bootstrap_is_paired_reproducible_and_handles_constant_features():
    rng=np.random.default_rng(26);a,y=rng.normal(size=(2,70))
    blocks,m=cluster_moments(a,a,y,np.arange(70),10)
    first,ids,state=cluster_bootstrap(m,count=65)
    second,ids2,state2=cluster_bootstrap(m,count=65)
    np.testing.assert_array_equal(first,np.zeros(65));np.testing.assert_array_equal(first,second)
    np.testing.assert_array_equal(ids,ids2);assert state==state2
    assert ids.shape==(65,len(blocks))
    _,m=cluster_moments(np.ones(70),np.ones(70),y,np.arange(70),10)
    assert moment_difference(m.sum(0))==0


def test_large_followup_holdouts_do_not_reuse_previous_rows():
    excluded=np.arange(30000)
    a=fresh_rows(200000,excluded,count=20000,seed=20261014)
    b=fresh_rows(200000,np.union1d(excluded,a),count=20000,seed=20261015)
    assert len(np.unique(np.concatenate((excluded,a,b))))==70000
    assert not np.intersect1d(a,b).size
    with pytest.raises(ValueError):cluster_moments(np.ones(3),np.ones(3),np.ones(3),np.arange(3),0)
