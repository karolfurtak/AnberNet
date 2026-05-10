# Anbernet

Lekka apka SDL2 do zarządzania WiFi na **Anbernic RG40XX V** (Allwinner H700, stock Ubuntu 22.04 firmware) — sterowana D-padem, integruje się z App Center, ma on-screen klawiaturę dla wpisywania haseł oraz obsługę BT klawiatury.

W zestawie też CLI `wifi` jako prosty wrapper na `nmcli` — dostępny z każdego terminala.

## Możliwości

**App (graficzna):**
- skan dostępnych sieci z poziomem sygnału (paski + %)
- oznaczanie sieci zapisanych (★) i aktywnej (✓)
- połączenie do zapisanej sieci jednym przyciskiem
- on-screen klawiatura QWERTY z trzema layoutami (`abc` / `ABC` / `123`) do wpisania hasła
- równoległa obsługa BT klawiatury (przez SDL_TextInput) — zwykłe pisanie, Enter, Backspace, Esc
- usuwanie zapisanych sieci
- wyświetlanie aktualnego IP

**CLI:**
- `wifi` — skan
- `wifi connect <SSID> <hasło>` — połącz
- `wifi reconnect` — auto-pick zapisanej
- `wifi disconnect` / `forget` / `saved` / `status` / `ip`

## Sterowanie (App)

| Akcja | Lista sieci | Tryb hasła |
|---|---|---|
| Nawigacja | D-pad ↑↓ | D-pad ←↑↓→ |
| Wybierz / wstaw | A | A |
| Backspace | — | B |
| Spacja | — | Y |
| Shift (abc/ABC) | — | X |
| Skanuj ponownie | B | — |
| Zapomnij sieć | X | — |
| Zatwierdź hasło | — | komórka **OK** w klawiaturze |
| Anuluj | — | komórka **×** w klawiaturze |
| Wyjście | MENU | MENU |

W trybie hasła ostatni wiersz klawiatury zawiera akcje `[ABC] [SPC] [DEL] [OK] [×]` — najedź D-padem i wciśnij A.

Z **BT klawiatury** w trybie hasła: pisz normalnie, **Enter** = połącz, **Backspace** = ←, **Esc** = anuluj.

## Wymagania

### Hardware

- **Anbernic RG40XX V** (Allwinner H700, axp2202 PMIC, 640×480 LCD landscape)
- inne RG40-serii **mogą działać** (kody przycisków evdev są zgodne z większością RG40xxx) — niesprawdzone

### Firmware

Tworzone i testowane na **stock Anbernic firmware build `20251225`** (December 25, 2025):
- Ubuntu 22.04.x LTS (Jammy)
- Kernel `4.9.170` (Allwinner H700 BSP)
- App Center: `dmenu.bin` (vendor)
- File: `/mnt/vendor/oem/version.ini` → `20251225`
- File: `/mnt/vendor/oem/board.ini` → `RG40xxV`

Inne firmware (muOS, Knulli, garlicOS) **niesprawdzone** — kody przycisków evdev mogą się różnić, NetworkManager może nie być obecny.

### System packages

Stock firmware już zawiera:

| Pakiet | Wersja stock | Rola |
|---|---|---|
| `nmcli` (network-manager) | systemowy | zarządzanie WiFi |
| `iw` | systemowy | diagnostyka WiFi |
| `libsdl2-2.0-0` | 2.0.20 | renderer |
| `python3` | 3.10.x | runtime |
| `fonts-dejavu` (DejaVuSansMono.ttf) | systemowy | font UI |

Jeśli czegoś brakuje:
```bash
apt update
apt install network-manager iw python3 python3-pip libsdl2-2.0-0 fonts-dejavu
```

### Python packages

| Pakiet | Wersja testowana | Rola |
|---|---|---|
| `pysdl2` | 0.9.17 | renderowanie GUI |
| `evdev` | 1.6.1 | gamepad input (D-pad, A/B/X/Y, MENU) |
| `pillow` (PIL) | 12.2.0 | rysowanie obrazów do bufora |

Instalacja:
```bash
pip install pysdl2 evdev Pillow
```

(Wszystkie zwykle są już obecne na stock firmware — `install.sh` sprawdza i raportuje braki.)

## Instalacja

```bash
git clone https://github.com/karolfurtak/Anbernet.git
cd Anbernet
./scripts/install.sh
```

Skrypt:
- kopiuje `app/main.py` do `/mnt/mmc/Roms/APPS/anbernet/main.py`
- kopiuje launcher do `/mnt/mmc/Roms/APPS/Anbernet.sh`
- generuje ikonę PNG do `/mnt/mmc/Roms/APPS/Imgs/Anbernet.png`
- instaluje `cli/wifi` do `/usr/local/bin/wifi`

Po instalacji **Anbernet** pojawi się w App Center na konsoli.

## Logi

- `/mnt/data/anbernet.log` — stdout / błędy launchera
- `/mnt/data/anbernet_debug.log` — eventy evdev (przyciski) z trybu hasła

## Licencja

MIT — patrz [LICENSE](LICENSE).
