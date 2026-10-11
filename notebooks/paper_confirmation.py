"""One proposed combined training followed by a separately authorized locked evaluation."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
import torch

from kaggle_budget_diagnostic import train_with_cycle
from sca.augment import augment_batch
from sca.data import normalize, sha256_file, load_validation_evaluation
from sca.evaluate import evaluate
from sca.metrics import evaluate_key_recovery
from sca.models import build_model
from sca.train import code_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/paper_confirmation_2026-10-11'
REFERENCE = ROOT/'runs/kaggle_control/budget_2026-10-11/nmavros/output_v2/extracted/none_seed0'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def require_authorization(plan, authorization, action):
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    if (authorization.get('plan_identity') != digest or
            authorization.get('approved_full_gpu_training_cap') != 6 or
            authorization.get('specific_user_agreement') is not True or
            authorization.get(action + '_authorized') is not True):
        raise PermissionError('Specific agreement for this frozen plan is required')


def verify_reference(reference, plan):
    for name, digest in plan['baseline_hashes'].items():
        if sha256_file(Path(reference)/name) != digest:
            raise ValueError('Frozen baseline changed: ' + name)
    if code_identity()['source_sha256'] != plan['production_source_sha256']:
        raise ValueError('Frozen production source changed')


def combined_config(reference_config, dataset, output, extension_hash):
    config = dict(reference_config)
    config.update(dataset=str(dataset), run_dir=str(Path(output)/'combined_seed0'),
                  device='cuda', augmentation={'noise_std':.1, 'max_shift':5, 'padding':'zero'},
                  confirmation_extension_sha256=extension_hash)
    return config


def save_clean_predictions(dataset, run, output):
    state = torch.load(Path(run)/'best.pt', map_location='cpu', weights_only=False)
    indices = np.load(Path(run)/'splits.npz')['validation']
    traces, plaintext, key = load_validation_evaluation(dataset, indices, 2)
    traces = normalize(traces, state['normalizer'])
    model = build_model('cnn_literature').cuda()
    model.load_state_dict(state['model']); model.eval()
    with torch.no_grad():
        lp = np.concatenate([torch.log_softmax(model(torch.from_numpy(traces[i:i+256]).cuda()).double(), dim=1).cpu().numpy()
                             for i in range(0, len(traces), 256)])
    np.save(Path(output)/'log_probabilities.npy', lp)
    np.save(Path(output)/'plaintext_byte.npy', plaintext)
    write_json(Path(output)/'evaluation_key.json', {'true_key_byte':int(key), 'evaluation_only':True})


def run_combined(dataset, reference, output, plan, authorization):
    require_authorization(plan, authorization, 'combined_training')
    verify_reference(reference, plan)
    if sha256_file(dataset) != plan['dataset_sha256']:
        raise ValueError('Dataset changed')
    extension_hash = sha256_file(__file__)
    if extension_hash != plan['extension_sha256']:
        raise ValueError('Confirmation extension changed')
    if sha256_file(Path(__file__).with_name('kaggle_budget_diagnostic.py')) != plan['cycle_extension_sha256']:
        raise ValueError('Original optimizer extension changed')
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('No automatic repeat or overwrite')
    config = combined_config(read(Path(reference)/'config.json'), dataset, output, extension_hash)
    for key, value in plan['training_scope'].items():
        if config[key] != value:
            raise ValueError('Training scope mismatch: ' + key)
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    write_json(output/'plan.json', plan)
    write_json(output/'authorization.json', authorization)
    write_json(output/'access.json', {'started_utc':datetime.now(timezone.utc).isoformat(),
                                   'attack_payloads_read':False, 'new_training_started':True})
    summary = train_with_cycle(config)
    run = output/'combined_seed0'
    best = torch.load(run/'best.pt', map_location='cpu', weights_only=False)
    baseline = torch.load(Path(reference)/'best.pt', map_location='cpu', weights_only=False)
    assert best['normalizer'] == baseline['normalizer']
    fresh, old = np.load(run/'splits.npz'), np.load(Path(reference)/'splits.npz')
    assert all(np.array_equal(fresh[name], old[name]) for name in ('training', 'validation'))
    assert summary['parameters'] == 16952 and summary['optimization_steps'] == 45000
    validation = evaluate(run, plan['clean_validation_config'], device='cuda', split='validation', output_dir=output/'validation')
    save_clean_predictions(dataset, run, output/'validation')
    last = torch.load(run/'last.pt', map_location='cpu', weights_only=False)
    np.save(output/'learning_rates.npy', last['optimizer']['author_cycle']['used_rates'])
    verify_reference(reference, plan)
    result = {'complete':True, 'new_gpu_trainings':1, 'full_gpu_trainings_total':6,
              'attack_payloads_read':False, 'combined_training_performed':True,
              'selection_rule':'minimum clean validation CE', 'summary':summary,
              'validation':validation, 'experiment_seconds':time.perf_counter()-started}
    write_json(output/'results.json', result)
    print(json.dumps(result, indent=2), flush=True)
    return result


def paired_counts(baseline_ranks, combined_ranks):
    b, c = np.asarray(baseline_ranks)[:,-1] == 0, np.asarray(combined_ranks)[:,-1] == 0
    if b.shape != c.shape:
        raise ValueError('Paired order counts differ')
    return {'both_success':int((b & c).sum()), 'baseline_only':int((b & ~c).sum()),
            'combined_only':int((~b & c).sum()), 'neither_success':int((~b & ~c).sum()),
            'delta_sr':float(c.mean()-b.mean())}


def evaluate_locked_pair(baseline_run, combined_run, dataset, output, evaluation_config):
    """Evaluate fixed checkpoints; also used only on synthetic fixtures for correctness."""
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Evaluation output already exists')
    output.mkdir(parents=True, exist_ok=True)
    states = [torch.load(Path(p)/'best.pt', map_location='cpu', weights_only=False)
              for p in (baseline_run, combined_run)]
    assert states[0]['normalizer'] == states[1]['normalizer']
    for key in ('model','n_train','n_validation','seed','split_seed','target_byte'):
        assert states[0]['config'][key] == states[1]['config'][key], key
    a, b = np.load(Path(baseline_run)/'splits.npz'), np.load(Path(combined_run)/'splits.npz')
    assert all(np.array_equal(a[key],b[key]) for key in ('training','validation'))
    started = time.perf_counter()
    records, hashes = {}, {}
    for label, run in [('baseline',baseline_run), ('combined',combined_run)]:
        condition_index, input_hashes = 0, []
        current_hash = hashlib.sha256()
        def captured_augment(x, **kwargs):
            nonlocal current_hash
            value = augment_batch(x, **kwargs)
            current_hash.update(value.contiguous().numpy().tobytes())
            return value
        def captured_metrics(lp, plaintext, key, **kwargs):
            nonlocal condition_index, current_hash
            if time.perf_counter()-started > 600:
                raise RuntimeError('Frozen CPU evaluation cost cap exceeded')
            name = evaluation_config['conditions'][condition_index]['name']
            path = output/label
            np.save(path/(name+'_log_probabilities.npy'),lp)
            np.save(path/'plaintext_byte.npy',plaintext)
            write_json(path/'evaluation_key.json',{'true_key_byte':int(key),'evaluation_only':True})
            input_hashes.append(current_hash.hexdigest()); current_hash = hashlib.sha256()
            condition_index += 1
            return evaluate_key_recovery(lp, plaintext, key, **kwargs)
        with patch('sca.evaluate.augment_batch',captured_augment), patch('sca.evaluate.evaluate_key_recovery',captured_metrics):
            records[label] = evaluate(run,evaluation_config,device='cpu',split='attack',
                                     dataset_override=dataset,output_dir=output/label)
        hashes[label] = input_hashes
    assert hashes['baseline'] == hashes['combined'], 'Corrupted model inputs differ'
    paired = {}
    for condition in evaluation_config['conditions']:
        name = condition['name']
        ranks = [np.load(output/label/(name+'_curves.npz'))['ranks'] for label in ('baseline','combined')]
        paired[name] = paired_counts(*ranks)
    by_name = {label:{r['condition']:r for r in rows} for label,rows in records.items()}
    h1 = by_name['baseline']['clean']['sr_at_budget'] >= .9
    h2 = (by_name['combined']['combined_both_ood']['sr_at_budget'] >= .9 and
          paired['combined_both_ood']['delta_sr'] > 0 and by_name['combined']['clean']['sr_at_budget'] >= .9)
    result = {'complete':True, 'baseline_clean_confirmation_met':bool(h1),
              'augmentation_joint_primary_met':bool(h2), 'models':records,'paired':paired,
              'common_corrupted_inputs_sha256':hashes['baseline'], 'evaluation_seconds':time.perf_counter()-started,
              'model_corrupted_inputs_sha256':hashes,
              'new_optimizer_updates':0, 'selection_from_attack':False}
    size = len(np.load(output/'baseline/plaintext_byte.npy'))
    rng = np.random.default_rng(evaluation_config['attack_order_seed'])
    orders = np.asarray([rng.permutation(size)[:evaluation_config['budget']]
                         for _ in range(evaluation_config['repetitions'])])
    np.save(output/'attack_orders.npy', orders)
    result['attack_orders_sha256'] = sha256_file(output/'attack_orders.npy')
    write_json(output/'results.json',result)
    return result


def run_attack(dataset, combined_output, output, plan, authorization):
    require_authorization(plan, authorization, 'attack_evaluation')
    verify_reference(REFERENCE, plan)
    if sha256_file(dataset) != plan['dataset_sha256']:
        raise ValueError('Dataset changed before attack access')
    if sha256_file(__file__) != plan['extension_sha256']:
        raise ValueError('Frozen evaluator changed')
    combined_output, output = Path(combined_output), Path(output)
    training_verification = read(OUT/'training_verification.json')
    assert training_verification['verified'] and training_verification['attack_payloads_read'] is False
    assert read(combined_output/'plan.json') == plan
    for name,digest in training_verification['artifact_sha256'].items():
        assert sha256_file(combined_output/name) == digest, name
    if output.exists():
        raise FileExistsError('No attack rerun or overwrite')
    # The access receipt precedes the first attack payload read.
    write_json(OUT/'attack_access.json', {'started_utc':datetime.now(timezone.utc).isoformat(),
               'plan_identity':authorization['plan_identity'], 'baseline_best_sha256':sha256_file(REFERENCE/'best.pt'),
               'combined_best_sha256':sha256_file(combined_output/'combined_seed0/best.pt'),
               'all_model_choices_locked':True, 'variable_payloads_read':False})
    try:
        return evaluate_locked_pair(REFERENCE,combined_output/'combined_seed0',dataset,output,plan['attack_config'])
    except Exception as error:
        write_json(OUT/'attack_failure.json', {'complete':False, 'automatic_retry':False,
                   'error_type':type(error).__name__, 'error':str(error), 'partial_output':str(output)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--combined-output',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    plan, authorization = read(OUT/'plan.json'), read(OUT/'authorization.json')
    result = run_attack(ROOT/'data/ASCAD.h5',args.combined_output,args.output,plan,authorization)
    print(json.dumps({k:result[k] for k in ('complete','baseline_clean_confirmation_met','augmentation_joint_primary_met','evaluation_seconds')}))


if __name__ == '__main__':
    main()
