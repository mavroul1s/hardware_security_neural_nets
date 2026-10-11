"""Quick-save canonical source after verified completion, without starting a run."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelRequest
from kagglesdk.kernels.types.kernels_enums import KernelExecutionType

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/kaggle_budget_2026-10-11/api'
CONTROL = ROOT/'runs/kaggle_control/budget_2026-10-11/nmavros'


def main():
    verification = json.loads((OUT/'verification.json').read_text())
    assert verification['verified'] and verification['full_gpu_trainings_total'] == 5
    assert not (OUT/'restoration.json').exists(), 'Restoration already recorded'
    source = ROOT/'notebooks/kaggle_baseline.ipynb'
    plan = json.loads((OUT/'plan.json').read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest() == plan['input_hashes']['notebooks/kaggle_baseline.ipynb']
    metadata = json.loads((CONTROL/'executed_v2/kernel-metadata.json').read_text())
    assert metadata['id'] == 'nmavros/hw-sec-exp2' and metadata['is_private']
    api = KaggleApi()
    api.authenticate()
    assert str(api.kernels_status(metadata['id']).status).endswith('.COMPLETE')
    request = ApiSaveKernelRequest()
    request.id = metadata['id_no']
    request.slug = metadata['id']
    request.new_title = metadata['title']
    request.text = source.read_text(encoding='utf-8')
    request.language = 'python'
    request.kernel_type = 'notebook'
    request.is_private = True
    request.enable_gpu = True
    request.enable_tpu = False
    request.enable_internet = True
    request.dataset_data_sources = metadata['dataset_sources']
    request.kernel_data_sources = []
    request.competition_data_sources = []
    request.model_data_sources = []
    request.docker_image_pinning_type = 'original'
    request.docker_image = metadata['docker_image']
    request.machine_shape = metadata['machine_shape']
    request.kernel_execution_type = KernelExecutionType.QUICK_SAVE
    with api.build_kaggle_client() as client:
        response = client.kernels.kernels_api_client.save_kernel(request)
    record = {'url': response.url, 'version': response.version_number,
              'error': response.error, 'invalid_dataset_sources': response.invalid_dataset_sources,
              'execution_type': 'QUICK_SAVE', 'new_training_started': False,
              'restored_original_source': True, 'recorded_utc': datetime.now(timezone.utc).isoformat(),
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    assert not record['error'] and not record['invalid_dataset_sources'], 'Quick save failed'
    (OUT/'restoration.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
