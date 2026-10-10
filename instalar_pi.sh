#!/usr/bin/env bash
# Instala o Bimo no Raspberry Pi (Raspberry Pi OS com ou sem desktop).
# Uso: bash instalar_pi.sh
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"

echo ">> Instalando pacotes do sistema..."
sudo apt install -y python3-venv python3-pygame python3-numpy libportaudio2 espeak-ng flac

# Permite escrever no LCD (/dev/fb1), usar áudio, vídeo (KMS/DRM) e entrada sem sudo
# (vale após logout/login ou reboot)
sudo usermod -aG video,audio,render,input "$USER"

echo ">> Criando ambiente Python..."
python3 -m venv --system-site-packages .venv

if [ ! -f requirements-pi.txt ]; then
  cat > requirements-pi.txt <<'EOF'
openai
python-dotenv
SpeechRecognition
sounddevice
standard-aifc
audioop-lts
EOF
fi
./.venv/bin/pip install -r requirements-pi.txt

# O rosto usa recursos do pygame 2. Em sistemas antigos o do apt é 1.x.
if ! ./.venv/bin/python -c "import pygame,sys; sys.exit(0 if int(pygame.version.ver.split('.')[0])>=2 else 1)"; then
  echo ">> pygame do sistema é antigo, instalando uma versão nova no ambiente..."
  ./.venv/bin/pip install pygame
fi

MODO_AUTO="nenhum"
read -r -p "Iniciar o Bimo automaticamente ao ligar o Pi? [s/N] " r
if [[ "$r" =~ ^[sS]$ ]]; then
  read -r -p "Este Pi tem interface gráfica (Desktop)? [s/N] " d
  if [[ "$d" =~ ^[sS]$ ]]; then
    # Com desktop: autostart da sessão gráfica (remove o service para não duplicar)
    sudo systemctl disable --now bimo.service 2>/dev/null || true
    mkdir -p "$HOME/.config/autostart"
    cat > "$HOME/.config/autostart/bimo.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Bimo
Path=$DIR
Exec=$DIR/.venv/bin/python $DIR/robo.py --fullscreen
Terminal=false
DESK
    MODO_AUTO="desktop"
    echo ">> Início automático (Desktop) ativado."
  else
    # Sem desktop (Pi OS Lite): service do systemd (remove o autostart para não duplicar)
    rm -f "$HOME/.config/autostart/bimo.desktop"
    sudo tee /etc/systemd/system/bimo.service >/dev/null <<SVC
[Unit]
Description=Bimo robo face
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$DIR
ExecStart=$DIR/.venv/bin/python $DIR/robo.py --fullscreen
Restart=always
RestartSec=5
SupplementaryGroups=video render input audio

[Install]
WantedBy=multi-user.target
SVC
    sudo systemctl daemon-reload
    sudo systemctl enable bimo.service
    MODO_AUTO="systemd"
    echo ">> Início automático (systemd) ativado. Ele sobe no próximo boot."
  fi
fi

echo
echo "Pronto. Confira o seu .env:  nano $DIR/.env"
echo "Reinicie o Pi (sudo reboot) para os grupos video/audio/render/input valerem."
case "$MODO_AUTO" in
  systemd)
    echo "Depois do reboot, veja o robô com:  journalctl -u bimo.service -f"
    echo "Para parar:  sudo systemctl stop bimo.service"
    ;;
  desktop)
    echo "Depois do reboot e do login no desktop, o Bimo abre sozinho."
    ;;
  *)
    echo "Teste manual:  $DIR/.venv/bin/python $DIR/robo.py --fullscreen"
    echo "(com desktop, use DISPLAY=:0 na frente)"
    ;;
esac
echo "Se der erro de microfone, veja:  $DIR/.venv/bin/python -m sounddevice  (e BIMO_MIC no .env)"
