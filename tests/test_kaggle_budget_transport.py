"""Verify actual notebook payload bytes across Windows/Linux line endings."""
import ast
import hashlib
import json
from pathlib import Path
import importlib.util


def test_embedded_extension_roundtrip_preserves_frozen_bytes(tmp_path):
    root=Path(__file__).resolve().parents[1]
    original=root/'notebooks/kaggle_budget_diagnostic.py'
    spec=importlib.util.spec_from_file_location('transport',root/'notebooks/prepare_byte_preserving_budget.py')
    transport=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    previous=f"extension_path.write_text({original.read_text(encoding='utf-8')!r},encoding='utf-8')"
    tree=ast.parse(transport.preserve_extension_bytes(previous,original))
    calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call)
           and isinstance(node.func,ast.Attribute) and node.func.attr=='write_bytes']
    assert len(calls)==1
    payload=ast.literal_eval(calls[0].args[0])
    path=tmp_path/'remote_extension.py'
    path.write_bytes(payload)
    plan=json.loads((root/'outputs/kaggle_budget_2026-10-11/api/plan.json').read_text())
    assert path.read_bytes()==original.read_bytes()
    assert hashlib.sha256(path.read_bytes()).hexdigest()==plan['extension_sha256']
    compile(path.read_bytes(),str(path),'exec')
    # The text transport that failed on Kaggle must differ for this frozen CRLF file.
    assert original.read_text(encoding='utf-8').encode()!=payload
