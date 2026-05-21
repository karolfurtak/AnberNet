#!/usr/bin/env python3
"""AnberNet — apka SDL2 do zarządzania WiFi na Anbernic RG40XX V.

GitHub: https://github.com/karolfurtak/AnberNet
"""
import os, sys, subprocess, ctypes, time
from pathlib import Path
from datetime import datetime

os.environ.pop('SDL_VIDEODRIVER', None)

import sdl2, sdl2.ext
from PIL import Image, ImageDraw, ImageFont

# ── Layout ──────────────────────────────────────────────────────────────────
W, H        = 640, 480
FONT_PATH   = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
FONT_SM, FONT_MD, FONT_LG = 12, 14, 18

BG  = (10, 12, 20, 255)
FG  = (200, 210, 220, 255)
ACC = (80, 180, 255, 255)
GRN = (80, 220, 100, 255)
YEL = (255, 210, 60, 255)
RED = (255, 80, 80, 255)
DIM = (90, 100, 110, 255)
SEP = (40, 50, 65, 255)
SEL = (40, 80, 130, 255)   # tło zaznaczenia

# ── Input codes (evdev) ─────────────────────────────────────────────────────
EXIT_KEYS  = {354, 316}   # MENU
KEY_A      = 304          # zatwierdź
KEY_B      = 305          # cofnij / backspace
KEY_X      = 307          # zapomnij / shift
KEY_Y      = 308          # spacja
KEY_START  = 315          # OK / submit
KEY_SELECT = 314          # zmień layout (abc/ABC/123)
KEY_L1     = 310          # cursor w lewo (alt do D-pad)
KEY_R1     = 311          # cursor w prawo
ABS_HAT0X  = 16           # D-pad left/right
ABS_HAT0Y  = 17           # D-pad up/down

# Klawiatura on-screen — 3 layouty
_ACTION_ROW = ['ABC', 'SPC', 'DEL', 'OK', '×']  # specjalne akcje — ostatni wiersz każdego layoutu

KB_LOWER = [
    list('1234567890'),
    list('qwertyuiop'),
    list('asdfghjkl@'),
    list('zxcvbnm-_.'),
    _ACTION_ROW,
]
KB_UPPER = [
    list('!@#$%^&*()'),
    list('QWERTYUIOP'),
    list('ASDFGHJKL+'),
    list('ZXCVBNM<>?'),
    _ACTION_ROW,
]
KB_SYMBOLS = [
    list('1234567890'),
    list('!@#$%^&*()'),
    list('-_=+[]{}|~'),
    list('`;:,.<>?/\\'),
    _ACTION_ROW,
]
KB_LAYOUTS = [('abc', KB_LOWER), ('ABC', KB_UPPER), ('123', KB_SYMBOLS)]

DBG_LOG = '/mnt/data/anbernet_debug.log'

def log(msg: str):
    with open(DBG_LOG, 'a') as f:
        f.write(f'{datetime.now():%H:%M:%S} {msg}\n')

