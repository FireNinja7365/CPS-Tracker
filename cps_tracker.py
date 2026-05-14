import ctypes
import tkinter as tk
from tkinter import font as tkfont
import time
from collections import deque
from pynput import mouse as pmouse
from pynput import keyboard as pkeyboard


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def _clip_cursor(x, y, w, h):
    r = _RECT(x, y, x + w, y + h)
    ctypes.windll.user32.ClipCursor(ctypes.byref(r))


def _unclip_cursor():
    ctypes.windll.user32.ClipCursor(None)


WINDOW_WIDTH = 700
WINDOW_HEIGHT = 420
SAMPLE_WINDOW = 1.0
REFRESH_MS = 5

BG = "#0a0a0f"
LEFT_COLOR = "#00e5ff"
RIGHT_COLOR = "#ff4d6d"
DIM_COLOR = "#2a2a3a"
TEXT_DIM = "#555566"


class CPSTracker:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CPS Tracker")
        self.root.geometry(f"{WINDOW_WIDTH }x{WINDOW_HEIGHT }")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.running = False
        self.fullscreen = False
        self.l_times: deque[float] = deque()
        self.r_times: deque[float] = deque()
        self.l_max_cps = 0.0
        self.r_max_cps = 0.0
        self.l_total = 0
        self.r_total = 0

        self._mouse_listener = None
        self._keyboard_listener = None
        self._update_id = None

        self._build_ui()

    def _build_ui(self):
        mono_big = tkfont.Font(family="Courier New", size=52, weight="bold")
        mono_med = tkfont.Font(family="Courier New", size=18, weight="bold")
        mono_small = tkfont.Font(family="Courier New", size=11)
        label_font = tkfont.Font(family="Courier New", size=10)

        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True)

        card = tk.Frame(outer, bg=BG, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        hdr = tk.Frame(card, bg=BG)
        hdr.pack(fill="x", padx=30, pady=(24, 0))

        tk.Label(
            hdr,
            text="CPS",
            font=tkfont.Font(family="Courier New", size=22, weight="bold"),
            bg=BG,
            fg="#ffffff",
        ).pack(side="left")
        tk.Label(
            hdr,
            text="TRACKER",
            font=tkfont.Font(family="Courier New", size=22),
            bg=BG,
            fg=DIM_COLOR,
        ).pack(side="left", padx=(6, 0))

        self.status_dot = tk.Label(
            hdr,
            text="●",
            font=tkfont.Font(family="Courier New", size=14),
            bg=BG,
            fg=DIM_COLOR,
        )
        self.status_dot.pack(side="right")
        self.status_lbl = tk.Label(
            hdr, text="IDLE", font=label_font, bg=BG, fg=DIM_COLOR
        )
        self.status_lbl.pack(side="right", padx=(0, 6))

        tk.Frame(card, bg=DIM_COLOR, height=1).pack(fill="x", padx=30, pady=10)

        stats = tk.Frame(card, bg=BG)
        stats.pack(fill="x", padx=30)

        left_col = tk.Frame(stats, bg=BG)
        left_col.pack(side="left", expand=True, fill="both")

        tk.Label(
            left_col, text="LEFT BUTTON", font=label_font, bg=BG, fg=LEFT_COLOR
        ).pack(anchor="w")
        self.l_cps_var = tk.StringVar(value="0.0")
        tk.Label(
            left_col,
            textvariable=self.l_cps_var,
            font=mono_big,
            bg=BG,
            fg=LEFT_COLOR,
            anchor="w",
            width=5,
        ).pack(anchor="w")
        tk.Label(left_col, text="CPS", font=mono_small, bg=BG, fg=TEXT_DIM).pack(
            anchor="w"
        )
        tk.Frame(left_col, bg=BG, height=12).pack()

        max_row_l = tk.Frame(left_col, bg=BG)
        max_row_l.pack(anchor="w")
        tk.Label(max_row_l, text="MAX  ", font=mono_small, bg=BG, fg=TEXT_DIM).pack(
            side="left"
        )
        self.l_max_var = tk.StringVar(value="0.0")
        tk.Label(
            max_row_l, textvariable=self.l_max_var, font=mono_med, bg=BG, fg=LEFT_COLOR
        ).pack(side="left")

        tot_row_l = tk.Frame(left_col, bg=BG)
        tot_row_l.pack(anchor="w", pady=(4, 0))
        tk.Label(tot_row_l, text="TOTAL  ", font=mono_small, bg=BG, fg=TEXT_DIM).pack(
            side="left"
        )
        self.l_tot_var = tk.StringVar(value="0")
        tk.Label(
            tot_row_l,
            textvariable=self.l_tot_var,
            font=mono_small,
            bg=BG,
            fg=LEFT_COLOR,
        ).pack(side="left")

        tk.Frame(stats, bg=DIM_COLOR, width=1).pack(side="left", fill="y", padx=30)

        right_col = tk.Frame(stats, bg=BG)
        right_col.pack(side="left", expand=True, fill="both")

        tk.Label(
            right_col, text="RIGHT BUTTON", font=label_font, bg=BG, fg=RIGHT_COLOR
        ).pack(anchor="w")
        self.r_cps_var = tk.StringVar(value="0.0")
        tk.Label(
            right_col,
            textvariable=self.r_cps_var,
            font=mono_big,
            bg=BG,
            fg=RIGHT_COLOR,
            anchor="w",
            width=5,
        ).pack(anchor="w")
        tk.Label(right_col, text="CPS", font=mono_small, bg=BG, fg=TEXT_DIM).pack(
            anchor="w"
        )
        tk.Frame(right_col, bg=BG, height=12).pack()

        max_row_r = tk.Frame(right_col, bg=BG)
        max_row_r.pack(anchor="w")
        tk.Label(max_row_r, text="MAX  ", font=mono_small, bg=BG, fg=TEXT_DIM).pack(
            side="left"
        )
        self.r_max_var = tk.StringVar(value="0.0")
        tk.Label(
            max_row_r, textvariable=self.r_max_var, font=mono_med, bg=BG, fg=RIGHT_COLOR
        ).pack(side="left")

        tot_row_r = tk.Frame(right_col, bg=BG)
        tot_row_r.pack(anchor="w", pady=(4, 0))
        tk.Label(tot_row_r, text="TOTAL  ", font=mono_small, bg=BG, fg=TEXT_DIM).pack(
            side="left"
        )
        self.r_tot_var = tk.StringVar(value="0")
        tk.Label(
            tot_row_r,
            textvariable=self.r_tot_var,
            font=mono_small,
            bg=BG,
            fg=RIGHT_COLOR,
        ).pack(side="left")

        tk.Frame(card, bg=DIM_COLOR, height=1).pack(fill="x", padx=30, pady=18)

        ctrl = tk.Frame(card, bg=BG)
        ctrl.pack()

        btn_font = tkfont.Font(family="Courier New", size=13, weight="bold")

        self.start_btn = tk.Button(
            ctrl,
            text="  START  ",
            font=btn_font,
            relief="flat",
            bd=0,
            padx=18,
            pady=10,
            cursor="hand2",
            bg="#1a1a2e",
            fg="#ffffff",
            activebackground="#22223a",
            activeforeground="#ffffff",
            command=self.start_session,
        )
        self.start_btn.pack(side="left", padx=(0, 16))

        tk.Label(
            ctrl,
            text="SPACE / ESC  to stop",
            font=tkfont.Font(family="Courier New", size=10),
            bg=BG,
            fg=TEXT_DIM,
        ).pack(side="left")

        tk.Label(
            card,
            text="F11  to toggle fullscreen  ·  cursor is locked while tracking",
            font=tkfont.Font(family="Courier New", size=8),
            bg=BG,
            fg="#333344",
        ).pack(pady=(6, 0))

        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self._blink()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)
        if self.running:
            self.root.after(50, self._apply_clip)

    def start_session(self):
        if self.running:
            return
        self.running = True
        self.l_times.clear()
        self.r_times.clear()
        self.l_max_cps = 0.0
        self.r_max_cps = 0.0
        self.l_total = 0
        self.r_total = 0

        for var in (self.l_cps_var, self.r_cps_var, self.l_max_var, self.r_max_var):
            var.set("0.0")
        self.l_tot_var.set("0")
        self.r_tot_var.set("0")

        self.status_lbl.config(text="TRACKING", fg="#00ff88")
        self.status_dot.config(fg="#00ff88")
        self.start_btn.config(state="disabled", fg=TEXT_DIM)

        self.root.update_idletasks()
        self._apply_clip()

        self._mouse_listener = pmouse.Listener(on_click=self._on_click)
        self._mouse_listener.start()

        self._keyboard_listener = pkeyboard.Listener(on_press=self._on_key)
        self._keyboard_listener.start()

        self._schedule_update()

    def _apply_clip(self):
        self.root.update_idletasks()
        x = self.root.winfo_rootx()
        y = self.root.winfo_rooty()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        _clip_cursor(x, y, w, h)

    def stop_session(self):
        if not self.running:
            return
        self.running = False

        _unclip_cursor()

        if self._update_id:
            self.root.after_cancel(self._update_id)
            self._update_id = None

        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None

        self.l_times.clear()
        self.r_times.clear()
        self._refresh_display()

        self.status_lbl.config(text="IDLE", fg=TEXT_DIM)
        self.status_dot.config(fg=DIM_COLOR)
        self.start_btn.config(state="normal", fg="#ffffff")

    def _on_click(self, x, y, button, pressed):
        if not self.running or not pressed:
            return
        now = time.monotonic()
        if button == pmouse.Button.left:
            self.l_times.append(now)
            self.l_total += 1
        elif button == pmouse.Button.right:
            self.r_times.append(now)
            self.r_total += 1

    def _on_key(self, key):
        if key in {pkeyboard.Key.space, pkeyboard.Key.esc}:
            self.root.after(0, self.stop_session)

    def _schedule_update(self):
        if self.running:
            self._refresh_display()
            self._update_id = self.root.after(REFRESH_MS, self._schedule_update)

    def _refresh_display(self):
        now = time.monotonic()
        cutoff = now - SAMPLE_WINDOW

        while self.l_times and self.l_times[0] < cutoff:
            self.l_times.popleft()
        while self.r_times and self.r_times[0] < cutoff:
            self.r_times.popleft()

        l_cps = len(self.l_times) / SAMPLE_WINDOW
        r_cps = len(self.r_times) / SAMPLE_WINDOW

        self.l_max_cps = max(self.l_max_cps, l_cps)
        self.r_max_cps = max(self.r_max_cps, r_cps)

        self.l_cps_var.set(f"{l_cps :.1f}")
        self.r_cps_var.set(f"{r_cps :.1f}")
        self.l_max_var.set(f"{self .l_max_cps :.1f}")
        self.r_max_var.set(f"{self .r_max_cps :.1f}")
        self.l_tot_var.set(str(self.l_total))
        self.r_tot_var.set(str(self.r_total))

    def _blink(self):
        if self.running:
            c = self.status_dot.cget("fg")
            self.status_dot.config(fg=BG if c == "#00ff88" else "#00ff88")
        self.root.after(600, self._blink)


def main():
    root = tk.Tk()
    app = CPSTracker(root)

    def on_close():
        app.stop_session()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
