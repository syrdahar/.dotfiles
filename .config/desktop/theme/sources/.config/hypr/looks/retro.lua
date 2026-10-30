-- ──────────────────────────────────────────────────────────────
--  Look "retro" : coins carrés, bordure pleine dorée, sans blur ni ombre
--  Activé via ~/.config/hypr/look.lua → looks/retro.lua (rice.sh look retro)
--  Fichier GÉNÉRÉ par « desk theme » : éditer la source dans
--  ~/.config/desktop/theme/sources/.config/hypr/looks/retro.lua
-- ──────────────────────────────────────────────────────────────

local c = require("colors")

hl.config({
    general = {
        col = {
            active_border   = c.gold,
            inactive_border = "rgba(49345988)",
        },
    },

    decoration = {
        rounding       = 0,
        rounding_power = 2.5,

        active_opacity   = 1.0,
        inactive_opacity = 0.97,

        dim_inactive = true,
        dim_strength = 0.06,

        shadow = { enabled = false },
        blur   = { enabled = false },
    },
})
