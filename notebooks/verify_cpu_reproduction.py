"""Check replay evidence and write a report from the measured CPU results."""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import numpy as np
from sca.train import code_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/cpu_reproduction_2026-10-05"
WORK = ROOT / "runs/cpu_reproduction_2026-10-05"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_sha(root):
    digest = hashlib.sha256()
    for path in sorted([*root.glob("src/**/*.py"), *root.glob("scripts/*.py"),
                        *root.glob("configs/*.json"), root / "pyproject.toml"]):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    result = read(OUT / "results.json")
    plan = read(OUT / "plan.json")
    wheels = read(OUT / "wheels.json")
    env = read(OUT / "environment.json")
    evaluation_plan = read(OUT / "evaluation_plan.json")
    expected_source = plan["source_sha256"]
    assert source_sha(ROOT) == source_sha(WORK / "source") == code_identity()["source_sha256"] == expected_source
    for relative, expected in evaluation_plan["input_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    for entry in plan["snapshot_files"]:
        assert sha(WORK / "source" / entry["path"]) == entry["sha256"], entry["path"]
    assert sha(WORK / "source/notebooks/reproduce_cpu.py") == sha(ROOT / "notebooks/reproduce_cpu.py")
    assert sha(ROOT / "requirements-lock-cpu-reproduction.txt") == wheels["lock_sha256"]
    assert env["packages"] == plan["targets"]
    assert env["isolated_flag"] == 1 and env["user_site_enabled"] is False
    assert "No broken requirements found." in (WORK / "pip_check.log").read_text(encoding="utf-8-sig")
    for name, entry in wheels["wheels"].items():
        assert sha(WORK / "wheelhouse" / entry["filename"]) == entry["sha256"], name
    suite = ET.parse(OUT / "pytest.xml").getroot().find("testsuite")
    tests = {name: int(suite.attrib[name]) for name in ("tests", "failures", "errors", "skipped")}
    assert tests == {"tests": 44, "failures": 0, "errors": 0, "skipped": 0}
    log = (WORK / "tests.log").read_text(encoding="utf-8-sig")
    match = re.search(r"44 passed, (\d+) warnings in ([\d.]+)s", log)
    assert match
    tests.update({"warnings": int(match[1]), "reported_seconds": float(match[2]),
                  "junit_seconds": float(suite.attrib["time"])})
    previous = ROOT / "outputs/correlation_robustness_2026-10-05"
    with np.load(OUT / "sensitivity/audit_arrays.npz", allow_pickle=False) as actual, \
            np.load(previous / "audit_arrays.npz", allow_pickle=False) as saved:
        assert set(actual.files) == set(saved.files)
        for name in saved.files:
            assert actual[name].dtype == saved[name].dtype
            assert actual[name].shape == saved[name].shape
            assert actual[name].tobytes() == saved[name].tobytes(), name
        assert len(actual.files) == 138
    assert result["sensitivity"]["independent_verification"]["endpoint_checks"] == 640
    assert result["new_real_data_optimizer_updates"] == result["new_gpu_trainings"] == 0
    assert result["final_attack_payloads_read"] is False
    assert result["inputs_preserved"]
    verification = {"tests": tests, "pip_check_passed": True, "exact_dependencies": 27,
        "wheel_hashes_verified": 27, "original_snapshot_files_verified": len(plan["snapshot_files"]),
        "original_and_snapshot_source_sha256": expected_source, "all_replay_inputs_preserved": True,
        "clean_cpu_rank_values_matched": 160000, "sensitivity_rank_values_matched": 1280000,
        "sensitivity_arrays_bitwise_equal": 138, "independent_endpoint_checks": 640,
        "new_real_data_optimizer_updates": 0, "new_gpu_trainings": 0,
        "full_gpu_trainings_total": 3, "canonical_notebook_count": 1,
        "final_attack_payloads_read": False,
        "artifact_hashes": {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(OUT.rglob("*"))
                            if path.is_file() and path not in {OUT / "verification.json", OUT / "REPORT_EL.md"}}}
    write_json(OUT / "verification.json", verification)
    best, last = result["checkpoints"]["best"], result["checkpoints"]["last"]
    text = f"""# Αναπαραγωγή αποθηκευμένων αποτελεσμάτων σε καθαρό CPU περιβάλλον

Ημερομηνία: 2026-10-05. **Ο έλεγχος αναπαραγωγής πέρασε.** Νέο venv από wheels,
ξεχωριστό αντίγραφο source, ίδια δεδομένα/splits/checkpoints και profiling validation.
Δεν έγινε νέα εκπαίδευση στα πραγματικά δεδομένα ή στο Kaggle.

## Τι επιβεβαιώθηκε

| Αποθηκευμένο checkpoint | Epoch | Clean validation CE | GE@2.000 | SR@2.000 |
|---|---:|---:|---:|---:|
| Literature CNN best | {best['epoch']} | {best['splits']['validation']['cross_entropy']:.12f} | {best['key_recovery']['ge_at_budget']:.2f} | 0/20 |
| Literature CNN last | {last['epoch']} | {last['splits']['validation']['cross_entropy']:.12f} | {last['key_recovery']['ge_at_budget']:.2f} | 0/20 |

Οι training/validation CE και accuracy συμφωνούν ακριβώς με την προηγούμενη CPU
διάγνωση: μετρημένη απόκλιση CE **0**, με ανοχή 1e-7 παγωμένη πριν την εκτέλεση.
Και οι 40.000 prefix ranks ανά checkpoint συμφωνούν με τα προηγούμενα CPU arrays.
Η σύγκριση αφορά αποθηκευμένο CPU inference· οι ήδη καταγεγραμμένες μικρές διαφορές
CPU/GPU σε ενδιάμεσα prefixes δεν επαναβαπτίζονται σε bitwise GPU αναπαραγωγή.
Τα ReLU/LeakyReLU historical trainings διατηρήθηκαν, αλλά δεν επαναξιολογήθηκαν εδώ.

Τα παγωμένα centered-product ζεύγη **181×521** και **156×517** διατηρούν clean
SR20/20 και GE0. Sustained SR90 στα **631** και **481** traces αντίστοιχα.
Άλλοι 80.000 raw-product prefix ranks συμφωνούν ακριβώς με την προηγούμενη διάγνωση.
Δεν επαναλήφθηκε επιλογή σημείων ή αναζήτηση καλύτερου ζεύγους.

Επαναλήφθηκαν οι **8 υπάρχουσες συνθήκες × 2 ζεύγη × 2 τρόποι εξαγωγής**:
και οι **32 γραμμές αποτελεσμάτων**, τα **138 arrays** (ίδια dtype/shape/bytes),
οι offsets, τα tensor hashes και οι έλεγχοι padding συμφωνούν. Αυτό περιλαμβάνει
1.280.000 sensitivity rank values. Ο ανεξάρτητος Pearson endpoint έλεγχος επαλήθευσε
ξανά **640 endpoints** και ανακατασκεύασε τα tensors με το production augment_batch.

## Καθαρό περιβάλλον και προέλευση

Windows AMD64, Python {env['runtime']['python']}, PyTorch {env['packages']['torch']},
NumPy {env['packages']['numpy']}, h5py {env['packages']['h5py']}, matplotlib {env['packages']['matplotlib']}.
Το νέο περιβάλλον είναι στο `runs/cpu_reproduction_2026-10-05/venv` και το source
στο `runs/cpu_reproduction_2026-10-05/source`. Εγκαταστάθηκαν **27 exact dependency
wheels** με `--no-index --require-hashes`, έπειτα editable project από το snapshot
με `--no-deps --no-build-isolation`. Το pip25.0.1 προήλθε από τη δημιουργία του venv.
Δεν αντιγράφηκαν εγκατεστημένα site-packages από το προηγούμενο venv.

Χρησιμοποιήθηκαν 26 αμετάβλητα wheel αρχεία από την τοπική cache
({wheels['cache_bytes']:,} bytes). Κατέβηκε μόνο το setuptools78.1.0 από το PyPI
({wheels['downloaded_bytes']:,} bytes, περίπου1,26MB wheel· δεν μετρήθηκε συνολικό HTTP traffic).
Τα filenames των cached wheels ανασυντέθηκαν από METADATA/WHEEL tags, χωρίς
repackaging ή αλλαγή των bytes. Τα hashes όλων των 27 wheels επαληθεύτηκαν ξανά.

Το [νέο CPU lockfile](../../requirements-lock-cpu-reproduction.txt) έχει exact versions
και SHA256 ανά συμβατό Windows/CPython3.12 wheel. Δεν είναι CUDA ή cross-platform lock.
Το παλιό `requirements-lock-cpu.txt` διατηρείται ως ιστορικό: η editable Git αναφορά
στο παλιό commit3cc007d δεν χρησιμοποιήθηκε για αυτόν τον έλεγχο.

Το `python -I` απέκλεισε inherited PYTHONPATH και user-site imports. Ελέγχθηκαν
sys.prefix, module paths, dependency versions και sca path: οι βιβλιοθήκες φορτώθηκαν
από το νέο venv και το sca από το ξεχωριστό snapshot. Το frozen source hash παραμένει
`{expected_source}` τόσο στο αρχικό project όσο και στο snapshot.
Το [environment.json](environment.json) καταγράφει τα πραγματικά paths/versions.

## Έλεγχοι και πραγματικό κόστος

Το πλήρες suite πέρασε: **44 passed, {tests['warnings']} warnings**, {tests['reported_seconds']:.2f}s
(JUnit {tests['junit_seconds']:.3f}s). Οι υπάρχουσες προειδοποιήσεις αφορούν deprecated
pyparsing interfaces μέσα στο matplotlib. Ο έλεγχος `pip check` πέρασε.
Ο χρόνος του suite ήταν μεγαλύτερος από προηγούμενες συνεδρίες· δεν μετρήθηκε η αιτία
και δεν αποδίδεται αυθαίρετα στο νέο venv ή σε αλλαγή αλγορίθμου.
Τα synthetic fixtures ελέγχουν correctness/continuation, όχι φυσική αποτελεσματικότητα.

Το πραγματικό validation replay πήρε **{result['total_replay_seconds']:.2f}s** μετά τις εισαγωγές:
clean CNN/raw correlation {result['clean_replay_seconds']:.2f}s,
sensitivity {result['sensitivity']['seconds']:.2f}s και ανεξάρτητη verification
{result['sensitivity']['independent_verification']['seconds']:.2f}s, συν μικρό υπόλοιπο ελέγχων/I/O.
Αυτοί δεν είναι συνολικοί χρόνοι λήψης, εγκατάστασης ή ολόκληρης συνεδρίας.
Νέες GPU εκπαιδεύσεις0, νέα optimizer updates σε πραγματικό ASCAD0.

## Προστασία του πρωτοκόλλου και όρια

Τα input hashes παγώθηκαν στο [evaluation_plan.json](evaluation_plan.json) πριν την
ανάγνωση traces και ελέγχθηκαν μετά: dataset, splits, best/last checkpoints,
παλιές διαγνωστικές μετρήσεις, active code/Input archives και canonical/saved notebook
διατηρήθηκαν. Το πραγματικό HDF5 διαβάστηκε μόνο στο Profiling_traces· τα synthetic
fixtures των tests είναι ξεχωριστά. Το final ASCAD Attack_traces payload δεν διαβάστηκε.

Το gate παραμένει failed: το minimum-CE CNN checkpoint έχει SR0/20, άρα combined
παραμένει skipped. Σύνολο3 full GPU trainings και1 canonical Kaggle notebook.
Το `.ipynb` μέσα στο snapshot είναι archival αντίγραφο του ίδιου notebook.
Η επιτυχία correlation δεν αλλάζει το gate και δεν αποδεικνύει όφελος training augmentation.
Το oracle εξακολουθεί να γνωρίζει την τεχνητή μετατόπιση· δεν είναι εκτιμημένη ευθυγράμμιση.

Η αναπαραγωγή ελέγχει checkpoint inference και CPU diagnostics στο ίδιο Windows
μηχάνημα και base interpreter. Δεν επανεκπαίδευσε CNN, δεν ελέγχει άλλο hardware,
άγνωστο κλειδί, άλλο dataset ή independent profiling device. Δεν είναι νέα ερευνητική
μέτρηση αποτελεσματικότητας ή εγγύηση μεταφοράς σε διαφορετικό περιβάλλον.

## Αρχεία και επανάληψη

Οι [μετρήσεις](results.json), το [JUnit](pytest.xml), τα [wheels/hashes](wheels.json),
η [τελική επαλήθευση](verification.json) και η
[ανεξάρτητη sensitivity verification](sensitivity/verification.json) περιέχουν τα τεκμήρια.
Οι companions είναι [reproduce_cpu.py](../../notebooks/reproduce_cpu.py),
[prepare_cpu_reproduction.py](../../notebooks/prepare_cpu_reproduction.py) και
[verify_cpu_reproduction.py](../../notebooks/verify_cpu_reproduction.py).
Installation/test logs, το wheelhouse και το source snapshot διατηρούνται κάτω από
`runs/cpu_reproduction_2026-10-05/`, εκτός Git. Δεν χρειάζονται Kaggle ή API credentials.

Η ακριβής σειρά που εκτελέστηκε ήταν: νέο venv → offline hashed dependencies →
editable snapshot → pip check → pytest από το snapshot → CPU replay → verification.
Οδηγίες με τις εντολές βρίσκονται στο [CPU_REPRODUCTION.md](../../docs/CPU_REPRODUCTION.md).
Το replay προστατεύει υπάρχοντα evidence directories και δεν επιτρέπει σιωπηρή αντικατάσταση.

Επόμενο βήμα: τελική επιμέλεια της ελληνικής διαγνωστικής μελέτης για συζήτηση στο μάθημα.
Νέο GPU πλάνο απαιτεί συγκεκριμένο ερευνητικό λόγο και συμφωνία αλλαγής scope/ορίου.
"""
    (OUT / "REPORT_EL.md").write_text(text, encoding="utf-8")
    print(json.dumps({"tests": tests, "sensitivity_arrays_bitwise_equal": 138,
                      "inputs_preserved": True, "report": str(OUT / "REPORT_EL.md")}, indent=2))


if __name__ == "__main__":
    main()
