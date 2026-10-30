-- ──────────────────────────────────────────────────────────────
--  Fond d'écran (awww) + thème auto (desk theme) — remplace hyprpaper
--  (hyprpaper est commenté dans hyprland.lua, pas supprimé).
--   desk wall login : fond aléatoire en fondu au démarrage, palette auto
--   desk wall watch : nouvelle image dans ~/Images/Wallpapers → affichée
--  Les animations propres au look (ex-look-post.conf) sont maintenant
--  dans looks/<look>.lua, chargé après les animations de hyprland.lua.
-- ──────────────────────────────────────────────────────────────

hl.on("hyprland.start", function()
    hl.exec_cmd("awww-daemon")
    hl.exec_cmd("~/.local/bin/desktop/desk wall login")
    hl.exec_cmd("~/.local/bin/desktop/desk wall watch")
end)
