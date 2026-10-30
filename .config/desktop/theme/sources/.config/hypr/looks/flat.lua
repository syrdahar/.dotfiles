-- ──────────────────────────────────────────────────────────────
--  Look "flat" : fenêtres opaques, bordure unie, sans blur ni ombre
--  Activé via ~/.config/hypr/look.lua → looks/flat.lua (rice.sh look flat)
--  Fichier GÉNÉRÉ par « desk theme » : éditer la source dans
--  ~/.config/desktop/theme/sources/.config/hypr/looks/flat.lua
-- ──────────────────────────────────────────────────────────────

local c = require("colors")

hl.config({
    general = {
        col = {
            active_border   = c.cyan,
            inactive_border = "rgba(49345966)",
        },
    },

    decoration = {
        rounding       = 6,
        rounding_power = 2.5,

        active_opacity   = 1.0,
        inactive_opacity = 1.0,

        dim_inactive = false,

        shadow = { enabled = false },
        blur   = { enabled = false },
    },
})
