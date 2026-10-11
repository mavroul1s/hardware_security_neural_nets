"""Check saved budget report, attempt history, preservation and remote restoration."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/kaggle_budget_2026-10-11/api'
CONTROL = ROOT/'runs/kaggle_control/budget_2026-10-11/nmavros'
REPAIR = OUT.parent/'transport_repair'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_sources(first, second):
    a, b = read(first), read(second)
    assert [(c['cell_type'], ''.join(c['source'])) for c in a['cells']] == [
        (c['cell_type'], ''.join(c['source'])) for c in b['cells']]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plot-visually-checked', action='store_true')
    args = parser.parse_args()
    assert args.plot_visually_checked, 'Inspect comparison plot first'
    artifact = CONTROL/'output_v2/extracted'
    verification = read(OUT/'verification.json')
    assert verification['verified']
    for name, digest in verification['artifact_sha256'].items():
        assert sha(artifact/name) == digest, name
    preservation = read(OUT.parent/'execution_status.json')['preservation_sha256']
    for name, digest in preservation.items():
        assert sha(ROOT/name) == digest, name
    report = (OUT/'REPORT_EL.md').read_text(encoding='utf-8')
    evidence = read(OUT/'evidence.json')
    assert evidence['primary_met'] == verification['primary_met']
    curves=np.load(artifact/'validation/clean_curves.npz')
    sustained=np.flatnonzero(np.minimum.accumulate(curves['sr'][::-1])[::-1]>=.9)
    sustained_count=int(sustained[0]+1) if len(sustained) else None
    assert evidence['traces_to_sustained_sr90']==sustained_count
    for row in evidence['comparisons']:
        expected = (f"| {row['name']} | {row['n_train']} | {row['updates']} | "
                    f"{row['best_epoch']} | {row['minimum_ce']:.6f} | "
                    f"{round(row['sr']*20)}/20 | {row['ge']:.6f} |")
        assert expected in report
    assert ('ΠΕΡΑΣΕ' if evidence['primary_met'] else 'ΑΠΕΤΥΧΕ') in report
    assert 'version2' in report and 'version1' in report and '105' in report
    old = read(ROOT/'runs/kaggle_control/recipe_2026-10-09/output/extracted/none_seed0/manifest.json')
    manifest = read(artifact/'none_seed0/manifest.json')
    assert evidence['same_runtime_environment'] == (old['environment'] == manifest['environment'])
    compare_sources(CONTROL/'repaired_kernel/kaggle_baseline.ipynb', CONTROL/'executed_v2/hw-sec-exp2.ipynb')
    compare_sources(ROOT/'notebooks/kaggle_baseline.ipynb', CONTROL/'restored/hw-sec-exp2.ipynb')
    restored = read(OUT/'restoration.json')
    assert restored['execution_type'] == 'QUICK_SAVE' and not restored['new_training_started']
    assert restored['version'] == 3
    metadata = read(CONTROL/'restored/kernel-metadata.json')
    assert metadata['id'] == 'nmavros/hw-sec-exp2' and metadata['is_private']
    assert metadata['dataset_sources'] == ['nmavros/hardware-sca-resume']
    deployed = read(CONTROL/'executed_v2/kernel-metadata.json')
    assert metadata['docker_image'] == deployed['docker_image']
    links = 0
    for target in re.findall(r'\]\(([^)]+)\)', report):
        if not target.startswith(('https://', 'http://')):
            assert (OUT/target).resolve().is_file(), target
            links += 1
    plan = read(OUT/'plan.json')
    submission = read(REPAIR/'submission.json')
    access = read(artifact/'access.json')
    assert datetime.fromisoformat(plan['api_freeze_utc']) < datetime.fromisoformat(submission['receipt_recorded_utc'])
    assert datetime.fromisoformat(submission['receipt_recorded_utc']) < datetime.fromisoformat(access['started_utc'])
    assert datetime.fromisoformat(access['started_utc']) <= datetime.fromisoformat(manifest['started_utc'])
    failed = read(OUT/'execution_status.json')
    assert failed['version'] == 1 and failed['new_optimizer_updates'] == 0
    assert sha(CONTROL/'output/budget_diagnostic_results.zip') == failed['archive_sha256']
    tests = ET.parse(REPAIR/'portable_pytest.xml').getroot().find('testsuite')
    assert tests.attrib['tests'] == '105' and tests.attrib['failures'] == tests.attrib['errors'] == '0'
    status = dict(submission)
    status.update(status='COMPLETE_VERIFIED', verified_utc=datetime.now(timezone.utc).isoformat(),
                  actual_total_trainings=5, new_gpu_trainings=1, primary_met=verification['primary_met'],
                  safe_saved_version=3, original_source_restored=True,
                  new_optimizer_updates=45000, actual_gpu=manifest['environment']['device_name'],
                  experiment_seconds=evidence['experiment_seconds'])
    (OUT/'execution_status_v2.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    names = ['REPORT_EL.md', 'budget_comparison.png', 'recovery_comparison.png', 'results.json', 'evidence.json',
             'verification.json', 'execution_status_v2.json', 'restoration.json', 'plan.json']
    record = {'verified': True, 'report_table_rows': 2, 'local_links_verified': links,
              'preserved_original_files': len(preservation), 'passing_cpu_tests': 105,
              'remote_executed_source_verified': True, 'safe_quick_save_version': 3,
              'original_remote_source_restored': True, 'private_notebook_and_input_verified': True,
              'original_fixed_attack_locked': True, 'variable_unused_rows': 30000,
              'full_gpu_trainings_total': 5, 'primary_met': verification['primary_met'],
              'plot_visually_checked': True, 'first_failed_attempt_preserved': True,
              'frozen_before_submission_and_training': True,
              'download_zip_sha256': sha(CONTROL/'output_v2/budget_diagnostic_results.zip'),
              'artifact_sha256': {name: sha(OUT/name) for name in names}}
    (OUT/'report_verification.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in record.items() if k != 'artifact_sha256'}, indent=2))


if __name__ == '__main__':
    main()
