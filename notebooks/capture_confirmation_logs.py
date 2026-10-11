"""Capture UTF-8 logs without submitting or restarting the notebook."""
from datetime import datetime, timezone
import json
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/paper_confirmation_2026-10-11'
CONTROL = ROOT/'runs/kaggle_control/confirmation_2026-10-11'


def main():
    api = KaggleApi();api.authenticate()
    request = ApiGetKernelRequest();request.user_name = 'nmavros';request.kernel_slug = 'hw-sec-exp2'
    with api.build_kaggle_client() as client:
        metadata = client.kernels.kernels_api_client.get_kernel(request).metadata
    expected = json.loads((OUT/'transport_repair/submission_attempt.json').read_text(encoding='utf-8'))['version_number']
    assert metadata.current_version_number == expected
    status = {'started_utc':datetime.now(timezone.utc).isoformat(),'version':expected,'events':0,'readonly':True}
    try:
        with (CONTROL/'live_logs.jsonl').open('a',encoding='utf-8') as log:
            for event in api.kernels_logs_stream('nmavros/hw-sec-exp2'):
                log.write(json.dumps(event,ensure_ascii=False)+'\n');log.flush()
                status['events'] += 1
                data = event.get('data','')
                if any(word in data for word in ('"epoch":','Error','passed','Preserved output','"complete":')):
                    print(data[-2000:],flush=True)
        status['stream_completed'] = True
    except Exception as error:
        status.update(stream_completed=False,error_type=type(error).__name__,error=str(error))
        print(json.dumps({'readonly_stream_disconnected':True,'error_type':type(error).__name__}),flush=True)
    status['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (OUT/'log_capture_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    print(json.dumps(status,indent=2),flush=True)


if __name__ == '__main__':main()
