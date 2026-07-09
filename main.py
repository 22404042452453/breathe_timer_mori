"""
Дыхательная практика — Вим Хоф
Kivy-версия для Android и ПК.

Логика практики крутится в фоновом потоке (_run), а всё, что касается
графики, звука и виджетов, маршалится в главный поток через Clock —
Kivy, как и большинство GUI-тулкитов, не потокобезопасен.
"""

import math
import os
import queue
import struct
import tempfile
import threading
import time
import wave

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Line
from kivy.lang import Builder

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


# --- Тема / анимация ---------------------------------------------------------

RING_OUTER = (0.06, 0.12, 0.22)
RING_INNER = (0.09, 0.13, 0.24)

# Радиус и цвет анимируемого круга для каждой фазы дыхания.
PHASE_RADIUS = {"inhale": 60.0, "exhale": 25.0, "hold": 45.0, "idle": 40.0}
PHASE_COLOR = {
    "inhale": [0.0, 0.82, 1.0, 1.0],
    "exhale": [1.0, 0.42, 0.42, 1.0],
    "hold": [1.0, 0.85, 0.24, 1.0],
    "idle": [0.0, 0.82, 1.0, 1.0],
}
DEFAULT_COLOR = PHASE_COLOR["idle"]


KV = '''
BoxLayout:
    orientation: 'vertical'
    spacing: '4dp'
    padding: '8dp'
    canvas:
        Color:
            rgba: 0.1, 0.1, 0.18, 1
        Rectangle:
            pos: self.pos
            size: self.size

    # canvas with circle
    Widget:
        id: breath_widget
        size_hint_y: 0.22

    # display
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 0.2
        Label:
            id: stage_label
            text: 'Готов'
            font_size: '18dp'
            bold: True
            color: 0, 0.82, 1, 1
        Label:
            id: round_label
            text: 'Нажмите Старт'
            font_size: '11dp'
            color: 0.63, 0.63, 0.75, 1
        Label:
            id: time_label
            text: '00:00'
            font_size: '48dp'
            bold: True
            color: 1, 1, 1, 1
        Label:
            id: detail_label
            text: ''
            font_size: '11dp'
            color: 0.49, 0.78, 0.89, 1

    # progress
    BoxLayout:
        size_hint_y: 0.04
        padding: ['30dp', 0]
        ProgressBar:
            id: progress_bar
            max: 100
            value: 0
    Label:
        id: progress_text
        text: ''
        font_size: '9dp'
        color: 0.38, 0.38, 0.5, 1
        size_hint_y: 0.02

    # settings
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 0.38
        padding: '10dp'
        canvas:
            Color:
                rgba: 0.09, 0.13, 0.24, 1
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [10]
        Label:
            text: 'Настройки'
            font_size: '11dp'
            bold: True
            color: 0.88,0.88,0.88,1
            size_hint_y: 0.13
        BoxLayout:
            orientation: 'vertical'
            spacing: '6dp'
            BoxLayout:
                size_hint_y: None
                height: '28dp'
                spacing: '4dp'
                Label:
                    text: 'Раундов:'
                    color: 0.75, 0.75, 0.82, 1
                    size_hint_x: 0.38
                    halign: 'left'
                    text_size: self.size
                TextInput:
                    id: rounds_input
                    text: '3'
                    size_hint_x: 0.12
                    input_filter: 'int'
                    multiline: False
                Label:
                    text: 'Циклов/раунд:'
                    color: 0.75, 0.75, 0.82, 1
                    size_hint_x: 0.38
                    halign: 'left'
                    text_size: self.size
                TextInput:
                    id: cycles_input
                    text: '30'
                    size_hint_x: 0.12
                    input_filter: 'int'
                    multiline: False
            BoxLayout:
                size_hint_y: None
                height: '28dp'
                spacing: '4dp'
                Label:
                    text: 'Темп (сек):'
                    color: 0.75, 0.75, 0.82, 1
                    size_hint_x: 0.38
                    halign: 'left'
                    text_size: self.size
                TextInput:
                    id: tempo_input
                    text: '2.0'
                    size_hint_x: 0.12
                    input_filter: 'float'
                    multiline: False
                Label:
                    text: 'Задержка вдоха:'
                    color: 0.75, 0.75, 0.82, 1
                    size_hint_x: 0.38
                    halign: 'left'
                    text_size: self.size
                TextInput:
                    id: inhale_hold_input
                    text: '15'
                    size_hint_x: 0.12
                    input_filter: 'int'
                    multiline: False
            BoxLayout:
                size_hint_y: None
                height: '28dp'
                spacing: '4dp'
                Label:
                    text: 'Задержки выдоха:'
                    color: 0.75, 0.75, 0.82, 1
                    size_hint_x: 0.38
                    halign: 'left'
                    text_size: self.size
                TextInput:
                    id: exhale_holds_input
                    text: '30,60,90'
                    size_hint_x: 0.62
                    multiline: False
            BoxLayout:
                size_hint_y: 0.2
                spacing: '8dp'
                BoxLayout:
                    spacing: '4dp'
                    CheckBox:
                        id: metronome_check
                        active: True
                    Label:
                        text: 'Метроном'
                        color: 0.75, 0.75, 0.82, 1
                BoxLayout:
                    spacing: '4dp'
                    CheckBox:
                        id: tts_check
                        active: True
                    Label:
                        text: 'Голос'
                        color: 0.75, 0.75, 0.82, 1
            BoxLayout:
                size_hint_y: 0.15
                spacing: '4dp'
                Label:
                    text: 'Скорость речи:'
                    color: 0.75, 0.75, 0.82, 1
                TextInput:
                    id: speech_rate_input
                    text: '180'
                    size_hint_x: 0.12
                    input_filter: 'int'
                    multiline: False

    # buttons
    BoxLayout:
        size_hint_y: 0.08
        spacing: '8dp'
        Button:
            text: 'Старт'
            background_color: 0.06,0.2,0.38,1
            color: 1,1,1,1
            font_size: '14dp'
            bold: True
            on_press: app.start()
        Button:
            text: 'Стоп'
            background_color: 0.29,0.1,0.1,1
            color: 1,1,1,1
            font_size: '14dp'
            bold: True
            on_press: app.stop()
'''


