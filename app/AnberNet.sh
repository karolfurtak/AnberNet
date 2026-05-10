#!/bin/bash
# AnberNet launcher dla App Center / dmenu
export PYSDL2_DLL_PATH="/usr/lib"
export HOME=/root
export PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin"
LOG=/mnt/data/anbernet.log
echo "$(date +%H:%M:%S): start" >> "$LOG"
cd /mnt/mmc/Roms/APPS/anbernet || exit 1
python3 main.py >> "$LOG" 2>&1
echo "$(date +%H:%M:%S): exit $?" >> "$LOG"
