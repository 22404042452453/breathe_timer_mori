
import tkinter as tk
from tkinter import ttk
import time

class PracticeTimer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Practice Timer")
        self.geometry("320x220")

        self.total_seconds = tk.IntVar(value=300)   # длительность подхода/практики (сек)
        self.remaining = 0
        self.running = False
        self.after_id = None

        frm = ttk.Frame(self, padding=15)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Минуты:").grid(row=0, column=0, sticky="w")
        self.min_entry = ttk.Spinbox(frm, from_=0, to=180, width=5)
        self.min_entry.set(5)
        self.min_entry.grid(row=0, column=1)

        ttk.Label(frm, text="Секунды:").grid(row=1, column=0, sticky="w")
        self.sec_entry = ttk.Spinbox(frm, from_=0, to=59, width=5)
        self.sec_entry.set(0)
        self.sec_entry.grid(row=1, column=1)

        self.display = ttk.Label(frm, text="00:00", font=("Arial", 36))
        self.display.grid(row=2, column=0, columnspan=2, pady=15)

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=3, column=0, columnspan=2)

        ttk.Button(btn_frame, text="Старт", command=self.start).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Пауза", command=self.pause).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Сброс", command=self.reset).pack(side="left", padx=5)

        self.reset()

    def set_from_inputs(self):
        m = int(self.min_entry.get() or 0)
        s = int(self.sec_entry.get() or 0)
        self.remaining = m * 60 + s
        self.update_display()

    def update_display(self):
        m, s = divmod(max(self.remaining, 0), 60)
        self.display.config(text=f"{m:02d}:{s:02d}")

    def tick(self):
        if self.running and self.remaining > 0:
            self.remaining -= 1
            self.update_display()
            self.after_id = self.after(1000, self.tick)
        elif self.remaining <= 0:
            self.running = False
            self.display.config(text="Время!")
            self.bell()

    def start(self):
        if not self.running:
            if self.remaining <= 0:
                self.set_from_inputs()
            self.running = True
            self.tick()

    def pause(self):
        self.running = False
        if self.after_id:
            self.after_cancel(self.after_id)

    def reset(self):
        self.pause()
        self.set_from_inputs()


if __name__ == "__main__":
    app = PracticeTimer()
    app.mainloop()
