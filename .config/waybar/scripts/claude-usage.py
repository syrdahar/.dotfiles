#!/usr/bin/env python3
"""Waybar custom/claude : quotas Claude Code via `cswap list --json`.

cswap sert son cache (< 180 s) et gère lui-même la cadence des appels à
l'API d'usage : on peut l'interroger toutes les 30 s sans risque de 429.
Envoie aussi des notifications quand un seuil est franchi ou qu'une limite
est réinitialisée (état dans $XDG_RUNTIME_DIR/claude-usage.json).
"""
import json
import os
import subprocess
from datetime import datetime, timezone
from html import escape
from pathlib import Path

CYAN, MAGENTA, GOLD, ORANGE, RED, DIM = "#29b4d7", "#c23d9e", "#e2b620", "#f57c2a", "#e0485a", "#c2b1c0"
STATE = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "claude-usage.json"
THRESHOLDS = {"fiveHour": (80, 95), "sevenDay": (90,)}
LABELS = {"fiveHour": "5h", "sevenDay": "7j"}
DAYS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


def level_color(pct):
    if pct is None:
        return DIM
    if pct >= 90:
        return RED
    if pct >= 75:
        return ORANGE
    if pct >= 50:
        return GOLD
    return CYAN


def local_reset(iso):
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()
    today = datetime.now().astimezone().date()
    delta = (dt.date() - today).days
    day = "auj." if delta == 0 else "demain" if delta == 1 else DAYS[dt.weekday()]
    return f"{day} {dt:%H:%M}"


def notify(summary, body, urgency="normal", icon="dialog-information-symbolic"):
    subprocess.Popen(["notify-send", "-a", "Claude Code", "-u", urgency, "-i", icon, summary, body],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def session_count():
    r = subprocess.run(["pgrep", "-xc", "claude"], capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


def check_alerts(accounts):
    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        state = {}
    new_state = {}
    for acc in accounts:
        name = acc.get("alias") or acc["email"].split("@")[0]
        for win, marks in THRESHOLDS.items():
            key = f'{acc["email"]}:{win}'
            pct = (acc.get("usage") or {}).get(win, {}).get("pct")
            if pct is None:
                continue
            prev = state.get(key)
            new_state[key] = pct
            if prev is None:
                continue
            if pct + 30 < prev:  # grosse chute = fenêtre réinitialisée
                notify(f"Limite {LABELS[win]} réinitialisée", f"{name} · {pct:.0f} %", "low",
                       "emblem-ok-symbolic")
                continue
            for m in marks:
                if prev < m <= pct and acc.get("active"):
                    notify(f"Claude Code · {LABELS[win]} à {pct:.0f} %",
                           f"{name} — clic droit sur le widget pour basculer de compte",
                           "critical" if m >= 95 else "normal", "dialog-warning-symbolic")
    try:
        STATE.write_text(json.dumps(new_state))
    except OSError:
        pass


def main():
    try:
        raw = subprocess.run(["cswap", "list", "--json"], capture_output=True, text=True, timeout=20)
        data = json.loads(raw.stdout)
    except Exception as exc:  # cswap absent, timeout, JSON invalide…
        print(json.dumps({"text": "✻ ?", "tooltip": f"cswap indisponible : {exc}", "class": "error"}))
        return

    accounts = data.get("accounts", [])
    active = next((a for a in accounts if a.get("active")), None)
    sessions = session_count()
    check_alerts(accounts)

    if not active or not active.get("usage"):
        print(json.dumps({"text": f"✻ —  󰚩 {sessions}", "tooltip": "Pas de données d'usage", "class": "error"}))
        return

    u = active["usage"]
    five, seven = u.get("fiveHour", {}).get("pct"), u.get("sevenDay", {}).get("pct")

    def chip(label, pct):
        val = "—" if pct is None else f"{pct:.0f}%"
        return (f"<span size='85%' foreground='{DIM}'>{label}</span> "
                f"<span foreground='{level_color(pct)}'>{val}</span>")

    text = f"✻ {chip('5h', five)}  {chip('7j', seven)}  <span foreground='{DIM}'>󰚩</span> {sessions}"

    # ── Tooltip ────────────────────────────────────────────────
    lines = [f"<b>Claude Code</b> · {sessions} session{'s' if sessions > 1 else ''} active{'s' if sessions > 1 else ''}", ""]
    for acc in accounts:
        name = escape(acc.get("alias") or acc["email"])
        mark = f"<span foreground='{MAGENTA}'>●</span>" if acc.get("active") else "○"
        lines.append(f"{mark} <b>{name}</b>")
        usage = acc.get("usage") or {}
        for win in ("fiveHour", "sevenDay"):
            w = usage.get(win) or {}
            pct = w.get("pct")
            if pct is None:
                continue
            bar_len = 12
            filled = round(bar_len * min(pct, 100) / 100)
            bar = (f"<span foreground='{level_color(pct)}'>{'━' * filled}</span>"
                   f"<span foreground='#493459'>{'━' * (bar_len - filled)}</span>")
            reset = f"  reset {local_reset(w['resetsAt'])} ({w['countdown']})" if w.get("resetsAt") else ""
            lines.append(f"   {LABELS[win]}  {bar} {pct:>3.0f}%{reset}")
            exhaust = w.get("projectedExhaustionAt")
            if (win == "sevenDay" and exhaust and pct < 100 and not w.get("willLastToReset", True)
                    and datetime.fromisoformat(exhaust.replace("Z", "+00:00")) > datetime.now(timezone.utc)):
                lines.append(f"       <span foreground='{ORANGE}'>au rythme actuel : épuisé {local_reset(exhaust)}</span>")
        lines.append("")
    age = active.get("usageAgeSeconds")
    if age is not None:
        lines.append(f"<span foreground='{DIM}' size='85%'>données il y a {age / 60:.0f} min · clic : tableau de bord · clic droit : meilleur compte</span>")

    worst = max(p for p in (five, seven) if p is not None)
    cls = "critical" if worst >= 90 else "warning" if worst >= 75 else "ok"
    print(json.dumps({"text": text, "tooltip": "<tt>" + "\n".join(lines).rstrip() + "</tt>", "class": cls}))


if __name__ == "__main__":
    main()
