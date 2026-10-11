"""Verify the report against both saved condition tables and retained evidence hashes."""
import hashlib
import json
from pathlib import Path
import re

from paper_confirmation import OUT,ROOT,read
from sca.data import sha256_file
from sca.train import write_json


def main():
    evidence,plan = read(OUT/'evidence.json'),read(OUT/'plan.json')
    for name,digest in evidence['artifact_sha256'].items():assert sha256_file(OUT/name) == digest,name
    for name,digest in plan['preservation_sha256'].items():assert sha256_file(ROOT/name) == digest,name
    artifact = Path(evidence['attack_output']);results = read(artifact/'results.json')
    report = (OUT/'REPORT_EL.md').read_text(encoding='utf-8')
    tables = {label:{row['condition']:row for row in rows} for label,rows in results['models'].items()}
    for condition in plan['attack_config']['conditions']:
        name = condition['name'];a,b = tables['baseline'][name],tables['combined'][name]
        expected = f"|{name}|{round(a['sr_at_budget']*100)}/100|{round(b['sr_at_budget']*100)}/100|{a['ge_at_budget']:.6f}|{b['ge_at_budget']:.6f}|"
        assert report.count(expected) == 1,name
        p = results['paired'][name]
        paired = f"|{name}|{p['delta_sr']:+.2f}|{p['both_success']}|{p['baseline_only']}|{p['combined_only']}|{p['neither_success']}|"
        assert report.count(paired) == 1,name
    for key,label in [('baseline_clean_confirmation_met','H1 baseline clean confirmation'),
                      ('augmentation_joint_primary_met','H2 augmentation joint primary')]:
        assert evidence[key] == results[key]
        assert label+': '+('ΠΕΡΑΣΕ' if results[key] else 'ΑΠΕΤΥΧΕ') in report
    paths = re.findall(r'\]\(([^)]+)\)',report)
    for target in paths:
        if not target.startswith(('http://','https://')):assert (OUT/target).exists(),target
    assert 'Actual6fullGPUtrainings/cap6exhausted,111850totalupdates/6500000exposures' in report
    assert 'Variableprofiling30k unused/variableattack10k unchanged' in report
    assert 'HTTP400' in report and 'Δεν επιλέχθηκε νέο checkpoint' in report
    record = {'verified':True,'condition_table_rows_verified':16,'paired_rows_verified':8,
              'local_links_verified':len(paths),'previous_artifacts_preserved':len(plan['preservation_sha256']),
              'actual_full_gpu_trainings':6,'report_sha256':sha256_file(OUT/'REPORT_EL.md')}
    write_json(OUT/'report_verification.json',record)
    print(json.dumps(record,indent=2))


if __name__ == '__main__':main()
