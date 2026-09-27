# desk — Hyprland command center

One shortcut = one intention. Everything goes through **rofi**, every action is
reachable from the **palette**, and every shortcut shows up in the **cheatsheet**
(generated from the loaded Hyprland config, so it can never drift).

UI language toggles between **English and French** (`SUPER+Space` then `l`);
rofi search always matches **both** languages.

## Entry points (points d'entrée)

| Keys | EN | FR |
|---|---|---|
| `SUPER+Space` | Leader mode: then **one** key (Esc cancels, 5 s timeout) | Mode leader : puis **une** touche (Échap annule, 5 s) |
| `SUPER+X` | Command palette (every action + its shortcut) | Palette de commandes (toutes les actions + raccourci) |
| `SUPER+ALT+Enter` | Toggle terminal scratchpad (tmux session `scratch`) | Scratchpad terminal (session tmux `scratch`) |
| `SUPER+CTRL+Space` | Previous layout (moved from `SUPER+Space`) | Layout précédent (déplacé depuis `SUPER+Espace`) |

Your existing shortcuts (`keybinds.conf`) are unchanged, except the line above.

## Leader keys (`SUPER+Space` then…)

In the leader, SUPER may stay pressed. Any other key cancels (and is swallowed).

| Key | EN | FR | Module |
|---|---|---|---|
| `Space` | Command palette | Palette de commandes | `desk palette` |
| `h` | Cheatsheet of all shortcuts | Cheatsheet de tous les raccourcis | `desk cheatsheet` |
| `a` | AI: Claude on clipboard (explain, fix, tests, commit msg, translate, review, ask) | IA : Claude sur le presse-papier | `desk ai` |
| `b` | Toggle btop scratchpad | Scratchpad btop | `desk scratch btop` |
| `c` | Clipboard actions for the copied content (URL, JSON, JWT, trace, timestamp, text, generators) | Actions selon le contenu copié | `desk clip` |
| `d` | Docker containers & compose stacks | Conteneurs et stacks Docker | `desk docker` |
| `f` | Proton Drive: browse, download, upload, public link, trash | Proton Drive : parcourir, télécharger, envoyer, lien | `desk drive` |
| `g` | Git menu for the active terminal's repo | Menu git du dossier courant | `desk git` |
| `k` | Listening ports (open, curl, kill) | Ports en écoute | `desk ports` |
| `l` | Toggle French / English | Basculer français / anglais | `desk lang toggle` |
| `m` | Mobile: scrcpy, emulator, adb reverse, RN dev menu | Mobile : scrcpy, émulateur, adb | `desk mobile` |
| `n` | Notes & TODOs in `~/notes` | Notes et TODO | `desk notes` |
| `o` | Claude Code session notifications (on/off, test) | Notifications des sessions Claude Code | `desk claudenotify` |
| `p` | Open / switch to a project (workspace + tmux + nvim) | Ouvrir / rejoindre un projet | `desk project` |
| `q` | Calculator & unit conversions (qalc) | Calculatrice et conversions | `desk calc` |
| `r` | Screenshots: OCR, annotate, window → clipboard, screen recording / GIF | Captures : OCR, annotation, vidéo | `desk capture` |
| `s` | SSH to a host from `~/.ssh/config` | Connexion SSH | `desk ssh` |
| `t` | Toggle terminal scratchpad | Scratchpad terminal | `desk scratch term` |
| `u` | Processes by CPU / RAM (kill, inspect; Alt+c / Alt+r / Alt+g) | Processus par CPU / RAM | `desk procs` |
| `w` | Web search with prefixes (`gh ghc mdn npm so aur pac aw yt`) | Recherche web avec préfixes | `desk web` |
| `x` | System: audio output/input, Wi-Fi, Bluetooth, VPN, DND, reload, lock, power | Système : audio, Wi-Fi, Bluetooth, VPN… | `desk system` |
| `z` | Focus: timer, pomodoro, focus mode (DND + hidden bar) | Focus : minuteur, pomodoro, mode focus | `desk focus` |

