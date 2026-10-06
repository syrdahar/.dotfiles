# desk pdf — boîte à outils PDF hors ligne (façon PDF24)

Date : 2026-09-28 · Statut : design validé, en attente de relecture

## 1. But

Remplacer PDF24 (en ligne) par un outil local intégré au command center Hyprland.
16 outils : Merge, Split, Compress, Edit, Sign, Converter, Images → PDF, PDF → Images,
Extract images, Protect, Unlock, Rotate, Remove pages, Extract pages, Rearrange,
Webpage → PDF.

Usage réel observé (~/Downloads) : lettres de motivation, CV, relevés, NDA, certificats,
sujets de cours → priorités pratiques : Sign, Merge, Compress.

## 2. Décisions

| Sujet | Décision |
|---|---|
| Interface | Hybride : moteur Python unique, utilisé par rofi, le clic droit Dolphin et une fenêtre PyQt6 |
| Converter | Office (docx/odt/xlsx/pptx…) → PDF via LibreOffice ; html/md → PDF via Qt WebEngine ; PDF → txt via `pdftotext -layout`. Pas de PDF → Word |
| Edit | Annotations et ajouts, masquage blanc, caviardage réel, remplissage des formulaires AcroForm. Pas de modification du texte existant |
| Sign | Signature visuelle (dessin ou image importée), enregistrée, aplatie à l'enregistrement. Signature certifiée → ouverture dans Okular |
| Sorties | À côté de l'original avec un suffixe, jamais d'écrasement (`-2`, `-3`…). Bouton « Enregistrer sous… » en plus dans la fenêtre |
| Leader | **P** = PDF ; les projets passent de P à **E** (leader et SUPER+touche) |
| i18n | Libellés « français ‖ english » (conventions `t` / `bi_row`) ; la fenêtre suit `desk lang` |

## 3. Architecture

```
~/.local/bin/desktop/
├── desk-pdf              bash : menu rofi, sélection des fichiers, appel du moteur, notifications
└── pdf/
    ├── ops.py            une fonction par outil, sans interface : (entrées, options) → chemins créés
    ├── pages.py          analyse des plages "1-3,5,8-"
    ├── naming.py         nom de sortie avec suffixe, sans écrasement
    ├── cli.py            `desk pdf <outil> fichiers… [options]` (argparse)
    ├── app.py            fenêtre : accueil (16 tuiles, favoris, dépôt de fichiers), panneaux d'options
    ├── organizer.py      vue miniatures
    ├── editor.py         vue page : annotations, masquage, caviardage, formulaires
    ├── signature.py      zone de dessin, import, bibliothèque de signatures
    └── tests/            pytest
~/.local/share/kio/servicemenus/desk-pdf.desktop   sous-menu « PDF » (exécutable)
~/.local/share/desk/pdf/signatures/                 PNG transparents
~/.local/state/desk/pdf.log                         journal technique (sans mots de passe)
~/.local/state/desk/pdf.favorites                   tuiles favorites
```

Règle : `ops.py` n'importe rien de Qt. Rofi, Dolphin et la fenêtre passent tous par lui,
directement ou via `cli.py`. `desk-pdf` source `lib.sh` (`DESK_NAME=pdf`, `notify`, `die`,
`desk_on_err`, `menu`, `t`, `bi_row`) comme les autres modules.

### Accès

- **Leader P / SUPER+P** → `desk leader pdf` : menu rofi des 16 outils, plus une ligne
  « Ouvrir la boîte à outils PDF ».
  - Fichiers d'entrée : ceux passés en argument (Dolphin), sinon un sélecteur de fichiers.
  - Les outils visuels (Edit, Sign, Rearrange) ouvrent directement la fenêtre sur la bonne vue.
- **Palette** : une entrée par outil (`actions.sh`).
- **Dolphin** : sous-menu « PDF » selon le type MIME.
  - `application/pdf` : tous les outils sauf Images → PDF.
  - `image/*` : Images → PDF.
  - Documents Office et html/md : Converter.
- **Notification de fin** : boutons Ouvrir, Afficher dans Dolphin, → Drive (`desk drive push`).

### Fichiers existants modifiés (avec sauvegarde `*.bak-2026-09-28-pdf`)

- `~/.config/hypr/desktop-leader.conf` : P → `desk leader pdf`, E → `desk leader project`
  (`bindd` du submap et `bind SUPER`).
- `~/.local/bin/desktop/actions.sh` : entrées de palette PDF ; ajouter `pdf` à la boucle des modules.
- `~/.local/bin/desktop/README.md` : section PDF et touche des projets mise à jour.
- Toute autre référence à « leader P = projets » trouvée par grep (cheatsheet, commentaires) est
  mise à jour. Aucune autre modification.

## 4. Outils (moteur)

Toutes les opérations sur les pages sont sans perte (pas de ré-encodage).