# ── nmcli wrappers ──────────────────────────────────────────────────────────
def nmcli(*args, timeout=10) -> tuple:
    try:
        r = subprocess.run(['nmcli', *args], capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, '', str(e)

def scan_networks(retries: int = 3) -> list:
    """Zwraca listę dict: ssid, signal, security, in_use, saved.
    Force rescan + retry żeby uniknąć "Brak sieci" gdy cache nmcli jest pusty/stale."""
    import time
    saved = saved_ssids()
    # Upewnij się że WiFi radio włączone (gdyby user wyłączył przez NM)
    nmcli('radio', 'wifi', 'on', timeout=5)
    # Force świeży scan (nie polegamy na cache nmcli)
    nmcli('device', 'wifi', 'rescan', 'ifname', 'wlan0', timeout=15)
    # Daj 2s na zebranie wyników
    time.sleep(2)
    nets = []
    for attempt in range(retries):
        rc, out, _ = nmcli('-t', '-f', 'IN-USE,SSID,SIGNAL,SECURITY', 'device', 'wifi', 'list',
                           'ifname', 'wlan0', '--rescan', 'no', timeout=15)
        if rc != 0:
            time.sleep(2); continue
        # Sprawdź czy lista nie pusta (są wpisy ze SSID)
        has_ssids = any(len(l.split(':', 2)[1]) > 0 for l in out.splitlines() if ':' in l)
        if has_ssids:
            break
        # pusta — spróbuj jeszcze raz po 2s (sieć może się jeszcze rozkręca)
        log(f'scan attempt {attempt+1} pusty, retry...')
        nmcli('device', 'wifi', 'rescan', 'ifname', 'wlan0', timeout=15)
        time.sleep(2)
    if rc != 0:
        return nets
    seen = set()
    for line in out.splitlines():
        parts = line.split(':')
        if len(parts) < 4:
            continue
        in_use, ssid, signal, security = parts[0], parts[1], parts[2], ':'.join(parts[3:])
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)
        nets.append({
            'ssid': ssid,
            'signal': int(signal) if signal.isdigit() else 0,
            'security': security or 'open',
            'in_use': in_use == '*',
            'saved': ssid in saved,
        })
    nets.sort(key=lambda n: (-n['in_use'], -n['saved'], -n['signal']))
    return nets

def saved_ssids() -> set:
    rc, out, _ = nmcli('-t', '-f', 'NAME,TYPE', 'connection', 'show')
    s = set()
    for line in out.splitlines():
        parts = line.rsplit(':', 1)
        if len(parts) == 2 and parts[1] == '802-11-wireless':
            s.add(parts[0])
    return s

def connect_saved(ssid: str) -> tuple:
    """Połącz z zapisaną siecią. Zwraca (ok, msg)."""
    rc, out, err = nmcli('connection', 'up', ssid, timeout=20)
    return (rc == 0, out if rc == 0 else err.split('\n')[-1])

def disconnect_wlan() -> tuple:
    rc, out, err = nmcli('device', 'disconnect', 'wlan0', timeout=10)
    return (rc == 0, err if rc else 'rozłączono')

def forget(ssid: str) -> bool:
    rc, _, _ = nmcli('connection', 'delete', ssid)
    return rc == 0

def current_ip() -> str:
    try:
        r = subprocess.check_output(['ip', '-4', 'addr', 'show', 'wlan0'], text=True)
        for line in r.splitlines():
            line = line.strip()
            if line.startswith('inet '):
                return line.split()[1].split('/')[0]
    except Exception:
        pass
    return ''

def signal_bars(signal: int) -> str:
    if signal >= 75: return '████'
    if signal >= 50: return '███░'
    if signal >= 25: return '██░░'
    if signal > 0:   return '█░░░'
    return '░░░░'

