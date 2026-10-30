-- ──────────────────────────────────────────────────────────────
--  Command center — window rules (classes desk-* uniquement,
--  aucune interaction avec les règles de hyprland.lua)
-- ──────────────────────────────────────────────────────────────

hl.window_rule({
    -- Terminal scratchpad (desk scratch term · SUPER+ALT+Entrée)
    name      = "desk-term-scratchpad",
    match     = { class = "^(desk-term)$" },
    workspace = "special:term silent",
    float     = true,
    size      = "monitor_w*0.7 monitor_h*0.65",
    center    = true,
})

hl.window_rule({
    -- Affichages ponctuels des scripts desk (JSON, JWT, curl, QR, réponses IA…)
    name   = "desk-float-viewer",
    match  = { class = "^(desk-float)$" },
    float  = true,
    size   = "monitor_w*0.6 monitor_h*0.7",
    center = true,
})

hl.window_rule({
    -- btop scratchpad (desk scratch btop · SUPER+Espace puis b)
    name      = "desk-btop-scratchpad",
    match     = { class = "^(desk-btop)$" },
    workspace = "special:btop silent",
    float     = true,
    size      = "monitor_w*0.65 monitor_h*0.7",
    center    = true,
})

hl.window_rule({
    -- Miroir du téléphone (desk mobile · scrcpy) : flottant, épinglé sur tous les workspaces
    name  = "desk-scrcpy",
    match = { title = "^(scrcpy · .*)$" },
    float = true,
    pin   = true,
})

hl.window_rule({
    -- Émulateur Android (desk mobile) : flottant, épinglé
    name  = "desk-android-emulator",
    match = { title = "^(Android Emulator - .*)$" },
    float = true,
    pin   = true,
})

hl.window_rule({
    -- Annotation de capture (desk capture · satty) : flottante, centrée
    name   = "desk-satty",
    match  = { class = [[^(com\.gabm\.satty|satty)$]] },
    float  = true,
    center = true,
})
