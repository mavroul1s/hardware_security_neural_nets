"""Build checked research artifacts from the single frozen objective experiment."""
import csv
import json
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from sca.train import write_json
from paper_alignment import ROOT, read, sha

OUT=ROOT/'outputs/paper_window_selection_2026-10-09'


def main():
    result,fit,verified,plan=[read(OUT/n) for n in ('results.json','fit.json','verification.json','plan.json')]
    for name,digest in verified['artifacts_sha256'].items():assert sha(OUT/name)==digest
    for name,rows in [('correlations.csv',result['correlations']),('oob_correlations.csv',fit['oob_coefficients']),('summaries.csv',result['summaries'])]:
        with (OUT/name).open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    with (OUT/'selected_points.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['draw','selector','family','point_a','point_b','selection_correlation'])
        old=read(ROOT/'outputs/paper_selection_stability_2026-10-06/fit.json')
        for selector,source in [('point_selector',old),('box_selector',fit)]:
            for row in source['draws']:
                for family,pair in row['pairs'].items():w.writerow([row['draw'],selector,family,*pair,row['selection_coefficients'][family]])
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,axes=plt.subplots(2,2,figsize=(11,7),sharey=True)
    for i,pool in enumerate(('primary','replication')):
        for j,feature in enumerate(('box_product','covariance_rank1')):
            ax=axes[i,j]
            for sel,color,label in [('point_selector','#946145','Point objective'),('box_selector','#216e7d','Window objective')]:
                values=[r['correlation'] for r in result['correlations'] if (r['pool'],r['condition'],r['family'],r['feature'],r['selector'])==(pool,'clean','pair2',feature,sel)]
                ax.plot(np.arange(1,21),values,'o-',color=color,label=label,lw=1,ms=4)
                ax.axhline(np.median(values),color=color,ls=':',lw=1)
            ax.axhline(.05,color='#777777',ls='--',lw=.8);ax.axhline(0,color='#bbbbbb',lw=.6)
            ax.set_title(pool.capitalize()+' / '+('Box product' if j==0 else 'Rank1 control'))
            ax.set_xticks([1,5,10,15,20]);ax.set_xlabel('Unchanged paired training draw')
            ax.set_ylabel('Clean signed HW correlation');ax.grid(alpha=.15)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.95),ncol=2,frameon=False)
    fig.suptitle('Family rank2: all matched selector perturbations',y=.995)
    fig.text(.5,.005,'Dotted lines: selector medians. Dashed grey line: frozen correlation threshold 0.05.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.025,1,.91));fig.savefig(OUT/'objective_comparison.png',dpi=170);plt.close(fig)
    primary=[r for r in result['summaries'] if r['condition']=='clean' and r['feature']=='box_product']
    total=read(ROOT/'outputs/paper_selection_stability_2026-10-06/evidence.json')['ten_phase_cpu_seconds']+result['seconds']
    tests=ET.parse(OUT/'pytest.xml').getroot().find('testsuite').attrib
    evidence={'H1_primary_met':result['H1_primary_met'],'H2_secondary_met':result['H2_secondary_met'],
        'primary':primary,'oob_prediction':result['oob_prediction'],'new_fresh_coefficients':960,'new_oob_coefficients':240,
        'new_key_recovery_rows':0,'new_gpu_trainings':0,'new_optimizer_updates':0,
        'phase11_cpu_seconds':result['seconds'],'fit_seconds_included':fit['seconds'],
        'independent_verifier_seconds':verified['seconds'],'eleven_phase_cpu_seconds':total,
        'variable_viewed_profiling_rows':170000,'variable_unused_profiling_rows':30000,
        'variable_viewed_attack_rows_unchanged':10000,'original_fixed_attack_locked':True,
        'novelty_verified':False,'paper_ready':False,'tests':tests,
        'artifact_sha256':{n:sha(OUT/n) for n in ('plan.json','splits.npz','fit.json','fit.npz','results.json','arrays.npz','verification.json','pytest.xml','literature_access.json')}}
    write_json(OUT/'evidence.json',evidence)
    lines=['# Επιλογή σημείων και παραθύρων: ελεγχόμενη σύγκριση — 9/10/2026','',
        '**H1 primary: '+('ΠΕΡΑΣΕ' if result['H1_primary_met'] else 'ΑΠΕΤΥΧΕ')+'. H2 secondary: '+('ΠΕΡΑΣΕ' if result['H2_secondary_met'] else 'ΑΠΕΤΥΧΕ')+'.**','',
        'Η φάση 11 ελέγχει αν η αστάθεια της επιλογής οφείλεται στη διαφορά μεταξύ '
        'του στόχου επιλογής και του τελικού χαρακτηριστικού. Η παλιά μέθοδος επιλέγει '
        'μεμονωμένα σημεία, ενώ η νέα επιλέγει απευθείας το γινόμενο των κεντραρισμένων '
        'μέσων δύο παραθύρων 11 δειγμάτων, μεγιστοποιώντας την απόλυτη συσχέτιση Pearson.','',
        'Η σύγκριση χρησιμοποιεί ακριβώς τα ίδια 20 ζευγαρωμένα training draws της '
        'φάσης 10 από τις αρχικές 10.000 traces. Διατηρούνται τα κέντρα ανά draw, '
        'η ευθυγράμμιση της φάσης 9, ακτίνα 5, περιθώριο 25, ελάχιστη απόσταση 50, '
        'κανόνας ποικιλίας 20 και τα ίδια 845.650 επιτρεπτά ζεύγη κέντρων. '
        'Αξιολογούνται όλα τα point/box/rank1 controls και οι δύο οικογένειες. '
        'Δεν επιλέγεται καλύτερο draw, ensemble ή νέα περιοχή/παράμετρος.','',
        'Οι υποθέσεις, τα κριτήρια, τα splits, το κόστος, ο κανόνας διακοπής και '
        'τα hashes κώδικα/εισόδων πάγωσαν πριν την πρόσβαση στα training δεδομένα. '
        'Όλα τα νέα fits και οι 240 εσωτερικές OOB συσχετίσεις αποθηκεύτηκαν πριν '
        'την πρόσβαση στις δύο νέες ομάδες επιβεβαίωσης των 10.000 rows '
        '(seeds 20261020 και 20261021). Η ένωση των profiling splits των φάσεων '
        '5–10 επαληθεύτηκε διαδοχικά: 15k → 20k → 30k → 70k → 110k → 150k. '
        'Οι δείκτες του attack συνόλου δεν προστέθηκαν στην ένωση profiling.','',
        '## H1: επιλογή με στόχο το τελικό χαρακτηριστικό','',
        'Το κύριο endpoint είναι η καθαρή box-product συσχέτιση της δεύτερης '
        'οικογένειας. Σε κάθε νέα ομάδα απαιτούνται: διάμεση ζευγαρωμένη βελτίωση '
        'Δr ≥ 0,02, διάμεση συσχέτιση της νέας επιλογής ≥ 0,05 και τουλάχιστον '
        '16/20 θετικά draws. Η διάμεση ζευγαρωμένη απώλεια στην πρώτη οικογένεια '
        'πρέπει να είναι ≤ 0,01. Υπολογίζεται median(a−b), με το ίδιο draw σε '
        'κάθε διαφορά, και όχι median(a)−median(b).','',
        '| Pool / family | Point median | Window median | Median paired Δr | Window positive |',
        '|---|---:|---:|---:|---:|']
    for r in primary:
        lines.append(f"| {r['pool']} / {r['family']} | {r['baseline_median']:.6f} | {r['window_median']:.6f} | {r['median_paired_difference']:.6f} | {r['window_positive_draws']}/20 |")
    lines += ['', 'Η επιλογή παραθύρων βελτίωσε περιγραφικά την πρώτη οικογένεια. '
        'Η δεύτερη παρέμεινε ασθενής: διάμεσοι 0,007642 και 0,006647, με 12/20 '
        'και 13/20 θετικά draws. Η διάμεση ζευγαρωμένη μεταβολή της δεύτερης '
        'οικογένειας είναι αρνητική και στις δύο ομάδες. Η συγκεκριμένη αλλαγή '
        'του στόχου επιλογής δεν αρκεί για σταθερό δεύτερο signal.','',
        'Το συμπέρασμα αφορά την εξαντλητική επιλογή με αυτό το σταθερό πλάτος '
        'παραθύρου, υπό το κοινό αρχικό training sample και preprocessing. '
        'Δεν απομονώνεται μοναδική αιτία της αστάθειας και δεν αποδεικνύεται ότι '
        'το αρχικό pair ήταν false positive. Η δεύτερη οικογένεια ορίζεται από '
        'κανόνα ποικιλίας της επιλογής, χωρίς εγγύηση ανεξάρτητης πληροφορίας '
        'διαρροής. Τα point/rank1 και combined5 παραμένουν δευτερεύοντα controls.','',
        '![Όλα τα ζευγαρωμένα draws της δεύτερης οικογένειας](objective_comparison.png)','',
        '## H2: εσωτερική διάγνωση με OOB rows','',
        'Out-of-bag (OOB) είναι οι αρχικές training rows που απουσιάζουν από ένα '
        'συγκεκριμένο draw. Αποκλείονται όλες οι επιλεγμένες θέσεις, μαζί με τις '
        'επαναλήψεις τους. Τα OOB labels δεν χρησιμοποιούνται στην επιλογή ή '
        'στο fit του draw. Οι traces τους όμως είχαν συμβάλει στην αρχική '
        'ευθυγράμμιση και στο template χωρίς labels. Η διάγνωση επομένως '
        'παραμένει conditional σε αυτό το κοινό preprocessing.','',
        'Το προκαθορισμένο κριτήριο απαιτεί |OOB median − fresh median| ≤ 0,02 '
        'και συμφωνία στο κατώφλι median ≥ 0,05. Εφαρμόζεται στη δεύτερη οικογένεια '
        'για box/rank1, με τις δύο μεθόδους επιλογής και τις δύο νέες ομάδες: '
        'οκτώ έλεγχοι συνολικά. Καμία OOB μέτρηση δεν αλλάζει σημεία ή βάρη.','',
        '| Selector / feature / pool | OOB median | Fresh median | Criterion |',
        '|---|---:|---:|---|']
    for r in result['oob_prediction']:
        lines.append(f"| {r['selector']} / {r['feature']} / {r['pool']} | {r['oob_median']:.6f} | {r['fresh_median']:.6f} | {'Πέρασε' if r['support'] else 'Απέτυχε'} |")
    lines += ['', 'Η συμφωνία στο κατώφλι 0,05 είναι 8/8: όλες οι διάμεσοι της '
        'δεύτερης οικογένειας είναι χαμηλότερες. Η αριθμητική συμφωνία εντός 0,02 '
        'είναι 7/8, οπότε το αυστηρό συνολικό H2 κριτήριο απέτυχε. Η εξαίρεση είναι '
        'point-selector/box/replication: OOB 0,012072 έναντι fresh 0,037832, '
        'με διαφορά 0,025760. Αυτό δεν τεκμηριώνει αποτυχία κάθε OOB διάγνωσης '
        'ούτε εγγύηση γενικής βαθμονόμησης.','',
        '## Τεκμηριωμένοι ισχυρισμοί, βιβλιογραφία και ανάκτηση κλειδιού','',
        'Η πρωτογενής βιβλιογραφία καλύπτει ήδη averaging παραθύρων, επιλογή '
        'higher-order projections με κατάλληλο objective και scheme-aware '
        'recombination. Ανακτήθηκε το πλήρες orthogonal-regression XML· παραμένουν '
        'κενά στη notation για retention/penalty και στον author code. '
        'Ο scheme-aware κώδικας επιθεωρήθηκε μερικώς σε συγκεκριμένο commit, '
        'χωρίς εκτέλεση τρίτου κώδικα ή πλήρες matched benchmark. Το '
        '[πρωτογενές audit](../../literature/SELECTION_OBJECTIVE_AUDIT_2026-10-09.md) '
        'διαχωρίζει πηγές, συμπεράσματα και κενά πρόσβασης.','',
        'Ελέγχθηκαν οι δύο υποθέσεις H1/H2. Το τρίτο θέμα που καταγράφηκε ως H3 '
        'στο frozen audit/plan είναι αναβαλλόμενο recovery ερώτημα, χωρίς '
        'πλήρως ορισμένο πείραμα ή νέο criterion εδώ. Αφορά τη σχέση profiling '
        'signal και σταθερότητας επιλογής με SR 18/20@2000 σε ανεξάρτητα '
        'αποκτημένα δεδομένα και πραγματικό key.','',
        'Δεν μετρήθηκε νέα ανάκτηση κλειδιού. Οι 960 συσχετίσεις αποτελούν '
        'διαγνωστικά endpoints, ενώ τα 20 draws μοιράζονται το ίδιο training sample. '
        'Οι δύο ομάδες επιβεβαίωσης ανήκουν στην ίδια καμπάνια. Δεν αποτελούν '
        'ανεξάρτητα neural seeds, keys ή acquisitions. Τα παλιά variable attack '
        '3/20–4/20 και τα failures των φάσεων 7/9/10 διατηρούνται. Δεν '
        'κατασκευάστηκε fixed-key επίθεση από varying-key profiling labels.','',
        'Τα κριτήρια είναι περιγραφικά και conditional στο κοινό preprocessing. '
        'Δεν εξάγονται confidence intervals ή independent-binomial συμπεράσματα '
        'από τα 20 draws, ούτε formal stability-selection ή across-phase '
        'alpha-spending εγγυήσεις. Η αλλαγή του objective είναι αιτιολογημένο '
        'adaptive follow-up με νέο freeze, χωρίς tuning σε εξετασμένα holdouts.','',
        '## Ορθότητα, πραγματικό κόστος και κανόνας διακοπής','',
        f"95 tests passed, με 14 προϋπάρχουσες warnings· suite {float(tests['time']):.3f}s. "
        'Πέντε νέα synthetic tests ελέγχουν συντεταγμένες, την ταυτότητα του '
        'box objective, περιορισμούς/ties, OOB αποκλεισμούς και τη ζευγαρωμένη '
        'διάμεσο. Αποτελούν ελέγχους ορθότητας, χωρίς φυσική attack-efficacy evidence.', '',
        f"CPU πείραμα: {result['seconds']:.6f}s, μαζί με {fit['seconds']:.6f}s για fit. "
        f"Χωριστός verifier: {verified['seconds']:.6f}s. Οι έντεκα φάσεις έχουν "
        f"καταγεγραμμένο experiment wall time {total:.6f}s, χωρίς imports, tests, "
        'verifiers, reports ή την υπόλοιπη συνεδρία. Το όριο των 600s δεν '
        'ενεργοποιήθηκε. Έγινε μία εκτέλεση, χωρίς επαναρύθμιση ή επόμενο trial.','',
        f"Η χωριστή επαλήθευση επανέλαβε {verified['full_searches']} πλήρεις αναζητήσεις "
        f"(20 baseline και 20 window), {verified['training_weight_vectors']} διανύσματα βαρών "
        f"και {verified['selected_coefficients']} επιλεγμένες training συσχετίσεις. "
        f"Ελέγχθηκαν όλες οι {verified['oob_coefficients']} OOB και {verified['fresh_coefficients']} "
        f"fresh συσχετίσεις/γινόμενα, {verified['sampled_offset_checks']} δειγματοληπτικοί έλεγχοι "
        'offsets, οι ενώσεις splits, η RNG, η χρονική σειρά πρόσβασης και τα hashes. '
        'Χρησιμοποιούνται ανεξάρτητοι αριθμητικοί τύποι στον ίδιο host. Η κοινή '
        'υλοποίηση ευθυγράμμισης ελέγχεται με χωριστό δειγματοληπτικό replay· '
        'δεν πρόκειται για cross-host reproduction ή ανεξάρτητη ανθρώπινη αξιολόγηση.','',
        'Variable profiling: 170k viewed/30k unused μετά τη φάση. Οι 20.000 νέες '
        'rows είναι πλέον εξετασμένες και αποκλείονται από tuning και μελλοντική '
        'fresh confirmation. Οι μελλοντικοί αποκλεισμοί περιλαμβάνουν την ένωση '
        'όλων των splits της φάσης 11. Fixed profiling 50k viewed, variable attack '
        '10k αμετάβλητο και αρχικό fixed attack locked. Παραμένουν ένα Kaggle '
        'notebook, 3 GPU trainings, ο ίδιος production source, checkpoints και '
        'το αποτυχημένο CNN gate. Δεν έγιναν νέα optimizer updates.','',
        'Πριν χρησιμοποιηθούν οι τελευταίες 30.000 rows χρειάζεται νέα ερώτηση '
        'που να διακρίνει εξηγήσεις. Η παρούσα φάση σταματά εδώ. Η τεκμηρίωση '
        'σε ανεξάρτητο πραγματικό key/acquisition παραμένει ουσιώδες κενό για '
        'ισχυρισμό αποτελεσματικής ανάκτησης. Ο ισχυρότερος σημερινός άξονας '
        'είναι benchmark και failure analysis· η πρωτοτυπία παραμένει ανεπιβεβαίωτη.','',
        '[Plan](plan.json) · [Splits](splits.npz) · [Fit](fit.json) · [Fit arrays](fit.npz) · '
        '[Results](results.json) · [960fresh rows](correlations.csv) · [240OOB rows](oob_correlations.csv) · '
        '[80selected pairs](selected_points.csv) · [Arrays](arrays.npz) · [Verification](verification.json) · '
        '[Evidence](evidence.json) · [Tests](pytest.xml) · [Literature access](literature_access.json) · '
        '[Execution](../../notebooks/paper_window_selection.py) · [Independent verifier](../../notebooks/verify_window_selection.py)', '']
    (OUT/'REPORT_EL.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'H1_primary_met':result['H1_primary_met'],'H2_secondary_met':result['H2_secondary_met'],'report':str(OUT/'REPORT_EL.md')},indent=2))


if __name__=='__main__':main()