Full, always-up-to-date list: `desk cheatsheet --print` (or `SUPER+Space` `h`).

## Modules (all runnable from a terminal)

`desk` with no argument lists modules. Each module: `desk <module>` opens its menu,
`desk <module> --list` prints its actions, most accept `run <id>`.

| Module | CLI examples |
|---|---|
| `clip` | `desk clip type` · `desk clip run json-pretty` · `desk clip run gen-uuid` |
| `calc` | `desk calc "72 kg to lb"` · `desk calc "80 * 15%"` |
| `clipwatch` | filter used by `wl-paste --watch` (see Security) · `desk clipwatch --test < file` |
| `project` | `desk project open ~/cours/CoursIA` · `desk project scan` |
| `git` | `desk git run status` · `desk git -C ~/repo run gh-pr` |
| `ports` / `procs` | `desk ports --print` · `desk procs --print ram app 10` |
| `docker`, `ssh`, `web`, `mobile` | `desk web "npm zod"` · `desk ssh epita` · `desk mobile run reverse` |
| `capture` | `desk capture run ocr` · `desk capture run record-gif` (again = stop) |
| `ai` | `desk ai explain` · `desk ai commit` (uses `git diff --staged`) |
| `system` | `desk system run sink` · `desk system run wifi` · `desk system run reload` |
| `notes` | `desk notes note "call the client"` · `desk notes todo "fix login"` |
| `focus` | `desk focus timer 25` · `desk focus timer 1h30` · `desk focus pomodoro` · `desk focus status` |
| `lang` | `desk lang` · `desk lang fr` · `desk lang toggle` |
| `drive` | `desk drive browse /my-files/Docs` · `desk drive upload /my-files/Docs file.pdf` · `desk drive get /my-files/a.pdf` · `desk drive link /my-files/a.pdf` · `desk drive list` · Dolphin: right-click → Send to Proton Drive |
| `shot` | called by hyprshot (`-s -- desk-shot`) after a screenshot to file: notification with thumbnail + Open · Annotate · → Drive (`/my-files/Captures`, recordings → `/my-files/Enregistrements`) |
| `claudenotify` | `desk claudenotify run toggle` · `desk claudenotify run test` · `hook` (called by Claude Code hooks) |

Add `~/.local/bin/desktop` to your PATH if you want `desk` in the shell
(it is **not** added automatically; modules are prefixed `desk-` so they never
shadow `git`, `docker`, `ssh`…).

## Files

| Path | Role |
|---|---|
| `~/.config/hypr/desktop-binds.conf` | direct binds (leader, palette, scratchpad) |
| `~/.config/hypr/desktop-leader.conf` | leader submap |
| `~/.config/hypr/desktop-rules.conf` | window rules for `desk-*` classes, satty, scrcpy, emulator |
| `~/.config/hypr/desktop-autostart.conf` | filtered clipboard watcher |
| `~/.config/rofi/desk.rasi` | compact theme (imports your `neon.rasi` + active look) |
| `~/.config/desktop/desk.conf` | settings: `DESK_LANG`, `DESK_BROWSER`, `DESK_TERMINAL`, `DESK_SEARCH_DEFAULT`, `DESK_AI_MODEL` |
| `~/.config/desktop/projects.conf` | project root folders (git repos found up to 3 levels deep) |
| `~/.config/desktop/projects.d/<name>.conf` | optional per-project config: tmux commands, URL, mobile (see `_exemple.conf`) |
| `~/.local/state/desk/` | language, history (projects, ssh), timer state |
| `~/Images/Captures`, `~/Vidéos/Enregistrements` | annotated screenshots, recordings |
| `~/notes/inbox.md`, `~/notes/todo.md` | timestamped notes, TODOs |

