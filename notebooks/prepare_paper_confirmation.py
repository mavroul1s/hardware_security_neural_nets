"""Freeze and package one proposed combined run; preparation never submits it."""
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from paper_confirmation import ROOT, OUT, REFERENCE, combined_config, read, verify_reference
from sca.data import sha256_file
from sca.train import code_identity, write_json

DEPLOY = ROOT/'runs/kaggle_control/confirmation_2026-10-11/kernel'
REFERENCE_ZIP = DEPLOY.parent/'baseline45k_reference.zip'


def plan_identity(plan):
    return hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()


def reference_archive(reference):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(Path(reference).iterdir()):
            if path.is_file():
                info = zipfile.ZipInfo(path.name,date_time=(1980,1,1,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info,path.read_bytes())
    return stream.getvalue()


def payload_cell(plan,authorization,reference_bytes,cycle_bytes,extension_bytes):
    """The prefix can be checked separately without importing or calling a trainer."""
    prefix = (
        'import base64, hashlib, io, json, sys, zipfile\nfrom pathlib import Path\n'
        f'frozen_plan = {plan!r}\nauthorization = {authorization!r}\n'
        f'cycle_bytes = {cycle_bytes!r}\nextension_bytes = {extension_bytes!r}\n'
        "assert hashlib.sha256(cycle_bytes).hexdigest() == frozen_plan['cycle_extension_sha256']\n"
        "assert hashlib.sha256(extension_bytes).hexdigest() == frozen_plan['extension_sha256']\n"
        "(PROJECT_ROOT / 'kaggle_budget_diagnostic.py').write_bytes(cycle_bytes)\n"
        "(PROJECT_ROOT / 'paper_confirmation.py').write_bytes(extension_bytes)\n"
        f'reference_bytes = base64.b64decode({base64.b64encode(reference_bytes).decode()!r})\n'
        "assert hashlib.sha256(reference_bytes).hexdigest() == frozen_plan['reference_zip_sha256']\n"
        "reference = PROJECT_ROOT.parent / 'baseline45k_reference'\nreference.mkdir(exist_ok=True)\n"
        'with zipfile.ZipFile(io.BytesIO(reference_bytes)) as archive:\n'
        "    assert sorted(archive.namelist()) == sorted(frozen_plan['baseline_hashes'])\n"
        "    for name,digest in frozen_plan['baseline_hashes'].items():\n"
        "        assert Path(name).name == name and name not in ('.','..')\n"
        '        value = archive.read(name)\n'
        '        assert hashlib.sha256(value).hexdigest() == digest\n'
        '        target = reference / name\n'
        '        if target.exists():\n            assert target.read_bytes() == value\n'
        '        else:\n            target.write_bytes(value)\n'
        'sys.path.insert(0,str(PROJECT_ROOT))\n'
    )
    execution = (
        'from paper_confirmation import run_combined, require_authorization\n'
        "require_authorization(frozen_plan,authorization,'combined_training')\n"
        "output = PROJECT_ROOT.parent / 'paper_confirmation'\n"
        'import shutil, traceback\n'
        'try:\n'
        '    run_combined(DATASET_PATH,reference,output,frozen_plan,authorization)\n'
        'except Exception as error:\n'
        '    output.mkdir(exist_ok=True)\n'
        "    write_json(output/'failure.json',{'complete':False,'automatic_retry':False,\n"
        "               'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc()})\n"
        '    raise\n'
        'finally:\n'
        '    if output.exists():\n'
        "        archive = shutil.make_archive(str(PROJECT_ROOT.parent/'confirmation_results'),'zip',output)\n"
        "        print('Preserved output:',archive,flush=True)\n"
    )
    return prefix + execution


def verify_payload_transport(source,plan,cycle_bytes,extension_bytes):
    prefix = source.split('from paper_confirmation import run_combined, require_authorization\n')[0]
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary)/'project';project.mkdir()
        namespace = {'PROJECT_ROOT':project}
        exec(compile(prefix,'transport-only','exec'),namespace)
        assert (project/'kaggle_budget_diagnostic.py').read_bytes() == cycle_bytes
        assert (project/'paper_confirmation.py').read_bytes() == extension_bytes
        for name,digest in plan['baseline_hashes'].items():
            assert sha256_file(project.parent/'baseline45k_reference'/name) == digest
        # Remove only the temporary import path inserted by this checked prefix.
        import sys
        sys.path.remove(str(project))


