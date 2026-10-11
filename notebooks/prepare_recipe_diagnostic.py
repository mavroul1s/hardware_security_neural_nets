"""Freeze one Kaggle optimizer-recipe diagnostic without modifying original artifacts."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from sca.train import code_identity, write_json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/kaggle_recipe_2026-10-09'
DEPLOY=ROOT/'runs/kaggle_control/recipe_2026-10-09/kernel'
OLD=ROOT/'runs/kaggle_control/literature_v7_output/runs/minimal_v3_literature/none_seed0'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (OUT/'plan.json').exists():
        plan=json.loads((OUT/'plan.json').read_text(encoding='utf-8'))
        for name,digest in plan['input_hashes'].items():assert sha(ROOT/name)==digest
        assert sha(ROOT/'notebooks/kaggle_recipe_diagnostic.py')==plan['extension_sha256']
        build_deployment(plan)
        return
    source=code_identity()['source_sha256']
    assert source=='84eff3cde04c0e9a1756a3d29c44ec82e115a1a08575132686a02520333e2b5c'
    tests=ET.parse(OUT/'pytest.xml').getroot().find('testsuite').attrib
    assert int(tests['tests'])==99 and int(tests['errors'])==int(tests['failures'])==0
    script=ROOT/'notebooks/kaggle_recipe_diagnostic.py'
    evaluation=json.loads((ROOT/'outputs/kaggle_literature_v7_2026-10-03/none/validation/evaluation_manifest.json').read_text())['evaluation_config']
    evaluation['conditions']=evaluation['conditions'][:1]
    baseline_names=['best.pt','last.pt','manifest.json','splits.npz','history.json','config.json']
    plan={
        'authorization':'User explicitly permitted a Kaggle experiment on2026-10-09; one further same-model baseline within cap4, same unique traces/epochs/seed, declared batch/schedule change',
        'hypothesis':'Published optimizer recipe adapted to the fixed10k sample restores clean validation SR>=18/20 at2000 compared with failed constant-LR batch128 baseline',
        'primary_endpoint':'Minimum-CE checkpoint clean validation SR@2000 over same20 trace orders',
        'primary_criterion':'SR>=0.90; all20 orders retained, no alternative success threshold',
        'secondary':'CE/accuracy/history/GE/sustainedSR and saved predictions, descriptive only',
        'baseline':'Completed literature16,952parameterCNN version7; same10k/5k/seed0/50epochs, batch128 constantAdam0.001',
        'alternative':'Same model and initializer, batch50, Adam linear author cycle max0.005/scale0.1/end0.2/no momentum cycling',
        'schedule_knot_updates':[0,4000,8000,10000],'schedule_knot_lr':[.0005,.005,.0005,.000005],
        'budget':'Same10000 unique training/5000validation/50epochs/500000 exposures;10000updates versus3950. Not equal-update compute comparison',
        'confounds':'Joint batch/schedule/update-count diagnostic; does not isolate causal factor or reproduce full45k Keras author recipe',
        'validation_status':'Previously viewed shared original5k profiling validation, not fresh confirmation. Its CE selects epoch; no efficacy claim on independent attack',
        'training_information':'Original identity labels; train-only per-position MinMax; model input traces alone',
        'new_confirmation_rows':0,'variable_unused_rows_unchanged':30000,'attack_payloads_read':False,
        'new_seeds':0,'new_models':0,'new_gpu_trainings_max':1,'full_gpu_trainings_total_after_success':4,
        'combined_training_authorized':False,'original_cnn_gate_preserved':True,'notebook_ref':'con1los/hw-sec-exp2',
        'stopping_rule':'One submission and one50epoch training; no HPO, restart, schedule search, extra seed or automatic combined. Stop on correctness/hash/nonfinite failure; preserve partial checkpoint and all negatives',
        'session_timeout_seconds':1200,'training_loop_expected_cap_seconds':600,
        'production_source_sha256':source,'dataset_sha256':sha(ROOT/'data/ASCAD.h5'),
        'extension_sha256':sha(script),'baseline_hashes':{n:sha(OLD/n) for n in baseline_names},
        'input_hashes':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in
            [ROOT/'notebooks/kaggle_baseline.ipynb',ROOT/'outputs/kaggle_resume_input_literature.zip',
             ROOT/'notebooks/verify_recipe_diagnostic.py',ROOT/'tests/test_kaggle_recipe_diagnostic.py',OUT/'pytest.xml',
             OUT/'LITERATURE_AND_PROTOCOL.md']},
        'evaluation_config':evaluation,'tests':tests,'frozen_utc':datetime.now(timezone.utc).isoformat(),
        'novelty_verified':False}
    write_json(OUT/'plan.json',plan)
    build_deployment(plan)


def build_deployment(plan):
    script=ROOT/'notebooks/kaggle_recipe_diagnostic.py'
    canonical=json.loads((ROOT/'notebooks/kaggle_baseline.ipynb').read_text(encoding='utf-8'))
    original_cells=[c for c in canonical['cells'] if c['cell_type']=='code']
    code=script.read_text(encoding='utf-8')
    execute=("from pathlib import Path\nimport json, shutil, sys\n"
        "extension_path=Path('/kaggle/working/kaggle_recipe_diagnostic.py')\n"
        f"extension_path.write_text({code!r},encoding='utf-8')\n"
        "sys.path.insert(0,'/kaggle/working')\nfrom kaggle_recipe_diagnostic import run_experiment\n"
        f"frozen_plan=json.loads({json.dumps(plan)!r})\n"
        "result=run_experiment(DATASET_PATH,RUN_ROOT/'none_seed0',Path('/kaggle/working/recipe_diagnostic'),frozen_plan)\n"
        "shutil.make_archive('/kaggle/working/recipe_diagnostic_results','zip','/kaggle/working/recipe_diagnostic')\n")
    cell=lambda text,kind='code':dict(cell_type=kind,metadata={},source=text,**({'execution_count':None,'outputs':[]} if kind=='code' else {}))
    notebook={**canonical,'cells':[cell('Same notebook: one frozen optimizer-recipe diagnostic. Original source/checkpoints/gate preserved. No combined or attack run.','markdown'),
        cell(''.join(original_cells[0]['source'])),cell(''.join(original_cells[1]['source'])),cell(execute)]}
    for c in notebook['cells']:
        if c['cell_type']=='code':compile(c['source'],'notebook-cell','exec')
    DEPLOY.mkdir(parents=True,exist_ok=True)
    path=DEPLOY/'kaggle_baseline.ipynb'
    path.write_text(json.dumps(notebook,ensure_ascii=False,indent=2),encoding='utf-8')
    metadata=json.loads((ROOT/'runs/kaggle_control/kernel/kernel-metadata.json').read_text(encoding='utf-8'))
    assert metadata['id']=='con1los/hw-sec-exp2' and metadata['is_private']
    write_json(DEPLOY/'kernel-metadata.json',metadata)
    write_json(OUT/'deployment.json',{'notebook_ref':metadata['id'],'notebook_sha256':sha(path),
        'metadata_sha256':sha(DEPLOY/'kernel-metadata.json'),'private':True,'new_remote_notebook':False,
        'canonical_v8_notebook_unchanged':True,'frozen_plan_sha256':sha(OUT/'plan.json')})
    print(json.dumps({'frozen':True,'new_gpu_trainings_max':1,'total_updates':10000,'passing_tests':99,'deployment':str(DEPLOY)},indent=2))


if __name__=='__main__':main()
