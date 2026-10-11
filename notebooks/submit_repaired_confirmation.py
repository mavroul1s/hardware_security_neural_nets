"""One separately approved corrected submission with a structured API receipt."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/paper_confirmation_2026-10-11'
REPAIR = OUT/'transport_repair'
DEPLOY = ROOT/'runs/kaggle_control/confirmation_2026-10-11/repaired_kernel'


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')


def main():
    plan,auth,prepared = read(OUT/'plan.json'),read(OUT/'authorization.json'),read(REPAIR/'preparation.json')
    approval = read(REPAIR/'corrected_submission_approval.json')
    assert auth['specific_user_agreement'] and auth['approved_full_gpu_training_cap'] == 6
    assert approval['specific_corrected_submission_agreement'] is True
    assert approval['frozen_plan_sha256'] == sha(OUT/'plan.json') == prepared['original_plan_sha256']
    assert approval['notebook_sha256'] == prepared['corrected_notebook_sha256'] == sha(DEPLOY/'kaggle_baseline.ipynb')
    assert prepared['corrected_metadata_sha256'] == sha(DEPLOY/'kernel-metadata.json')
    for name,digest in plan['input_hashes'].items():assert sha(ROOT/name) == digest,name
    assert not (REPAIR/'submission_attempt.json').exists(), 'No automatic third submission'
    attempt = {'started_utc':datetime.now(timezone.utc).isoformat(),'notebook_ref':plan['notebook_ref'],
               'notebook_sha256':prepared['corrected_notebook_sha256'],'automatic_retry':False}
    save(REPAIR/'submission_attempt.json',attempt)
    api = KaggleApi();api.authenticate()
    try:
        response = api.kernels_push(str(DEPLOY),timeout='1800',acc='NvidiaTeslaT4')
        attempt.update(version_number=response.version_number,url=response.url,error=response.error,
                       invalid_dataset_sources=response.invalid_dataset_sources,accepted=not bool(response.error))
        assert not response.error and not response.invalid_dataset_sources
    except Exception as error:
        http = getattr(error,'response',None)
        attempt.update(accepted=False,error_type=type(error).__name__,error=str(error))
        if http is not None:
            attempt.update(http_status=http.status_code,http_response_body=http.text[:2000])
        save(REPAIR/'submission_attempt.json',attempt)
        print(json.dumps(attempt,indent=2))
        raise
    attempt['finished_utc'] = datetime.now(timezone.utc).isoformat()
    save(REPAIR/'submission_attempt.json',attempt)
    print(json.dumps(attempt,indent=2))


if __name__ == '__main__':main()