def main():
    OUT.mkdir(parents=True,exist_ok=True);DEPLOY.mkdir(parents=True,exist_ok=True)
    previous = read(ROOT/'outputs/kaggle_budget_2026-10-11/api/plan.json')
    verification = read(ROOT/'outputs/kaggle_budget_2026-10-11/api/verification.json')
    assert verification['verified'] and verification['primary_met'] and not verification['attack_payloads_read']
    assert verification['full_gpu_trainings_total'] == 5
    reference_bytes = reference_archive(REFERENCE)
    reference_hash = hashlib.sha256(reference_bytes).hexdigest()
    if REFERENCE_ZIP.exists():assert REFERENCE_ZIP.read_bytes() == reference_bytes
    else:REFERENCE_ZIP.write_bytes(reference_bytes)
    cycle_bytes = (ROOT/'notebooks/kaggle_budget_diagnostic.py').read_bytes()
    extension_bytes = (ROOT/'notebooks/paper_confirmation.py').read_bytes()
    extension_hash = hashlib.sha256(extension_bytes).hexdigest()
    if (OUT/'plan.json').exists():
        plan = read(OUT/'plan.json')
        for name,digest in plan['input_hashes'].items():assert sha256_file(ROOT/name) == digest,name
    else:
        suite = ET.parse(OUT/'pytest.xml').getroot().find('testsuite').attrib
        assert int(suite['tests']) >= 111 and int(suite['errors']) == int(suite['failures']) == 0
        scope = combined_config(read(REFERENCE/'config.json'),'dataset','output',extension_hash)
        scope = {k:v for k,v in scope.items() if k not in ('dataset','run_dir','confirmation_extension_sha256')}
        preservation = read(ROOT/'outputs/kaggle_budget_2026-10-11/execution_status.json')['preservation_sha256']
        for path in REFERENCE.iterdir():
            if path.is_file():preservation[path.relative_to(ROOT).as_posix()] = sha256_file(path)
        for name in [
            'runs/kaggle_control/budget_2026-10-11/nmavros/output/budget_diagnostic_results.zip',
            'runs/kaggle_control/budget_2026-10-11/nmavros/output_v2/budget_diagnostic_results.zip',
            'outputs/kaggle_budget_2026-10-11/api/restoration.json',
            'outputs/kaggle_budget_2026-10-11/api/verification.json',
            'outputs/kaggle_budget_2026-10-11/api/plan.json']:
            preservation[name] = sha256_file(ROOT/name)
        inputs = [
            'docs/PAPER_CONFIRMATION_PROTOCOL_2026-10-11.md',
            'notebooks/prepare_paper_confirmation.py','notebooks/verify_confirmation_training.py',
            'notebooks/verify_confirmation_attack.py','tests/test_paper_confirmation.py',
            'outputs/paper_confirmation_2026-10-11/pytest.xml',
            'configs/evaluation_final.json','configs/matrix.json']
        plan = {
            'status':'PROPOSED_NOT_APPROVED','authorization_required':'Specific cap6 and locked attack agreement; preparation is not execution',
            'hypotheses':{'H1':'Frozen baseline clean attack SR@2000>=0.90',
                'H2':'Combined_both_ood SR>=0.90 AND paired deltaSR>0 AND combined clean SR>=0.90'},
            'h2_primary_condition':'combined_both_ood','secondary':'All other GE/SR/sustainedSR/paired discordances; descriptive',
            'selection_rule':'Minimum clean profiling-validation CE over all50epochs; attack never selects',
            'execution_order':['one combined training','independent training verification and both checkpoints locked','one CPU paired attack evaluation','independent saved-prediction rank verification'],
            'training_scope':scope,'baseline_best_epoch':21,'baseline_validation_sr_at_2000':1.0,
            'clean_validation_config':previous['evaluation_config'],'attack_config':read(ROOT/'configs/evaluation_final.json'),
            'baseline_hashes':{p.name:sha256_file(p) for p in REFERENCE.iterdir() if p.is_file()},
            'reference_zip_sha256':reference_hash,'extension_sha256':extension_hash,
            'cycle_extension_sha256':hashlib.sha256(cycle_bytes).hexdigest(),
            'production_source_sha256':previous['production_source_sha256'],'dataset_sha256':previous['dataset_sha256'],
            'input_hashes':{name:sha256_file(ROOT/name) for name in inputs},'preservation_sha256':preservation,
            'notebook_ref':'nmavros/hw-sec-exp2','dataset_sources':['nmavros/hardware-sca-resume'],
            'docker_image':'gcr.io/kaggle-private-byod/python@sha256:2757e0c7d1e0a9cb43da657b97e223c321a98f5014bdf64f44f2f6b083ad2b2f',
            'accelerator':'NvidiaTeslaT4','new_remote_notebook':False,'input_packet_changed':False,
            'original_full_gpu_trainings':5,'proposed_full_gpu_training_cap':6,'new_full_gpu_trainings_max':1,
            'schedule_knots_updates':[0,18000,36000,45000],'schedule_knots_lr':[.0005,.005,.0005,.000005],
            'new_optimizer_updates':45000,'new_trace_exposures':2250000,'new_models':0,'new_seeds':0,
            'session_timeout_seconds':1800,'training_loop_cap_seconds':900,'cpu_evaluation_cap_seconds':600,
            'stopping_rule':'One submission/training/evaluation only; preserve partial failures; no automatic retry or tuning',
            'validation_is_viewed':True,'attack_campaign':'Original fixed-key10k held out traces, same key/acquisition campaign',
            'independent_keys_or_acquisitions':0,'orders_are_conditional':True,'synthetic_corruptions_are_not_physical_replications':True,
            'variable_profiling_unused_unchanged':30000,'variable_payloads_read':False,'novelty_verified':False,
            'tests':suite,'frozen_utc':datetime.now(timezone.utc).isoformat()}
        write_json(OUT/'plan.json',plan)
    assert reference_hash == plan['reference_zip_sha256'] and extension_hash == plan['extension_sha256']
    assert hashlib.sha256(cycle_bytes).hexdigest() == plan['cycle_extension_sha256']
    verify_reference(REFERENCE,plan)
    assert code_identity()['source_sha256'] == plan['production_source_sha256']
    assert sha256_file(ROOT/'data/ASCAD.h5') == plan['dataset_sha256']
    for name,digest in plan['preservation_sha256'].items():assert sha256_file(ROOT/name) == digest,name
    if not (OUT/'authorization.json').exists():
        write_json(OUT/'authorization.json',{'plan_identity':plan_identity(plan),'specific_user_agreement':False,
                   'approved_full_gpu_training_cap':5,'combined_training_authorized':False,'attack_evaluation_authorized':False})
    auth = read(OUT/'authorization.json')
    assert auth['plan_identity'] == plan_identity(plan)
    execution = payload_cell(plan,auth,reference_bytes,cycle_bytes,extension_bytes)
    verify_payload_transport(execution,plan,cycle_bytes,extension_bytes)
    canonical = read(ROOT/'notebooks/kaggle_baseline.ipynb')
    original = [c for c in canonical['cells'] if c['cell_type'] == 'code']
    def cell(source,kind='code'):
        return {'cell_type':kind,'metadata':{},'source':source,**({'execution_count':None,'outputs':[]} if kind == 'code' else {})}
    notebook = {**canonical,'cells':[
        cell('One proposed combined45k in the same private notebook. Requires specific cap6 approval. No attack is read here.','markdown'),
        cell(''.join(original[0]['source'])),cell(''.join(original[1]['source'])),cell(execution)]}
    for c in notebook['cells']:
        if c['cell_type'] == 'code':compile(c['source'],'confirmation-notebook','exec')
    write_json(DEPLOY/'kaggle_baseline.ipynb',notebook)
    metadata = read(ROOT/'runs/kaggle_control/budget_2026-10-11/nmavros/restored/kernel-metadata.json')
    metadata['code_file'] = 'kaggle_baseline.ipynb'
    assert metadata['id'] == plan['notebook_ref'] and metadata['is_private']
    assert metadata['dataset_sources'] == plan['dataset_sources'] and metadata['docker_image'] == plan['docker_image']
    write_json(DEPLOY/'kernel-metadata.json',metadata)
    record = {'execution_status':'prepared_not_submitted','new_real_trainings':0,'attack_payloads_read':False,
        'plan_sha256':sha256_file(OUT/'plan.json'),'plan_identity':plan_identity(plan),
        'authorization_sha256':sha256_file(OUT/'authorization.json'),'specifically_authorized':auth['specific_user_agreement'],
        'notebook_sha256':sha256_file(DEPLOY/'kaggle_baseline.ipynb'),'metadata_sha256':sha256_file(DEPLOY/'kernel-metadata.json'),
        'byte_transport_verified':True,'compiled_code_cells':3,'preserved_artifacts':len(plan['preservation_sha256']),
        'current_full_gpu_trainings':5,'passing_cpu_tests':int(plan['tests']['tests']),
        'notebook_ref':plan['notebook_ref'],'deployment_directory':str(DEPLOY)}
    write_json(OUT/'preparation.json',record)
    print(json.dumps(record,indent=2))


if __name__ == '__main__':main()
