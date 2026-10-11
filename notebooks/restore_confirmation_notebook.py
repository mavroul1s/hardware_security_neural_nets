"""Restore original source using QUICK_SAVE only after both independent verifications."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelRequest,ApiGetKernelRequest
from kagglesdk.kernels.types.kernels_enums import KernelExecutionType

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/paper_confirmation_2026-10-11'


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    training,attack = read(OUT/'training_verification.json'),read(OUT/'attack_verification.json')
    assert training['verified'] and training['full_gpu_trainings_total'] == 6 and attack['verified']
    assert not (OUT/'restoration.json').exists(), 'Restoration already recorded'
    plan = read(OUT/'plan.json');source = ROOT/'notebooks/kaggle_baseline.ipynb'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_hash == plan['preservation_sha256']['notebooks/kaggle_baseline.ipynb']
    submission = read(OUT/'transport_repair/submission_attempt.json')
    api = KaggleApi();api.authenticate()
    assert str(api.kernels_status(plan['notebook_ref']).status).endswith('.COMPLETE')
    get = ApiGetKernelRequest();get.user_name = 'nmavros';get.kernel_slug = 'hw-sec-exp2'
    with api.build_kaggle_client() as client:
        metadata = client.kernels.kernels_api_client.get_kernel(get).metadata
    assert metadata.current_version_number == submission['version_number'] and metadata.is_private
    assert metadata.dataset_data_sources == plan['dataset_sources'] and metadata.docker_image == plan['docker_image']
    request = ApiSaveKernelRequest()
    request.id = metadata.id;request.slug = plan['notebook_ref'];request.new_title = metadata.title
    request.text = source.read_text(encoding='utf-8');request.language = 'python';request.kernel_type = 'notebook'
    request.is_private = True;request.enable_gpu = True;request.enable_tpu = False;request.enable_internet = True
    request.dataset_data_sources = plan['dataset_sources'];request.kernel_data_sources = []
    request.competition_data_sources = [];request.model_data_sources = []
    request.docker_image_pinning_type = 'original';request.docker_image = plan['docker_image']
    request.machine_shape = plan['accelerator'];request.kernel_execution_type = KernelExecutionType.QUICK_SAVE
    with api.build_kaggle_client() as client:
        response = client.kernels.kernels_api_client.save_kernel(request)
    record = {'url':response.url,'version':response.version_number,'error':response.error,
        'invalid_dataset_sources':response.invalid_dataset_sources,'execution_type':'QUICK_SAVE',
        'new_training_started':False,'restored_original_source':True,'source_sha256':source_hash,
        'preserved_executed_version':submission['version_number'],'recorded_utc':datetime.now(timezone.utc).isoformat()}
    assert not record['error'] and not record['invalid_dataset_sources']
    (OUT/'restoration.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2))


if __name__ == '__main__':main()