def _make_beep_file(directory=None):
    """Однократно генерирует короткий WAV-щелчок для метронома (без ассетов).

    directory: куда писать. На Android temp-каталог может быть недоступен —
    туда передаём App.user_data_dir (гарантированно доступен на запись).
    """
    directory = directory or tempfile.gettempdir()
    path = os.path.join(directory, "breath_metronome.wav")
    if os.path.exists(path):
        return path
    framerate, duration, freq = 44100, 0.06, 880.0
    frames = int(framerate * duration)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(framerate)
        for i in range(frames):
            fade = 1.0 - i / frames            # плавное затухание — без «клика»
            amp = 0.5 * fade
            sample = int(amp * 32767 * math.sin(2 * math.pi * freq * i / framerate))
            w.writeframesraw(struct.pack("<h", sample))
    return path


class BreathApp(App):
    title = "Вим Хоф"

    # -- Жизненный цикл -------------------------------------------------------

    def build(self):
        self.root_widget = Builder.load_string(KV)
        self.breath_widget = self.root_widget.ids.breath_widget

        self.running = False
        self.stop_flag = False

        # Анимация круга (управляется только из главного потока).
        self.radius = PHASE_RADIUS["idle"]
        self.target_radius = PHASE_RADIUS["idle"]
        self.phase = "idle"
        self.color = list(DEFAULT_COLOR)
        self._anim_event = None

        # Метроном.
        self._beep_sound = None
        try:
            self._beep_sound = SoundLoader.load(_make_beep_file(self.user_data_dir))
        except Exception as ex:          # аудио может быть недоступно — не критично
            print(f"Метроном недоступен: {ex}")

        # TTS: единственный рабочий поток с очередью — pyttsx3 не переносит
        # параллельные вызовы runAndWait().
        self.tts_engine = None
        self.tts_ready = False
        self._tts_queue = queue.Queue()
        self._tts_stop = threading.Event()
        if PYTTSX3_AVAILABLE:
            self._init_tts()

        self.breath_widget.bind(pos=self._on_layout, size=self._on_layout)
        return self.root_widget

    def on_stop(self):
        self.stop_flag = True
        self._tts_stop.set()
        self._tts_queue.put(None)

    # -- Настройки ------------------------------------------------------------

    def _read_int(self, widget, default):
        try:
            return int(widget.text.strip())
        except (ValueError, AttributeError):
            return default

    def _read_float(self, widget, default):
        try:
            return float(widget.text.strip())
        except (ValueError, AttributeError):
            return default

    def _read_config(self):
        """Считываем настройки в главном потоке перед запуском практики."""
        ids = self.root_widget.ids
        rounds = max(1, self._read_int(ids.rounds_input, 3))
        exhale_holds = self._parse_holds(ids.exhale_holds_input.text, rounds)
        return {
            "rounds": rounds,
            "cycles": max(1, self._read_int(ids.cycles_input, 30)),
            "tempo": max(0.2, self._read_float(ids.tempo_input, 2.0)),
            "inhale_hold": max(1, self._read_int(ids.inhale_hold_input, 15)),
            "exhale_holds": exhale_holds,
            "metronome": ids.metronome_check.active,
        }

    @staticmethod
    def _parse_holds(text, rounds):
        """'30,60,90' -> [30, 60, 90]; недостающие раунды берут последнее число."""
        parts = []
        for chunk in text.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                parts.append(int(chunk))
            except ValueError:
                continue
        if not parts:
            parts = [30]
        return [parts[i] if i < len(parts) else parts[-1] for i in range(rounds)]

    # -- TTS ------------------------------------------------------------------

    def _init_tts(self):
        def worker():
            try:
                engine = pyttsx3.init(driverName="sapi5")
                engine.setProperty("rate", 180)
                engine.setProperty("volume", 0.8)
                for voice in engine.getProperty("voices"):
                    try:
                        if "russian" in voice.name.lower():
                            engine.setProperty("voice", voice.id)
                            break
                    except Exception:
                        continue
                self.tts_engine = engine
                self.tts_ready = True
                self._tts_loop()
            except Exception as ex:
                print(f"TTS: {ex}")

        threading.Thread(target=worker, daemon=True).start()

    def _tts_loop(self):
        while not self._tts_stop.is_set():
            try:
                text = self._tts_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if text is None:
                break
            try:
                self.tts_engine.setProperty(
                    "rate", self._read_int(self.root_widget.ids.speech_rate_input, 180)
                )
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as ex:
                print(f"TTS speak: {ex}")

    def speak(self, text):
        if not self.tts_ready or not self.root_widget.ids.tts_check.active:
            return
        self._tts_queue.put(text)

    def beep(self):
        if self._beep_sound is None:
            return
        Clock.schedule_once(lambda _dt: self._play_beep(), 0)

    def _play_beep(self):
        try:
            self._beep_sound.stop()
            self._beep_sound.play()
        except Exception:
            pass

    # -- Анимация круга (только главный поток) --------------------------------

    def set_phase(self, phase):
        """Может вызываться из фонового потока — переносим в главный."""
        Clock.schedule_once(lambda _dt: self._apply_phase(phase), 0)

    def _apply_phase(self, phase):
        self.phase = phase
        self.target_radius = PHASE_RADIUS.get(phase, PHASE_RADIUS["idle"])
        self.color = PHASE_COLOR.get(phase, DEFAULT_COLOR)
        if self._anim_event is None:
            self._anim_event = Clock.schedule_interval(self._animate_step, 0.03)

    def _animate_step(self, _dt):
        diff = self.target_radius - self.radius
        if abs(diff) <= 0.5:
            self.radius = self.target_radius
            self._redraw()
            self._anim_event = None
            return False          # достигли цели — останавливаем перерисовку
        self.radius += diff * 0.08
        self._redraw()

    def _on_layout(self, *_args):
        self._redraw()

    def _redraw(self):
        cx, cy = self.breath_widget.center_x, self.breath_widget.center_y
        canvas = self.breath_widget.canvas
        canvas.clear()
        with canvas:
            Color(*RING_OUTER)
            Line(circle=(cx, cy, 75), width=1)
            Color(*RING_INNER)
            Line(circle=(cx, cy, 70), width=2)
            Color(*self.color)
            Line(circle=(cx, cy, self.radius), width=4)

    # -- Обновление дисплея (только главный поток) ----------------------------

    def update_display(self, stage, round_text, seconds, detail="", pct=0):
        Clock.schedule_once(
            lambda _dt: self._set_display(stage, round_text, seconds, detail, pct), 0
        )

    def _set_display(self, stage, round_text, seconds, detail, pct):
        ids = self.root_widget.ids
        ids.stage_label.text = stage
        ids.round_label.text = round_text
        minutes, secs = divmod(max(int(seconds), 0), 60)
        ids.time_label.text = f"{minutes:02d}:{secs:02d}"
        ids.detail_label.text = detail
        if pct > 0:
            ids.progress_bar.value = pct
            ids.progress_text.text = f"{int(pct)}%"
        else:
            ids.progress_bar.value = 0
            ids.progress_text.text = ""

    # -- Практика (фоновый поток) ---------------------------------------------

    def start(self):
        if self.running:
            return
        self.running = True
        self.stop_flag = False
        config = self._read_config()
        self.update_display("", "", 0)
        threading.Thread(target=self._run, args=(config,), daemon=True).start()

    def stop(self):
        self.stop_flag = True
        self.running = False

    def _countdown(self, seconds, stage, round_text, detail_fn=None,
                   start_pct=0, end_pct=100, phase="hold"):
        total = int(seconds)
        self.set_phase(phase)
        for remaining in range(total, 0, -1):
            if self.stop_flag:
                return False
            pct = start_pct + (end_pct - start_pct) * (total - remaining) / total if total else 0
            detail = detail_fn(remaining) if detail_fn else ""
            self.update_display(stage, round_text, remaining, detail, pct)
            time.sleep(1)
        return True

    def _run(self, cfg):
        rounds = cfg["rounds"]
        cycles = cfg["cycles"]
        tempo = cfg["tempo"]
        exhale_holds = cfg["exhale_holds"]
        inhale_hold = cfg["inhale_hold"]
        metronome = cfg["metronome"]
        total_cycles = rounds * cycles
        done_cycles = 0

        for i in range(3, 0, -1):
            if self.stop_flag:
                break
            self.update_display(f"Старт через {i}...", "", 0, "Приготовьтесь")
            self.speak(str(i))
            time.sleep(1)

        for rnd in range(1, rounds + 1):
            if self.stop_flag:
                break
            round_text = f"Раунд {rnd} из {rounds}"
            self.speak(f"Раунд {rnd}, начали")

            for cycle in range(1, cycles + 1):
                if self.stop_flag:
                    break
                pct = done_cycles / total_cycles * 100 if total_cycles else 0
                self.update_display("Вдох", round_text, 0, f"Цикл {cycle} из {cycles}", pct)
                self.set_phase("inhale")
                if metronome:
                    self.beep()
                if cycle == 1 and rnd == 1:
                    self.speak("Вдох")
                time.sleep(tempo / 2)

                if self.stop_flag:
                    break
                pct = (done_cycles + 0.5) / total_cycles * 100 if total_cycles else 0
                self.update_display("Выдох", round_text, 0, f"Цикл {cycle} из {cycles}", pct)
                self.set_phase("exhale")
                if metronome:
                    self.beep()
                if cycle == cycles:
                    self.speak("Выдох")
                time.sleep(tempo / 2)
                done_cycles += 1

            if self.stop_flag:
                break

            # Задержка на выдохе.
            hold_secs = exhale_holds[rnd - 1]
            base_pct = done_cycles / total_cycles * 100 if total_cycles else 0
            ok = self._countdown(
                hold_secs, "Задержка на выдохе", round_text,
                lambda r: "Не дышим" if r > 3 else "Почти готов",
                base_pct, base_pct + 5, "hold",
            )
            if not ok:
                break

            # Глубокий вдох + задержка на вдохе.
            self.speak("Глубокий вдох")
            self.update_display("Глубокий вдох", round_text, 0, "Наберите полные лёгкие")
            self.set_phase("inhale")
            time.sleep(1)
            if self.stop_flag:
                break

            self.speak("Задержите дыхание")
            base_pct = (done_cycles + 1) / total_cycles * 100 if total_cycles else 0
            ok = self._countdown(
                inhale_hold, "Задержка на вдохе", round_text,
                lambda r: "Держим" if r > 3 else "Сейчас выдох",
                base_pct, 100, "hold",
            )
            if not ok:
                break
            self.speak("Выдох")

        if not self.stop_flag:
            self.update_display("Практика завершена!", "", 0, "Отличная работа!", 100)
            self.speak("Практика завершена, отличная работа")
        else:
            self.update_display("Остановлено", "", 0, "")
            self.speak("Практика остановлена")
        self.set_phase("idle")
        self.running = False


if __name__ == '__main__':
    BreathApp().run()
