"""Record the specific human approval received on 2026-10-11, without submitting."""
from datetime import datetime, timezone
import json

from paper_confirmation import OUT, read
from prepare_paper_confirmation import plan_identity
from sca.train import write_json


def main():
    plan = read(OUT/'plan.json')
    old = read(OUT/'authorization.json')
    assert not old['specific_user_agreement'], 'Approval already recorded'
    write_json(OUT/'authorization_before_approval.json',old)
    authorization = {'plan_identity':plan_identity(plan),'specific_user_agreement':True,
        'approved_full_gpu_training_cap':6,'combined_training_authorized':True,'attack_evaluation_authorized':True,
        'user_answer':'Ναι, cap6 και τελική attack αξιολόγηση',
        'scope':'One combined45k submission; lock and independently verify both checkpoints before one CPU fixed-key attack evaluation, all8frozenconditions; no automatic retry or tuning',
        'received_utc':datetime.now(timezone.utc).isoformat()}
    write_json(OUT/'authorization.json',authorization)
    print(json.dumps({'recorded':True,'cap':6,'plan_identity':authorization['plan_identity']}))


if __name__ == '__main__':main()
