"""Submit exactly once after the specific frozen-plan approval; never retry."""
from datetime import datetime, timezone
import json
import subprocess

from paper_confirmation import OUT, ROOT, read, require_authorization
from prepare_paper_confirmation import DEPLOY
from sca.data import sha256_file
from sca.train import write_json


def main():
    plan,auth,prepared = read(OUT/'plan.json'),read(OUT/'authorization.json'),read(OUT/'preparation.json')
    require_authorization(plan,auth,'combined_training')
    assert prepared['specifically_authorized'] and prepared['execution_status'] == 'prepared_not_submitted'
    assert prepared['plan_sha256'] == sha256_file(OUT/'plan.json')
    assert prepared['authorization_sha256'] == sha256_file(OUT/'authorization.json')
    assert prepared['notebook_sha256'] == sha256_file(DEPLOY/'kaggle_baseline.ipynb')
    assert prepared['metadata_sha256'] == sha256_file(DEPLOY/'kernel-metadata.json')
    assert not (OUT/'submission_attempt.json').exists(), 'No automatic second submission'
    attempt = {'started_utc':datetime.now(timezone.utc).isoformat(),'notebook_ref':plan['notebook_ref'],
               'notebook_sha256':prepared['notebook_sha256'],'automatic_retry':False,'completed_cli_call':False}
    write_json(OUT/'submission_attempt.json',attempt)
    result = subprocess.run([str(ROOT/'.venv-kaggle/Scripts/kaggle.exe'),'kernels','push','-p','.',
                             '-t','1800','--accelerator','NvidiaTeslaT4'],cwd=DEPLOY,
                            capture_output=True,encoding='utf-8',errors='replace')
    attempt.update(completed_cli_call=True,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr,
                   finished_utc=datetime.now(timezone.utc).isoformat())
    write_json(OUT/'submission_attempt.json',attempt)
    print(json.dumps(attempt,indent=2))
    if result.returncode:raise RuntimeError('Single submission failed; no automatic retry')


if __name__ == '__main__':main()
