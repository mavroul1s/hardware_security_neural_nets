"""Prepare a smaller byte-identical reference transport and known-working metadata."""
import base64
import hashlib
import io
import json
import lzma
from pathlib import Path
import tarfile

from paper_confirmation import OUT, ROOT, REFERENCE, read
from prepare_paper_confirmation import DEPLOY,verify_payload_transport
from sca.data import sha256_file
from sca.train import write_json

REPAIR = OUT/'transport_repair'
REPAIRED_DEPLOY = DEPLOY.parent/'repaired_kernel'


def compact_reference(reference):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as archive:
        for path in sorted(Path(reference).iterdir()):
            if path.is_file():
                value = path.read_bytes();info = tarfile.TarInfo(path.name)
                info.size = len(value)
                archive.addfile(info,io.BytesIO(value))
    return lzma.compress(stream.getvalue(),preset=9)


def replace_reference_transport(source,reference_transport):
    start,end = source.index('reference_bytes = base64.b64decode('),source.index('sys.path.insert(0,str(PROJECT_ROOT))')
    digest = hashlib.sha256(reference_transport).hexdigest()
    replacement = (
        'import lzma, tarfile\n'
        f'reference_transport = base64.b64decode({base64.b64encode(reference_transport).decode()!r})\n'
        f'assert hashlib.sha256(reference_transport).hexdigest() == {digest!r}\n'
        "reference = PROJECT_ROOT.parent / 'baseline45k_reference'\nreference.mkdir(exist_ok=True)\n"
        "with tarfile.open(fileobj=io.BytesIO(lzma.decompress(reference_transport)),mode='r:') as archive:\n"
        "    assert sorted(archive.getnames()) == sorted(frozen_plan['baseline_hashes'])\n"
        "    for name,digest in frozen_plan['baseline_hashes'].items():\n"
        "        assert Path(name).name == name and name not in ('.','..')\n"
        '        member = archive.getmember(name)\n'
        '        assert member.isfile() and member.size <= 5000000\n'
        '        value = archive.extractfile(member).read()\n'
        '        assert hashlib.sha256(value).hexdigest() == digest\n'
        '        target = reference / name\n'
        '        if target.exists():\n            assert target.read_bytes() == value\n'
        '        else:\n            target.write_bytes(value)\n'
    )
    return source[:start]+replacement+source[end:]


def main():
    plan,prepared = read(OUT/'plan.json'),read(OUT/'preparation.json')
    assert read(OUT/'submission_attempt.json')['exit_code'] == 1
    assert read(OUT/'rejection_verification.json')['current_version_number'] == 3
    assert sha256_file(DEPLOY/'kaggle_baseline.ipynb') == prepared['notebook_sha256']
    REPAIR.mkdir(exist_ok=True);REPAIRED_DEPLOY.mkdir(exist_ok=True)
    notebook = read(DEPLOY/'kaggle_baseline.ipynb')
    compact = compact_reference(REFERENCE)
    notebook['cells'][-1]['source'] = replace_reference_transport(notebook['cells'][-1]['source'],compact)
    verify_payload_transport(notebook['cells'][-1]['source'],plan,
                             (ROOT/'notebooks/kaggle_budget_diagnostic.py').read_bytes(),
                             (ROOT/'notebooks/paper_confirmation.py').read_bytes())
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code':compile(cell['source'],'repaired-confirmation','exec')
    write_json(REPAIRED_DEPLOY/'kaggle_baseline.ipynb',notebook)
    # These metadata bytes already succeeded for the previous baseline submission.
    metadata = read(ROOT/'runs/kaggle_control/budget_2026-10-11/nmavros/repaired_kernel/kernel-metadata.json')
    assert metadata['id'] == plan['notebook_ref'] and metadata['is_private']
    assert metadata['dataset_sources'] == plan['dataset_sources'] and metadata['docker_image'] == plan['docker_image']
    write_json(REPAIRED_DEPLOY/'kernel-metadata.json',metadata)
    record = {'status':'PREPARED_NOT_SUBMITTED','requires_specific_corrected_submission_agreement':True,
        'http_failure':400,'scientific_protocol_changed':False,'checkpoint_member_bytes_changed':False,
        'original_plan_sha256':sha256_file(OUT/'plan.json'),'extension_sha256':sha256_file(ROOT/'notebooks/paper_confirmation.py'),
        'change':'TAR/XZ replaces inline ZIP transport for the same nine exact files; reuse known-successful private metadata with original image pinning',
        'cause_status':'HTTP400 response body unavailable; transport size and metadata differ from known-successful submission, exact server cause unconfirmed',
        'old_notebook_bytes':(DEPLOY/'kaggle_baseline.ipynb').stat().st_size,
        'corrected_notebook_bytes':(REPAIRED_DEPLOY/'kaggle_baseline.ipynb').stat().st_size,
        'corrected_notebook_sha256':sha256_file(REPAIRED_DEPLOY/'kaggle_baseline.ipynb'),
        'corrected_metadata_sha256':sha256_file(REPAIRED_DEPLOY/'kernel-metadata.json'),
        'reference_transport_sha256':hashlib.sha256(compact).hexdigest(),
        'byte_transport_verified':True,'new_remote_versions':0,'new_real_trainings':0,'attack_payloads_read':False}
    assert record['corrected_notebook_bytes'] < 1000000
    write_json(REPAIR/'preparation.json',record)
    print(json.dumps(record,indent=2))


if __name__ == '__main__':main()
