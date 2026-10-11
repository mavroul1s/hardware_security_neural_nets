"""Freeze the explicitly approved 45k diagnostic in the existing Kaggle notebook."""
import json
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from prepare_recipe_diagnostic import sha, build_deployment
import prepare_recipe_diagnostic as previous
from sca.train import code_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/kaggle_budget_2026-10-11'
DEPLOY = ROOT / 'runs/kaggle_control/budget_2026-10-11/kernel'


def main():
    old = json.loads((ROOT / 'outputs/kaggle_recipe_2026-10-09/plan.json').read_text())
    plan_path = OUT / 'plan.json'
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        for name, digest in plan['input_hashes'].items():
            assert sha(ROOT / name) == digest
        assert sha(ROOT / 'notebooks/kaggle_budget_diagnostic.py') == plan['extension_sha256']
    else:
        suite = ET.parse(OUT / 'pytest.xml').getroot().find('testsuite').attrib
        assert int(suite['errors']) == int(suite['failures']) == 0
        assert int(suite['tests']) >= 104
        plan = dict(old)
        plan.update(
            authorization='User explicitly approved one baseline45k and cap5 on2026-10-11; no combined or attack authorization',
            hypothesis='Same adapted CNN/author cycle with45k training restores clean validation SR>=18/20 at2000',
            baseline='Completed recipe diagnostic10k/batch50/cycle/seed0/50epochs; reference old source checkpoint remains preserved',
            alternative='Same16952parameterCNN/seed0/50epochs/batch50/cycle, nested45k training and refitted training-only MinMax',
            budget='45000training/5000sharedvalidation/50epochs/2250000exposures/45000updates versus500000exposures/10000updates',
            confounds='Joint unique-sample/update-count/refitted-scaler diagnostic; not equal-compute or exact Keras reproduction',
            schedule_knot_updates=[0,18000,36000,45000],
            full_gpu_trainings_total_after_success=5,
            session_timeout_seconds=1800, training_loop_expected_cap_seconds=900,
            tests=suite, extension_sha256=sha(ROOT / 'notebooks/kaggle_budget_diagnostic.py'),
            input_hashes={str(p.relative_to(ROOT)).replace('\\','/'): sha(p) for p in [
                ROOT/'notebooks/kaggle_baseline.ipynb', ROOT/'outputs/kaggle_resume_input_literature.zip',
                ROOT/'notebooks/verify_budget_diagnostic.py', ROOT/'tests/test_kaggle_budget_diagnostic.py',
                OUT/'pytest.xml', ROOT/'docs/PAPER_NEXT_PROTOCOL_2026-10-11.md',
                ROOT/'outputs/kaggle_recipe_2026-10-09/results.json',
                ROOT/'outputs/paper_readiness_2026-10-11/audit.json']},
            frozen_utc=datetime.now(timezone.utc).isoformat())
        assert code_identity()['source_sha256'] == plan['production_source_sha256']
        write_json(plan_path, plan)
    # Reuse the packaging layout, replacing only the explicit extension and output name.
    previous.OUT, previous.DEPLOY = OUT, DEPLOY
    previous.build_deployment(plan)
    notebook_path = DEPLOY/'kaggle_baseline.ipynb'
    notebook = json.loads(notebook_path.read_text(encoding='utf-8'))
    extension = (ROOT/'notebooks/kaggle_budget_diagnostic.py').read_text(encoding='utf-8')
    old_extension = (ROOT/'notebooks/kaggle_recipe_diagnostic.py').read_text(encoding='utf-8')
    execute = notebook['cells'][-1]['source']
    execute = execute.replace(repr(old_extension), repr(extension))
    execute = execute.replace('kaggle_recipe_diagnostic', 'kaggle_budget_diagnostic')
    execute = execute.replace('recipe_diagnostic', 'budget_diagnostic')
    notebook['cells'][-1]['source'] = execute
    notebook['cells'][0]['source'] = 'Same private notebook: one approved45k budget diagnostic. No combined or attack. Original study preserved.'
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code': compile(cell['source'], 'notebook-cell', 'exec')
    notebook_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding='utf-8')
    deployment = json.loads((OUT/'deployment.json').read_text())
    deployment['notebook_sha256'] = sha(notebook_path)
    deployment['execution_status'] = 'prepared_not_submitted'
    write_json(OUT/'deployment.json', deployment)
    print(json.dumps({'frozen':True,'deployment':str(DEPLOY),'updates':45000,'total_trainings_cap':5}))


if __name__ == '__main__': main()
