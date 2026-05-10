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

- Anbernic RG40XX V z stock firmware (Ubuntu 22.04 base, `dmenu.bin` jako App Center)
- `nmcli` (NetworkManager) — domyślnie obecne
- Python 3.10+ z bibliotekami:
  - `pysdl2` (najczęściej wbudowane w stock firmware)
  - `python-evdev`
  - `pillow`

Jeśli `evdev` brakuje:
```bash
pip install evdev
```

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
