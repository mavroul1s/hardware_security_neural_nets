"""Compact transport retains every checkpoint byte and the frozen execution suffix."""
import hashlib
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'notebooks'))

from prepare_confirmation_transport_repair import compact_reference,replace_reference_transport
from prepare_paper_confirmation import payload_cell,reference_archive,verify_payload_transport


def test_compact_transport_keeps_all_reference_bytes_and_execution_code(tmp_path):
    reference = tmp_path/'reference';reference.mkdir()
    (reference/'best.pt').write_bytes(b'unchanged weights\x00\xff')
    (reference/'config.json').write_bytes(b'{"seed":0}\r\n')
    digest = lambda value:hashlib.sha256(value).hexdigest()
    cycle,extension = b'# cycle\r\nx=1\r\n',b'# extension\r\ny=2\r\n'
    original_archive = reference_archive(reference)
    plan = {'cycle_extension_sha256':digest(cycle),'extension_sha256':digest(extension),
            'reference_zip_sha256':digest(original_archive),
            'baseline_hashes':{p.name:digest(p.read_bytes()) for p in reference.iterdir()}}
    source = payload_cell(plan,{},original_archive,cycle,extension)
    compact = compact_reference(reference)
    assert compact_reference(reference) == compact
    corrected = replace_reference_transport(source,compact)
    compile(corrected,'compact-fixture','exec')
    verify_payload_transport(corrected,plan,cycle,extension)
    separator = 'from paper_confirmation import run_combined, require_authorization\n'
    assert corrected.split(separator)[1] == source.split(separator)[1]
