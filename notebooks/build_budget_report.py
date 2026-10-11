"""Build the budget diagnostic report from independently verified saved output."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/kaggle_budget_2026-10-11/api'


def read(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',type=Path,required=True)
    args = parser.parse_args()
    verified = read(OUT/'verification.json')
    assert verified['verified']
    result = read(args.download/'results.json')
    old_result = read(ROOT/'outputs/kaggle_recipe_2026-10-09/results.json')
    new_history = read(args.download/'none_seed0/history.json')
    old_history = read(ROOT/'runs/kaggle_control/recipe_2026-10-09/output/extracted/none_seed0/history.json')
    new_manifest = read(args.download/'none_seed0/manifest.json')
    old_manifest = read(ROOT/'runs/kaggle_control/recipe_2026-10-09/output/extracted/none_seed0/manifest.json')
    same_environment = new_manifest['environment'] == old_manifest['environment']
    records = []
    for label, n, updates, history, r in [('recipe10k',10000,10000,old_history,old_result),
                                        ('budget45k',45000,45000,new_history,result)]:
        best = min(history,key=lambda row:row['validation_loss'])
        validation = r['validation'][0]
        records.append({'name':label,'n_train':n,'updates':updates,'best_epoch':best['epoch'],
            'minimum_ce':best['validation_loss'],'sr':validation['sr_at_budget'],
            'ge':validation['ge_at_budget'],'last_train_ce':history[-1]['train_loss'],
            'last_validation_ce':history[-1]['validation_loss']})
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig, axes = plt.subplots(1,2,figsize=(10,4.3))
    for history,color,label in [(old_history,'#8d644e','10k / 10,000 updates'),
                                (new_history,'#286d80','45k / 45,000 updates')]:
        epochs = [row['epoch'] for row in history]
        axes[0].plot(epochs,[row['train_loss'] for row in history],color=color,label=label)
        axes[1].plot(epochs,[row['validation_loss'] for row in history],color=color,label=label)
    axes[0].set_title('Training cross-entropy')
    axes[1].set_title('Shared validation cross-entropy')
    for ax in axes:
        ax.set_xlabel('Epoch');ax.set_ylabel('Cross-entropy');ax.grid(alpha=.2)
    axes[1].legend(frameon=False,fontsize=9)
    fig.suptitle('Same CNN / seed0 / cycle / 50 epochs; joint budget and scaler change')
    fig.tight_layout();fig.savefig(OUT/'budget_comparison.png',dpi=170);plt.close(fig)
    fig, axes = plt.subplots(1,2,figsize=(10,4.3))
    for path,color,label in [(ROOT/'runs/kaggle_control/recipe_2026-10-09/output/extracted/validation/clean_curves.npz','#8d644e','10k / epoch1'),
                             (args.download/'validation/clean_curves.npz','#286d80','45k / epoch21')]:
        curves=np.load(path)
        counts=np.arange(1,len(curves['ge'])+1)
        axes[0].plot(counts,curves['ge'],color=color,label=label)
        axes[1].plot(counts,curves['sr'],color=color,label=label)
    axes[0].set_ylabel('Mean key rank (0 = best)')
    axes[1].set_ylabel('Fraction of orders with rank 0')
    axes[1].axhline(.9,color='#666666',linestyle='--',linewidth=1,label='Frozen threshold 0.90')
    axes[1].set_ylim(-.03,1.03);axes[1].legend(frameon=False,fontsize=9)
    for ax in axes:
        ax.set_xlabel('Validation traces per order');ax.grid(alpha=.2)
    fig.suptitle('Clean shared validation; same 20 overlapping orders, one key / seed')
    fig.tight_layout();fig.savefig(OUT/'recovery_comparison.png',dpi=170);plt.close(fig)
    outcome = 'ΠΕΡΑΣΕ' if result['primary_met'] else 'ΑΠΕΤΥΧΕ'
    evidence = {'primary_met':result['primary_met'],'comparisons':records,
        'new_gpu_trainings':1,'total_full_gpu_trainings':5,'approved_cap_exhausted':True,
        'new_confirmation_rows':0,'unused_variable_profiling_rows':30000,
        'same_runtime_environment':same_environment,'actual_environment':new_manifest['environment'],
        'training_seconds':result['summary']['train_seconds'],
        'validation_seconds':result['summary']['validation_seconds'],
        'experiment_seconds':result['experiment_seconds'],'verifier_seconds':verified['seconds'],
        'traces_to_sustained_sr90':result['validation'][0]['traces_to_sustained_success'],
        'novelty_verified':False,'independent_efficacy_claim':False,
        'archive_result_sha256':sha(args.download/'results.json')}
    (OUT/'evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    (OUT/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines = ['# Kaggle baseline45k — 11/10/2026','',
        f'**Το προκαθορισμένο primary criterion {outcome}.**','',
        'Η μία πρόσθετη baseline εκτελέστηκε στην version2 του private notebook '
        'nmavros/hw-sec-exp2, μετά από ρητή συμφωνία για45k/cap5 και account migration. '
        'Το original con1los notebook και όλα τα τέσσερα προηγούμενα trainings διατηρούνται.','',
        'Η version1 σταμάτησε πριν από training λόγω CRLF/LF στη συσκευασία, με μηδέν '
        'optimizer updates. Η version2 εγκρίθηκε χωριστά από τον χρήστη και μετέφερε '
        'ακριβώς τα ίδια frozen bytes. Η τεχνική αποτυχία και το αρχικό archive '
        'διατηρούνται. Δεν έγινε αυτόματη επανάληψη.','',
        'Ίδιο CNN16952, identity labels/byte2, seed0,50epochs,batch50 και authorlinearcycle '
        'max0,005. Training10k→45k, ίδιο χωριστό validation5k, refittedtrain-onlyMinMax. '
        'Updates10000→45000, exposures500000→2250000. Ελέγχεται η κοινή αλλαγή '
        'unique sample/update count/scaler fit, χωρίς isolated-cause ή equal-compute claim.','',
        'Minimum validation CE επιλέγει checkpoint. Όλα20orders/seed8001 διατηρούνται, '
        'budget2000, rank0best/conservative ties. Το validation είναι ήδη viewed και '
        'δεν αποτελεί ανεξάρτητη επιβεβαίωση efficacy. Original failed gates διατηρούνται.','',
        '| Run | Training | Updates | Best epoch | Minimum CE | SR@2000 | GE@2000 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in records:
        lines.append(f"| {r['name']} | {r['n_train']} | {r['updates']} | {r['best_epoch']} | {r['minimum_ce']:.6f} | {round(r['sr']*20)}/20 | {r['ge']:.6f} |")
    conclusion = ('Το45k setup έφτασε το παγωμένο diagnostic threshold. Αυτό δεν '
        'απομονώνει μοναδική αιτία και δεν αποδεικνύει independent-key efficacy. '
        'Combined απαιτεί νέα συγκεκριμένη πρόταση και συμφωνία· δεν εκτελέστηκε.' if result['primary_met'] else
        'Το45k setup δεν έφτασε το παγωμένο diagnostic threshold. Η συγκεκριμένη '
        'jointbudget επέκταση δεν αρκεί. Δεν αποδεικνύεται γενική αδυναμία neuralSCA '
        'ή ότι augmentation δεν βοηθά. Σταματά αυτή η GPU κατεύθυνση σύμφωνα με το πλάνο.')
    sustained=result['validation'][0]['traces_to_sustained_success']
    sustained_text=(f'Δευτερεύον endpoint: SR ≥ 90% διατηρείται από τα {sustained} μέχρι τα '
        '2.000 traces. Πρόκειται για τις ίδιες 20 επικαλυπτόμενες σειρές από ένα pool '
        '5.000 traces, με ένα κλειδί και έναν training seed.' if sustained is not None else
        'Το δευτερεύον sustained SR ≥ 90% endpoint δεν επιτεύχθηκε μέχρι τα 2.000 traces.')
    lines += ['',conclusion,'',sustained_text,'',
        '![Ανάκτηση στο κοινό validation](recovery_comparison.png)','',
        '![Καμπύλες training και shared validation](budget_comparison.png)','',
        'Ο ανεξάρτητος verifier έλεγξε45000LRvalues,40000rankprefixes,minimumCEselection, '
        'nested/disjointsplits, νέο train-onlyMinMaxfit και5000CPU/GPUprobabilities. '
        f"Maxlogproberror{verified['cpu_gpu_max_logprob_error']:.9g}, verifier{verified['seconds']:.6f}s. "
        'Τα104CPUtests είχαν περάσει πριν το freeze και105 μετά τη διόρθωση μεταφοράς. '
        'Syntheticchecks μόνο ορθότητας.','',
        f"Trainingloops{evidence['training_seconds']:.6f}s,validationloops{evidence['validation_seconds']:.6f}s, "
        f"experiment{evidence['experiment_seconds']:.6f}s μετά το notebook setup. "
        'Δεν μετράται εδώ συνολικό setup/queue/session ή account GPU κόστος. '
        f"Exact recorded runtime equality με recipe10k: {same_environment}. "
        'Το actual runtime καταγράφεται στο evidence.json.','',
        'Σύνολο5fullGPUtrainings/cap5exhausted. No combined/attack, originalfixedattacklocked, '
        'variableattackviewed unchanged και variableprofiling30kunused. Δεν επιλέγεται '
        'νέο μοντέλο/seed/checkpoint από attack ή ανεξάρτητο efficacy claim.','',
        'Μετά τη λήψη και την επαλήθευση, η version3 QUICK_SAVE επαναφέρει την αρχική '
        'notebook πηγή χωρίς εκτέλεση. Τα αποτελέσματα της version2 διατηρούνται χωριστά.','',
        '[Kaggle notebook](https://www.kaggle.com/code/nmavros/hw-sec-exp2) · '
        '[Frozen API plan](plan.json) · [Verification](verification.json) · '
        '[Evidence](evidence.json) · [Results](results.json)','']
    (OUT/'REPORT_EL.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(evidence,indent=2))


if __name__ == '__main__': main()
