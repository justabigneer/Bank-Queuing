import tkinter as tk
from tkinter import ttk
import random
import math
import time
from collections import deque

# ─── CONFIG ───────────────────────────────────────────────────────────────────
NUM_SERVERS       = 3
ARRIVAL_PROB      = 0.35
SERVICE_TIME_RANGE = (3, 8)
SIM_SPEED_MS      = 300        # ms per tick
MAX_QUEUE         = 18

# ─── COLOURS ──────────────────────────────────────────────────────────────────
BG        = "#f7f4d5"
PANEL_BG  = "#839958"
ACCENT    = "#58a6ff"
GREEN     = "#839958"
ORANGE    = "#a05432"
RED       = "#b18882"
YELLOW    = "#fceea8"
WHITE     = "#f2e8d6"
MUTED     = "#8b949e"
GOLD      = "#e3d6bf"

SERVER_COLOURS =  ["#105666", "#d3968c", "#e6a341", "#b14a36", "#8c0902"]


def draw_person(canvas, x, y, color="#58a6ff", size=18, tag="person"):
    r = size // 3
    # head
    canvas.create_oval(x-r, y-size//2, x+r, y-size//2+r*2,
                       fill=color, outline="", tags=tag)
    # body
    canvas.create_line(x, y-size//2+r*2, x, y+size//4,
                       fill=color, width=3, tags=tag)
    # arms
    canvas.create_line(x-size//3, y-size//8, x+size//3, y-size//8,
                       fill=color, width=2, tags=tag)
    # legs
    canvas.create_line(x, y+size//4, x-size//4, y+size//2,
                       fill=color, width=2, tags=tag)
    canvas.create_line(x, y+size//4, x+size//4, y+size//2,
                       fill=color, width=2, tags=tag)

# ─── ANIMATED NUMBER COUNTER ──────────────────────────────────────────────────
class AnimatedStat:
    def __init__(self, canvas, x, y, label, color, fmt="{:.0f}"):
        self.canvas = canvas
        self.fmt    = fmt
        self.value  = 0
        self.target = 0
        self.lbl_id = canvas.create_text(x, y-14, text=label,
                                          fill=MUTED, font=("Consolas", 9))
        self.val_id = canvas.create_text(x, y+8, text="0",
                                          fill=color, font=("Consolas", 20, "bold"))
    def set_target(self, v):
        self.target = v
    def tick(self):
        if abs(self.value - self.target) > 0.5:
            self.value += (self.target - self.value) * 0.3
        else:
            self.value = self.target
        self.canvas.itemconfig(self.val_id, text=self.fmt.format(self.value))

