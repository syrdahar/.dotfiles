-- ──────────────────────────────────────────────────────────────
--  Command center — autostart
--  Remplace la ligne de hyprland.lua (commentée, validé par toi) :
--    wl-paste --type text  --watch cliphist store
--  Le texte copié passe par un filtre : les secrets (clés, tokens, JWT,
--  clés privées, password=…) ne sont jamais stockés et sont effacés
--  du presse-papier après 30 s. Les images restent sur la ligne d'origine.
-- ──────────────────────────────────────────────────────────────

hl.on("hyprland.start", function()
    hl.exec_cmd("wl-paste --type text --watch ~/.local/bin/desktop/desk clipwatch")
end)
