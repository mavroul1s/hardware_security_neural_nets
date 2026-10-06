# Πρωτογενής έλεγχος δεύτερης ASCAD καμπάνιας — 5/10/2026

Ελέγχθηκαν οι επίσημες ANSSI-FR πηγές:

- [Variable-key README](https://github.com/ANSSI-FR/ASCAD/blob/master/ATMEGA_AES_v1/ATM_AES_v1_variable_key/Readme.md): ήδη ασυγχρόνιστη καμπάνια, μία σταθερού και δύο τυχαίου κλειδιού λήψεις ανά τρεις, extracted profiling200k/attack100k και window1400. Το αρχικό extracted αρχείο και τα πρόσθετα desync50/100 έχουν διαφορετικά checksums.
- [Extraction example](https://github.com/ANSSI-FR/ASCAD/blob/master/ATMEGA_AES_v1/ATM_AES_v1_variable_key/example_generate_params): profiling raw index modulo3≠2, attack modulo3=2. Το συγκεκριμένο example δημιουργεί desync100, δεν εκτελέστηκε εδώ.
- [Official generation code](https://github.com/ANSSI-FR/ASCAD/blob/master/ASCAD_generate.py): identity label SBOX(plaintext[2] xor key[2]); εξαγωγή άθικτου window ή με πρόσθετη τυχαία μετατόπιση.

Κατέβηκε μόνο το αρχικό extracted resource b4ace767-c2a4-4db4-8e01-4527b5b91f00.
Το επίσημο SHA-256 d834da6ca5a288c4ba5add8e336845270a055d6eaf854dcf2f325a2eb6d7de06
επαληθεύτηκε τοπικά. Τα σχήματα/dtypes ελέγχθηκαν χωρίς ανάγνωση τιμών πριν την
προοπτική παγίωση. Training και evaluated attack labels ελέγχθηκαν μετά το fit.
Πηγή και checksum αφορούν dataset provenance, δεν αποδεικνύουν επιτυχία της μεθόδου.

Η δοκιμή είναι επανάληψη πρωτοκόλλου με νέο training fit στην ίδια οικογένεια
ATMega8515 implementation. Δεν αποδεικνύεται διαφορετική φυσική συσκευή, zero-shot
μεταφορά ή αποτέλεσμα από αλλαγή κλειδιού μόνο. Το νέο κλειδί και η απουσία του από
το επιλεγμένο training ελέγχθηκαν μετά την παγίωση· η αποτελεσματικότητα προκύπτει
από τοπικό frozen evaluation, όχι από τα παραδείγματα των δημιουργών.

Οι γνωστές μέθοδοι και τα κενά novelty audit διατηρούνται στα
[alignment audit](PAPER_ALIGNMENT_AUDIT_2026-10-05.md) και
[SAD baseline audit](ALIGNMENT_BASELINES_2026-10-05.md). Καμία exhaustive novelty
verification, φυσική injected-noise acquisition ή cross-device σύγκριση δεν έγινε.
