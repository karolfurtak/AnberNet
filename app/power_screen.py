"""Screen power toggle przez fb0/blank — POWER button (event0) wygasza ekran
bez zamykania aplikacji.

Użycie:
    pwr = ScreenPowerToggle()

    # w pętli głównej:
    pwr.poll()
    pwr.tick(sdl2.SDL_GetTicks())
    if pwr.is_off:
        sdl2.SDL_Delay(50)
        continue   # pomiń render

    # w cleanup / quit:
    pwr.restore()
"""
import select
from pathlib import Path

POWER_KEY = 116
FB_BLANK  = '/sys/class/graphics/fb0/blank'
RE_WRITE_MS = 200   # ponów fb0/blank=4 co 200ms (kernel czasem przywraca)


class ScreenPowerToggle:
    def __init__(self, event_path: str = '/dev/input/event0'):
        self._screen_off = False
        self._last_write = 0
        self._pwr = None
        try:
            import evdev
            self._pwr = evdev.InputDevice(event_path)
            try:
                self._pwr.grab()
            except Exception:
                pass
        except Exception:
            self._pwr = None

    @property
    def is_off(self) -> bool:
        return self._screen_off

    def poll(self) -> bool:
        """Sprawdź event0; jeśli POWER naciśnięty — toggle. Zwraca True gdy zmiana stanu."""
        if not self._pwr:
            return False
        try:
            if not select.select([self._pwr.fd], [], [], 0)[0]:
                return False
            changed = False
            for e in self._pwr.read():
                if e.type == 1 and e.code == POWER_KEY and e.value == 1:
                    self._screen_off = not self._screen_off
                    self._write()
                    changed = True
            return changed
        except OSError:
            return False

    def tick(self, now_ms: int):
        """Wywołaj co cykl pętli — gdy ekran ma być OFF, ponawiaj fb0/blank=4
        co RE_WRITE_MS żeby kernel nie przywrócił."""
        if self._screen_off and now_ms - self._last_write >= RE_WRITE_MS:
            self._write()

    def _write(self):
        try:
            Path(FB_BLANK).write_text('4' if self._screen_off else '0')
            from time import monotonic
            # bez czytania zegara z SDL — używamy własnego stamp dla tick()
            self._last_write = int(monotonic() * 1000)
        except Exception:
            pass

    def restore(self):
        """Przywróć ekran ON i zwolnij grab. Wywołać przy zamykaniu apki."""
        try:
            Path(FB_BLANK).write_text('0')
        except Exception:
            pass
        if self._pwr is not None:
            try:
                self._pwr.ungrab()
            except Exception:
                pass
            self._pwr = None
