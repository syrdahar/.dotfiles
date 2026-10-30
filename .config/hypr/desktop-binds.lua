-- ──────────────────────────────────────────────────────────────
--  Command center — binds directs (scripts : ~/.local/bin/desktop/)
--  Même format que keybinds.lua :
--    bindd("MODS + touche", "Catégorie · description", commande)
--  → visibles dans la palette (SUPER+X), la cheatsheet (SUPER+Espace puis h)
--    et l'aide existante (SUPER+F1).
-- ──────────────────────────────────────────────────────────────

local bindd = require("helpers").bindd
local desk  = "~/.local/bin/desktop/desk"

bindd("SUPER + space",        "Leader · Mode leader (une lettre ensuite · Échap annule) ‖ Leader · Leader mode (then one key · Esc cancels)", desk .. " leader enter")
bindd("SUPER + X",            "Palette · Palette de commandes ‖ Palette · Command palette",                          "pkill rofi || " .. desk .. " palette")
bindd("SUPER + ALT + Return", "Scratchpad · Terminal (tmux) afficher/cacher ‖ Scratchpad · Toggle terminal (tmux)",  desk .. " scratch term")
