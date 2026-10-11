"""Export the approved budget experiment for manual upload under nmavros."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import zipfile
from prepare_byte_preserving_budget import preserve_extension_bytes

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/kaggle_budget_2026-10-11/manual'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original_plan = ROOT/'outputs/kaggle_budget_2026-10-11/plan.json'
    original_notebook = ROOT/'runs/kaggle_control/budget_2026-10-11/kernel/kaggle_baseline.ipynb'
    plan = json.loads(original_plan.read_text(encoding='utf-8'))
    for name, digest in plan['input_hashes'].items():
        assert sha(ROOT/name) == digest, name
    assert sha(ROOT/'notebooks/kaggle_budget_diagnostic.py') == plan['extension_sha256']
    packet = ROOT/'outputs/kaggle_resume_input_literature.zip'
    with zipfile.ZipFile(packet) as archive:
        assert set(archive.namelist()) == {'kaggle_project.zip', 'ASCAD.h5',
                                         'ASCAD.provenance.json', 'sca_runs_minimal_v3_literature.zip'}
        assert archive.testzip() is None
    revised = dict(plan)
    revised.update(notebook_ref='nmavros/hw-sec-exp2',
        notebook_ref_status='Intended manual-upload title; actual URL must be recorded after creation',
        original_frozen_plan_sha256=sha(original_plan),
        account_revision={'previous_owner':'con1los','authorized_owner':'nmavros',
            'mode':'Manual upload; one active continuation notebook in the new account',
            'authorization':'User requested using nmavros and asked to prepare the notebook for manual execution',
            'scientific_protocol_changed':False,'new_training_authorization':False,
            'original_private_notebook_preserved':True},
        input_delivery='Upload unchanged kaggle_resume_input_literature.zip as a private Dataset in nmavros and attach it',
        manual_export_utc=datetime.now(timezone.utc).isoformat())
    notebook = json.loads(original_notebook.read_text(encoding='utf-8'))
    notebook['cells'][0]['source'] = (
        '# ASCAD: approved 45k baseline\n\n'
        'Account: nmavros. One additional baseline only, total cap5.\n'
        'Same CNN16952 / seed0 / 50epochs / batch50 / author LR cycle.\n'
        'Training45k / shared validation5k / training-only MinMax. No combined or attack.\n\n'
        '## Before execution\n'
        '1. Upload kaggle_resume_input_literature.zip as a PRIVATE Dataset and attach it with Add Input.\n'
        '2. Enable Internet and GPU (prefer Tesla T4). Keep notebook private.\n'
        '3. Execute once using Save Version > Save & Run All. Do not run interactively first.\n'
        '4. Download budget_diagnostic_results.zip from Output after completion.\n\n'
        'The input archive contains code, official ASCAD and the preserved original checkpoint. '
        'No API key is needed inside this notebook. The original con1los study is preserved.\n')
    execute = preserve_extension_bytes(notebook['cells'][-1]['source'],ROOT/'notebooks/kaggle_budget_diagnostic.py')
    old_literal = repr(json.dumps(plan))
    assert old_literal in execute
    execute = execute.replace(old_literal, repr(json.dumps(revised)))
    needle = "shutil.make_archive('/kaggle/working/budget_diagnostic_results'"
    assert needle in execute
    run_line = "result=run_experiment(DATASET_PATH,RUN_ROOT/'none_seed0',Path('/kaggle/working/budget_diagnostic'),frozen_plan)"
    assert run_line in execute
    prefix = execute[:execute.index(run_line)]
    execute = prefix + (
        "from sca.train import write_json\n"
        "experiment_output=Path('/kaggle/working/budget_diagnostic')\n"
        "try:\n"
        f"    {run_line}\n"
        "except Exception as error:\n"
        "    experiment_output.mkdir(parents=True,exist_ok=True)\n"
        "    write_json(experiment_output/'execution_failure.json',{'complete':False,'error_type':type(error).__name__,'message':str(error),'automatic_retry':False})\n"
        "    raise\n"
        "finally:\n"
        "    if experiment_output.exists():\n"
        "        write_json(experiment_output/'account_revision.json',frozen_plan['account_revision'])\n"
        "        shutil.make_archive('/kaggle/working/budget_diagnostic_results','zip',experiment_output)\n"
        "        print('Download from Output: budget_diagnostic_results.zip')\n")
    notebook['cells'][-1]['source'] = execute
    notebook['metadata']['kaggle'] = {'isInternetEnabled':True,'isGpuEnabled':True,
                                     'language':'python','sourceType':'notebook'}
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code':
            assert cell.get('execution_count') is None and cell.get('outputs') == []
            compile(cell['source'], 'manual-notebook', 'exec')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'plan.json').write_text(json.dumps(revised, indent=2), encoding='utf-8')
    path = OUT/'kaggle_baseline.ipynb'
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding='utf-8')
    record = {'prepared':True,'submitted':False,'executed':False,'owner':'nmavros',
        'original_plan_sha256':sha(original_plan),'revised_plan_sha256':sha(OUT/'plan.json'),
        'notebook_sha256':sha(path),'input_sha256':sha(packet),'input_bytes':packet.stat().st_size,
        'input_zip_integrity_verified':True,'compiled_code_cells':sum(c['cell_type']=='code' for c in notebook['cells']),
        'scientific_protocol_changed':False,'original_notebook_sha256':sha(ROOT/'notebooks/kaggle_baseline.ipynb')}
    (OUT/'packaging_verification.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(record, indent=2))


if __name__ == '__main__': main()
