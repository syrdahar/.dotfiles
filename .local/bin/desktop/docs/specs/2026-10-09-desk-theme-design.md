# desk theme / desk wall — thème qui suit le fond d'écran

Date : 2026-10-09 · Statut : design validé par l'utilisateur

## But
1. Les couleurs de tout le rice suivent automatiquement le fond d'écran (palette « auto »),
   avec une transition animée du fond (awww) puis re-thème.
2. Plus de thèmes : palettes presets (alternative à auto) × looks (neon, glass + flat, aurora, retro, zen).

## Décisions utilisateur
- Moteur maison Python (PIL + numpy, OKLCH), pas matugen. UI toujours sombre.
- awww remplace hyprpaper (hyprland.conf:40 commentée, pas supprimée).
- Changement de fond : sélecteur rofi à miniatures, rotation (timer systemd user, 30 min,
  `DESK_WALL_INTERVAL` dans desk.conf), aléatoire au login, surveillance de `~/Images/Wallpapers`.
- Fonds déplacés dans `~/Images/Wallpapers` ; `~/Images/einstein.jpg` reste en lien symbolique.
- Leader **Y** = menu Thème/Fond. Libellés bilingues « fr ‖ en ». Rofi compact (theme desk.rasi).
- Fichiers existants modifiés avec backup `*.bak-2026-10-09-wallpal` : voir § Intégration.

## Architecture

```
~/.local/bin/desktop/
  desk-theme            bash : palette auto|<preset> · look <nom> · apply · menu · status
  desk-wall             bash : pick · random · next · set <img> · login · rotate on|off|toggle · watch
  theme/palette.py      image → palette JSON (auto) ; preset → JSON ; swatch PNG
  theme/recolor.py      sources → fichiers live via transfert de palette
  theme/tests/          pytest
~/.config/desktop/theme/
  palettes/*.json       presets (neon-graffiti, catppuccin-mocha, tokyo-night, rose-pine,
                        gruvbox-dark, nord, dracula, kanagawa, everforest)
  sources/<chemin relatif à $HOME>   copies Neon Graffiti des fichiers colorés (source de vérité)
  manifest.txt          une ligne par fichier source : « chemin-relatif-à-$HOME »
~/.local/state/desk/theme/
  state                 palette=auto|<preset>  wallpaper=<chemin>
  palette.json          palette active
  rendered.sha          sha256 des fichiers live au dernier rendu (détection d'édition manuelle)
~/.cache/desk/theme/<sha1-image>.json   palettes auto en cache
~/.cache/desk/wall/thumbs/<sha1>.png    miniatures
```

### Format palette (JSON)
```json
{"name": "neon-graffiti", "source": "preset",
 "colors": {"base":"#100c1f","mantle":"#1a1530","surface":"#2a2346","overlay":"#493459",
            "text":"#e6ddf0","subtext":"#c2b1c0","cyan":"#29b4d7","blue":"#3a7bd5",
            "magenta":"#c23d9e","pink":"#ff5fb7","gold":"#e2b620","orange":"#f57c2a",
            "red":"#e0485a","green":"#5fd7a7"}}
```
14 rôles, toujours tous présents. `cyan`/`magenta`/`gold` = accents 1/2/3 (noms gardés pour compat).
Pour une palette auto, `source` = `"auto:<chemin image>"`.

