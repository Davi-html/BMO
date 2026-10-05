#!/usr/bin/env bash
# Instala o Bimo no Raspberry Pi (Raspberry Pi OS com desktop).
# Uso: bash instalar_pi.sh
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"

echo ">> Instalando pacotes do sistema..."
sudo apt install -y python3-venv python3-pygame python3-numpy libportaudio2 espeak-ng flac

# Permite escrever no LCD (/dev/fb1) e usar o áudio sem sudo (vale após logout/login)
sudo usermod -aG video,audio "$USER"

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

read -r -p "Iniciar o Bimo junto com a área de trabalho? [s/N] " r
if [[ "$r" =~ ^[sS]$ ]]; then
  mkdir -p "$HOME/.config/autostart"
  cat > "$HOME/.config/autostart/bimo.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Bimo
Path=$DIR
Exec=$DIR/.venv/bin/python $DIR/robo.py --fullscreen
DESK
  echo ">> Início automático ativado."
fi

echo
echo "Pronto. Confira o seu .env:  nano $DIR/.env"
echo "Reinicie o Pi (sudo reboot) para os grupos video/audio valerem."
echo "Depois teste:  DISPLAY=:0 $DIR/.venv/bin/python $DIR/robo.py"