| Outil | Outil utilisé | Comportement | Sortie |
|---|---|---|---|
| Merge | PyMuPDF `insert_pdf` | Ordre de sélection ; garde les liens ; un signet par fichier source | `<premier>-merged.pdf` |
| Split | pikepdf | Modes : chaque page / toutes les N pages / plages `1-3,4-7,8-` | dossier `<nom>-split/` (`<nom>-001.pdf`…) |
| Compress | Ghostscript puis `qpdf --object-streams=generate` | Niveaux : léger (/printer, 300 dpi), **recommandé** (/ebook, 150 dpi), fort (/screen, 72 dpi). Si le résultat n'est pas plus petit, il est jeté. La notification affiche le gain | `<nom>-compressed.pdf` |
| Edit | editor.py | voir §5 | `<nom>-edited.pdf` |
| Sign | editor.py + signature.py | voir §5 | `<nom>-signed.pdf` |
| Converter | `soffice --headless --convert-to pdf` ; Qt WebEngine `printToPdf` pour html/md ; `pdftotext -layout` | Profil LibreOffice temporaire isolé ; délai max 120 s | `<nom>.pdf` / `<nom>.txt` |
| Images → PDF | img2pdf (magick convertit d'abord webp/heic/gif) | JPEG et PNG intégrés sans recompression ; option « A4 ajusté » (défaut) ou « taille de l'image » ; ordre = sélection | `<premier>-images.pdf` |
| PDF → Images | pdftoppm | PNG (défaut) ou JPG ; 150 (défaut) ou 300 dpi ; plages optionnelles | dossier `<nom>-images/` |
| Extract images | `pdfimages -all` | Images d'origine, format natif | dossier `<nom>-extracted/` |
| Protect | pikepdf, AES-256 (R6) | Mot de passe d'ouverture ; option : interdire l'impression et la copie | `<nom>-protected.pdf` |
| Unlock | pikepdf | Avec le mot de passe, ou sans s'il n'y a que des restrictions | `<nom>-unlocked.pdf` |
| Rotate | pikepdf (`/Rotate`) | 90/180/270, tout le document ou des plages | `<nom>-rotated.pdf` |
| Remove pages | pikepdf | Plages à supprimer (refus si toutes les pages sont supprimées) | `<nom>-removed.pdf` |
| Extract pages | pikepdf | Plages → un seul PDF | `<nom>-extract.pdf` |
| Rearrange | organiseur ; rofi : « inverser l'ordre » | — | `<nom>-reordered.pdf` |
| Webpage → PDF | Qt WebEngine hors écran | URL (presse-papier proposé si c'est une URL) ou fichier html local ; A4 ; fonds imprimés ; attend `loadFinished` + 1 s ; délai max 30 s | `~/Downloads/<titre-de-la-page>.pdf` |

### Règles communes

- **Plages** : `1-3,5,8-`, numérotation à partir de 1, `8-` = jusqu'à la fin. Espaces tolérés.
  Une page hors limites ou une syntaxe invalide donne une erreur explicite.
- **Nommage** : `naming.py` → `<dossier de l'original>/<nom>-<suffixe>.pdf`, puis `-2`, `-3`…
  s'il existe. Les dossiers suivent la même règle.
- **Écriture atomique** : écriture dans un fichier temporaire du même dossier, puis `os.replace`.
  Le temporaire est supprimé en cas d'échec.
- **Mots de passe** : saisis via rofi `-password` ou `QLineEdit` en mode Password ; transmis par
  stdin (`--password-stdin`), jamais en argument ; jamais écrits dans le journal ni affichés
  dans une notification.
- **Métadonnées** conservées (sauf Compress).
- **Code de retour du CLI** : 0 = succès, les chemins créés sur stdout (un par ligne) ;
  ≠ 0 = message lisible sur stderr.

## 5. Fenêtre (PyQt6)

- **Identifiant** : app id / classe `desk-pdf`. Thème hérité de qt6ct et Kvantum (Neon Graffiti).
- **Langue** : lue dans `~/.local/state/desk/lang`.
- **Lancement** : `desk pdf gui [--tool <outil>] [fichiers…]`.

### Accueil

- Grille de 16 tuiles (icônes Papirus) ; étoile de favori, favoris en premier.
- Dépôt de fichiers sur toute la fenêtre.
- Outil simple : panneau d'options + liste des fichiers (réordonnables) + « Lancer » (appel
  de `ops` dans un thread) + « Enregistrer sous… ».

### Organiseur (Merge, Rearrange, Rotate, Remove, Extract pages)

- Miniatures rendues par PyMuPDF dans un thread (chargement progressif), zoom des miniatures.
- Sélection multiple, glisser-déposer pour réordonner, pivoter à gauche ou à droite (↺ ↻),
  Suppr, « Extraire la sélection ».
- « Ajouter un PDF » (fusion) ; une pastille de couleur indique le fichier d'origine de chaque page.
- `QUndoStack` (Ctrl+Z / Ctrl+Maj+Z). Rien n'est écrit avant « Enregistrer ». La construction
  finale se fait avec pikepdf : copie des pages et `/Rotate`.

### Éditeur (Edit, Sign)

- `QGraphicsScene` par page (image de la page rendue en fond) ; zoom, défilement, liste des pages.
- **Outils** :
  - sélectionner / déplacer ;
  - texte (Helvetica, Times ou Courier ; taille ; couleur) ;
  - surligner ;
  - rectangle, ellipse, ligne, flèche ;
  - stylo à main levée ;
  - image ;
  - masquer en blanc ;
  - caviarder.
- **Formulaires** : panneau latéral listant les champs (texte, case à cocher, liste, radio) ;
  le champ actif est mis en surbrillance sur la page.
- Tous les objets restent modifiables jusqu'à l'enregistrement (`QUndoStack`).
- **Enregistrement Edit** : les objets deviennent des annotations PDF standard (FreeText,
  Highlight, Square, Circle, Line, Ink, Stamp pour les images). Masquage et caviardage passent
  par `add_redact_annot` + `apply_redactions` (le contenu sous la zone est réellement supprimé ;
  masquage = remplissage blanc, caviardage = noir). Case « Aplatir » : tout incruster dans la page.
- **Enregistrement Sign** : aplatissement complet (signatures, tampons, annotations, champs remplis).

### Signature

- **Bibliothèque** : `~/.local/share/desk/pdf/signatures/*.png` (fond transparent).
- **Nouvelle** : zone de dessin (souris ou tablette via QTabletEvent, trait lissé, épaisseur et
  couleur réglables, bleu encre ou noir) ou import d'une image (seuillage : le fond clair devient
  transparent, puis recadrage automatique).
