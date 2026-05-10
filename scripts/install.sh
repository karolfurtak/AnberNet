#!/bin/bash
# AnberNet installer dla Anbernic RG40XX V
# Uruchom z root (lub sudo) na konsoli (np. po SSH)
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APPS_DIR="/mnt/mmc/Roms/APPS"
APP_DIR="$APPS_DIR/anbernet"
IMGS_DIR="$APPS_DIR/Imgs"

echo "=== AnberNet install ==="

# 1. SDL2 app
mkdir -p "$APP_DIR"
cp "$REPO_DIR/app/main.py" "$APP_DIR/main.py"
cp "$REPO_DIR/app/AnberNet.sh" "$APPS_DIR/AnberNet.sh"
chmod +x "$APPS_DIR/AnberNet.sh"
echo "✓ App skopiowane do $APP_DIR"

# 2. Ikona (generowana w PIL)
mkdir -p "$IMGS_DIR"
python3 - <<EOF
from PIL import Image, ImageDraw
img = Image.new('RGBA', (240, 180), (0,0,0,0))
d = ImageDraw.Draw(img)
d.rectangle([(0,0),(240,180)], fill=(15,20,35,255))
cx, cy = 120, 130
for r in (60, 38, 18):
    d.arc([cx-r, cy-r, cx+r, cy+r], start=200, end=340, fill=(80,180,255,255), width=8)
d.ellipse([cx-6, cy-6, cx+6, cy+6], fill=(80,180,255,255))
img.save('$IMGS_DIR/AnberNet.png')
EOF
echo "✓ Ikona w $IMGS_DIR/AnberNet.png"

# 3. CLI wrapper
cp "$REPO_DIR/cli/wifi" /usr/local/bin/wifi
chmod +x /usr/local/bin/wifi
echo "✓ CLI: /usr/local/bin/wifi (uruchom: wifi)"

# 4. Sprawdź zależności
python3 -c "import sdl2" 2>/dev/null || echo "⚠️  brak pysdl2 — pip install pysdl2"
python3 -c "import evdev" 2>/dev/null || echo "⚠️  brak evdev — pip install evdev"
python3 -c "import PIL" 2>/dev/null || echo "⚠️  brak Pillow — pip install Pillow"

echo ""
echo "Zainstalowane. Uruchom 'AnberNet' z App Center."
