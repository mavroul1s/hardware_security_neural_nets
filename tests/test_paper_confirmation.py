"""Authorization, paired-input and independent-ranking correctness checks."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'notebooks'))
import paper_confirmation as confirmation
from prepare_paper_confirmation import payload_cell,reference_archive,verify_payload_transport
from kaggle_budget_diagnostic import train_with_cycle
from sca.aes import SBOX
from sca.synthetic import create_fixture


@pytest.mark.parametrize('action',['combined_training','attack_evaluation'])
def test_specific_plan_and_cap_agreement_required_before_any_real_read(action):
    with pytest.raises(PermissionError):
        confirmation.require_authorization({}, {}, action)
    plan = {'frozen':True}
    authorization = {'plan_identity':hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest(),
                     'approved_full_gpu_training_cap':6,'specific_user_agreement':True,action+'_authorized':True}
    confirmation.require_authorization(plan,authorization,action)
    for field,value in [('plan_identity','different'),('approved_full_gpu_training_cap',5),('specific_user_agreement',False)]:
        invalid = {**authorization,field:value}
        with pytest.raises(PermissionError):confirmation.require_authorization(plan,invalid,action)
    with pytest.raises(PermissionError):
        confirmation.run_combined('missing.h5','missing','missing',plan,{})
    with pytest.raises(PermissionError):
        confirmation.run_attack('missing.h5','missing','missing',plan,{})


def test_combined_config_preserves_reference_and_only_declares_augmentation():
    reference = {'n_train':45000,'seed':0,'epochs':50,'batch_size':50,'augmentation':{'noise_std':0.,'max_shift':0,'padding':'zero'}}
    before = copy.deepcopy(reference)
    combined = confirmation.combined_config(reference,'dataset','output','extension')
    assert reference == before
    assert combined['augmentation'] == {'noise_std':.1,'max_shift':5,'padding':'zero'}
    assert all(combined[name] == reference[name] for name in ('n_train','seed','epochs','batch_size'))


def test_paired_discordances_retain_wins_losses_and_ties():
    baseline = np.array([[0],[5],[0],[2]])
    combined = np.array([[0],[0],[3],[7]])
    assert confirmation.paired_counts(baseline,combined) == {
        'both_success':1,'baseline_only':1,'combined_only':1,'neither_success':1,'delta_sr':0.}
    with pytest.raises(ValueError):confirmation.paired_counts(baseline,combined[:2])


def test_notebook_payload_preserves_crlf_and_reference_bytes(tmp_path):
    reference = tmp_path/'reference';reference.mkdir()
    (reference/'best.pt').write_bytes(b'fixture checkpoint\x00\xff')
    (reference/'config.json').write_bytes(b'{"seed":0}\r\n')
    packed = reference_archive(reference)
    assert reference_archive(reference) == packed
    cycle,extension = b'# original\r\nx=1\r\n',b'# extension\r\ny=2\r\n'
    digest = lambda value:hashlib.sha256(value).hexdigest()
    plan = {'cycle_extension_sha256':digest(cycle),'extension_sha256':digest(extension),
            'reference_zip_sha256':digest(packed),
            'baseline_hashes':{p.name:digest(p.read_bytes()) for p in reference.iterdir()}}
    source = payload_cell(plan,{},packed,cycle,extension)
    compile(source,'notebook-fixture','exec')
    verify_payload_transport(source,plan,cycle,extension)


def test_synthetic_pair_smoke_uses_common_corrupted_inputs_and_independent_ranks(tmp_path):
    dataset = tmp_path/'synthetic.h5';create_fixture(dataset,n_profiling=40,n_attack=12)
    config = {'dataset':str(dataset),'model':'cnn_literature','normalization':'feature_minmax_training_only',
              'target_byte':2,'seed':0,'split_seed':2026,'n_train':16,'n_validation':8,'epochs':2,
              'batch_size':4,'learning_rate':.005,'threads':1,'device':'cpu'}
    for label,augmentation in [('baseline',{'noise_std':0.,'max_shift':0,'padding':'zero'}),
                               ('combined',{'noise_std':.1,'max_shift':5,'padding':'zero'})]:
        train_with_cycle({**config,'run_dir':str(tmp_path/label),'augmentation':augmentation})
    evaluation = json.loads((ROOT/'configs/evaluation_final.json').read_text())
    evaluation.update(budget=6,repetitions=3,batch_size=4)
    output = tmp_path/'evaluated'
    result = confirmation.evaluate_locked_pair(tmp_path/'baseline',tmp_path/'combined',dataset,output,evaluation)
    assert len(result['models']['baseline']) == len(result['models']['combined']) == 8
    assert len(result['common_corrupted_inputs_sha256']) == 8 and result['new_optimizer_updates'] == 0
    assert all(row['synthetic'] for rows in result['models'].values() for row in rows)
    for label in ('baseline','combined'):
        plaintext = np.load(output/label/'plaintext_byte.npy')
        key = json.loads((output/label/'evaluation_key.json').read_text())['true_key_byte']
        for condition in evaluation['conditions']:
            name = condition['name'];lp = np.load(output/label/(name+'_log_probabilities.npy'))
            rng = np.random.default_rng(8001);expected = []
            for _ in range(3):
                order = rng.permutation(12)[:6]
                scores = np.zeros(256);ranks = []
                for row in order:
                    for candidate in range(256):scores[candidate] += lp[row,SBOX[plaintext[row]^candidate]]
                    ranks.append(sum(score >= scores[key] for score in scores)-1)
                expected.append(ranks)
            np.testing.assert_array_equal(expected,np.load(output/label/(name+'_curves.npz'))['ranks'])