### Transfert de palette (recolor.py)
P0 = preset neon-graffiti, P1 = palette cible. Pour toute couleur littérale c d'un fichier source :
1. c ∈ FIXES (`#ffffff`, `#000000`, `#d97757` orange Claude) → inchangée.
2. Rôle r = rôle de P0 le plus proche de c en distance OKLab.
3. Si P1[r] == P0[r] → c inchangée (garantit l'identité exacte pour P1 = P0).
4. Sinon : en OKLCH, c' = P1[r] + (c − P0[r]) sur L et C (C ≥ 0), teinte : h(P1[r]) + (h(c) − h(P0[r]))
   (si C(c) < 0.02, garder la teinte de P1[r]) ; clip gamut sRGB en réduisant C ; arrondi.
5. Le canal alpha et le format d'écriture d'origine sont conservés.

Formats reconnus (regex, insensibles à la casse) :
`#rrggbb` · `#rrggbbaa` · `rgb(rrggbb)` · `rgba(rrggbbaa)` (Hyprland) ·
`rgba(R, G, B, a)` / `rgb(R, G, B)` (CSS, espaces variables) ·
lignes `Clé=R,G,B` (KDE .colors) · `$xxxHex = rrggbb` (hex nu, hypr/colors.conf).
Les références de variables (`$cyan`, `@magenta`, `$goldHexee`) ne sont pas touchées.

Écriture : atomique (tmp + mv), seulement si le contenu change. Avant d'écraser, si le sha du
fichier live ≠ celui de `rendered.sha` (édité à la main) : copie en `<fichier>.bak-theme-<date>`
et notification « éditez la source ». Les liens symboliques (look.*) ne sont jamais touchés ;
les cibles de looks/ sont des fichiers ordinaires rendus comme les autres.

Fichiers source (manifest) : hypr/colors.conf, hypr/hyprlock.conf, hypr/looks/*.conf,
waybar/colors.css, waybar/base.css, waybar/config, waybar/looks/*.css, swaync/style.css,
swaync/looks/*.css, swayosd/style.css, swayosd/looks/*.css, rofi/neon.rasi, rofi/looks/*.rasi,
alacritty/neon-graffiti.toml, alacritty/looks/*.toml, Kvantum/NeonGraffiti{,Glass}/*.{kvconfig,svg},
Kvantum/looks/*.kvconfig, .local/share/color-schemes/NeonGraffiti.colors.

**Test golden** : rendu avec P1 = neon-graffiti → chaque fichier live identique octet pour octet.

### Palette auto (palette.py)
Image → miniature 200 px → OKLab par pixel (numpy).
- Teinte dominante hd : moyenne circulaire des teintes pondérée par C ; chroma moyen Cm.
- Pics d'accent : pixels C ≥ 0.06 et 0.25 ≤ L ≤ 0.95 ; histogramme de teinte 36 × 10°, poids C ;
  lissage circulaire [1,2,1] ; pics gloutons (max, puis suppression ±40°), jusqu'à 5, chacun ≥ 8 %
  du 1er. Teinte du pic = moyenne circulaire des pixels à ±15°.
  Moins de 3 pics : compléter par des analogues a1±45° (rester dans l'ambiance de l'image) ;
  aucun pic (image grise) : a1 = hd.
- Attribution (révisée en revue) : parmi les pics, on choisit 3 pics et leur ordre pour
  cyan/magenta/gold en minimisant Σ écart de teinte au rôle néon + 10° × rang du pic.
  L et C d'un accent = ceux du rôle néon chromatique de teinte la plus proche (un jaune garde
  la luminosité du gold : pas de kaki). blue/pink/orange/red/green : teinte néon du rôle, tirée
  de 20 % vers l'accent le plus proche s'il est à < 60° ; L et C du rôle.
  Neutres base…subtext : h = hd, C×0.5 si Cm < 0.03.
  Chroma des accents : C × clamp(Cm/0.08, 0.85, 1.15), minimum 0.12.
- Contraste (WCAG) : text/base ≥ 7, chaque accent/base ≥ 4.5 ; sinon L += 0.02 jusqu'à OK.
- Clip gamut sRGB en réduisant C. Résultat déterministe ; cache par sha1 du fichier.
- `palette.py swatch palette.json out.png` : bande de 14 pastilles (rond, 48 px) pour la notif.

## desk theme
- `desk theme apply` : palette active (auto → cache ou calcul depuis le fond courant ; preset → JSON)
  → recolor de tous les fichiers → reload : `hyprctl reload` + `wm.sh reapply`, waybar SIGUSR2,
  `swaync-client -rs`, redémarrage de swayosd-server, alacritty se recharge seul,
  Kvantum/Qt au prochain lancement → notification avec la swatch.
- `desk theme palette auto|<preset>` (écrit state puis apply) ; `desk theme look <nom>` → `rice.sh look`.
- `desk theme menu` (leader Y) : entrées bilingues, état courant marqué ● :
  Fond · Choisir · Aléatoire · Suivant · Rotation on/off · Ouvrir le dossier ;
  Palette · Auto + presets ; Look · 6 looks.
- `desk theme status`.

## desk wall
- `set <img>` : `awww img` (transition selon l'appel), mémorise state.wallpaper ; si palette=auto,
  calcule la palette pendant la transition et applique juste après.
- `pick` : grille rofi de miniatures (thème rofi/wall.rasi, couleurs = palette) ; transition
  `grow` depuis le curseur. `random`/`next` : transition aléatoire parmi wipe, wave, outer, center.
- `login` (exec-once) : attend awww-daemon, fond aléatoire, apply.
- `rotate on|off|toggle` : (dés)active `desk-wall-rotate.timer` (systemd user, OnUnitActiveSec =
  `DESK_WALL_INTERVAL`, défaut 30min) qui lance `desk wall next`.
- `watch` (exec-once) : `inotifywait -m -e close_write,moved_to ~/Images/Wallpapers` →
  `desk wall set <nouveau>` (extensions jpg jpeg png webp).

## Nouveaux looks (fichiers pour les 8 apps, couleurs exprimées en Neon Graffiti → recolorées)
- **flat** : opaque, blur/ombre off, bordure 1 couleur (cyan), rounding 6, dim off.
- **aurora** : bordure dégradée 3 accents qui tourne (`animation = borderangle, 1, 100, linear, loop`),
  ombre lumineuse teintée accent, translucide (0.92/0.85), blur moyen.
- **retro** : rounding 0, bordure pleine 2 px, sans blur ni ombre ; rofi/waybar carrés.
- **zen** : pas de bordure visible, inactives atténuées fort (dim 0.25), rounding 18.
Kvantum : flat/retro → copie de neon.kvconfig, aurora/zen → copie de glass.kvconfig.
Limites : waybar/swaync/swayosd importent look.css avant leurs règles → un look n'y change que
les variables (couleurs/alpha), pas les arrondis ; gaps et border_size restent gérés par wm.sh.
Animations : `looks/post-<look>.conf`, lien `hypr/look-post.conf` (LOOK_LINKS de rice.sh), sourcé par
desktop-theme.conf en fin de hyprland.conf (après le bloc animations) ; aurora y met la boucle
borderangle, les autres restaurent `borderangle, 1, 20, easeOutQuint`.
hyprlock : fond = `~/.cache/desk/wall/current` (lien vers le fond courant).

## Intégration (fichiers existants modifiés, backups *.bak-2026-10-09-wallpal)
- hyprland.conf : ligne 40 `exec-once = hyprpaper` commentée ; ajout en fin
  `source = ~/.config/hypr/desktop-theme.conf` (nouveau : exec-once awww-daemon, desk wall login,
  desk wall watch).
- desktop-leader.conf : bindd Y + bind SUPER,Y. actions.sh : entrées palette. README.md : section.
- rice.sh : LOOKS += flat aurora retro zen ; menu : entrée « palette » → desk theme menu.
- desk.conf : `DESK_WALL_DIR`, `DESK_WALL_INTERVAL=30min`.
- Les fichiers colorés live deviennent des sorties générées (édition → sources/).

## Tests / validation
- pytest : golden identité ; formats du recolor ; palette auto déterministe + contrastes pour
  les 3 fonds ; presets valides (14 rôles, hex).
- `hyprctl configerrors` vide après apply ; waybar/swaync/swayosd vivants ; captures grim relues.
- Revue par l'orchestrateur (Opus) de chaque lot Haiku, puis validation utilisateur.
