"""Verify report numbers, complete CSV artifacts, local links and visual flag."""
import argparse
import ast
import csv
import json
import re
from sca.train import write_json
from paper_alignment import ROOT,read,sha

OUT=ROOT/'outputs/paper_window_selection_2026-10-09'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plot-visually-checked',action='store_true')
    args=parser.parse_args()
    if not args.plot_visually_checked:raise ValueError('Inspect objective_comparison.png before confirming visual QA')
    report=(OUT/'REPORT_EL.md').read_text(encoding='utf-8')
    result,fit,verified,evidence=[read(OUT/n) for n in ('results.json','fit.json','verification.json','evidence.json')]
    for name,digest in verified['artifacts_sha256'].items():assert sha(OUT/name)==digest
    assert 'H1 primary: ΑΠΕΤΥΧΕ. H2 secondary: ΑΠΕΤΥΧΕ.' in report
    assert not result['H1_primary_met'] and not result['H2_secondary_met']
    for r in evidence['primary']:
        line=f"| {r['pool']} / {r['family']} | {r['baseline_median']:.6f} | {r['window_median']:.6f} | {r['median_paired_difference']:.6f} | {r['window_positive_draws']}/20 |"
        assert line in report
    for r in result['oob_prediction']:
        line=f"| {r['selector']} / {r['feature']} / {r['pool']} | {r['oob_median']:.6f} | {r['fresh_median']:.6f} | {'Πέρασε' if r['support'] else 'Απέτυχε'} |"
        assert line in report
    assert sum(r['support'] for r in result['oob_prediction'])==7
    csv_count=0
    for name,expected in [('correlations.csv',result['correlations']),('oob_correlations.csv',fit['oob_coefficients']),('summaries.csv',result['summaries'])]:
        with (OUT/name).open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
        assert len(rows)==len(expected)
        for actual,source in zip(rows,expected):
            for key,value in source.items():
                parsed=ast.literal_eval(actual[key]) if isinstance(value,list) else int(actual[key]) if isinstance(value,int) else float(actual[key]) if isinstance(value,float) else actual[key]
                assert parsed==value,(name,key)
        csv_count+=len(rows)
    with (OUT/'selected_points.csv').open(encoding='utf-8',newline='') as f:points=list(csv.DictReader(f))
    assert len(points)==80
    old=read(ROOT/'outputs/paper_selection_stability_2026-10-06/fit.json')
    for r in points:
        source=(old if r['selector']=='point_selector' else fit)['draws'][int(r['draw'])]
        assert [int(r['point_a']),int(r['point_b'])]==source['pairs'][r['family']]
        assert float(r['selection_correlation'])==source['selection_coefficients'][r['family']]
    links=0
    for target in re.findall(r'\]\(([^)]+)\)',report):
        if not target.startswith(('https://','http://')):assert (OUT/target).resolve().is_file(),target;links+=1
    assert f"{evidence['eleven_phase_cpu_seconds']:.6f}s" in report
    assert '95 tests passed' in report and '170k viewed/30k unused' in report
    assert float(evidence['tests']['tests'])==95 and float(evidence['tests']['failures'])==float(evidence['tests']['errors'])==0
    record={'verified':True,'fresh_csv_rows':960,'oob_csv_rows':240,'summary_csv_rows':24,'selected_pair_rows':80,
        'total_verified_csv_rows':csv_count+80,'primary_table_rows':4,'secondary_table_rows':8,
        'local_links':links,'passing_tests':95,'H1_primary_met':False,'H2_secondary_met':False,
        'plots_visually_checked':['objective_comparison.png'],'remaining_unused_rows':30000,
        'artifact_sha256':{n:sha(OUT/n) for n in ('REPORT_EL.md','evidence.json','verification.json','correlations.csv','oob_correlations.csv','summaries.csv','selected_points.csv','objective_comparison.png')}}
    write_json(OUT/'report_verification.json',record)
    print(json.dumps({k:v for k,v in record.items() if k!='artifact_sha256'},indent=2))


if __name__=='__main__':main()
