"""Schedule, optimizer continuation, and frozen-budget correctness checks."""
import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest
import torch

spec = importlib.util.spec_from_file_location("recipe", Path(__file__).parents[1]/"notebooks/kaggle_recipe_diagnostic.py")
recipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recipe)


def test_author_schedule_matches_independent_three_line_interpolation():
    expected = np.interp(np.arange(10001), [0,4000,8000,10000], [.0005,.005,.0005,.000005])
    actual = np.array([recipe.author_cycle_lr(i,10000) for i in range(10001)])
    np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-18)
    assert actual.argmax() == 4000 and np.all(actual > 0)


def test_optimizer_resume_preserves_parameters_moments_and_rates():
    parameter = torch.nn.Parameter(torch.tensor([1.0,-1.0]))
    optimizer = recipe.AuthorCycleAdam([parameter], .005, total_updates=10)
    for _ in range(4):
        optimizer.zero_grad(); (parameter.square().sum()).backward(); optimizer.step()
    saved = copy.deepcopy(optimizer.state_dict())
    restored_parameter = torch.nn.Parameter(parameter.detach().clone())
    restored = recipe.AuthorCycleAdam([restored_parameter],.005,total_updates=10)
    restored.load_state_dict(saved)
    for _ in range(6):
        for p,o in [(parameter,optimizer),(restored_parameter,restored)]:
            o.zero_grad(); p.square().sum().backward(); o.step()
        assert torch.equal(parameter,restored_parameter)
    assert optimizer.used_rates == restored.used_rates
    assert torch.equal(optimizer.state[parameter]['exp_avg'],restored.state[restored_parameter]['exp_avg'])
    with pytest.raises(RuntimeError,match="budget exhausted"):
        optimizer.step()


def test_schedule_identity_and_invalid_positions_are_rejected():
    p=torch.nn.Parameter(torch.ones(1))
    a=recipe.AuthorCycleAdam([p],.005,total_updates=10)
    b=recipe.AuthorCycleAdam([p],.005,total_updates=20)
    with pytest.raises(ValueError,match="identity mismatch"):b.load_state_dict(a.state_dict())
    for step,total in [(-1,10),(11,10),(0,4)]:
        with pytest.raises(ValueError):recipe.author_cycle_lr(step,total)


def test_frozen_trainer_cpu_smoke_and_completed_checkpoint_reuse(tmp_path):
    from sca.synthetic import create_fixture
    from sca.train import code_identity
    dataset=tmp_path/'synthetic.h5'
    create_fixture(dataset,n_profiling=40,n_attack=8)
    config={'dataset':str(dataset),'run_dir':str(tmp_path/'run'),'model':'cnn_literature',
        'normalization':'feature_minmax_training_only','target_byte':2,'seed':0,'split_seed':2026,
        'n_train':16,'n_validation':8,'epochs':2,'batch_size':4,'learning_rate':.005,
        'threads':1,'device':'cpu','augmentation':{'noise_std':0.,'max_shift':0,'padding':'zero'}}
    source=code_identity()['source_sha256']
    summary=recipe.train_with_cycle(config)
    checkpoint=torch.load(tmp_path/'run/last.pt',weights_only=False)
    assert summary['optimization_steps']==8
    assert checkpoint['optimizer']['author_cycle']['completed_updates']==8
    assert recipe.train_with_cycle(config,resume=True,reuse_completed=True)['optimization_steps']==8
    assert code_identity()['source_sha256']==source
    assert torch.optim.Adam is recipe.BaseAdam
