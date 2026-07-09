import tkinter as tk
from tkinter import ttk
import threading
import queue
import time
import math

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

class BreathTimer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Дыхательная практика — Вим Хоф")
        self.geometry("480x580+200+50")
        self.configure(bg="#1a1a2e")

        self.running = False
        self.stop_flag = False

        self._anim_radius = 40
        self._anim_target = 40
        self._anim_color = "#00d2ff"
        self._anim_phase = "idle"
        self._anim_after_id = None
        self._phase_text = None
        self._breath_circle = None

        self.tts_engine = None
        self.tts_ready = False
        self._tts_queue = queue.Queue()
        self._tts_stop = threading.Event()
        self._tts_init_started = False
        self._init_tts()

        # Фоновый поток практики не трогает виджеты напрямую (tkinter не
        # потокобезопасен) — кладёт колбэки сюда, а главный поток их выполняет.
        self._ui_queue = queue.Queue()
        self._ui_after_id = None

        self._setup_styles()
        self._build_ui()
        self._start_idle_animation()
        self._poll_ui()

    def _poll_ui(self):
        try:
            while True:
                fn = self._ui_queue.get_nowait()
                try:
                    fn()
                except Exception as ex:
                    print(f"UI update: {ex}")
        except queue.Empty:
            pass
        self._ui_after_id = self.after(30, self._poll_ui)

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", thickness=8, troughcolor="#16213e",
                        background="#00d2ff")

    def _build_ui(self):
        # === Canvas ===
        c = tk.Canvas(self, width=460, height=140, bg="#1a1a2e", highlightthickness=0)
        c.pack(pady=(8, 0))
        self._draw_c(c)

        # === Display ===
        f = tk.Frame(self, bg="#1a1a2e")
        f.pack(fill="x", padx=15, pady=(2, 0))

        self.stage = tk.Label(f, text="Готов к старту", font=("Segoe UI", 16, "bold"),
                               fg="#00d2ff", bg="#1a1a2e")
        self.stage.pack(pady=(2, 0))

        self.round = tk.Label(f, text="Нажмите Старт", font=("Segoe UI", 10),
                               fg="#a0a0c0", bg="#1a1a2e")
        self.round.pack()

        self.timer = tk.Label(f, text="00:00", font=("Segoe UI", 42, "bold"),
                               fg="#ffffff", bg="#1a1a2e")
        self.timer.pack(pady=(0, 0))

        self.detail = tk.Label(f, text="", font=("Segoe UI", 11),
                                fg="#7ec8e3", bg="#1a1a2e")
        self.detail.pack()

        # === Progress ===
        p = tk.Frame(self, bg="#1a1a2e")
        p.pack(fill="x", padx=20, pady=(4, 0))

        self.prog = ttk.Progressbar(p, mode="determinate")
        self.prog.pack(fill="x")

        self.prog_lbl = tk.Label(p, text="", font=("Segoe UI", 8),
                                  fg="#606080", bg="#1a1a2e")
        self.prog_lbl.pack(pady=(1, 0))

        # === Settings ===
        card = tk.Frame(self, bg="#16213e", highlightthickness=0)
        card.pack(fill="x", padx=15, pady=(4, 0))

        tk.Label(card, text="⚙ Настройки", font=("Segoe UI", 10, "bold"),
                 fg="#e0e0e0", bg="#16213e").pack(anchor="w", padx=12, pady=(6, 2))

        grid = tk.Frame(card, bg="#16213e")
        grid.pack(padx=12, pady=(0, 8))

        # Variables
        self.rnd = tk.IntVar(value=3)
        self.cyc = tk.IntVar(value=30)
        self.tem = tk.DoubleVar(value=2.0)
        self.hold_i = tk.IntVar(value=15)
        self.holds_s = tk.StringVar(value="30,60,90")
        self.met = tk.BooleanVar(value=True)
        self.tts_v = tk.BooleanVar(value=True)
        self.spr = tk.IntVar(value=180)

        if not PYTTSX3_AVAILABLE:
            self.tts_v.set(False)

        def row(r, c, txt, var, fr, to, inc=1, w=4):
            tk.Label(grid, text=txt, font=("Segoe UI", 9), fg="#c0c0d0",
                     bg="#16213e").grid(row=r, column=c, sticky="w", padx=(0, 3), pady=1)
            ttk.Spinbox(grid, from_=fr, to=to, increment=inc,
                        textvariable=var, width=w).grid(row=r, column=c+1, sticky="w", pady=1)

        row(0, 0, "Раундов:", self.rnd, 1, 10)
        row(0, 2, "Циклов/раунд:", self.cyc, 5, 60)
        row(1, 0, "Темп (сек):", self.tem, 1.0, 5.0, 0.5)
        row(1, 2, "Задержка вдоха:", self.hold_i, 5, 60)

        tk.Label(grid, text="Задержки выдоха:", font=("Segoe UI", 9),
                 fg="#c0c0d0", bg="#16213e").grid(row=2, column=0, sticky="w", padx=(0, 3), pady=1)
        ttk.Entry(grid, textvariable=self.holds_s, width=10).grid(row=2, column=1, sticky="w", pady=1)

        r3 = tk.Frame(grid, bg="#16213e")
        r3.grid(row=3, column=0, columnspan=4, sticky="w", pady=2)
        tk.Checkbutton(r3, text="🔊 Метроном", variable=self.met,
                       font=("Segoe UI", 9), fg="#c0c0d0", bg="#16213e",
                       selectcolor="#16213e", activebackground="#16213e",
                       highlightthickness=0, bd=0).pack(side="left", padx=(0, 12))
        tk.Checkbutton(r3, text="🗣 Голос", variable=self.tts_v,
                       font=("Segoe UI", 9), fg="#c0c0d0", bg="#16213e",
                       selectcolor="#16213e", activebackground="#16213e",
                       highlightthickness=0, bd=0,
                       command=self._toggle_tts).pack(side="left")

        row(4, 0, "Скорость речи:", self.spr, 100, 300, 10)

        if not PYTTSX3_AVAILABLE:
            tk.Label(grid, text="⚠ pyttsx3 не установлен",
                     font=("Segoe UI", 7), fg="#ff6b6b", bg="#16213e").grid(
                         row=5, column=0, columnspan=4, sticky="w")

        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(3, weight=1)

        # === Buttons ===
        bf = tk.Frame(self, bg="#1a1a2e")
        bf.pack(fill="x", padx=15, pady=(6, 12))

        self.start_btn = tk.Button(bf, text="▶ Старт", command=self.start,
                                    bg="#0f3460", fg="white",
                                    font=("Segoe UI", 12, "bold"),
                                    relief="flat", bd=0, height=1,
                                    activebackground="#1a5276")
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.stop_btn = tk.Button(bf, text="■ Стоп", command=self.stop,
                                   bg="#4a1a1a", fg="white",
                                   font=("Segoe UI", 12, "bold"),
                                   relief="flat", bd=0, height=1,
                                   activebackground="#6b2a2a")
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))

    def _draw_c(self, c):
        cx, cy = 230, 70
        c.create_oval(cx-70, cy-70, cx+70, cy+70, outline="#16213e", width=2)
        self._phase = c.create_text(cx, cy, text="🌀", font=("Segoe UI", 10, "bold"),
                                     fill="#00d2ff")
        self._circle = c.create_oval(cx-40, cy-40, cx+40, cy+40, outline="#00d2ff", width=4)
        self._c = c
        self._cx, self._cy = cx, cy

    def _animate(self, phase):
        # Может вызываться из фонового потока практики — переносим в главный.
        self._ui_queue.put(lambda: self._animate_main(phase))

    def _animate_main(self, phase):
        targets = {"inhale": 60, "exhale": 25, "hold": 45, "idle": 40}
        colors = {"inhale": "#00d2ff", "exhale": "#ff6b6b", "hold": "#ffd93d", "idle": "#00d2ff"}
        self._anim_target = targets.get(phase, 40)
        self._anim_color = colors.get(phase, "#00d2ff")
        self._anim_phase = phase
        if self._anim_after_id:
            self._c.after_cancel(self._anim_after_id)
            self._anim_after_id = None
        self._smooth()

    def _smooth(self):
        diff = self._anim_target - self._anim_radius
        if abs(diff) > 1:
            self._anim_radius += diff * 0.08
        else:
            self._anim_radius = self._anim_target
        r = self._anim_radius
        self._c.coords(self._circle, self._cx-r, self._cy-r, self._cx+r, self._cy+r)
        self._c.itemconfig(self._circle, outline=self._anim_color)

        labels = {"inhale": ("🌬 ВДОХ", "#00d2ff"), "exhale": ("💨 ВЫДОХ", "#ff6b6b"),
                  "hold": ("🧘 ЗАДЕРЖКА", "#ffd93d")}
        if self._anim_phase in labels:
            t, cl = labels[self._anim_phase]
            self._c.itemconfig(self._phase, text=t, fill=cl)
        else:
            self._c.itemconfig(self._phase, text="🌀", fill="#606080")

        if self._anim_phase != "idle" or abs(diff) > 1:
            self._anim_after_id = self._c.after(30, self._smooth)
        else:
            self._idle_pulse()

    def _idle_pulse(self):
        if self.running:
            return
        p = math.sin(time.time() * 2) * 3
        r = 40 + p
        self._c.coords(self._circle, self._cx-r, self._cy-r, self._cx+r, self._cy+r)
        self._c.itemconfig(self._circle, outline="#00d2ff" if p > 0 else "#0f3460")
        self._anim_after_id = self._c.after(50, self._idle_pulse)

    def _start_idle_animation(self):
        self._idle_pulse()

    def _stop_anim(self):
        if self._anim_after_id:
            self._c.after_cancel(self._anim_after_id)
            self._anim_after_id = None

    # ==== TTS ====
    def _init_tts(self):
        if not PYTTSX3_AVAILABLE or self._tts_init_started:
            return
        self._tts_init_started = True
        def _i():
            try:
                e = pyttsx3.init(driverName="sapi5")
                e.setProperty("rate", 180)
                e.setProperty("volume", 0.8)
                for v in e.getProperty("voices"):
                    try:
                        if "russian" in v.name.lower():
                            e.setProperty("voice", v.id)
                            break
                    except: continue
                self.tts_engine = e
                self.tts_ready = True
                self._tts_loop()
            except Exception as ex:
                print(f"TTS: {ex}")
                self._tts_init_started = False
        threading.Thread(target=_i, daemon=True).start()

    def _tts_loop(self):
        # Single worker thread: serializes all speech so only one
        # runAndWait() loop is ever active (pyttsx3 restriction).
        while not self._tts_stop.is_set():
            try:
                text = self._tts_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if text is None:
                self._tts_queue.task_done()
                break
            try:
                self.tts_engine.setProperty("rate", self.spr.get())
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as ex:
                print(f"TTS speak: {ex}")
            self._tts_queue.task_done()

    def _toggle_tts(self):
        if self.tts_v.get() and not self.tts_ready and PYTTSX3_AVAILABLE:
            self._init_tts()

    def speak(self, text):
        if not self.tts_v.get() or not self.tts_ready or self.tts_engine is None:
            return
        self._tts_queue.put(text)

    # ==== Logic ====
    def beep(self):
        # run_practice работает в фоновом потоке; звонок — только из главного.
        self._ui_queue.put(self._beep)

    def _beep(self):
        try: self.bell()
        except: pass

    def parse_holds(self):
        raw = [x.strip() for x in self.holds_s.get().split(",") if x.strip()]
        nums = []
        for x in raw:
            try:
                nums.append(int(x))
            except ValueError:
                continue          # игнорируем мусор вместо падения практики
        if not nums:
            nums = [30]
        return [nums[i] if i < len(nums) else nums[-1] for i in range(self.rnd.get())]

    def set_d(self, stage, round_text, secs, detail="", pct=0):
        # Маршалим обновление виджетов в главный поток (tkinter не потокобезопасен).
        self._ui_queue.put(lambda: self._set_d(stage, round_text, secs, detail, pct))

    def _set_d(self, stage, round_text, secs, detail, pct):
        self.stage.config(text=stage)
        self.round.config(text=round_text)
        m, s = divmod(max(int(secs), 0), 60)
        self.timer.config(text=f"{m:02d}:{s:02d}")
        self.detail.config(text=detail)
        if pct > 0:
            self.prog["value"] = pct
            self.prog_lbl.config(text=f"{int(pct)}%")
        else:
            self.prog["value"] = 0
            self.prog_lbl.config(text="")

    def countdown(self, secs, stage, rt, dfn=None, sp=0, ep=100, phase="hold"):
        total = int(secs)
        self._animate(phase)
        for r in range(total, 0, -1):
            if self.stop_flag: return False
            d = dfn(r) if dfn else ""
            pct = sp + (ep - sp) * (total - r) / total if total else 0
            self.set_d(stage, rt, r, d, pct)
            time.sleep(1)
        return True

    def run_practice(self, cfg):
        rn = cfg["rounds"]
        cy = cfg["cycles"]
        tm = cfg["tempo"]
        hd = cfg["holds"]
        ih = cfg["inhale_hold"]
        mt = cfg["metronome"]
        tw = rn * cy
        td = 0

        for i in range(3, 0, -1):
            if self.stop_flag: break
            self.set_d(f"Старт через {i}...", "", 0, "Приготовьтесь")
            self.speak(str(i))
            time.sleep(1)

        for r in range(1, rn + 1):
            if self.stop_flag: break
            rt = f"Раунд {r} из {rn}"
            self.speak(f"Раунд {r}, начали")
            for c in range(1, cy + 1):
                if self.stop_flag: break
                pct = td / tw * 100 if tw else 0
                self.set_d("Вдох", rt, 0, f"Цикл {c} из {cy}", pct)
                self._animate("inhale")
                if mt: self.beep()
                if c == 1 and r == 1: self.speak("Вдох")
                time.sleep(tm / 2)
                if self.stop_flag: break
                pct = (td + 0.5) / tw * 100 if tw else 0
                self.set_d("Выдох", rt, 0, f"Цикл {c} из {cy}", pct)
                self._animate("exhale")
                if mt: self.beep()
                if c == cy: self.speak("Выдох")
                time.sleep(tm / 2)
                td += 1
            if self.stop_flag: break
            hs = hd[r - 1]
            self.beep()
            ps = td / tw * 100 if tw else 0
            ok = self.countdown(hs, "Задержка на выдохе", rt,
                                lambda r: "⏳ Не дышим" if r > 3 else "⚡ Почти готов",
                                ps, ps + 5, "hold")
            if not ok: break
            self.speak("Глубокий вдох")
            self.beep()
            self.set_d("Глубокий вдох", rt, 0, "🌬 Наберите полные лёгкие")
            self._animate("inhale")
            time.sleep(1)
            self.speak("Задержите дыхание")
            ps = (td + 1) / tw * 100 if tw else 0
            ok = self.countdown(ih, "Задержка на вдохе", rt,
                                lambda r: "🧘 Держим" if r > 3 else "🔔 Сейчас выдох",
                                ps, 100, "hold")
            if not ok: break
            self.beep()
            self.speak("Выдох")

        self._stop_anim()
        if not self.stop_flag:
            self.set_d("✅ Практика завершена!", "", 0, "Отличная работа! 🎉", 100)
            self.speak("Практика завершена, отличная работа")
        else:
            self.set_d("⏹ Остановлено", "", 0, "")
            self.speak("Практика остановлена")
        self._animate("idle")
        self.running = False

    def _read_config(self):
        # Все настройки читаем в главном потоке — до запуска фонового потока.
        return {
            "rounds": self.rnd.get(),
            "cycles": self.cyc.get(),
            "tempo": self.tem.get(),
            "holds": self.parse_holds(),
            "inhale_hold": self.hold_i.get(),
            "metronome": self.met.get(),
        }

    def start(self):
        if self.running: return
        self.running = True
        self.stop_flag = False
        self.prog["value"] = 0
        self.prog_lbl.config(text="")
        cfg = self._read_config()
        threading.Thread(target=self.run_practice, args=(cfg,), daemon=True).start()

    def stop(self):
        self.stop_flag = True
        self.running = False
        self.prog["value"] = 0
        self.prog_lbl.config(text="")
        self._stop_anim()
        self._idle_pulse()

    def destroy(self):
        if self._ui_after_id:
            try: self.after_cancel(self._ui_after_id)
            except: pass
            self._ui_after_id = None
        self._stop_anim()
        self._tts_stop.set()
        if self._tts_queue is not None:
            self._tts_queue.put(None)
        if self.tts_engine:
            try: self.tts_engine.stop()
            except: pass
        super().destroy()

if __name__ == "__main__":
    BreathTimer().mainloop()