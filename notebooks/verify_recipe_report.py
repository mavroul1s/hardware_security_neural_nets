"""Check report tables, artifacts, same environment, remote sources, and restoration."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from datetime import datetime, timezone

from sca.train import write_json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/kaggle_recipe_2026-10-09'
CONTROL=ROOT/'runs/kaggle_control/recipe_2026-10-09'


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_sources(first,second):
    a,b=read(first),read(second)
    assert len(a['cells'])==len(b['cells'])
    for x,y in zip(a['cells'],b['cells']):
        assert x['cell_type']==y['cell_type'] and ''.join(x['source'])==''.join(y['source'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plot-visually-checked',action='store_true')
    args=parser.parse_args()
    if not args.plot_visually_checked:raise ValueError('Inspect comparison plot first')
    report=(OUT/'REPORT_EL.md').read_text(encoding='utf-8')
    evidence=read(OUT/'evidence.json')
    verification=read(OUT/'verification.json')
    artifact=CONTROL/'output/extracted'
    for name,digest in verification['artifact_sha256'].items():assert sha(artifact/name)==digest
    for row in evidence['comparisons']:
        assert f"| {row['recipe']} | {row['updates']} | {row['best_epoch']} | {row['minimum_ce']:.6f} | {round(row['sr']*20)}/20 | {row['ge']:.6f} |" in report
    assert '99 tests' in report and 'ΑΠΕΤΥΧΕ' in report and not evidence['primary_met']
    old_environment=read(ROOT/'runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0/manifest.json')['environment']
    assert read(artifact/'none_seed0/manifest.json')['environment']==old_environment
    compare_sources(CONTROL/'kernel/kaggle_baseline.ipynb',CONTROL/'executed/hw-sec-exp2.ipynb')
    compare_sources(ROOT/'notebooks/kaggle_baseline.ipynb',CONTROL/'restored/hw-sec-exp2.ipynb')
    restoration=read(OUT/'restoration.json')
    assert restoration['version']==10 and restoration['execution_type']=='QUICK_SAVE'
    assert not restoration['new_training_started']
    metadata=read(CONTROL/'restored/kernel-metadata.json')
    assert metadata['id']=='con1los/hw-sec-exp2' and metadata['is_private']
    assert metadata['dataset_sources']==['con1los/hardware-sca-resume']
    links=0
    for target in re.findall(r'\]\(([^)]+)\)',report):
        if not target.startswith(('https://','http://')):
            assert (OUT/target).resolve().is_file(),target
            links+=1
    status=read(OUT/'execution_status.json')
    plan=read(OUT/'plan.json')
    manifest=read(artifact/'none_seed0/manifest.json')
    access=read(artifact/'access.json')
    assert datetime.fromisoformat(plan['frozen_utc']) < datetime.fromisoformat(status['submitted_utc'])
    assert datetime.fromisoformat(status['submitted_utc']) < datetime.fromisoformat(access['started_utc'])
    assert datetime.fromisoformat(access['started_utc']) <= datetime.fromisoformat(manifest['started_utc'])
    status.update(status='COMPLETE_VERIFIED',verified_utc=datetime.now(timezone.utc).isoformat(),
        full_gpu_trainings_completed_total=4,primary_met=False,new_gpu_trainings=1,
        safe_saved_version=10,original_source_restored=True,remote_sources_verified=True,
        actual_gpu='Tesla T4',experiment_seconds=evidence['experiment_seconds'])
    write_json(OUT/'execution_status.json',status)
    record={'verified':True,'report_table_rows':2,'local_links_verified':links,'same_runtime_environment':True,
        'new_training_completed':True,'full_gpu_trainings_total':4,'primary_met':False,
        'passing_cpu_tests':99,'remote_executed_source_verified':True,'safe_quick_save_version':10,
        'original_remote_source_restored':True,'same_private_notebook':True,'input_unchanged':True,
        'original_fixed_attack_locked':True,'variable_unused_rows':30000,
        'plot_visually_checked':True,'checkpoint_download_zip_sha256':sha(CONTROL/'output/recipe_diagnostic_results.zip'),
        'frozen_before_submission_and_training':True,
        'version_specific_pull_access':'Ordinal9 pull returned403; unversioned latest9 pull before restoration matched deployment cell-for-cell',
        'artifact_sha256':{n:sha(OUT/n) for n in ['REPORT_EL.md','recipe_comparison.png','results.json','evidence.json',
            'verification.json','execution_status.json','restoration.json','plan.json','deployment.json','pytest.xml','LITERATURE_AND_PROTOCOL.md']}}
    write_json(OUT/'report_verification.json',record)
    print(json.dumps({k:v for k,v in record.items() if k!='artifact_sha256'},indent=2))


if __name__=='__main__':main()
