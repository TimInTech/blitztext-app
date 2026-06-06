#!/usr/bin/env bash
# install.sh — Installationsskript für BlitztextLinux auf Ubuntu/Kubuntu
# Idempotent: kann mehrfach ausgeführt werden, ohne Schaden anzurichten.
set -euo pipefail

# ─── Farben & Hilfsfunktionen ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${BOLD}[INFO]${RESET}  $*"; }
ok()      { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
err()     { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
die()     { err "$*"; exit 1; }
step()    { echo -e "\n${BOLD}▶ $*${RESET}"; }

# Protokolliert durchgeführte Aktionen für die abschließende Zusammenfassung
DONE_ITEMS=()
done_add() { DONE_ITEMS+=("$1"); }

# ─── Pfade ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLITZTEXT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${BLITZTEXT_DIR}/.venv"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
SERVICE_SRC="${BLITZTEXT_DIR}/systemd/blitztext-linux.service"
SERVICE_DST="${SYSTEMD_USER_DIR}/blitztext-linux.service"
YDOTOOLD_SERVICE="${SYSTEMD_USER_DIR}/ydotoold.service"

# ─── Voraussetzungen prüfen ───────────────────────────────────────────────────
step "Voraussetzungen prüfen"

# Nicht als root ausführen
if [[ "${EUID}" -eq 0 ]]; then
    die "Dieses Skript darf NICHT als root ausgeführt werden. Bitte als normaler Benutzer starten."
fi
ok "Läuft als Benutzer: $(whoami)"

# Ubuntu/Debian-basiertes System prüfen
if [[ ! -f /etc/os-release ]]; then
    die "/etc/os-release nicht gefunden — kein erkanntes Linux-System."
fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" && "${ID_LIKE:-}" != *"debian"* && "${ID:-}" != "debian" ]]; then
    die "Dieses Skript ist nur für Ubuntu/Debian-basierte Systeme gedacht (erkannt: ${ID:-unbekannt})."
fi
ok "Betriebssystem erkannt: ${PRETTY_NAME:-${ID}}"

# Python3 >= 3.10 prüfen
if ! command -v python3 &>/dev/null; then
    die "python3 nicht gefunden. Bitte 'sudo apt install python3' ausführen."
fi
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [[ "${PY_MAJOR}" -lt 3 || ( "${PY_MAJOR}" -eq 3 && "${PY_MINOR}" -lt 10 ) ]]; then
    die "Python 3.10 oder neuer erforderlich (gefunden: ${PY_VERSION})."
fi
ok "Python-Version: ${PY_VERSION}"

# ─── apt-Pakete installieren ──────────────────────────────────────────────────
step "Systempakete prüfen und installieren"

APT_PACKAGES=(
    pulseaudio-utils
    wl-clipboard
    ydotool
    ffmpeg
    python3-venv
    python3-evdev
    socat
)

MISSING_PKGS=()
for pkg in "${APT_PACKAGES[@]}"; do
    if ! dpkg-query -W -f='${Status}' "${pkg}" 2>/dev/null | grep -q "install ok installed"; then
        MISSING_PKGS+=("${pkg}")
    else
        ok "  ${pkg} bereits installiert"
    fi
done

if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
    info "Installiere fehlende Pakete: ${MISSING_PKGS[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y "${MISSING_PKGS[@]}"
    done_add "Systempakete installiert: ${MISSING_PKGS[*]}"
    ok "Pakete installiert."
else
    ok "Alle Systempakete bereits vorhanden."
fi

# ─── Python venv einrichten ───────────────────────────────────────────────────
step "Virtuelles Python-Environment einrichten"

if [[ ! -d "${VENV_DIR}" ]]; then
    info "Erstelle .venv in ${VENV_DIR} ..."
    python3 -m venv "${VENV_DIR}"
    done_add ".venv erstellt unter ${VENV_DIR}"
    ok ".venv erstellt."
else
    ok ".venv bereits vorhanden: ${VENV_DIR}"
fi

PIP="${VENV_DIR}/bin/pip"

info "Aktualisiere pip ..."
"${PIP}" install --quiet --upgrade pip

PIP_PACKAGES=(PyQt6 evdev openai pytest)
info "Installiere pip-Pakete: ${PIP_PACKAGES[*]} ..."
"${PIP}" install --quiet "${PIP_PACKAGES[@]}"
done_add "pip-Pakete installiert: ${PIP_PACKAGES[*]}"
ok "pip-Pakete installiert."

# ─── openai-whisper via pipx ──────────────────────────────────────────────────
step "openai-whisper via pipx"

if command -v pipx &>/dev/null; then
    if pipx list 2>/dev/null | grep -q "openai-whisper"; then
        ok "openai-whisper bereits via pipx installiert."
    else
        info "Installiere openai-whisper via pipx ..."
        pipx install openai-whisper
        done_add "openai-whisper via pipx installiert"
        ok "openai-whisper installiert."
    fi
else
    warn "pipx nicht gefunden — openai-whisper wird übersprungen."
    warn "Installieren Sie pipx mit: sudo apt install pipx && pipx ensurepath"
    warn "Danach: pipx install openai-whisper"
fi

# ─── Gruppe "input" ───────────────────────────────────────────────────────────
step "Benutzergruppe 'input' prüfen"

if groups "$(whoami)" | grep -qw "input"; then
    ok "Benutzer ist bereits Mitglied der Gruppe 'input'."
else
    info "Füge $(whoami) zur Gruppe 'input' hinzu ..."
    sudo usermod -aG input "$(whoami)"
    done_add "Benutzer zur Gruppe 'input' hinzugefügt (Re-Login erforderlich!)"
    warn "WICHTIG: Sie müssen sich ab- und wieder anmelden (oder neu starten),"
    warn "         damit die Gruppenmitgliedschaft aktiv wird."
fi

# ─── ydotoold als systemd-User-Service ────────────────────────────────────────
step "ydotoold systemd-User-Service einrichten"

mkdir -p "${SYSTEMD_USER_DIR}"

if [[ ! -f "${YDOTOOLD_SERVICE}" ]]; then
    info "Erstelle ${YDOTOOLD_SERVICE} ..."
    cat > "${YDOTOOLD_SERVICE}" <<'EOF'
[Unit]
Description=ydotool Daemon (ydotoold)
Documentation=man:ydotoold(8)
After=default.target

[Service]
Type=simple
ExecStart=/usr/bin/ydotoold --socket-path=%t/.ydotool_socket --socket-perm=0600
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF
    done_add "ydotoold.service angelegt"
    ok "ydotoold.service erstellt."
else
    ok "ydotoold.service bereits vorhanden."
fi

systemctl --user daemon-reload

if systemctl --user is-enabled --quiet ydotoold 2>/dev/null; then
    ok "ydotoold bereits aktiviert."
else
    systemctl --user enable ydotoold
    done_add "ydotoold.service aktiviert"
    ok "ydotoold.service aktiviert."
fi

if systemctl --user is-active --quiet ydotoold 2>/dev/null; then
    ok "ydotoold läuft bereits."
else
    systemctl --user start ydotoold
    done_add "ydotoold.service gestartet"
    ok "ydotoold.service gestartet."
fi

# ─── blitztext-linux.service einrichten ───────────────────────────────────────
step "blitztext-linux systemd-User-Service einrichten"

if [[ ! -f "${SERVICE_SRC}" ]]; then
    die "Service-Datei nicht gefunden: ${SERVICE_SRC}"
fi

info "Kopiere Service-Datei und setze WorkingDirectory auf ${BLITZTEXT_DIR} ..."
mkdir -p "${SYSTEMD_USER_DIR}"
sed "s|%BLITZTEXT_DIR%|${BLITZTEXT_DIR}|g" "${SERVICE_SRC}" > "${SERVICE_DST}"
done_add "blitztext-linux.service installiert nach ${SERVICE_DST}"
ok "Service-Datei installiert."

systemctl --user daemon-reload

if systemctl --user is-enabled --quiet blitztext-linux 2>/dev/null; then
    ok "blitztext-linux.service bereits aktiviert (Autostart)."
else
    systemctl --user enable blitztext-linux
    done_add "blitztext-linux.service für Autostart aktiviert (nicht gestartet)"
    ok "blitztext-linux.service für Autostart aktiviert."
fi

# ─── Zusammenfassung ──────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}══════════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}  Installation abgeschlossen${RESET}"
echo -e "${BOLD}══════════════════════════════════════════════════════${RESET}"
echo ""
echo -e "${BOLD}Durchgeführte Aktionen:${RESET}"
for item in "${DONE_ITEMS[@]}"; do
    echo -e "  ${GREEN}✔${RESET}  ${item}"
done

echo ""
echo -e "${BOLD}Nächste Schritte:${RESET}"
echo ""

if groups "$(whoami)" | grep -qw "input"; then
    echo -e "  ${GREEN}✔${RESET}  Gruppe 'input' bereits aktiv — kein Re-Login nötig."
else
    echo -e "  ${YELLOW}1.${RESET}  ${BOLD}Re-Login durchführen${RESET} (oder System neu starten),"
    echo      "     damit die Gruppe 'input' für evdev-Hotkeys aktiv wird."
fi

echo ""
echo -e "  ${YELLOW}2.${RESET}  ${BOLD}Manuellen Test starten:${RESET}"
echo      "     cd ${BLITZTEXT_DIR}"
echo      "     .venv/bin/python app/blitztext_linux.py"
echo ""
echo -e "  ${YELLOW}3.${RESET}  ${BOLD}Wenn alles funktioniert — Autostart aktivieren:${RESET}"
echo      "     systemctl --user start blitztext-linux"
echo ""
echo -e "  ${YELLOW}4.${RESET}  ${BOLD}Diagnose bei Problemen:${RESET}"
echo      "     bash scripts/verify.sh"
echo ""
