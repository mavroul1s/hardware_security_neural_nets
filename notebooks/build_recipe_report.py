"""Build a Greek report from verified Kaggle artifacts, without another training."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from sca.train import write_json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/kaggle_recipe_2026-10-09'


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',type=Path,required=True)
    args=parser.parse_args()
    verified=read(OUT/'verification.json')
    assert verified['verified']
    result=read(args.download/'results.json')
    new_history=read(args.download/'none_seed0/history.json')
    old=ROOT/'outputs/kaggle_literature_v7_2026-10-03/none'
    old_history=read(old/'history.json')
    old_result=read(old/'validation/results.json')[0]
    old_best=min(old_history,key=lambda r:r['validation_loss'])
    new_best=min(new_history,key=lambda r:r['validation_loss'])
    new_result=result['validation'][0]
    plan=read(OUT/'plan.json')
    rows=[{'recipe':'constant LR / batch128','updates':3950,'best_epoch':old_best['epoch'],
           'minimum_ce':old_best['validation_loss'],'sr':old_result['sr_at_budget'],'ge':old_result['ge_at_budget']},
          {'recipe':'author linear cycle / batch50','updates':10000,'best_epoch':new_best['epoch'],
           'minimum_ce':new_best['validation_loss'],'sr':new_result['sr_at_budget'],'ge':new_result['ge_at_budget']}]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for history,color,label in [(old_history,'#986544','Constant LR / batch128'),(new_history,'#216e7d','Author cycle / batch50')]:
        epochs=[r['epoch'] for r in history]
        axes[0].plot(epochs,[r['train_loss'] for r in history],color=color,label=label)
        axes[1].plot(epochs,[r['validation_loss'] for r in history],color=color,label=label)
    axes[0].set_title('Training cross-entropy');axes[1].set_title('Shared validation cross-entropy')
    for ax in axes:ax.set_xlabel('Epoch');ax.set_ylabel('Cross-entropy');ax.grid(alpha=.2)
    axes[1].legend(frameon=False,fontsize=9)
    fig.suptitle('Same CNN / 10k training / seed0 / 50 epochs; different update counts')
    fig.tight_layout();fig.savefig(OUT/'recipe_comparison.png',dpi=170);plt.close(fig)
    evidence={'primary_met':result['primary_met'],'comparisons':rows,'new_gpu_trainings':1,
        'full_gpu_trainings_total':4,'new_confirmation_rows':0,'variable_unused_rows':30000,
        'training_loop_seconds':result['summary']['train_seconds'],
        'validation_loop_seconds':result['summary']['validation_seconds'],
        'experiment_seconds':result['experiment_seconds'],'verifier_seconds':verified['seconds'],
        'cpu_tests':plan['tests'],'independent_efficacy_claim':False,'novelty_verified':False,
        'last_epoch_old':old_history[-1],'last_epoch_new':new_history[-1],
        'source_and_old_checkpoints_preserved':True,'same_remote_notebook':True,'attack_locked':True}
    write_json(OUT/'evidence.json',evidence)
    write_json(OUT/'results.json',result)
    outcome='ΠΕΡΑΣΕ' if result['primary_met'] else 'ΑΠΕΤΥΧΕ'
    text=['# Kaggle: ίδιο CNN με διαφορετικό training recipe — 9/10/2026','',
        f'**Το προκαθορισμένο primary criterion {outcome}.**','',
        'Ο χρήστης επέτρεψε ένα νέο πείραμα στο Kaggle. Η version 9 του ίδιου ιδιωτικού '
        'notebook εκτέλεσε μία επιπλέον baseline, με το ίδιο CNN των 16.952 parameters, '
        'original training 10k/validation 5k, seed 0, 50 epochs και train-only MinMax. '
        'Δεν έγινε combined training και δεν διαβάστηκε attack payload.','',
        'Η υπόθεση ήταν ότι το προσαρμοσμένο author optimizer recipe αποκαθιστά '
        'clean validation SR@2000 ≥ 18/20. Άλλαξαν batch 128 → 50 και constant '
        'Adam LR 0,001 → τριφασικό γραμμικό cycle με max 0,005. Ο αριθμός updates '
        'αυξήθηκε από 3.950 σε 10.000, με ίδιες 500.000 εκθέσεις traces. '
        'Ελέγχεται το joint recipe, χωρίς equal-update ή isolated-cause claim.','',
        'Το [πρωτόκολλο και author-code audit](LITERATURE_AND_PROTOCOL.md) '
        'και το [plan](plan.json) πάγωσαν πριν από τη νέα εκπαίδευση. Η LR επέκταση '
        'έχει δικό της hash σε plan/config/checkpoints· ο production source παρέμεινε '
        'αμετάβλητος. Η προσαρμογή δεν αναπαράγει το πλήρες author 45k/Keras experiment.','',
        '## Κοινό validation endpoint','',
        'Checkpoint επιλογής: minimum validation CE μεταξύ των 50 epochs. '
        'Αξιολόγηση: όλα τα ίδια 20 trace orders, budget 2.000 και rank 0 = best, '
        'με conservative ties. Το validation έχει ήδη εξεταστεί. Δεν αποτελεί '
        'νέα prospective confirmation ή ανεξάρτητο acquisition/key.','',
        '| Recipe | Updates | Best epoch | Minimum CE | SR@2000 | GE@2000 |',
        '|---|---:|---:|---:|---:|---:|']
    for r in rows:text.append(f"| {r['recipe']} | {r['updates']} | {r['best_epoch']} | {r['minimum_ce']:.6f} | {round(r['sr']*20)}/20 | {r['ge']:.6f} |")
    conclusion=('Το joint recipe έφτασε το diagnostic criterion στο κοινό validation. '
        'Δεν απομονώνεται η συμβολή batch, schedule ή αριθμού updates. Ανεξάρτητη '
        'επιβεβαίωση θα χρειαζόταν νέο πρωτόκολλο και επιτρεπτά δεδομένα.' if result['primary_met'] else
        'Το joint recipe δεν αποκατέστησε το απαιτούμενο clean recovery στο κοινό '
        'validation. Η συγκεκριμένη αλλαγή δεν αρκεί υπό το 10k/50-epoch setup. '
        'Δεν αποδεικνύεται ότι μεγαλύτερο unique training budget ή άλλος model '
        'θα αποτύγχανε, ούτε απομονώνεται μοναδική αιτία των CNN failures.')
    text += ['',conclusion,'',
        f"Στην τελευταία epoch το νέο training CE είναι {new_history[-1]['train_loss']:.6f} "
        f"και το validation CE {new_history[-1]['validation_loss']:.6f}, έναντι "
        f"{old_history[-1]['train_loss']:.6f} και {old_history[-1]['validation_loss']:.6f} στο παλιό recipe. "
        'Η καλύτερη προσαρμογή στο training συνυπάρχει με χειρότερο τελικό validation CE. '
        'Πρόκειται για περιγραφική απόκλιση, χωρίς απομόνωση αιτίας της αποτυχίας recovery.','',
        '![Learning curves της παγωμένης σύγκρισης](recipe_comparison.png)','',
        '## Επαλήθευση, κόστος και όρια','',
        f"Πριν το freeze πέρασαν 99 tests/14 προϋπάρχουσες warnings, με JUnit χρόνο {float(plan['tests']['time']):.3f}s. "
        'Τα τέσσερα νέα tests περιλαμβάνουν πραγματικό synthetic CPU smoke και '
        'state-continuation check. Αποτελούν correctness checks, χωρίς φυσική efficacy evidence.','',
        'Ο χωριστός verifier έλεγξε 10.000 LR values, minimum-CE checkpoint, ίδια '
        'splits και normalizer, όλες τις 40.000 GPU rank prefixes και CPU inference '
        f"σε 5.000 traces. Μέγιστη CPU/GPU log-probability απόκλιση: {verified['cpu_gpu_max_logprob_error']:.9g}. "
        'Επαληθεύτηκαν τα hashes όλων των προηγούμενων checkpoints και εισόδων.','',
        'Τα αποθηκευμένα περιβάλλοντα συμφωνούν: Python 3.13.15, Torch 2.8.0+cu126, '
        'CUDA 12.6, Tesla T4, NumPy 2.2.6 και h5py 3.14.0. Η version 10 είναι '
        'QUICK_SAVE της αρχικής ασφαλούς notebook πηγής, χωρίς νέα εκτέλεση. '
        'Η executed version 9, τα νέα checkpoints και οι προβλέψεις διατηρούνται.','',
        f"Training loops {result['summary']['train_seconds']:.6f}s, validation loops {result['summary']['validation_seconds']:.6f}s. "
        f"Experiment wall time {result['experiment_seconds']:.6f}s· τοπικός verifier {verified['seconds']:.6f}s χωριστά. "
        'Τα loops δεν περιλαμβάνουν setup, installs, queue ή session teardown. '
        'Το experiment timer αρχίζει μετά το notebook setup και περιλαμβάνει '
        'checks/training/checkpoint I/O/evaluation. Δεν καταγράφεται ολόκληρη η GPU '
        'χρέωση του λογαριασμού ως μετρημένο κόστος.','',
        'Το όριο είναι πλέον τέσσερα ολοκληρωμένα GPU trainings συνολικά. '
        'Η παρούσα εκτέλεση δεν ενεργοποιεί automatic combined ή νέο seed/budget. '
        'Το αρχικό αποτυχημένο gate και όλες οι CPU αρνητικές επιβεβαιώσεις διατηρούνται. '
        'Οι 30.000 unused variable profiling rows παραμένουν αχρησιμοποίητες. '
        'Το αρχικό fixed attack παραμένει locked και το viewed variable attack δεν επαναξιολογήθηκε.','',
        'Η ισχυρότερη ερμηνεία παραμένει diagnostic benchmark/failure analysis. '
        'Δεν τεκμηριώνεται νέα μέθοδος, cross-device physical efficacy ή '
        'ανεξάρτητη key-recovery γενίκευση.','',
        '[Kaggle notebook — executed version 9](https://www.kaggle.com/code/con1los/hw-sec-exp2) · '
        '[Results](results.json) · [Evidence](evidence.json) · [Independent verification](verification.json) · '
        '[Execution status](execution_status.json) · [Tests](pytest.xml)','']
    (OUT/'REPORT_EL.md').write_text('\n'.join(text),encoding='utf-8')
    print(json.dumps({k:v for k,v in evidence.items() if k!='cpu_tests'},indent=2))


if __name__=='__main__':main()