# ── SDL App ─────────────────────────────────────────────────────────────────
class WifiApp:
    def __init__(self):
        log('=== START ===')
        sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_EVENTS)

        self.win = sdl2.SDL_CreateWindow(
            b"AnberNet", sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED,
            0, 0, sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP | sdl2.SDL_WINDOW_SHOWN
        )
        self.ren = sdl2.SDL_CreateRenderer(self.win, -1, sdl2.SDL_RENDERER_SOFTWARE) \
                   or sdl2.SDL_CreateRenderer(self.win, -1, 0)

        self.img  = Image.new('RGBA', (W, H), BG)
        self.draw = ImageDraw.Draw(self.img)
        self.fsm  = ImageFont.truetype(FONT_PATH, FONT_SM)
        self.fmd  = ImageFont.truetype(FONT_PATH, FONT_MD)
        self.flg  = ImageFont.truetype(FONT_PATH, FONT_LG)

        self._tex   = None
        self._dpad_repeat_time = 0

        # evdev
        self._gp = None
        try:
            import evdev
            self._gp = evdev.InputDevice('/dev/input/event1')
            self._gp.grab()
            log(f'evdev OK: {self._gp.name}')
            import select as _sel
            while _sel.select([self._gp.fd], [], [], 0)[0]:
                self._gp.read()
        except Exception as e:
            log(f'evdev FAIL: {e}')

        # state
        self.mode     = 'list'      # 'list' lub 'password'
        self.networks: list = []
        self.cursor   = 0
        self.scroll   = 0
        self.message  = 'Skanuję sieci...'
        self.busy     = False
        self.scanning = True
        # password mode
        self.pw_target_ssid = ''
        self.pw_text        = ''
        self.pw_kb_row      = 1
        self.pw_kb_col      = 0
        self.pw_layout_idx  = 0     # index w KB_LAYOUTS

    def _text(self, x, y, txt, font, color):
        self.draw.text((x, y), txt, font=font, fill=color)

    def render(self):
        d = self.draw
        d.rectangle([(0, 0), (W, H)], fill=BG)

        # nagłówek
        self._text(8, 6, '⬡ AnberNet', self.flg, ACC)
        ip = current_ip()
        ip_str = f'IP: {ip}' if ip else 'IP: brak'
        tw = self.fmd.getlength(ip_str)
        self._text(W - int(tw) - 8, 10, ip_str, self.fmd, DIM)
        d.line([(0, 32), (W, 32)], fill=SEP, width=1)

        if self.mode == 'password':
            self._render_keyboard()
            self._blit()
            return

        # lista sieci
        list_top = 38
        line_h   = 26
        max_visible = (H - list_top - 60) // line_h

        if not self.networks:
            self._text(W // 2 - 60, H // 2 - 10,
                       self.message or 'Brak sieci', self.fmd, DIM)
        else:
            # scroll do kursora
            if self.cursor < self.scroll:
                self.scroll = self.cursor
            elif self.cursor >= self.scroll + max_visible:
                self.scroll = self.cursor - max_visible + 1

            for i in range(self.scroll, min(len(self.networks), self.scroll + max_visible)):
                net = self.networks[i]
                y = list_top + (i - self.scroll) * line_h
                if i == self.cursor:
                    d.rectangle([(0, y - 2), (W, y + line_h - 4)], fill=SEL)
                col = ACC if net['in_use'] else (GRN if net['saved'] else FG)
                marker = '✓' if net['in_use'] else ('★' if net['saved'] else ' ')
                lock = '🔒' if net['security'] != 'open' else '  '
                ssid_disp = net['ssid'][:32]
                self._text(8, y, marker, self.fmd, col)
                self._text(28, y, ssid_disp, self.fmd, col)
                self._text(W - 130, y, signal_bars(net['signal']), self.fmd, col)
                self._text(W - 70, y, f'{net["signal"]:3d}%', self.fsm, col)

        # status bar dolny
        d.line([(0, H - 50), (W, H - 50)], fill=SEP, width=1)
        if self.message:
            mc = RED if self.message.lower().startswith(('błąd', 'error')) else FG
            self._text(8, H - 44, self.message, self.fsm, mc)
        # legenda
        legend = 'A=połącz/rozłącz  B=skanuj  X=zapomnij  MENU=wyjście'
        self._text(8, H - 16, legend, self.fsm, DIM)

        self._blit()

    def _blit(self):
        raw = self.img.tobytes()
        surf = sdl2.SDL_CreateRGBSurfaceWithFormatFrom(
            raw, W, H, 32, W * 4, sdl2.SDL_PIXELFORMAT_RGBA32)
        if self._tex:
            sdl2.SDL_DestroyTexture(self._tex)
        self._tex = sdl2.SDL_CreateTextureFromSurface(self.ren, surf)
        sdl2.SDL_FreeSurface(surf)
        sdl2.SDL_RenderClear(self.ren)
        sdl2.SDL_RenderCopy(self.ren, self._tex, None, None)
        sdl2.SDL_RenderPresent(self.ren)

    def do_scan(self):
        self.message = 'Skanuję sieci...'
        self.render()
        self.networks = scan_networks()
        if self.cursor >= len(self.networks):
            self.cursor = max(0, len(self.networks) - 1)
        if self.networks:
            self.message = f'Znaleziono {len(self.networks)} sieci'
        else:
            self.message = 'Brak sieci — naciśnij B aby skanować ponownie'

    def do_connect(self):
        if not self.networks: return
        net = self.networks[self.cursor]
        if net['in_use']:
            self.message = f'Rozłączam {net["ssid"]}...'
            self.render()
            ok, msg = disconnect_wlan()
            self.message = 'Rozłączono' if ok else f'Błąd: {msg}'
            self.do_scan()
        elif net['saved']:
            self.message = f'Łączę z {net["ssid"]}...'
            self.render()
            ok, msg = connect_saved(net['ssid'])
            self.message = f'Połączono z {net["ssid"]}' if ok else f'Błąd: {msg[:50]}'
            self.do_scan()
        elif net['security'] == 'open':
            # otwarta sieć bez hasła
            self.message = f'Łączę z {net["ssid"]} (otwarta)...'
            self.render()
            rc, _, err = nmcli('device', 'wifi', 'connect', net['ssid'], 'ifname', 'wlan0', timeout=20)
            self.message = f'Połączono' if rc == 0 else f'Błąd: {err[:50]}'
            self.do_scan()
        else:
            # wymaga hasła — wejdź w tryb password
            self.mode = 'password'
            self.pw_target_ssid = net['ssid']
            self.pw_text = ''
            self.pw_kb_row = 1
            self.pw_kb_col = 0
            self.pw_layout_idx = 0
            self.message = 'Wpisz hasło (BT KB lub ekran), Enter/START=połącz'
            sdl2.SDL_StartTextInput()

    def do_password_submit(self):
        if not self.pw_text:
            self.message = 'Hasło puste'
            return
        ssid = self.pw_target_ssid
        self.message = f'Łączę z {ssid}...'
        self.mode = 'list'
        sdl2.SDL_StopTextInput()
        self.render()
        rc, out, err = nmcli('device', 'wifi', 'connect', ssid, 'password', self.pw_text,
                             'ifname', 'wlan0', timeout=25)
        if rc == 0:
            self.message = f'Połączono z {ssid}'
        else:
            self.message = f'Błąd: {err.split(chr(10))[-1][:60]}'
        self.pw_text = ''
        self.pw_target_ssid = ''
        self.do_scan()

    def _render_keyboard(self):
        d = self.draw
        # tło dla obszaru klawiatury (dolna połowa)
        kb_y0 = 180
        d.rectangle([(0, kb_y0), (W, H)], fill=(8, 10, 18, 255))
        # nagłówek password
        self._text(8, 40, f'Połącz z:', self.fmd, DIM)
        self._text(110, 40, self.pw_target_ssid[:40], self.fmd, ACC)
        self._text(8, 70, 'Hasło:', self.fmd, DIM)
        # pole hasła z kursorem
        masked = '*' * len(self.pw_text) + '|'
        d.rectangle([(80, 66), (W-8, 92)], outline=SEP, width=1)
        self._text(86, 70, masked[:60], self.fmd, FG)
        # info layoutu
        layout_name = KB_LAYOUTS[self.pw_layout_idx][0]
        self._text(W - 80, 100, f'[{layout_name}]', self.fsm, ACC)
        self._text(8, 100, f'Hasło: {len(self.pw_text)} znak.', self.fsm, DIM)

        # klawiatura — siatka 5 wierszy (4 znaków + akcje)
        layout = KB_LAYOUTS[self.pw_layout_idx][1]
        cell_w, cell_h = 56, 38
        kb_x0 = (W - cell_w * 10) // 2
        kb_y_base = 200
        ACTION_COL = ACC
        for r, row in enumerate(layout):
            is_action_row = (r == len(layout) - 1)
            # rozciągnij wiersz akcji na całą szerokość
            n_cells = len(row)
            row_w = cell_w * n_cells * (10 / n_cells if is_action_row else 1)
            row_x0 = kb_x0 if not is_action_row else (W - int(row_w)) // 2
            cw = cell_w if not is_action_row else int(row_w / n_cells)
            for c, ch in enumerate(row):
                x = row_x0 + c * cw
                y = kb_y_base + r * cell_h
                col_text = ACTION_COL if is_action_row else FG
                if r == self.pw_kb_row and c == self.pw_kb_col:
                    d.rectangle([(x, y), (x + cw - 4, y + cell_h - 4)], fill=SEL)
                else:
                    d.rectangle([(x, y), (x + cw - 4, y + cell_h - 4)],
                                outline=ACTION_COL if is_action_row else SEP, width=1)
                # centruj tekst w komórce
                tw = self.fmd.getlength(ch)
                self._text(x + (cw - int(tw)) // 2, y + 8, ch, self.fmd, col_text)

        # legenda dolna
        d.line([(0, H - 22), (W, H - 22)], fill=SEP, width=1)
        self._text(8, H - 16,
                   'D-pad=ruch  A=wybierz  B=←  Y=spacja  X=Shift  | OK/×/DEL w ostatnim wierszu',
                   self.fsm, DIM)

    def do_forget(self):
        if not self.networks: return
        net = self.networks[self.cursor]
        if not net['saved']:
            self.message = 'Sieć nie jest zapisana'
            return
        if forget(net['ssid']):
            self.message = f'Usunięto {net["ssid"]}'
        else:
            self.message = f'Błąd usuwania {net["ssid"]}'
        self.do_scan()

    def run(self):
        # POWER button → wygaszanie ekranu bez zamykania apki
        try:
            from power_screen import ScreenPowerToggle
            self._screen_pwr = ScreenPowerToggle()
        except Exception:
            self._screen_pwr = None

        # początkowy skan
        self.render()
        self.do_scan()
        self.render()

        ev = sdl2.SDL_Event()
        start_ms = sdl2.SDL_GetTicks()
        GUARD_MS = 3000

        while True:
            now = sdl2.SDL_GetTicks()
            guard = (now - start_ms) < GUARD_MS

            # POWER button — toggle ekranu (nie zamyka)
            if self._screen_pwr is not None:
                self._screen_pwr.poll()
                self._screen_pwr.tick(now)
                if self._screen_pwr.is_off:
                    sdl2.SDL_Delay(50)
                    continue

            # evdev events
            if self._gp:
                import select
                if select.select([self._gp.fd], [], [], 0)[0]:
                    for e in self._gp.read():
                        if guard: continue
                        if self.mode == 'list':
                            self._handle_list_event(e)
                        else:
                            self._handle_password_event(e)
                        if self.mode == '__quit__':
                            self.quit(); return

            # SDL events — BT klawiatura
            while sdl2.SDL_PollEvent(ctypes.byref(ev)):
                if guard: continue
                if ev.type == sdl2.SDL_TEXTINPUT and self.mode == 'password':
                    try:
                        ch = bytes(ev.text.text).decode('utf-8', errors='ignore').rstrip('\x00')
                    except Exception:
                        ch = ''
                    if ch and ch.isprintable() and len(self.pw_text) + len(ch) <= 63:
                        self.pw_text += ch
                        self.render()
                elif ev.type == sdl2.SDL_KEYDOWN:
                    sym = ev.key.keysym.sym
                    if self.mode == 'password':
                        if sym == sdl2.SDLK_BACKSPACE:
                            self.pw_text = self.pw_text[:-1]
                            self.render()
                        elif sym in (sdl2.SDLK_RETURN, sdl2.SDLK_KP_ENTER):
                            self.do_password_submit()
                            self.render()
                        elif sym == sdl2.SDLK_ESCAPE:
                            self.mode = 'list'
                            self.pw_text = ''
                            sdl2.SDL_StopTextInput()
                            self.message = 'Anulowano'
                            self.do_scan()
                            self.render()
                    else:
                        if sym == sdl2.SDLK_ESCAPE:
                            self.quit(); return

            sdl2.SDL_Delay(50)

    def _handle_list_event(self, e):
        if e.type == 1 and e.value == 1:  # EV_KEY press
            if e.code in EXIT_KEYS:
                self.mode = '__quit__'
            elif e.code == KEY_A:
                self.do_connect(); self.render()
            elif e.code == KEY_B:
                self.do_scan(); self.render()
            elif e.code == KEY_X:
                self.do_forget(); self.render()
        elif e.type == 3 and e.code == ABS_HAT0Y:  # D-pad Y
            if e.value == -1 and self.networks:
                self.cursor = (self.cursor - 1) % len(self.networks)
                self.render()
            elif e.value == 1 and self.networks:
                self.cursor = (self.cursor + 1) % len(self.networks)
                self.render()

    def _press_current_cell(self):
        """A na aktualnej komórce klawiatury — wstaw znak lub wykonaj akcję."""
        layout = KB_LAYOUTS[self.pw_layout_idx][1]
        cell = layout[self.pw_kb_row][self.pw_kb_col]
        if cell == 'OK':
            self.do_password_submit()
        elif cell == '×':
            # cancel
            self.mode = 'list'
            self.pw_text = ''
            sdl2.SDL_StopTextInput()
            self.message = 'Anulowano'
            self.do_scan()
        elif cell == 'DEL':
            self.pw_text = self.pw_text[:-1]
        elif cell == 'SPC':
            if len(self.pw_text) < 63:
                self.pw_text += ' '
        elif cell == 'ABC':
            self.pw_layout_idx = (self.pw_layout_idx + 1) % len(KB_LAYOUTS)
        else:
            # zwykły znak
            if len(self.pw_text) < 63:
                self.pw_text += cell

    def _handle_password_event(self, e):
        layout = KB_LAYOUTS[self.pw_layout_idx][1]
        rows = len(layout)
        if e.type == 1 and e.value == 1:
            log(f'pw key code={e.code}')
            if e.code in EXIT_KEYS:
                self.mode = 'list'
                self.message = 'Anulowano'
                self.pw_text = ''
                sdl2.SDL_StopTextInput()
                self.do_scan()
                self.render()
            elif e.code == KEY_A:
                self._press_current_cell()
                self.render()
            elif e.code == KEY_B:
                self.pw_text = self.pw_text[:-1]
                self.render()
            elif e.code == KEY_Y:
                if len(self.pw_text) < 63:
                    self.pw_text += ' '
                self.render()
            elif e.code == KEY_X:
                # toggle Shift = abc <-> ABC
                if self.pw_layout_idx == 0:    self.pw_layout_idx = 1
                elif self.pw_layout_idx == 1:  self.pw_layout_idx = 0
                self.render()
            elif e.code == KEY_L1:
                self.pw_kb_col = (self.pw_kb_col - 1) % len(layout[self.pw_kb_row])
                self.render()
            elif e.code == KEY_R1:
                self.pw_kb_col = (self.pw_kb_col + 1) % len(layout[self.pw_kb_row])
                self.render()
        elif e.type == 3:
            log(f'pw abs code={e.code} val={e.value}')
            if e.code == ABS_HAT0X:
                if e.value == -1:
                    self.pw_kb_col = (self.pw_kb_col - 1) % len(layout[self.pw_kb_row])
                    self.render()
                elif e.value == 1:
                    self.pw_kb_col = (self.pw_kb_col + 1) % len(layout[self.pw_kb_row])
                    self.render()
            elif e.code == ABS_HAT0Y:
                if e.value == -1:
                    self.pw_kb_row = (self.pw_kb_row - 1) % rows
                    self.pw_kb_col = min(self.pw_kb_col, len(layout[self.pw_kb_row]) - 1)
                    self.render()
                elif e.value == 1:
                    self.pw_kb_row = (self.pw_kb_row + 1) % rows
                    self.pw_kb_col = min(self.pw_kb_col, len(layout[self.pw_kb_row]) - 1)
                    self.render()

    def quit(self):
        log('quit')
        if getattr(self, '_screen_pwr', None) is not None:
            self._screen_pwr.restore()
        if self._gp:
            try: self._gp.ungrab()
            except Exception: pass
        if self._tex:
            sdl2.SDL_DestroyTexture(self._tex)
        sdl2.SDL_DestroyRenderer(self.ren)
        sdl2.SDL_DestroyWindow(self.win)
        sdl2.SDL_Quit()


if __name__ == '__main__':
    WifiApp().run()