# ─── MAIN APP ─────────────────────────────────────────────────────────────────
class BankSim(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🏦  Multi-Server Bank Queue Simulator")
        self.configure(bg=BG)
        self.resizable(False, False)

        self._build_ui()
        self._reset_state()
        self.running = False
        self._after_id = None

    # ── UI CONSTRUCTION ───────────────────────────────────────────────────────
    def _build_ui(self):
        W, H = 900, 620

        # ── top bar ──────────────────────────────────────────────────────────
        top = tk.Frame(self, bg=PANEL_BG, height=54)
        top.pack(fill="x")
        tk.Label(top, text="🏦  BANK QUEUE SIMULATOR",
                 bg=PANEL_BG, fg=WHITE,
                 font=("Consolas", 15, "bold")).pack(side="left", padx=20, pady=12)
        self.lbl_tick = tk.Label(top, text="T = 0",
                                  bg=PANEL_BG, fg=ACCENT,
                                  font=("Consolas", 13, "bold"))
        self.lbl_tick.pack(side="right", padx=20)

        # ── main canvas ──────────────────────────────────────────────────────
        self.cv = tk.Canvas(self, width=W, height=H, bg=BG,
                            highlightthickness=0)
        self.cv.pack(padx=10, pady=(4,0))

        # ── control bar ──────────────────────────────────────────────────────
        ctrl = tk.Frame(self, bg=PANEL_BG, height=54)
        ctrl.pack(fill="x")

        btn_kw = dict(font=("Consolas", 10, "bold"), relief="flat",
                      cursor="hand2", padx=14, pady=6)
        self.btn_start = tk.Button(ctrl, text="▶  START",  bg=GREEN,  fg=BG,
                                   command=self.start, **btn_kw)
        self.btn_pause = tk.Button(ctrl, text="⏸  PAUSE",  bg=YELLOW, fg=BG,
                                   command=self.pause, **btn_kw)
        self.btn_reset = tk.Button(ctrl, text="↺  RESET",  bg=RED,    fg=WHITE,
                                   command=self.reset, **btn_kw)
        for b in (self.btn_start, self.btn_pause, self.btn_reset):
            b.pack(side="left", padx=8, pady=10)

        # speed slider
        tk.Label(ctrl, text="Speed:", bg=PANEL_BG, fg=MUTED,
                 font=("Consolas", 9)).pack(side="left", padx=(20,4))
        self.speed_var = tk.IntVar(value=SIM_SPEED_MS)
        sl = ttk.Scale(ctrl, from_=50, to=800, orient="horizontal",
                       variable=self.speed_var, length=140)
        sl.pack(side="left")

        # arrival prob slider
        tk.Label(ctrl, text="  Arrival:", bg=PANEL_BG, fg=MUTED,
                 font=("Consolas", 9)).pack(side="left", padx=(16,4))
        self.arr_var = tk.DoubleVar(value=ARRIVAL_PROB)
        sl2 = ttk.Scale(ctrl, from_=0.05, to=0.9, orient="horizontal",
                        variable=self.arr_var, length=140)
        sl2.pack(side="left")
        self.lbl_arr = tk.Label(ctrl, text=f"{ARRIVAL_PROB:.0%}",
                                 bg=PANEL_BG, fg=ACCENT,
                                 font=("Consolas", 9, "bold"))
        self.lbl_arr.pack(side="left", padx=4)

        # ── pre-draw static chrome ────────────────────────────────────────────
        self._draw_static(W, H)

        # ── stat counters ─────────────────────────────────────────────────────
        stat_y = H - 54
        sx = [110, 270, 430, 590, 750]
        self.stat_served   = AnimatedStat(self.cv, sx[0], stat_y, "SERVED",    GREEN)
        self.stat_waiting  = AnimatedStat(self.cv, sx[1], stat_y, "WAITING",   ORANGE)
        self.stat_avgwait  = AnimatedStat(self.cv, sx[2], stat_y, "AVG WAIT",  ACCENT, "{:.1f}")
        self.stat_util     = AnimatedStat(self.cv, sx[3], stat_y, "UTILIZ %",  YELLOW, "{:.0f}")
        self.stat_dropped  = AnimatedStat(self.cv, sx[4], stat_y, "DROPPED",   RED)

    def _draw_static(self, W, H):
        cv = self.cv

        # subtle grid lines
        for x in range(0, W, 60):
            cv.create_line(x, 0, x, H, fill="#1c2230", width=1)
        for y in range(0, H, 60):
            cv.create_line(0, y, W, y, fill="#1c2230", width=1)

        # entrance door on left
        cv.create_rectangle(0, H//2-60, 22, H//2+60, fill="#21262d", outline=MUTED)
        cv.create_text(11, H//2, text="IN", fill=MUTED,
                       font=("Consolas", 8, "bold"), angle=90)

        # queue lane
        cv.create_rectangle(30, H//2-36, 580, H//2+36,
                             fill="#131920", outline="#30363d", width=2, dash=(6,4))
        cv.create_text(305, H//2-42, text="QUEUE LANE",
                       fill="#30363d", font=("Consolas", 8))

        # servers panel
        panel_x = 600
        cv.create_rectangle(panel_x-8, 30, W-8, H-80,
                             fill=PANEL_BG, outline="#30363d", width=2)
        cv.create_text(panel_x + (W-panel_x)//2 - 8, 48,
                       text="TELLERS", fill=MUTED, font=("Consolas", 9, "bold"))

        # server booths
        bh = (H - 130) // NUM_SERVERS
        self._server_rects = []
        self._server_lights = []
        self._server_labels = []
        self._server_progress = []
        self._server_person_tag = []

        for i in range(NUM_SERVERS):
            by = 65 + i * bh
            bx = panel_x
            bw = W - bx - 16
            color = SERVER_COLOURS[i % len(SERVER_COLOURS)]
            # booth bg
            r = cv.create_rectangle(bx, by, bx+bw, by+bh-10,
                                     fill="#0d1117", outline=color, width=2)
            # status light
            light = cv.create_oval(bx+bw-22, by+8, bx+bw-8, by+22,
                                    fill=GREEN, outline="")
            # teller name
            lbl = cv.create_text(bx+60, by+bh//2-10,
                                  text=f"Teller {i+1}", fill=color,
                                  font=("Consolas", 11, "bold"))
            # progress bar bg
            cv.create_rectangle(bx+8, by+bh-28, bx+bw-8, by+bh-14,
                                  fill="#21262d", outline="")
            prog = cv.create_rectangle(bx+8, by+bh-28, bx+8, by+bh-14,
                                        fill=color, outline="")
            ptag = f"sp_{i}"
            self._server_rects.append(r)
            self._server_lights.append(light)
            self._server_labels.append(lbl)
            self._server_progress.append((prog, bx+8, bx+bw-8, by+bh-28, by+bh-14, color))
            self._server_person_tag.append(ptag)

        # stats divider line
        cv.create_line(0, H-80, W, H-80, fill="#30363d", width=1)

    # ── STATE MANAGEMENT ─────────────────────────────────────────────────────
    def _reset_state(self):
        self.tick        = 0
        self.queue       = deque()
        self.servers     = [{"busy": False, "remaining": 0, "total_busy": 0}
                            for _ in range(NUM_SERVERS)]
        self.waiting_times  = []
        self.dropped        = 0
        self._redraw_queue()
        self._update_servers()

    def reset(self):
        self.pause()
        self._reset_state()
        self.lbl_tick.config(text="T = 0")
        for stat in (self.stat_served, self.stat_waiting,
                     self.stat_avgwait, self.stat_util, self.stat_dropped):
            stat.set_target(0)
            stat.tick()

    # ── SIMULATION TICK ──────────────────────────────────────────────────────
    def _tick(self):
        if not self.running:
            return
        self.tick += 1
        arr_prob = self.arr_var.get()
        self.lbl_arr.config(text=f"{arr_prob:.0%}")

        # arrivals
        if random.random() < arr_prob:
            if len(self.queue) < MAX_QUEUE:
                self.queue.append(0)
                self._flash_entrance()
            else:
                self.dropped += 1

        # service
        for s in self.servers:
            if s["busy"]:
                s["remaining"] -= 1
                s["total_busy"] += 1
                if s["remaining"] <= 0:
                    s["busy"] = False
            if not s["busy"] and self.queue:
                wt = self.queue.popleft()
                self.waiting_times.append(wt)
                s["remaining"] = random.randint(*SERVICE_TIME_RANGE)
                s["max_service"] = s["remaining"]
                s["busy"] = True

        # age waiting customers
        self.queue = deque(w+1 for w in self.queue)

        # update visuals
        self._redraw_queue()
        self._update_servers()
        self._update_stats()

        self.lbl_tick.config(text=f"T = {self.tick}")
        self._after_id = self.after(self.speed_var.get(), self._tick)

    def _flash_entrance(self):
        cv = self.cv
        H = int(cv["height"])
        flash = cv.create_rectangle(0, H//2-60, 22, H//2+60,
                                     fill=GREEN, outline="")
        self.after(120, lambda: cv.delete(flash))

    # ── QUEUE DRAWING ─────────────────────────────────────────────────────────
    def _redraw_queue(self):
        self.cv.delete("qperson")
        H = int(self.cv["height"])
        cx_start, cy = 50, H // 2
        step = 28
        for i, wt in enumerate(self.queue):
            x = cx_start + i * step
            # colour by wait time: green→orange→red
            ratio = min(wt / 20.0, 1.0)
            if ratio < 0.5:
                color = GREEN
            elif ratio < 0.8:
                color = ORANGE
            else:
                color = RED
            draw_person(self.cv, x, cy, color=color, size=20, tag="qperson")
            if wt > 5:
                self.cv.create_text(x, cy-16, text=str(wt),
                                     fill=color, font=("Consolas", 7),
                                     tags="qperson")

    # ── SERVER DRAWING ────────────────────────────────────────────────────────
    def _update_servers(self):
        cv = self.cv
        H = int(cv["height"])
        bh = (H - 130) // NUM_SERVERS

        for i, s in enumerate(self.servers):
            light  = self._server_lights[i]
            ptag   = self._server_person_tag[i]
            prec, px1, px2, py1, py2, pcol = self._server_progress[i]

            cv.delete(ptag)

            if s["busy"]:
                cv.itemconfig(light, fill=ORANGE)
                by = 65 + i * bh
                mid_x = 650 + 15
                mid_y = by + bh // 2 - 8
                draw_person(cv, mid_x, mid_y, color=pcol, size=22, tag=ptag)

                # progress bar
                max_st = s.get("max_service", SERVICE_TIME_RANGE[1])
                done = max_st - s["remaining"]
                frac = done / max(max_st, 1)
                fill_x = px1 + frac * (px2 - px1)
                cv.coords(prec, px1, py1, fill_x, py2)
            else:
                cv.itemconfig(light, fill=GREEN)
                cv.coords(prec, px1, py1, px1, py2)

    # ── STATS ────────────────────────────────────────────────────────────────
    def _update_stats(self):
        total_busy = sum(s["total_busy"] for s in self.servers)
        max_busy   = self.tick * NUM_SERVERS
        util = (total_busy / max_busy * 100) if max_busy else 0
        avg  = sum(self.waiting_times) / len(self.waiting_times) if self.waiting_times else 0

        self.stat_served.set_target(len(self.waiting_times))
        self.stat_waiting.set_target(len(self.queue))
        self.stat_avgwait.set_target(avg)
        self.stat_util.set_target(util)
        self.stat_dropped.set_target(self.dropped)

        for stat in (self.stat_served, self.stat_waiting,
                     self.stat_avgwait, self.stat_util, self.stat_dropped):
            stat.tick()

    # ── CONTROLS ─────────────────────────────────────────────────────────────
    def start(self):
        if not self.running:
            self.running = True
            self._tick()

    def pause(self):
        self.running = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None


# ─── RUN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = BankSim()
    app.mainloop()