"""Report every frozen condition after independent training and attack verification."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from paper_confirmation import OUT,ROOT,read,verify_reference,REFERENCE
from sca.data import sha256_file
from sca.train import write_json


def plot_curves(attack,conditions):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for metric,title,ylabel in [('sr','Conditional recovery over100trace orders','Success rate'),
                               ('ge','Mean conservative key rank over100trace orders','Guessing entropy (rank0=best)')]:
        fig,axes = plt.subplots(2,4,figsize=(14,6.5),sharex=True,sharey=True)
        for axis,condition in zip(axes.flat,conditions):
            name = condition['name']
            for label,color in [('baseline','#2459a6'),('combined','#ba531a')]:
                curves = np.load(attack/label/(name+'_curves.npz'))
                axis.plot(curves['trace_counts'],curves[metric],color=color,label=label,linewidth=1.4)
            if metric == 'sr':axis.axhline(.9,color='#666666',linewidth=.8,linestyle='--');axis.set_ylim(-.025,1.025)
            else:axis.set_ylim(-3,258)
            axis.set_title(name.replace('_',' '),fontsize=10)
            axis.grid(alpha=.18);axis.set_xlim(1,2000)
        for axis in axes[-1]:axis.set_xlabel('Attack traces')
        for axis in axes[:,0]:axis.set_ylabel(ylabel)
        handles,labels = axes.flat[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='upper right',ncol=2,frameon=False)
        fig.suptitle(title+' — one fixed key, synthetic corruptions',fontsize=12,x=.42)
        fig.tight_layout(rect=[0,0,1,.95])
        fig.savefig(OUT/(metric+'_attack.png'),dpi=180);plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training-output',type=Path,required=True)
    parser.add_argument('--attack-output',type=Path,required=True)
    args = parser.parse_args()
    plan,training,verification = read(OUT/'plan.json'),read(OUT/'training_verification.json'),read(OUT/'attack_verification.json')
    assert training['verified'] and verification['verified']
    verify_reference(REFERENCE,plan)
    for name,digest in plan['preservation_sha256'].items():assert sha256_file(ROOT/name) == digest,name
    result = read(args.attack_output/'results.json');trained = read(args.training_output/'results.json')
    for path,record in [(args.training_output,training),(args.attack_output,verification)]:
        for name,digest in record['artifact_sha256'].items():assert sha256_file(path/name) == digest,name
    restoration = read(OUT/'restoration.json')
    assert restoration['execution_type'] == 'QUICK_SAVE' and not restoration['new_training_started']
    assert read(OUT/'restored_source_verification.json')['verified']
    summaries = {label:{row['condition']:row for row in rows} for label,rows in result['models'].items()}
    plot_curves(args.attack_output,plan['attack_config']['conditions'])
    rows,paired_rows = [],[]
    for condition in plan['attack_config']['conditions']:
        name = condition['name'];baseline,combined = summaries['baseline'][name],summaries['combined'][name]
        def successes(row):return int(round(row['sr_at_budget']*100))
        def traces(row):return str(row['traces_to_sustained_success']) if row['traces_to_sustained_success'] is not None else '>2000 (censored)'
        rows.append(f"|{name}|{successes(baseline)}/100|{successes(combined)}/100|{baseline['ge_at_budget']:.6f}|{combined['ge_at_budget']:.6f}|{traces(baseline)}|{traces(combined)}|")
        paired = result['paired'][name]
        paired_rows.append(f"|{name}|{paired['delta_sr']:+.2f}|{paired['both_success']}|{paired['baseline_only']}|{paired['combined_only']}|{paired['neither_success']}|")
    h1 = 'ΠΕΡΑΣΕ' if result['baseline_clean_confirmation_met'] else 'ΑΠΕΤΥΧΕ'
    h2 = 'ΠΕΡΑΣΕ' if result['augmentation_joint_primary_met'] else 'ΑΠΕΤΥΧΕ'
    text = f'''# Combined45k και κλειδωμένη τελική attack αξιολόγηση — 11/10/2026

**H1 baseline clean confirmation: {h1}. H2 augmentation joint primary: {h2}.**
Όλες οι οκτώ προκαθορισμένες συνθήκες και όλες οι100σειρές διατηρούνται.
Δεν επιλέχθηκε νέο checkpoint ή recipe από τα attack αποτελέσματα.

## Κλειδωμένο πείραμα

Επαναχρησιμοποιήθηκε η verified baseline45k, minimumCE checkpoint epoch21.
Μία combined45k εκπαίδευση στο ίδιο private nmavros/hw-sec-exp2/version4:
CNN16952,seed0,45k/5k,50epochs,batch50,45000author-cycleupdates/2250000exposures.
Ίδια splits και training-only featureMinMax. Μόνη recipe αλλαγή shifts±5/zero
padding, κατόπιν Gaussianσ0,1, μετάMinMax χωρίς clipping. Minimum clean validation
CE επέλεξε το combined checkpoint epoch{training['best_epoch']}, CE{training['minimum_validation_ce']:.9f}.
Clean viewed validation combinedSR@2000={training['clean_validation_sr_at_2000']:.2f},
GE{training['clean_validation_ge_at_2000']:.6f}. Το validation δεν είναι νέα confirmation.

Μετά ανεξάρτητη επαλήθευση45000LRvalues/40000rankprefixes/5000CPUpredictions,
κλειδώθηκαν και τα δύο checkpoints. Τότε άνοιξε το πλήρες originalfixedattack10k
για μία CPU paired αξιολόγηση, budget2000/100orders/seed8001, corruptionseed9001,
ίδιες αλλοιωμένες inputs και orders στα δύο μοντέλα. Byte2/identity256, traces-only
model inputs, evaluation metadata/key μόνο για scoring, conservative ties/rank0best.

## Όλα τα αποτελέσματα attack

|Condition|Baseline SR@2000|Combined SR@2000|Baseline GE|Combined GE|Baseline sustainedSR90|Combined sustainedSR90|
|---|---:|---:|---:|---:|---|---|
{chr(10).join(rows)}

H1 απαιτεί baselinecleanSR≥0,90. H2 απαιτεί ταυτόχρονα combined_both_oodSR≥0,90,
strictlypositivepairedΔSR έναντι baseline και combinedcleanSR≥0,90. Δεν αλλάζει
το primary εκ των υστέρων. Άλλα contrasts/GE/sustainedSR είναι descriptive secondary.

|Condition|Paired ΔSR|Both success|Baseline only|Combined only|Neither|
|---|---:|---:|---:|---:|---:|
{chr(10).join(paired_rows)}

![Όλες οι SR καμπύλες](sr_attack.png)
![Όλες οι GE καμπύλες](ge_attack.png)

## Όρια ερμηνείας

Η attack confirmation αφορά αθέατες traces της ίδιας fixed-key καμπάνιας,
ίδιο key/acquisition context. Δεν είναι νέο κλειδί, συσκευή ή ανεξάρτητη φυσική
καμπάνια. Οι100overlapping trace orders είναι conditional, όχι100independent
trainings/keys/acquisitions. Δεν αποδίδονται independentBernoulliCIs/p-values.
Τα noise/shifts είναι συνθετικές αλλοιώσεις πραγματικών traces. Ένας trainingseed
δεν εκτιμά between-training variance. Καμία νέα efficacy ή novelty claim πέρα από
τις συγκεκριμένες μετρήσεις δεν ακολουθεί. Τα τέσσερα10kfailures και οι CPU/variable
campaign/selection failures διατηρούνται. Η baseline10k→45k άλλαξε από κοινού
samples/updates/scaler· η νέα matched σύγκριση αφορά μόνο την combined recipe.

## Επαλήθευση, πραγματικό κόστος και ιστορικό

Ο ανεξάρτητος attack verifier ανακατασκεύασε{verification['rank_prefixes_verified']}rankprefixes,
GE/SR/sustainedSR/paired endpoints από savedpredictions, ίδιοplaintext/key/orders,
finite normalizedprobabilities και τα δύο primarycriteria. Δεν έγινε optimizerupdate
στην attack αξιολόγηση. Training verifier{training['seconds']:.6f}s,
CPUattack evaluation{result['evaluation_seconds']:.6f}s,
attack replay verifier{verification['seconds']:.6f}s.
Combinedtrainingloops{trained['summary']['train_seconds']:.6f}s,
validationloops{trained['summary']['validation_seconds']:.6f}s,
experiment{trained['experiment_seconds']:.6f}s μετάsetup. Setup/queue/accountGPUcharge
δεν μετρήθηκαν ως συνολική χρέωση. Recordedruntime matchesbaseline:
{training['recorded_runtime_matches_baseline']}.

Αρχική SaveKernel υποβολή:HTTP400 πριν από version/training, preservedreceipt.
Χωριστά approved compactTAR/XZ correctedsubmission:version4, exactfrozenbytes,
scienceunchanged. Η ακριβής αρχική servercause παραμένει unconfirmed.
112CPUtests passed/14existingwarnings. Τα40previouspreservationartifacts πέρασαν.
Μετά ολοκλήρωση, version{restoration['version']} QUICK_SAVE originalsource χωρίςrun,
remote cells/private/Input verified. Originalcon1los history και nmavrosversions1–4
διατηρούνται. Actual6fullGPUtrainings/cap6exhausted,111850totalupdates/6500000exposures.
Variableprofiling30k unused/variableattack10k unchanged. Νέο πείραμα/seed/model/budget
ή retuning σε αυτά τα viewed attack rows δεν εξουσιοδοτείται από αυτό το πρωτόκολλο.

Πρωτόκολλο:[frozen proposal](../../docs/PAPER_CONFIRMATION_PROTOCOL_2026-10-11.md),
[machine plan](plan.json),[specific approval](authorization.json),
[training verification](training_verification.json),[attack verification](attack_verification.json).
'''
    (OUT/'REPORT_EL.md').write_text(text,encoding='utf-8')
    inputs = ['plan.json','authorization.json','submission_attempt.json','transport_repair/submission_attempt.json',
              'transport_repair/preparation.json','transport_repair/corrected_submission_approval.json',
              'training_verification.json','attack_verification.json','attack_access.json','restoration.json',
              'restored_source_verification.json','REPORT_EL.md','sr_attack.png','ge_attack.png']
    evidence = {'complete':True,'baseline_clean_confirmation_met':result['baseline_clean_confirmation_met'],
                'augmentation_joint_primary_met':result['augmentation_joint_primary_met'],'full_gpu_trainings_total':6,
                'rank_prefixes_verified':verification['rank_prefixes_verified'],'preserved_artifacts':40,
                'attack_output':str(args.attack_output),'training_output':str(args.training_output),
                'recorded_utc':datetime.now(timezone.utc).isoformat(),
                'artifact_sha256':{name:sha256_file(OUT/name) for name in inputs}}
    write_json(OUT/'evidence.json',evidence)
    print(json.dumps({k:v for k,v in evidence.items() if k != 'artifact_sha256'},indent=2))


if __name__ == '__main__':main()