- Clic = poser ; poignées pour déplacer et redimensionner (proportions conservées).
- « Dupliquer sur : toutes les pages / plages » ; tampons « Date » (format selon la langue) et
  « Lu et approuvé » / « Read and approved ».
- Bouton « Signature certifiée → Okular » : ouvre le fichier courant (déjà enregistré) dans Okular.

## 6. Erreurs

- `desk-pdf` utilise `desk_on_err`. Le CLI transforme les exceptions connues en messages clairs.
  Le détail technique est ajouté à `pdf.log`, sans jamais de mot de passe.
- **Mot de passe incorrect** : on redemande, 3 essais maximum.
- **PDF chiffré passé à un autre outil** : on propose « Déverrouiller d'abord ? ». La version
  déverrouillée est temporaire et n'est jamais écrite à côté de l'original.
- **PDF abîmé** : pikepdf l'ouvre en le réparant ; avertissement dans la notification.
- **LibreOffice absent** : notification « installer `libreoffice-fresh` ».
  **Délais dépassés** : LibreOffice 120 s, page web 30 s.
- **Fenêtre** : une erreur donne une boîte de dialogue, la fenêtre et le travail sont conservés.
  Fermer avec des modifications non enregistrées demande confirmation.

## 7. Tests

- **pytest** (`pdf/tests/`) : des fixtures génèrent des PDFs avec PyMuPDF (texte « PAGE n »,
  images, formulaire AcroForm, version chiffrée). Par outil :
  - nombre, ordre et rotation des pages ;
  - texte absent après caviardage ;
  - champs remplis et aplatis ;
  - ouverture refusée sans le mot de passe ;
  - taille réduite après compression ;
  - pas d'écrasement (`-2`) ;
  - analyse des plages (cas valides et invalides) ;
  - pas de fichier temporaire restant après un échec.
- **Ligne de commande** : `DESK_TEST=1 desk pdf <outil> …` (notifications sur stderr).
- **Hyprland** : `hyprctl reload` puis `hyprctl configerrors` vide ; P et E corrects dans
  `hyprctl binds` / la cheatsheet.
- **Interface** : lancement et captures d'écran pour vérifier ; validation finale par l'utilisateur.

## 8. Phases (chacune validée par l'utilisateur avant la suivante)

1. **Moteur + CLI + rofi + Dolphin**
   - 13 outils : tous sauf Edit, Sign et Rearrange visuel ; Rearrange = « inverser l'ordre ».
   - Leader P, projets sur E, palette.
2. **Fenêtre** : accueil (tuiles, favoris, dépôt de fichiers, panneaux d'options) + organiseur.
3. **Éditeur** : annotations, masquage, caviardage, formulaires.
4. **Signature** : bibliothèque, dessin, import, placement, duplication, tampons, aplatissement,
   bouton Okular ; README.

## 9. Hors périmètre

PDF → Word, modification du texte existant, signature certifiée intégrée (Okular s'en charge),
OCR (tesseract est installé ; ajout possible plus tard avec `ocrmypdf`), traitement par lots
de dossiers entiers.
