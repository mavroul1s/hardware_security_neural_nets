# Διορθωμένη συσκευασία — προετοιμασμένη, δεν υποβλήθηκε

Η μία εγκεκριμένη υποβολή απορρίφθηκε από το SaveKernel API με HTTP400 στις
11/10/2026, πριν δημιουργηθεί version ή ξεκινήσει training. Ο ανεξάρτητος read-only
έλεγχος επέστρεψε currentversion3/private, με τις canonical code cells αμετάβλητες.
Η αρχική προσπάθεια και το πλήρες CLI stderr διατηρούνται στο ../submission_attempt.json.
Actual5GPUtrainings, κανένα νέο optimizer update και fixedattack ακόμη κλειστό.

Η ακριβής αιτία της server απόρριψης δεν επιβεβαιώθηκε: το CLI δεν αποθήκευσε το
response body. Το αρχικό notebook είχε1235267bytes και metadata που διέφεραν από
την προηγούμενη επιτυχή υποβολή. Η διορθωμένη προετοιμασία αντιμετωπίζει και τα δύο:

- Inline TAR/XZ αντί ZIP:813745bytes notebook. Και τα εννέα reference files έχουν
  ακριβώς τα frozen SHA256. Κανένα checkpoint/config/split/scaler byte δεν αλλάζει.
- Τα ήδη επιτυχημένα private metadata επαναχρησιμοποιούνται, με explicit
  docker_image_pinning_type=original, ίδιο pinnedimage/T4/Input/notebook identity.
- Όλες3codecells compile, τα πραγματικά embedded payloads ανακτώνται προσωρινά
  και επαληθεύονται. Το execution suffix και τα δύο frozen extension bytes διατηρούνται.
- FullCPU suite:112passed/14existingwarnings/26,96s. Ο αρχικός frozen111test report
  διατηρείται· το νέο transport test έχει δικό του report, χωρίς αλλαγή scientific plan.

Frozen scientific plan SHA256:
`6e3d016533598b7da89c5952a578bd9d7a42b39bff0cce3967ba1ffdb7302a9e`.
Corrected notebook SHA256:
`3e267c3030729d552ae046d02f0d9237e946e32b1a58f88e986448f0ab066d28`.
Original extension SHA256:
`7bcb6573af4bbfdc206e7efe64b5537172827b7a587a87afe31507a1174ef972`.

Η έγκριση cap6/τελικήςattack αξιολόγησης παραμένει σε ισχύ. Χρειάζεται χωριστή
συμφωνία για μία διορθωμένη υποβολή, επειδή το εγκεκριμένο πρωτόκολλο όριζε μία
υποβολή χωρίς automatic retry. Δεν εκτελέστηκε δεύτερη SaveKernel κλήση.
