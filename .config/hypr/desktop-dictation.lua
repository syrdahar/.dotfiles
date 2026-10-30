-- ──────────────────────────────────────────────────────────────
--  Dictée locale (desk dictate → voxtype, Whisper large-v3-turbo sur GPU Vulkan, hors-ligne)
--  Config : ~/.config/voxtype/config.toml · service : systemctl --user status voxtype
--  La touche micro envoie appui+relâché en même temps (vérifié avec wev)
--  → mode bascule : ALT+micro démarre, ALT+micro arrête et tape le texte.
--  Seule, la touche micro garde son rôle (couper le micro, keybinds.lua).
-- ──────────────────────────────────────────────────────────────

local bindd = require("helpers").bindd
local desk  = "~/.local/bin/desktop/desk"

bindd("ALT + XF86AudioMicMute",         "Dictée · Démarrer / arrêter (texte tapé au curseur) ‖ Dictation · Start / stop (text typed at cursor)",        desk .. " dictate toggle")
bindd("ALT + SHIFT + XF86AudioMicMute", "Dictée · Démarrer / arrêter avec nettoyage IA (ollama) ‖ Dictation · Start / stop with AI cleanup (ollama)", desk .. " dictate clean")
bindd("ALT + CTRL + XF86AudioMicMute",  "Dictée · Annuler l'enregistrement en cours ‖ Dictation · Cancel current recording",                          desk .. " dictate cancel")
