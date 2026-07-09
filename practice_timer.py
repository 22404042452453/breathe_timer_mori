import tkinter as tk
from tkinter import ttk
import time
import math
import queue
import threading

# Попытка импорта pyttsx3 (голосовое сопровождение)
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


class PracticeTimer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Таймер практики")
        self.geometry("400x480")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")

        self.total_seconds = tk.IntVar(value=300)
        self.remaining = 0
        self.session_total = 0          # длительность сессии — для стабильного прогресса
        self.running = False
        self.after_id = None

        # --- Инициализация TTS ---
        self.tts_engine = None
        self.tts_ready = False
        self._tts_queue = queue.Queue()
        self._tts_stop = threading.Event()
        self._init_tts()

        # --- Стилизация ---
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TLabel", background="#1a1a2e", foreground="#e0e0e0",
                        font=("Segoe UI", 10))
        style.configure("TLabelframe", background="#1a1a2e", foreground="#e0e0e0",
                        font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe.Label", background="#1a1a2e", foreground="#e0e0e0",
                        font=("Segoe UI", 10, "bold"))
        style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=8)
        style.configure("TSpinbox", font=("Segoe UI", 10), padding=2)
        style.configure("TFrame", background="#1a1a2e")
        style.map("TButton",
                  background=[("active", "#0f3460"), ("!active", "#16213e")],
                  foreground=[("active", "#ffffff"), ("!active", "#e0e0e0")])

        # --- Canvas для анимации ---
        self.canvas_frame = tk.Frame(self, bg="#1a1a2e", height=160)
        self.canvas_frame.pack(fill="x", padx=10, pady=(10, 0))

        self.canvas = tk.Canvas(self.canvas_frame, width=380, height=150,
                                bg="#1a1a2e", highlightthickness=0)
        self.canvas.pack()

        self._draw_canvas()

        # --- Дисплей ---
        display_frame = tk.Frame(self, bg="#1a1a2e")
        display_frame.pack(fill="both", expand=True, padx=15, pady=(0, 5))

        self.status_label = tk.Label(display_frame, text="Готов к старту",
                                      font=("Segoe UI", 16, "bold"),
                                      fg="#00d2ff", bg="#1a1a2e")
        self.status_label.pack(pady=(5, 0))

        self.display = tk.Label(display_frame, text="00:00",
                                 font=("Segoe UI", 52, "bold"),
                                 fg="#ffffff", bg="#1a1a2e")
        self.display.pack(pady=5)

        # --- Прогресс-бар ---
        progress_frame = tk.Frame(self, bg="#1a1a2e")
        progress_frame.pack(fill="x", padx=20, pady=(0, 5))

        self.progress = ttk.Progressbar(progress_frame, length=360, mode="determinate",
                                         style="TProgressbar")
        self.progress.pack()

        style.configure("TProgressbar", thickness=10, troughcolor="#16213e",
                        background="#00d2ff", bordercolor="#1a1a2e",
                        lightcolor="#00d2ff", darkcolor="#0f3460")

        self.progress_label = tk.Label(progress_frame, text="",
                                        font=("Segoe UI", 9),
                                        fg="#606080", bg="#1a1a2e")
        self.progress_label.pack(pady=(2, 0))

        # --- Настройки ---
        settings = ttk.LabelFrame(self, text="Настройки", padding=12)
        settings.pack(fill="x", padx=15, pady=5)

        ttk.Label(settings, text="Минуты:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.min_entry = ttk.Spinbox(settings, from_=0, to=180, width=5)
        self.min_entry.set(5)
        self.min_entry.grid(row=0, column=1, padx=(0, 15))

        ttk.Label(settings, text="Секунды:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.sec_entry = ttk.Spinbox(settings, from_=0, to=59, width=5)
        self.sec_entry.set(0)
        self.sec_entry.grid(row=0, column=3)

        # TTS чекбокс
        self.tts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings, text="Голосовое сопровождение (pyttsx3)",
                         variable=self.tts_var,
                         command=self._toggle_tts).grid(row=1, column=0, columnspan=4, sticky="w", pady=(5, 0))

        if not PYTTSX3_AVAILABLE:
            self.tts_var.set(False)
            ttk.Label(settings, text="pyttsx3 не установлен",
                      foreground="#ff6b6b", background="#1a1a2e",
                      font=("Segoe UI", 8)).grid(row=2, column=0, columnspan=4, sticky="w", padx=(10, 0))

        # --- Кнопки ---
        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(fill="x", padx=15, pady=(5, 15))

        ttk.Button(btn_frame, text="▶ Старт", command=self.start).pack(side="left", expand=True, fill="x", padx=3)
        ttk.Button(btn_frame, text="⏸ Пауза", command=self.pause).pack(side="left", expand=True, fill="x", padx=3)
        ttk.Button(btn_frame, text="↺ Сброс", command=self.reset).pack(side="left", expand=True, fill="x", padx=3)

        # --- Анимация ---
        self._anim_after_id = None
        self._anim_angle = 0
        self._start_idle_animation()

        self.reset()

    # ========== TTS ==========

    def _init_tts(self):
        if not PYTTSX3_AVAILABLE:
            self.tts_ready = False
            return

        def _init():
            try:
                engine = pyttsx3.init(driverName="sapi5")
                engine.setProperty("rate", 180)
                engine.setProperty("volume", 0.8)
                voices = engine.getProperty("voices")
                for v in voices:
                    if "russian" in v.name.lower() or (hasattr(v, "languages") and v.languages and "ru" in v.languages[0].lower()):
                        engine.setProperty("voice", v.id)
                        break
                self.tts_engine = engine
                self.tts_ready = True
                self._tts_loop()
            except Exception as e:
                print(f"TTS init error: {e}")
                self.tts_ready = False

        threading.Thread(target=_init, daemon=True).start()

    def _tts_loop(self):
        # Один рабочий поток сериализует речь: runAndWait() нельзя звать
        # из нескольких потоков одновременно.
        while not self._tts_stop.is_set():
            try:
                text = self._tts_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if text is None:
                break
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception:
                pass

    def _toggle_tts(self):
        if self.tts_var.get() and not self.tts_ready and PYTTSX3_AVAILABLE:
            self._init_tts()

    def speak(self, text):
        if not self.tts_var.get() or not self.tts_ready or self.tts_engine is None:
            return
        self._tts_queue.put(text)

    # ========== Canvas ==========

    def _draw_canvas(self):
        self.canvas.delete("all")
        cx, cy = 190, 75
        # Внешний круг
        self.canvas.create_oval(cx - 60, cy - 60, cx + 60, cy + 60,
                                 outline="#16213e", width=2, tags="bg_circle")
        # Внутренний круг (анимируемый)
        self._anim_circle = self.canvas.create_oval(
            cx - 35, cy - 35, cx + 35, cy + 35,
            outline="#00d2ff", width=3, tags="anim_circle"
        )
        # Текст статуса на канве
        self._canvas_status = self.canvas.create_text(cx, cy, text="⏱",
                                                       font=("Segoe UI", 20),
                                                       fill="#606080", tags="canvas_status")

    def _start_idle_animation(self):
        cx, cy = 190, 75
        self._idle_pulse(cx, cy)

    def _idle_pulse(self, cx, cy):
        if self.running:
            return
        pulse = math.sin(time.time() * 2) * 5
        r = 35 + pulse
        self.canvas.coords(self._anim_circle, cx - r, cy - r, cx + r, cy + r)
        self.canvas.itemconfig(self._anim_circle, outline="#00d2ff" if pulse > 0 else "#0f3460")
        self._anim_after_id = self.canvas.after(50, lambda: self._idle_pulse(cx, cy))

    def _animate_running(self, cx, cy):
        if not self.running:
            return
        # Пульсация во время работы
        pulse = math.sin(time.time() * 3) * 8
        r = 35 + pulse
        self.canvas.coords(self._anim_circle, cx - r, cy - r, cx + r, cy + r)
        self.canvas.itemconfig(self._anim_circle, outline="#ffd93d" if pulse > 0 else "#ff6b6b")
        self._anim_after_id = self.canvas.after(50, lambda: self._animate_running(cx, cy))

    def _stop_animation(self):
        if self._anim_after_id:
            self.canvas.after_cancel(self._anim_after_id)
            self._anim_after_id = None

    # ========== Логика таймера ==========

    @staticmethod
    def _to_int(value):
        try:
            return int(str(value).strip() or 0)
        except ValueError:
            return 0

    def set_from_inputs(self):
        m = self._to_int(self.min_entry.get())
        s = self._to_int(self.sec_entry.get())
        self.remaining = m * 60 + s
        self.session_total = self.remaining     # фиксируем базу прогресса на старте
        self._update_display()

    def _update_display(self):
        m, s = divmod(max(self.remaining, 0), 60)
        self.display.config(text=f"{m:02d}:{s:02d}")

        # Прогресс считаем от зафиксированной длительности сессии,
        # чтобы правка полей во время отсчёта не дёргала шкалу.
        total = self.session_total
        if total > 0:
            pct = (total - self.remaining) / total * 100
            self.progress["value"] = pct
            self.progress_label.config(text=f"{int(pct)}%")
        else:
            self.progress["value"] = 0
            self.progress_label.config(text="")

    def tick(self):
        if self.running and self.remaining > 0:
            self.remaining -= 1
            self._update_display()

            # Голосовые подсказки на ключевых точках
            if self.remaining in [60, 30, 10, 5, 3, 2, 1]:
                if self.remaining >= 60:
                    self.speak(f"Осталась {self.remaining // 60} минута")
                elif self.remaining == 1:
                    self.speak("Одна секунда")
                else:
                    self.speak(str(self.remaining))

            self.after_id = self.after(1000, self.tick)
        elif self.remaining <= 0:
            self.running = False
            self._stop_animation()
            self.display.config(text="⏰ Время!")
            self.status_label.config(text="✅ Время вышло")
            self.progress["value"] = 100
            self.progress_label.config(text="100%")
            self.bell()
            self.speak("Время вышло")
            cx, cy = 190, 75
            self._idle_pulse(cx, cy)

    def start(self):
        if not self.running:
            if self.remaining <= 0:
                self.set_from_inputs()
            if self.remaining <= 0:
                return
            self.running = True
            self.status_label.config(text="▶ Выполняется")
            self._stop_animation()
            cx, cy = 190, 75
            self._animate_running(cx, cy)
            self.speak("Старт")
            self.tick()

    def pause(self):
        if self.running:
            self.running = False
            self.status_label.config(text="⏸ Пауза")
            self.speak("Пауза")
            if self.after_id:
                self.after_cancel(self.after_id)
            self._stop_animation()
            cx, cy = 190, 75
            self._idle_pulse(cx, cy)

    def reset(self):
        self.pause()
        self.set_from_inputs()
        self.status_label.config(text="Готов к старту")
        self.progress["value"] = 0
        self.progress_label.config(text="")
        self._stop_animation()
        cx, cy = 190, 75
        self._idle_pulse(cx, cy)

    def destroy(self):
        self._stop_animation()
        self._tts_stop.set()
        self._tts_queue.put(None)
        if self.tts_engine is not None:
            try:
                self.tts_engine.stop()
            except Exception:
                pass
        super().destroy()


if __name__ == "__main__":
    app = PracticeTimer()
    app.mainloop()