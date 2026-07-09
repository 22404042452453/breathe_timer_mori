
import tkinter as tk
from tkinter import ttk
import threading
import time
import sys

# Практика дыхания по методу Вима Хофа (озвучка "профессор Мориарти")
# 3 раунда:
#   1) N быстрых циклов вдох-выдох (метроном, по умолчанию 30 циклов, темп настраивается)
#   2) задержка дыхания на выдохе (30 / 60 / 90 сек по раундам, можно менять)
#   3) вдох + задержка на вдохе 15 сек

class BreathTimer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Дыхательная практика — таймер")
        self.geometry("420x460")
        self.resizable(False, False)

        self.running = False
        self.stop_flag = False

        # --- Настройки ---
        settings = ttk.LabelFrame(self, text="Настройки", padding=10)
        settings.pack(fill="x", padx=10, pady=10)

        ttk.Label(settings, text="Раундов:").grid(row=0, column=0, sticky="w")
        self.rounds_var = tk.IntVar(value=3)
        ttk.Spinbox(settings, from_=1, to=10, textvariable=self.rounds_var, width=5).grid(row=0, column=1)

        ttk.Label(settings, text="Циклов дыхания в раунде:").grid(row=1, column=0, sticky="w")
        self.cycles_var = tk.IntVar(value=30)
        ttk.Spinbox(settings, from_=5, to=60, textvariable=self.cycles_var, width=5).grid(row=1, column=1)

        ttk.Label(settings, text="Темп вдох/выдох (сек на цикл):").grid(row=2, column=0, sticky="w")
        self.tempo_var = tk.DoubleVar(value=2.0)
        ttk.Spinbox(settings, from_=1.0, to=5.0, increment=0.5, textvariable=self.tempo_var, width=5).grid(row=2, column=1)

        ttk.Label(settings, text="Задержки на выдохе по раундам (сек, через запятую):").grid(row=3, column=0, sticky="w")
        self.holds_var = tk.StringVar(value="30,60,90")
        ttk.Entry(settings, textvariable=self.holds_var, width=15).grid(row=3, column=1)

        ttk.Label(settings, text="Задержка на вдохе (сек):").grid(row=4, column=0, sticky="w")
        self.inhale_hold_var = tk.IntVar(value=15)
        ttk.Spinbox(settings, from_=5, to=60, textvariable=self.inhale_hold_var, width=5).grid(row=4, column=1)

        self.metronome_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings, text="Включить звуковой метроном на вдох/выдох",
                         variable=self.metronome_var).grid(row=5, column=0, columnspan=2, sticky="w", pady=(5,0))

        # --- Дисплей ---
        display_frame = ttk.Frame(self, padding=10)
        display_frame.pack(fill="both", expand=True)

        self.stage_label = ttk.Label(display_frame, text="Готов к старту", font=("Arial", 16))
        self.stage_label.pack(pady=(5, 0))

        self.round_label = ttk.Label(display_frame, text="", font=("Arial", 12))
        self.round_label.pack()

        self.timer_label = ttk.Label(display_frame, text="00:00", font=("Arial", 48))
        self.timer_label.pack(pady=10)

        self.detail_label = ttk.Label(display_frame, text="", font=("Arial", 12))
        self.detail_label.pack()

        # --- Кнопки ---
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill="x")
        self.start_btn = ttk.Button(btn_frame, text="Старт", command=self.start)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="Стоп", command=self.stop)
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=5)

    def beep(self):
        try:
            self.bell()
        except Exception:
            pass

    def parse_holds(self, rounds):
        raw = [x.strip() for x in self.holds_var.get().split(",") if x.strip()]
        holds = []
        for i in range(rounds):
            if i < len(raw):
                holds.append(int(raw[i]))
            else:
                holds.append(int(raw[-1]) if raw else 30)
        return holds

    def set_display(self, stage, round_text, seconds_left, detail=""):
        self.stage_label.config(text=stage)
        self.round_label.config(text=round_text)
        m, s = divmod(max(int(seconds_left), 0), 60)
        self.timer_label.config(text=f"{m:02d}:{s:02d}")
        self.detail_label.config(text=detail)
        self.update_idletasks()

    def countdown(self, seconds, stage, round_text, detail_fn=None, tick_fn=None):
        for remaining in range(int(seconds), 0, -1):
            if self.stop_flag:
                return False
            detail = detail_fn(remaining) if detail_fn else ""
            self.set_display(stage, round_text, remaining, detail)
            if tick_fn:
                tick_fn(remaining)
            time.sleep(1)
        return True

    def run_practice(self):
        rounds = self.rounds_var.get()
        cycles = self.cycles_var.get()
        tempo = self.tempo_var.get()
        holds = self.parse_holds(rounds)
        inhale_hold = self.inhale_hold_var.get()
        metronome = self.metronome_var.get()

        for r in range(1, rounds + 1):
            if self.stop_flag:
                break
            round_text = f"Раунд {r} из {rounds}"

            # Этап 1: цикл дыхания
            self.set_display("Дышим: вдох-выдох", round_text, cycles * tempo,
                              f"Цикл 1 из {cycles}")
            for c in range(1, cycles + 1):
                if self.stop_flag:
                    break
                self.set_display("Вдох", round_text, 0, f"Цикл {c} из {cycles}")
                if metronome:
                    self.beep()
                time.sleep(tempo / 2)
                if self.stop_flag:
                    break
                self.set_display("Выдох", round_text, 0, f"Цикл {c} из {cycles}")
                if metronome:
                    self.beep()
                time.sleep(tempo / 2)

            if self.stop_flag:
                break

            # Этап 2: задержка на выдохе
            hold_seconds = holds[r - 1]
            self.beep()
            ok = self.countdown(hold_seconds, "Задержка на выдохе", round_text,
                                 detail_fn=lambda rem: "Не дышим")
            if not ok:
                break

            # Этап 3: вдох + задержка на вдохе
            self.beep()
            self.set_display("Глубокий вдох", round_text, 0, "Задержите дыхание")
            time.sleep(1)
            ok = self.countdown(inhale_hold, "Задержка на вдохе", round_text,
                                 detail_fn=lambda rem: "Держим вдох")
            if not ok:
                break
            self.beep()

        if not self.stop_flag:
            self.set_display("Практика завершена!", "", 0, "Отличная работа")
        else:
            self.set_display("Остановлено", "", 0, "")
        self.running = False

    def start(self):
        if self.running:
            return
        self.running = True
        self.stop_flag = False
        threading.Thread(target=self.run_practice, daemon=True).start()

    def stop(self):
        self.stop_flag = True
        self.running = False


if __name__ == "__main__":
    app = BreathTimer()
    app.mainloop()
