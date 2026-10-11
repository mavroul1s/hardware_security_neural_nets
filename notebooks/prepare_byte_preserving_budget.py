"""Prepare a correction that transports the original extension bytes exactly."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'runs/kaggle_control/budget_2026-10-11/nmavros/kernel'
OUT=ROOT/'outputs/kaggle_budget_2026-10-11/transport_repair'
DEPLOY=ROOT/'runs/kaggle_control/budget_2026-10-11/nmavros/repaired_kernel'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def preserve_extension_bytes(source, script):
    previous=f"extension_path.write_text({script.read_text(encoding='utf-8')!r},encoding='utf-8')"
    assert source.count(previous)==1
    return source.replace(previous,f"extension_path.write_bytes({script.read_bytes()!r})")


def main():
    plan=json.loads((ROOT/'outputs/kaggle_budget_2026-10-11/api/plan.json').read_text())
    script=ROOT/'notebooks/kaggle_budget_diagnostic.py'
    original_bytes=script.read_bytes()
    assert sha(script)==plan['extension_sha256']
    nb=json.loads((OLD/'kaggle_baseline.ipynb').read_text(encoding='utf-8'))
    nb['cells'][-1]['source']=preserve_extension_bytes(nb['cells'][-1]['source'],script)
    for cell in nb['cells']:
        if cell['cell_type']=='code':compile(cell['source'],'repaired-notebook','exec')
    OUT.mkdir(parents=True,exist_ok=True);DEPLOY.mkdir(parents=True,exist_ok=True)
    (DEPLOY/'kaggle_baseline.ipynb').write_text(json.dumps(nb,indent=2,ensure_ascii=False),encoding='utf-8')
    metadata=json.loads((OLD/'kernel-metadata.json').read_text())
    (DEPLOY/'kernel-metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    record={'status':'PREPARED_NOT_SUBMITTED','automatic_retry':False,'requires_specific_resubmission_agreement':True,
        'change':'write_bytes replaces write_text for extension transport; original CRLF bytes and original SHA256 preserved',
        'scientific_protocol_changed':False,'extension_bytes_changed':False,'original_plan_sha256':sha(ROOT/'outputs/kaggle_budget_2026-10-11/api/plan.json'),
        'extension_sha256':sha(script),'notebook_sha256':sha(DEPLOY/'kaggle_baseline.ipynb'),
        'metadata_sha256':sha(DEPLOY/'kernel-metadata.json'),'original_failed_version':1,
        'original_total_trainings':4,'approved_full_training_cap':5}
    (OUT/'preparation.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
