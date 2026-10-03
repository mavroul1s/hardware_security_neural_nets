# Δεδομένα (εκτός Git)

Στόχος: μόνο το συγχρονισμένο `ASCAD_databases/ASCAD.h5`, 700 samples,
50.000 profiling και 10.000 attack traces. Byte 2, identity = SBOX(plaintext[2] XOR key[2]).

Επίσημη πηγή και checksum:
[ANSSI fixed-key README](https://github.com/ANSSI-FR/ASCAD/blob/master/ATMEGA_AES_v1/ATM_AES_v1_fixed_key/Readme.md).
Το επίσημο ZIP περιλαμβάνει raw δεδομένα: ~4,2 GB λήψη και ~7,3 GB αποσυμπίεση.
Το script `scripts/download_ascad.py` χρησιμοποιεί HTTP ranges για το μικρό προεπεξεργασμένο μέλος,
ελέγχει το επίσημο SHA-256 και γράφει provenance JSON. Αν ο server αγνοεί Range, σταματά.
Δεν χρειάζεται λήψη raw δεδομένων για το παρόν scope.

Το campaign README αναφέρει EM acquisition, ενώ ο συνοπτικός πίνακας του repository λέει Power (Icc).
Διατηρούμε αυτή την ασυμφωνία ως σημείωση προέλευσης· το αρχικό paper περιγράφει ηλεκτρομαγνητικές μετρήσεις.
Δεν ισχυριζόμαστε ότι οι συνθετικές αλλοιώσεις είναι πραγματικές μετρήσεις από διαφορετική συσκευή.