Changes to pre-existing files (everything else is new):
`hyprland.conf` — line 46 (text cliphist watcher) commented + `source =` lines at the end;
`keybinds.conf` line 121 — layout-prev moved to `SUPER+CTRL+Space`;
`keybinds.conf` lines 191–196 — hyprshot file captures end with `-s -- ~/.local/bin/desktop/desk-shot` (own notification with buttons);
`alacritty.toml` — `[selection] save_to_clipboard = true` (select = copy).
Backups: `~/.config/hypr.bak-2026-09-27/`, `~/.config/rofi.bak-2026-09-27/`, `alacritty.toml.bak-2026-09-27`.

## Security

- **Clipboard history filter** (`desk clipwatch`): copied text matching secrets
  (private keys, JWTs, `sk-…`/`ghp_…`/AWS/Google/Slack/Stripe/npm/HF keys,
  `password=`/`token:`-style assignments, `Authorization:` headers, URLs with
  credentials) or flagged sensitive (`wl-copy --sensitive`, password managers) is
  **never stored** in cliphist and is **cleared after 30 s**. Code such as
  `token = getToken()` is not flagged. Patterns live in `lib.sh` (`DESK_SECRET_RE`).
- **AI** (`desk ai`): input is passed through `mask_secrets` before being sent.
  `claude -p` runs from an empty directory with no tools, no MCP servers and no
  user settings (hooks, plugins) — it only sees what is sent. It uses your Claude
  subscription (`--bare` is deliberately not used: it disables OAuth).
- Wi-Fi passwords are passed to `nmcli` on stdin, never as a visible argument.

## Adding an action (palette + cheatsheet)

1. **In a module** (`desk-<module>`): add `"id|Libellé FR ‖ English label"` to
   `ACTIONS` and a function `a_<id>` (dashes → underscores). If the module is in
   the loop at the bottom of `actions.sh`, the action appears in the palette
   automatically. Use `t "français" "english"` for messages and `die "…"` for errors
   (each action must give feedback through `notify`).
2. **Or directly in `actions.sh`**:
   `action "Catégorie · Libellé ‖ Category · Label" cmd "desk …"` (shell command)
   or `action "… ‖ …" bind "exact description of an existing bindd"`.
3. **Optional shortcut**: in `desktop-leader.conf` (before the `catchall` lines),
   `bindd = , KEY, Catégorie · libellé ‖ Category · label, exec, $desk leader <module> …`
   plus `bind = SUPER, KEY, exec, …` (SUPER-held variant). Descriptions must not
   contain commas. Or a direct bind in `desktop-binds.conf`.
4. Nothing else to maintain: the palette finds the shortcut by matching the command,
   the cheatsheet and the which-key notification read `hyprctl binds`.
5. Check: `hyprctl reload && hyprctl configerrors`,
   `desk palette --print | grep …`, `desk cheatsheet --print | grep …`.

Testing helpers: `DESK_TEST=1` (notifications to stderr), `DESK_CLIP_IN="…"`
(fake clipboard input), `DESK_CLIP_OUT=file` (capture what would be copied),
`DESK_CWD=dir` (force the "active terminal" directory).

## Troubleshooting

- Stuck in the leader: `Esc`, or wait 5 s, or `hyprctl dispatch submap reset`.
- Hyprland 0.56 quirk: `catchall` also fires after a bound key — that is why the
  leader's catchall only does `submap, reset` and must stay **last**.
- `gh` actions need `gh auth login`; without it, "open PR" opens GitHub's compare page.

## Dependencies

rofi (≥ 2.0, Wayland), hyprland, jq, python3, perl, cliphist, wl-clipboard, grim,
slurp, hyprshot, satty, tesseract + tesseract-data-{fra,eng}, imagemagick,
wf-recorder, ffmpeg, libqalculate (qalc), go-yq, glow, bat, qrencode, fd, tmux,
alacritty, neovim, gh, docker, scrcpy, android-tools, networkmanager, bluez-utils,
pipewire-pulse (pactl), swaync, libnotify, claude (Claude Code).
