"""Orbital Ambulance: a 30-level supply game using BFS, Bayes, HMM and MDP.

Desktop launch: double-click START_GAME.bat, or run `python medbot_x.py`.
The game uses only Python's standard library.
"""

from collections import deque
from dataclasses import dataclass
import colorsys
import ctypes
import random
import threading
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from pathlib import Path


TOTAL_LEVELS = 30
SIZE_CHOICES = (5, 10, 20, 40, 60, 100)
STYLE_NAMES = ("Clinic", "Pixel", "Realistic", "Mixed")
CHARACTERS = ("Space Ambulance",)
THEME_NAMES = [f"{i:03d} {STYLE_NAMES[min((i - 1)//40, 3)]}"
               for i in range(1, 159)]
HMM_TRANSITION = {
    "free": {"free": .80, "blocked": .20},
    "blocked": {"free": .30, "blocked": .70},
}
REWARDS = {
    "CONTINUE": {"free": 10, "blocked": -20},
    "PAUSE": {"free": -2, "blocked": 2},
}


def dark_titlebar(window):
    """Use the Windows dark title bar when the desktop supports it."""
    try:
        window.update_idletasks()
        enabled = ctypes.c_int(1)
        hwnd = window.winfo_id()
        for attribute in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)) == 0:
                break
    except (AttributeError, OSError, tk.TclError):
        pass


def bfs_trace(start, goal, size, walls):
    """Return a shortest four-neighbor route and number of expanded cells."""
    queue = deque([start])
    parent = {start: None}
    expanded = 0
    while queue:
        cell = queue.popleft()
        expanded += 1
        if cell == goal:
            route = []
            while cell is not None:
                route.append(cell)
                cell = parent[cell]
            return route[::-1], expanded
        x, y = cell
        for next_cell in ((x + 1, y), (x, y - 1), (x - 1, y), (x, y + 1)):
            nx, ny = next_cell
            if (0 <= nx < size and 0 <= ny < size and next_cell not in walls
                    and next_cell not in parent):
                parent[next_cell] = cell
                queue.append(next_cell)
    return [], expanded


def bfs(start, goal, size, walls):
    return bfs_trace(start, goal, size, walls)[0]


def bayes_free(report, prior, sensitivity, false_alarm):
    """P(free | one CLEAR or ALERT report)."""
    if report not in ("CLEAR", "ALERT"):
        raise ValueError("report must be CLEAR or ALERT")
    p_report_free = sensitivity if report == "CLEAR" else 1 - sensitivity
    p_report_blocked = false_alarm if report == "CLEAR" else 1 - false_alarm
    free_part = prior * p_report_free
    blocked_part = (1 - prior) * p_report_blocked
    return free_part / (free_part + blocked_part), free_part, blocked_part


def viterbi(observations, prior, sensitivity, false_alarm):
    """Most likely sequence of the hidden free/blocked corridor states."""
    if not observations or any(x not in ("CLEAR", "ALERT") for x in observations):
        raise ValueError("observations must contain CLEAR or ALERT")
    states = ("free", "blocked")

    def emission(state, report):
        p_clear = sensitivity if state == "free" else false_alarm
        return p_clear if report == "CLEAR" else 1 - p_clear

    values = {"free": prior * emission("free", observations[0]),
              "blocked": (1 - prior) * emission("blocked", observations[0])}
    paths = {state: (state,) for state in states}
    trace = [values.copy()]
    for report in observations[1:]:
        next_values, next_paths = {}, {}
        for state in states:
            previous = max(states, key=lambda old: values[old] * HMM_TRANSITION[old][state])
            next_values[state] = (values[previous] * HMM_TRANSITION[previous][state]
                                  * emission(state, report))
            next_paths[state] = paths[previous] + (state,)
        values, paths = next_values, next_paths
        trace.append(values.copy())
    final = max(states, key=values.get)
    return paths[final], trace


def mdp_decision(prob_free):
    """Compare one-step expected rewards in two states for two actions."""
    q = {action: prob_free * reward["free"] + (1 - prob_free) * reward["blocked"]
         for action, reward in REWARDS.items()}
    return max(q, key=q.get), q


def level_size(mode, level_number, campaign_seed):
    """Fixed size, or a fresh random size that differs from the previous level."""
    if mode != "Random":
        return int(mode)
    rng = random.Random(campaign_seed)
    previous = None
    selected = SIZE_CHOICES[0]
    for _ in range(level_number):
        selected = rng.choice([size for size in SIZE_CHOICES if size != previous])
        previous = selected
    return selected


@dataclass(frozen=True)
class Floor:
    size: int
    start: tuple
    wards: dict
    walls: frozenset
    prior: float
    sensitivity: float
    false_alarm: float
    level_number: int


def generate_floor(size, level_number, seed):
    """Generate a solvable level with two wards and increasing wall density."""
    if size not in SIZE_CHOICES or not 1 <= level_number <= TOTAL_LEVELS:
        raise ValueError("unsupported size or level")
    start = (0, size // 2)
    wards = {"A": (size - 1, 0), "B": (size - 1, size - 1)}
    reserved = {start, *wards.values()}
    candidates = [(x, y) for y in range(size) for x in range(size)
                  if (x, y) not in reserved]
    density = min(.13 + .0065 * (level_number - 1), .33)
    wall_count = round(len(candidates) * density)
    rng = random.Random(seed)
    for _ in range(160):
        if size == 5:
            walls = frozenset(rng.sample(candidates, wall_count))
        else:
            grouped = set()
            target_grouped = round(wall_count * .65)
            max_span = max(2, min(7, size // 5))
            attempts = 0
            while len(grouped) < target_grouped and attempts < 2000:
                attempts += 1
                x0 = rng.randrange(1, size - 1)
                y0 = rng.randrange(1, size - 1)
                width = rng.randint(2, max_span)
                height = rng.randint(2, max_span)
                for y in range(y0, min(size - 1, y0 + height)):
                    for x in range(x0, min(size - 1, x0 + width)):
                        if len(grouped) >= target_grouped:
                            break
                        if (x, y) not in reserved:
                            grouped.add((x, y))
            remaining = [cell for cell in candidates if cell not in grouped]
            walls = frozenset(grouped | set(rng.sample(remaining, wall_count - len(grouped))))
        if all(bfs(start, ward, size, walls) for ward in wards.values()):
            break
    else:
        # A deterministic clear corridor guarantees a playable fallback.
        walls = set(rng.sample(candidates, wall_count))
        for x in range(size):
            walls.discard((x, start[1]))
        for y in range(size):
            walls.discard((size - 1, y))
        walls = frozenset(walls)
    prior = max(.54, .82 - .008 * (level_number - 1))
    sensitivity = max(.78, .94 - .005 * (level_number - 1))
    false_alarm = min(.28, .12 + .005 * (level_number - 1))
    return Floor(size, start, wards, walls, prior, sensitivity, false_alarm, level_number)


def theme_colors(index):
    """A palette for one of 158 generated looks in four map styles."""
    if not 1 <= index <= 158:
        raise ValueError("theme index must be 1..158")
    family = min((index - 1) // 40, 3)
    variant = (index - 1) % 40
    # Dark, low-saturation palettes only. Variants stay comfortable to view.
    hues = (.43, .51, .58, .34, .10, .68, .03, .47)
    hue = hues[variant % len(hues)]

    def color(saturation, value, h=hue):
        return "#%02x%02x%02x" % tuple(round(c * 255) for c in colorsys.hsv_to_rgb(h, saturation, value))

    # All four families use a readable, restrained UI; the map styling changes.
    return {
        "background": "#12191b",
        "card": "#1c2729",
        "ink": "#e1e8e4",
        "muted": "#a7b5b0",
        "line": "#344245",
        "accent": color(.23, .59 + index * .00065),
        "floor": "#263335" if family in (0, 3) else "#293639",
        "wall": "#526064" if family != 2 else "#596366",
        "path": color(.24, .43),
        "highlight": "#31423f",
        "family": family,
    }


class Game:
    MAP_W, MAP_H = 700, 640

    def __init__(self, root):
        self.root = root
        root.title("Orbital Ambulance — Emergency Supply Run")
        root.geometry("1200x820")
        root.resizable(False, False)
        dark_titlebar(root)
        self.campaign_seed = random.SystemRandom().randrange(10**9)
        self.mode = "Random"
        self.level_number = 0
        self.floor = None
        self.target = "A"
        self.route = []
        self.expanded = 0
        self.position_index = 0
        self.player_position = (0, 0)
        self.facing = (1, 0)
        self.scanned_cell = None
        self.hazard_state = None
        self.energy = 0
        self.score = 0
        self.moves = 0
        self.show_hint = False
        self.motion_active = False
        self.motion_from = None
        self.motion_to = None
        self.motion_fraction = 1.0
        self.pending_moves = deque(maxlen=5)
        self.hidden_state = "free"
        self.reports = []
        self.bayes_result = None
        self.hmm_result = None
        self.mdp_result = None
        self.robot_name = "Space Ambulance"
        self.theme_index = 1
        self.palette = theme_colors(1)
        self.state = "menu"
        self.paused = False
        self.sound_on = tk.BooleanVar(value=True)
        self.music_on = tk.BooleanVar(value=True)
        self.challenge_kind = None
        self.challenge_overlay = None
        self.challenge_answer = None
        self.challenge_explanation = ""
        self.challenge_solved = set()
        self.challenge_pending = None
        self.resume_state = "running"
        self.ad_overlay = None
        self.ads_remaining = 0
        self.ads_total = 0
        self.ads_pending = False
        self.ad_resume_state = "running"
        self.zoom = None
        self.tick_count = 0
        self.level_token = 0
        self.events = deque(maxlen=3)
        self.randomizer = random.Random(self.campaign_seed)

        self.menu = tk.Frame(root)
        self.game = tk.Frame(root)
        self.build_menu()
        self.build_game()
        self.show_menu()
        root.bind("<Escape>", self.escape)
        root.bind_all("<KeyPress>", self.handle_key)
        root.after(180, self.tick)

    def build_menu(self):
        p = self.palette
        self.menu.configure(bg=p["background"])
        top = tk.Frame(self.menu, bg=p["background"])
        top.pack(fill="x", padx=58, pady=(43, 0))
        tk.Label(top, text="ORBITAL AMBULANCE", bg=p["background"], fg=p["ink"],
                 font=("Segoe UI", 33, "bold")).pack(anchor="w")
        tk.Label(top, text="Emergency supply run · 30 orbital stations", bg=p["background"], fg=p["muted"],
                 font=("Segoe UI", 15)).pack(anchor="w", pady=(0, 34))
        body = tk.Frame(self.menu, bg=p["background"])
        body.pack(fill="both", expand=True, padx=58)
        self.menu_art = tk.Canvas(body, width=530, height=510, bg="#1a292b", highlightthickness=0)
        self.menu_art.pack(side="left", padx=(0, 45))
        settings = tk.Frame(body, bg=p["card"], padx=36, pady=30,
                            highlightbackground=p["line"], highlightthickness=1)
        settings.pack(side="left", fill="both", expand=True)
        tk.Label(settings, text="Start a shift", bg=p["card"], fg=p["ink"],
                 font=("Segoe UI", 23, "bold")).pack(anchor="w", pady=(0, 11))
        tk.Label(settings, text="Thirty deliveries. New floor and look each level.",
                 bg=p["card"], fg=p["muted"], font=("Segoe UI", 11)).pack(anchor="w")
        tk.Label(settings, text="Map size", bg=p["card"], fg=p["ink"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(35, 8))
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Dark.TCombobox", fieldbackground=p["card"], background=p["card"],
                        foreground=p["ink"], arrowcolor=p["ink"], bordercolor=p["line"])
        style.map("Dark.TCombobox", fieldbackground=[("readonly", p["card"])],
                  foreground=[("readonly", p["ink"])])
        self.mode_box = ttk.Combobox(settings, state="readonly", width=25, style="Dark.TCombobox",
                                      values=("Random", "5", "10", "20", "40", "60", "100"),
                                      font=("Segoe UI", 12))
        self.mode_box.current(1)
        self.mode_box.pack(anchor="w")
        tk.Label(settings, text="Random can change from 5×5 to 100×100 on the next level.",
                 bg=p["card"], fg=p["muted"], wraplength=360, justify="left",
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(9, 24))
        self.menu_button(settings, "Ready · start mission", self.start_campaign, primary=True)
        self.menu_button(settings, "How to play", self.show_tutorial)
        self.menu_button(settings, "Quit", self.root.destroy)
        tk.Checkbutton(settings, text="Sound effects", variable=self.sound_on, bg=p["card"],
                       fg=p["ink"], selectcolor=p["card"], activebackground=p["card"],
                       font=("Segoe UI", 10)).pack(anchor="w", pady=(20, 0))
        tk.Checkbutton(settings, text="Background music", variable=self.music_on,
                       command=self.toggle_music, bg=p["card"], fg=p["ink"],
                       selectcolor=p["card"], activebackground=p["card"],
                       font=("Segoe UI", 10)).pack(anchor="w", pady=(5, 0))
        self.draw_menu_art()

    def menu_button(self, parent, title, action, primary=False):
        p = self.palette
        button = tk.Button(parent, text=title, command=action, anchor="w",
                           bg=p["accent"] if primary else p["card"],
                           fg="white" if primary else p["ink"],
                           activebackground=p["path"], activeforeground=p["ink"],
                           font=("Segoe UI", 12, "bold" if primary else "normal"),
                           relief="flat", padx=18, pady=11, cursor="hand2")
        button.pack(fill="x", pady=5)
        return button

    def draw_menu_art(self):
        c = self.menu_art
        c.delete("all")
        c.create_rectangle(36, 42, 494, 468, fill="#1d3031", outline="")
        for y in range(4):
            for x in range(4):
                x1, y1 = 70 + x * 98, 70 + y * 95
                c.create_rectangle(x1, y1, x1+86, y1+82,
                                   fill="#2a3d3e" if (x+y)%2 else "#304647", outline="")
        for x,y in ((1,0),(2,1),(1,3)):
            x1,y1=70+x*98,70+y*95
            c.create_rectangle(x1,y1,x1+86,y1+82,fill="#5a6768",outline="")
        c.create_line(110, 300, 210, 300, 210, 207, 315, 207, 315, 110,
                      fill="#78a89a", width=9, smooth=False)
        self.draw_character(c, 112, 300, 65, "Space Ambulance", "#78a89a")
        c.create_text(418, 100, text="A", fill="#b8d0c6", font=("Segoe UI", 19, "bold"))
        c.create_text(418, 390, text="B", fill="#b8d0c6", font=("Segoe UI", 19, "bold"))
        c.create_text(265, 435, text="Clear the signal. Drive the ambulance.", fill="#b8c9c5",
                      font=("Segoe UI", 13))

    def build_game(self):
        p = self.palette
        self.game.configure(bg=p["background"])
        header = tk.Frame(self.game, bg=p["background"])
        header.pack(fill="x", padx=22, pady=(15, 10))
        self.level_title = tk.Label(header, bg=p["background"], fg=p["ink"],
                                    font=("Segoe UI", 19, "bold"))
        self.level_title.pack(side="left")
        self.pause_button = tk.Button(header, text="Pause", command=self.toggle_pause,
                                      bg=p["card"], fg=p["ink"], relief="flat",
                                      font=("Segoe UI", 11), padx=18, pady=6)
        self.pause_button.pack(side="right", padx=(8, 0))
        tk.Button(header, text="Menu", command=self.show_menu, bg=p["card"], fg=p["ink"],
                  relief="flat", font=("Segoe UI", 11), padx=18, pady=6).pack(side="right")
        body = tk.Frame(self.game, bg=p["background"])
        body.pack(fill="both", expand=True, padx=22)
        map_frame = tk.Frame(body, bg=p["card"], highlightbackground=p["line"], highlightthickness=1)
        map_frame.pack(side="left", padx=(0, 14), fill="y")
        self.map_canvas = tk.Canvas(map_frame, width=self.MAP_W, height=self.MAP_H,
                                    bg=p["floor"], highlightthickness=0)
        self.map_canvas.pack(padx=8, pady=8)
        sidebar = tk.Frame(body, bg=p["background"], width=380)
        sidebar.pack(side="left", fill="both", expand=True)
        sidebar.pack_propagate(False)
        self.info_cards = {}
        for key, title in (("bfs", "Route · BFS"), ("bayes", "Sensor · Bayes"),
                           ("hmm", "Pattern · HMM"), ("mdp", "Action · MDP")):
            frame = tk.Frame(sidebar, bg=p["card"], padx=15, pady=11,
                              highlightbackground=p["line"], highlightthickness=1)
            frame.pack(fill="x", pady=(0, 9))
            heading = tk.Label(frame, text=title, bg=p["card"], fg=p["ink"],
                               font=("Segoe UI", 12, "bold"))
            heading.pack(anchor="w")
            content = tk.Label(frame, bg=p["card"], fg=p["muted"], justify="left",
                               wraplength=345, font=("Segoe UI", 10))
            content.pack(anchor="w", pady=(5, 0), fill="x")
            self.info_cards[key] = content
        controls = tk.Frame(sidebar, bg=p["background"])
        controls.pack(fill="x", pady=(5, 0))
        self.zoom_out = tk.Button(controls, text="−", command=lambda: self.change_zoom(-1),
                                  font=("Segoe UI", 15), width=3, bg=p["card"], fg=p["ink"],
                                  activebackground=p["line"], relief="flat")
        self.zoom_out.pack(side="left")
        self.zoom_in = tk.Button(controls, text="+", command=lambda: self.change_zoom(1),
                                 font=("Segoe UI", 15), width=3, bg=p["card"], fg=p["ink"],
                                 activebackground=p["line"], relief="flat")
        self.zoom_in.pack(side="left", padx=6)
        self.view_label = tk.Label(controls, bg=p["background"], fg=p["muted"],
                                   font=("Segoe UI", 10))
        self.view_label.pack(side="left", padx=12)
        tk.Label(sidebar, text="DRIVE THE AMBULANCE", bg=p["background"], fg=p["ink"],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(15, 5))
        pad = tk.Frame(sidebar, bg=p["background"])
        pad.pack(anchor="w")
        def drive_button(parent, text, command, row, column):
            button = tk.Button(parent, text=text, command=command, bg=p["card"], fg=p["ink"],
                               activebackground=p["line"], activeforeground=p["ink"],
                               font=("Segoe UI", 11, "bold"), relief="flat", width=7, pady=5)
            button.grid(row=row, column=column, padx=3, pady=3)
            return button
        drive_button(pad, "↑ / W", lambda: self.move(0, -1), 0, 1)
        drive_button(pad, "← / A", lambda: self.move(-1, 0), 1, 0)
        drive_button(pad, "↓ / S", lambda: self.move(0, 1), 1, 1)
        drive_button(pad, "→ / D", lambda: self.move(1, 0), 1, 2)
        actions = tk.Frame(sidebar, bg=p["background"])
        actions.pack(anchor="w", pady=(4, 0))
        for title, command in (("Scan E", self.scan_front), ("Wait Space", self.wait_turn),
                               ("Hint H · costly", self.toggle_hint)):
            tk.Button(actions, text=title, command=command, bg=p["card"], fg=p["ink"],
                      activebackground=p["line"], activeforeground=p["ink"],
                      font=("Segoe UI", 10), relief="flat", padx=8, pady=7).pack(side="left", padx=3)
        footer = tk.Frame(self.game, bg=p["background"])
        footer.pack(fill="x", padx=22, pady=(5, 15))
        self.status_label = tk.Label(footer, bg=p["background"], fg=p["ink"],
                                     font=("Segoe UI", 11, "bold"))
        self.status_label.pack(anchor="w")
        self.event_label = tk.Label(footer, bg=p["background"], fg=p["muted"],
                                    font=("Segoe UI", 10), justify="left")
        self.event_label.pack(anchor="w", pady=(4, 0))
        self.pause_overlay = None

    def show_menu(self):
        self.state = "menu"
        self.paused = False
        self.motion_active = False
        self.pending_moves.clear()
        self.level_token += 1
        self.stop_music()
        self.hide_challenge()
        self.hide_ads()
        self.hide_pause()
        self.game.pack_forget()
        self.menu.pack(fill="both", expand=True)

    def start_campaign(self):
        self.mode = self.mode_box.get()
        self.campaign_seed = random.SystemRandom().randrange(10**9)
        self.randomizer.seed(self.campaign_seed)
        self.level_number = 1
        self.show_hint = False
        self.hide_pause()
        self.menu.pack_forget()
        self.game.pack(fill="both", expand=True)
        self.load_level()
        self.start_music()

    def load_level(self, restart=False):
        self.hide_challenge()
        self.hide_ads()
        self.hide_pause()
        if self.level_number > TOTAL_LEVELS:
            self.state = "campaign_complete"
            self.show_pause("Campaign complete", "All 30 deliveries are finished.", completed=True)
            return
        self.level_token += 1
        if not restart:
            size = level_size(self.mode, self.level_number, self.campaign_seed)
            seed = self.campaign_seed + self.level_number * 1741
            self.floor = generate_floor(size, self.level_number, seed)
            self.target = self.randomizer.choice(("A", "B"))
            self.route, self.expanded = bfs_trace(self.floor.start, self.floor.wards[self.target],
                                                  size, self.floor.walls)
            previous_theme = self.theme_index
            while self.theme_index == previous_theme:
                self.theme_index = self.randomizer.randint(1, 158)
            self.palette = theme_colors(self.theme_index)
            self.robot_name = "Space Ambulance"
        self.player_position = self.floor.start
        self.position_index = 0
        self.moves = 0
        self.score = 0
        self.energy = max(35, round((len(self.route) - 1) * 2.8))
        self.start_distance = len(self.route) - 1
        self.facing = (1, 0)
        self.scanned_cell = None
        self.hazard_state = None
        self.motion_active = False
        self.motion_from = self.motion_to = None
        self.motion_fraction = 1.0
        self.pending_moves.clear()
        self.hidden_state = "free" if self.randomizer.random() < self.floor.prior else "blocked"
        self.reports = []
        self.bayes_result = self.hmm_result = self.mdp_result = None
        self.challenge_solved = set()
        self.challenge_pending = None
        self.ads_total = 4 + self.level_number
        self.ads_remaining = self.ads_total
        self.ads_pending = True
        self.show_hint = False
        self.state = "running"
        self.paused = False
        self.zoom = max(14, min(110, (self.MAP_H - 34) // self.floor.size))
        self.events.clear()
        self.events.append(f"Drive {self.robot_name} to Ward {self.target}. Clear {self.ads_total} signal tabs.")
        self.update_game()
        self.show_challenge("BFS")

    def change_zoom(self, direction):
        if not self.floor:
            return
        self.zoom = max(8, min(130, self.zoom + direction * 6))
        self.update_game()

    def toggle_pause(self):
        if self.state not in ("running", "challenge", "interference", "paused"):
            return
        if self.paused:
            self.paused = False
            self.state = self.resume_state
            self.hide_pause()
            self.start_music()
        else:
            self.resume_state = self.state
            self.paused = True
            self.state = "paused"
            self.stop_music()
            self.show_pause("Paused", "Take your time. The robot will wait.")
        self.update_game()

    def escape(self, event=None):
        if self.state in ("running", "challenge", "interference", "paused"):
            self.toggle_pause()

    def show_pause(self, heading, description, completed=False, failed=False):
        self.hide_pause()
        p = self.palette
        overlay = tk.Frame(self.game, bg=p["card"], padx=35, pady=30,
                            highlightbackground=p["line"], highlightthickness=2)
        overlay.place(relx=.5, rely=.5, anchor="center")
        tk.Label(overlay, text=heading, bg=p["card"], fg=p["ink"],
                 font=("Segoe UI", 23, "bold")).pack(anchor="w")
        tk.Label(overlay, text=description, bg=p["card"], fg=p["muted"],
                 font=("Segoe UI", 11)).pack(anchor="w", pady=(7, 22))
        if failed:
            self.menu_button(overlay, "Restart level", self.restart_level, primary=True)
        elif not completed:
            self.menu_button(overlay, "Resume", self.toggle_pause, primary=True)
            self.menu_button(overlay, "Restart level", self.restart_level)
        else:
            self.menu_button(overlay, "New campaign", self.start_campaign, primary=True)
        self.menu_button(overlay, "Main menu", self.show_menu)
        self.pause_overlay = overlay

    def hide_pause(self):
        if self.pause_overlay is not None:
            self.pause_overlay.destroy()
            self.pause_overlay = None

    def restart_level(self):
        self.hide_pause()
        self.load_level(restart=True)

    def tick(self):
        try:
            self.tick_count += 1
            self.root.after(150, self.tick)
        except tk.TclError:
            pass

    def animate_motion(self, token):
        if token != self.level_token or self.state == "menu" or not self.motion_active:
            self.motion_active = False
            return
        if self.paused:
            self.root.after(35, lambda: self.animate_motion(token))
            return
        self.motion_fraction = min(1.0, self.motion_fraction + .2)
        self.draw_map()
        if self.motion_fraction < 1.0:
            self.root.after(35, lambda: self.animate_motion(token))
        else:
            self.motion_active = False
            if self.pending_moves and self.state == "running":
                dx, dy = self.pending_moves.popleft()
                self.root.after(1, lambda: self.move(dx, dy))

    def handle_key(self, event):
        if self.state != "running" or self.paused:
            return
        key = event.keysym.lower()
        directions = {"up": (0, -1), "w": (0, -1), "left": (-1, 0), "a": (-1, 0),
                      "down": (0, 1), "s": (0, 1), "right": (1, 0), "d": (1, 0)}
        if key in directions:
            self.move(*directions[key])
        elif key == "e":
            self.scan_front()
        elif key == "space":
            self.wait_turn()
        elif key == "h":
            self.toggle_hint()

    def front_cell(self):
        return (self.player_position[0] + self.facing[0],
                self.player_position[1] + self.facing[1])

    def valid_cell(self, cell):
        x, y = cell
        return 0 <= x < self.floor.size and 0 <= y < self.floor.size and cell not in self.floor.walls

    def scan_front(self):
        if self.state != "running" or self.paused or self.motion_active:
            return
        cell = self.front_cell()
        if not self.valid_cell(cell):
            self.events.append("Scanner sees a wall. Turn toward a corridor.")
            self.update_game()
            return
        if self.scanned_cell != cell or self.hazard_state is None:
            old = self.hidden_state
            self.hidden_state = ("free" if self.randomizer.random() < HMM_TRANSITION[old]["free"]
                                 else "blocked")
            self.hazard_state = self.hidden_state
            self.scanned_cell = cell
        p_clear = self.floor.sensitivity if self.hazard_state == "free" else self.floor.false_alarm
        report = "CLEAR" if self.randomizer.random() < p_clear else "ALERT"
        self.reports.append(report)
        p_free, free_part, blocked_part = bayes_free(
            report, self.floor.prior, self.floor.sensitivity, self.floor.false_alarm)
        self.bayes_result = (report, p_free, free_part, blocked_part)
        if len(self.reports) >= 3:
            self.hmm_result = viterbi(self.reports[-3:], self.floor.prior,
                                      self.floor.sensitivity, self.floor.false_alarm)
        self.mdp_result = mdp_decision(p_free)
        self.energy -= 1
        self.events.append(f"Scan {cell}: {report}. MDP suggests {self.mdp_result[0].title()}.")
        self.check_energy()
        self.update_game()

    def move(self, dx, dy):
        if self.state != "running" or self.paused:
            return
        if self.motion_active:
            self.pending_moves.append((dx, dy))
            return
        direction = (dx, dy)
        if direction != self.facing:
            self.facing = direction
            self.scanned_cell = None
            self.hazard_state = None
        cell = self.front_cell()
        if not self.valid_cell(cell):
            self.energy -= 1
            self.score = max(0, self.score - 2)
            self.events.append("Wall ahead. Choose another direction.")
            self.check_energy()
            self.update_game()
            return
        if cell == self.floor.wards[self.target] and "MDP" not in self.challenge_solved:
            self.show_challenge("MDP", pending_move=(dx, dy))
            return
        if self.scanned_cell != cell or self.hazard_state is None:
            self.scan_front()
        if self.state != "running":
            return
        risky = self.mdp_result is not None and self.mdp_result[0] == "PAUSE"
        previous_cell = self.player_position
        self.player_position = cell
        self.moves += 1
        self.score += 2 if risky else 5
        self.energy -= 2 if risky else 1
        self.scanned_cell = self.hazard_state = None
        self.route, self.expanded = bfs_trace(self.player_position,
                                              self.floor.wards[self.target],
                                              self.floor.size, self.floor.walls)
        self.motion_from = previous_cell
        self.motion_to = cell
        self.motion_fraction = 0.0
        self.motion_active = True
        token = self.level_token
        self.root.after(35, lambda: self.animate_motion(token))
        if cell == self.floor.wards[self.target]:
            self.state = "level_complete"
            self.events.append(f"Ward {self.target} reached. Level complete!")
            self.sound("complete")
            self.root.after(1600, lambda: self.advance_level(token))
        else:
            self.events.append((f"Moved to {cell} despite sensor warning; extra energy used."
                                if risky else f"Moved to {cell}. Choose the next step."))
            self.check_energy()
        self.update_game()
        self.trigger_challenge()

    def trigger_challenge(self):
        if self.state != "running":
            return
        bayes_step = max(2, self.start_distance // 3)
        hmm_step = max(4, (self.start_distance * 2) // 3)
        if "Bayes" not in self.challenge_solved and self.moves >= bayes_step and self.bayes_result:
            self.show_challenge("Bayes")
        elif ("HMM" not in self.challenge_solved and self.moves >= hmm_step
              and self.hmm_result is not None):
            self.show_challenge("HMM")

    def wait_turn(self):
        if self.state != "running" or self.paused or self.motion_active:
            return
        self.energy -= 1
        self.scanned_cell = self.hazard_state = None
        self.events.append("Waited one turn. The corridor may change.")
        self.check_energy()
        self.update_game()

    def toggle_hint(self):
        if self.state != "running":
            return
        if not self.show_hint:
            cost = max(18, round(max(35, self.start_distance * 2.8) * .5))
            if self.energy <= cost:
                self.events.append(f"Route hint needs {cost} Energy. Current Energy: {self.energy}.")
                self.update_game()
                return
            self.energy -= cost
            self.events.append(f"BFS route hint on. Signal boost cost {cost} Energy.")
        else:
            self.events.append("BFS route hint off.")
        self.show_hint = not self.show_hint
        self.update_game()

    def show_challenge(self, kind, pending_move=None):
        if self.state != "running" or kind in self.challenge_solved:
            return
        self.hide_challenge()
        self.state = "challenge"
        self.challenge_kind = kind
        self.challenge_pending = pending_move
        p = self.palette
        if kind == "BFS":
            distance = len(self.route) - 1
            prompt = (f"The route to Ward {self.target} is highlighted for this task. BFS explored "
                      f"{self.expanded} cells. How many moves are in the shortest route?")
            answer = distance
            options = [max(1, distance - 2), distance, distance + 2]
            explanation = (f"BFS explores neighbors in distance order. The route has "
                           f"{len(self.route)} cells, so it has {distance} moves (edges).")
        elif kind == "Bayes":
            report, probability, first, other = self.bayes_result
            prompt = (f"Sensor report: {report}. Prior P(free)={self.floor.prior:.0%}; "
                      f"P(CLEAR|free)={self.floor.sensitivity:.0%}; "
                      f"P(CLEAR|blocked)={self.floor.false_alarm:.0%}. "
                      "What is P(free | report), rounded to a whole percent?")
            answer = round(probability * 100)
            options = list(dict.fromkeys((answer, round(self.floor.prior * 100),
                                          round((1 - probability) * 100))))
            while len(options) < 3:
                options.append((answer + 13 * len(options)) % 100)
            explanation = (f"Bayes: {first:.3f} / ({first:.3f} + {other:.3f}) "
                           f"= {probability:.1%}. The new probability uses one noisy report.")
        elif kind == "HMM":
            path, trace = self.hmm_result
            prompt = ("Three reports: " + " → ".join(self.reports[-3:]) +
                      ". Hidden states are FREE and BLOCKED. "
                      f"Initial P(free)={self.floor.prior:.0%}; "
                      f"P(CLEAR|free)={self.floor.sensitivity:.0%}; "
                      f"P(CLEAR|blocked)={self.floor.false_alarm:.0%}. "
                      "Transitions: F→F 80%, F→B 20%, B→F 30%, B→B 70%. "
                      "What is the final state in the most likely Viterbi path?")
            answer = path[-1].upper()
            options = ["FREE", "BLOCKED"]
            explanation = ("Viterbi path: " + " → ".join(state.upper() for state in path) +
                           f". Final scores: F={trace[-1]['free']:.3f}, "
                           f"B={trace[-1]['blocked']:.3f}.")
        else:  # MDP
            probability = self.bayes_result[1] if self.bayes_result else self.floor.prior
            answer, q = mdp_decision(probability)
            prompt = (f"P(free)={probability:.1%}. Continue rewards: +10 free, −20 blocked. "
                      "Pause rewards: −2 free, +2 blocked. Which action has the "
                      "higher one-step expected reward?")
            options = ["CONTINUE", "PAUSE"]
            explanation = (f"Q(Continue)={q['CONTINUE']:+.2f}; "
                           f"Q(Pause)={q['PAUSE']:+.2f}. Choose {answer}.")
        self.challenge_answer = answer
        self.challenge_explanation = explanation
        self.randomizer.shuffle(options)
        overlay = tk.Frame(self.game, bg=p["card"], padx=18, pady=20,
                            highlightbackground=p["accent"], highlightthickness=2)
        overlay.place(relx=1.0, x=-20, y=105, anchor="ne", width=380)
        tk.Label(overlay, text=f"{kind.upper()} CHALLENGE", bg=p["card"], fg=p["accent"],
                 font=("Segoe UI", 19, "bold")).pack(anchor="w", pady=(0, 12))
        tk.Label(overlay, text=prompt, bg=p["card"], fg=p["ink"],
                 wraplength=330, justify="left", font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 14))
        answers = tk.Frame(overlay, bg=p["card"])
        answers.pack(fill="x")
        for option in options:
            suffix = "%" if kind == "Bayes" else " moves" if kind == "BFS" else ""
            tk.Button(answers, text=f"{option}{suffix}",
                      command=lambda option=option: self.answer_challenge(option),
                      bg=p["background"], fg=p["ink"], activebackground=p["line"],
                      activeforeground=p["ink"], relief="flat", font=("Segoe UI", 11, "bold"),
                      padx=15, pady=8).pack(fill="x", pady=4)
        feedback = tk.Label(overlay, text="A correct answer moves the robot one step.",
                            bg=p["card"], fg=p["muted"], wraplength=330,
                            justify="left", font=("Segoe UI", 10))
        feedback.pack(anchor="w", pady=(12, 0))
        self.challenge_overlay = overlay
        self.challenge_answers = answers
        self.challenge_feedback = feedback
        self.update_game()

    def answer_challenge(self, answer):
        if self.state != "challenge":
            return
        if answer != self.challenge_answer:
            self.challenge_feedback.configure(text="Not quite. Try another answer.",
                                              fg="#c9a09b")
            self.sound("warning")
            return
        self.challenge_solved.add(self.challenge_kind)
        self.score += 15
        for child in self.challenge_answers.winfo_children():
            child.destroy()
        self.challenge_feedback.configure(text=self.challenge_explanation,
                                          fg=self.palette["ink"])
        tk.Button(self.challenge_answers, text="Continue · move one step",
                  command=self.continue_challenge,
                  bg=self.palette["accent"], fg="#112021", relief="flat",
                  font=("Segoe UI", 11, "bold"), padx=14, pady=9).pack(fill="x", pady=6)
        self.sound("correct")

    def continue_challenge(self):
        pending = self.challenge_pending
        self.hide_challenge()
        self.state = "running"
        self.update_game()
        if pending is None and len(self.route) > 1:
            next_cell = self.route[1]
            pending = (next_cell[0] - self.player_position[0],
                       next_cell[1] - self.player_position[1])
        if pending is not None:
            self.move(*pending)
        if self.state == "running" and self.ads_pending:
            self.show_ads()

    def hide_challenge(self):
        if self.challenge_overlay is not None:
            self.challenge_overlay.destroy()
            self.challenge_overlay = None
        self.challenge_kind = None
        self.challenge_pending = None

    def show_ads(self):
        if not self.ads_pending or self.state != "running":
            return
        self.ads_pending = False
        self.state = "interference"
        self.render_ads()
        self.update_game()

    def render_ads(self):
        self.hide_ads()
        if self.ads_remaining <= 0:
            self.state = "running"
            self.events.append("Signal clear. Ambulance controls restored.")
            self.update_game()
            return
        p = self.palette
        closed = self.ads_total - self.ads_remaining
        overlay = tk.Frame(self.game, bg=p["card"], padx=20, pady=17,
                           highlightbackground=p["accent"], highlightthickness=2)
        overlay.place(x=44, y=130, width=655, height=405)
        tk.Label(overlay, text="SIGNAL INTERFERENCE", bg=p["card"], fg=p["accent"],
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(overlay, text=f"Close every incoming tab · {closed}/{self.ads_total} cleared",
                 bg=p["card"], fg=p["muted"], font=("Segoe UI", 11)).pack(anchor="w", pady=(4, 15))
        tabs = tk.Frame(overlay, bg=p["card"])
        tabs.pack(fill="x")
        visible = min(5, self.ads_remaining)
        for i in range(visible):
            number = closed + i + 1
            button = tk.Button(tabs, text=f"{number:02d}  ×", command=self.close_ad,
                               bg=p["background"], fg=p["ink"], activebackground=p["line"],
                               relief="flat", font=("Segoe UI", 11, "bold"), padx=10, pady=7)
            button.grid(row=0, column=i, padx=(0, 7), sticky="ew")
            tabs.grid_columnconfigure(i, weight=1)
        messages = (
            "Medical dispatch channel is busy.",
            "Navigation beacon requests attention.",
            "Supply manifest notification received.",
            "Station bulletin is covering the map.",
            "Emergency comms need a clear screen.",
        )
        tk.Label(overlay, text=messages[closed % len(messages)], bg=p["card"], fg=p["ink"],
                 font=("Segoe UI", 15), wraplength=570).pack(anchor="w", pady=(45, 10))
        tk.Label(overlay, text="Select each × tab above. New tabs appear until the queue is empty.",
                 bg=p["card"], fg=p["muted"], font=("Segoe UI", 11),
                 wraplength=570).pack(anchor="w")
        self.ad_overlay = overlay

    def close_ad(self):
        if self.state != "interference" or self.ads_remaining <= 0 or self.paused:
            return
        self.ads_remaining -= 1
        self.sound("correct")
        self.render_ads()

    def hide_ads(self):
        if self.ad_overlay is not None:
            self.ad_overlay.destroy()
            self.ad_overlay = None

    def check_energy(self):
        if self.energy > 0 or self.state != "running":
            return
        self.state = "failed"
        self.events.append("Battery empty. Restart the level to try again.")
        self.show_pause("Battery empty", "Try a shorter route and scan before risky moves.", failed=True)

    def advance_level(self, token):
        if self.state != "level_complete" or token != self.level_token:
            return
        self.level_number += 1
        self.load_level()

    def sound(self, kind):
        if not self.sound_on.get():
            return
        try:
            import winsound
            freq, duration = {"complete": (750, 120), "move": (430, 35),
                              "warning": (250, 70)}.get(kind, (450, 50))
            threading.Thread(target=winsound.Beep, args=(freq, duration), daemon=True).start()
        except ImportError:
            pass

    def start_music(self):
        if not self.music_on.get() or self.state == "menu":
            return
        path = Path(__file__).with_name("medbot_theme.wav")
        if not path.exists():
            return
        try:
            import winsound
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        except (ImportError, RuntimeError):
            pass

    @staticmethod
    def stop_music():
        try:
            import winsound
            winsound.PlaySound(None, 0)
        except (ImportError, RuntimeError):
            pass

    def toggle_music(self):
        if self.music_on.get() and self.state not in ("menu", "paused"):
            self.start_music()
        else:
            self.stop_music()

    def update_game(self):
        if not self.floor:
            return
        p = self.palette
        self.game.configure(bg=p["background"])
        self.level_title.configure(text=f"Level {self.level_number:02d} / {TOTAL_LEVELS}     ·     {self.floor.size} × {self.floor.size}     ·     Ward {self.target}",
                                   bg=p["background"], fg=p["ink"])
        if self.state == "challenge":
            motion_text = f"Solve the {self.challenge_kind} challenge to advance one step"
        elif self.state == "interference":
            motion_text = f"Signal interference · close {self.ads_remaining} remaining tabs"
        elif self.state == "level_complete":
            motion_text = "Delivery complete · next level starting"
        elif self.paused:
            motion_text = "Paused by player"
        elif self.state == "failed":
            motion_text = "Battery empty · restart the level"
        else:
            motion_text = (f"Your turn · {self.robot_name} at {self.player_position} · "
                           f"Energy {self.energy} · Score {self.score} · Moves {self.moves}")
        self.status_label.configure(text=motion_text,
                                    bg=p["background"], fg=p["ink"])
        self.event_label.configure(text="   •   ".join(self.events), bg=p["background"], fg=p["muted"])
        self.view_label.configure(text=f"View: {self.zoom}px  ·  {STYLE_NAMES[p['family']]}  ·  Look {self.theme_index}/158",
                                  bg=p["background"], fg=p["muted"])
        self.info_cards["bfs"].configure(
            text=f"From {self.player_position} to Ward {self.target}. "
                 f"Expanded {self.expanded} cells; {max(0,len(self.route)-1)} moves remain. "
                 f"Press H to {'hide' if self.show_hint else 'show'} the route.")
        if self.state == "challenge" and self.challenge_kind == "BFS":
            self.info_cards["bfs"].configure(
                text=f"BFS expanded {self.expanded} cells. Count the highlighted route moves.")
        if self.bayes_result:
            report, prob, first, second = self.bayes_result
            bayes_text = (f"Input: {report}, prior {self.floor.prior:.0%}.\n"
                          f"{first:.3f} / ({first:.3f} + {second:.3f}) = {prob:.1%} free.")
        else:
            bayes_text = "Face a corridor and press E to scan. Moving also triggers a scan."
        if self.state == "challenge" and self.challenge_kind == "Bayes":
            bayes_text = f"Report: {self.bayes_result[0]}. Use the prior and sensor likelihoods to calculate P(free)."
        self.info_cards["bayes"].configure(text=bayes_text)
        if self.hmm_result:
            states, trace = self.hmm_result
            hmm_text = ("Reports: " + " → ".join(self.reports[-3:]) + "\n"
                        "Viterbi: " + " → ".join(s.title() for s in states) +
                        f"\nFinal scores: F {trace[-1]['free']:.3f}, B {trace[-1]['blocked']:.3f}.")
        else:
            hmm_text = f"Collecting reports: {len(self.reports[-3:])}/3. Two hidden states."
        if self.state == "challenge" and self.challenge_kind == "HMM":
            hmm_text = "Reports: " + " → ".join(self.reports[-3:]) + ". Compute the final hidden state."
        self.info_cards["hmm"].configure(text=hmm_text)
        if self.mdp_result:
            action, q = self.mdp_result
            mdp_text = (f"Q(Continue) {q['CONTINUE']:+.2f}   Q(Pause) {q['PAUSE']:+.2f}\n"
                        f"Advice: {action.title()}. You decide whether to move or wait.")
        else:
            mdp_text = "The adviser compares Move and Wait after a scan."
        if self.state == "challenge" and self.challenge_kind == "MDP":
            mdp_text = "Use P(free) and rewards to compare Q(Continue) and Q(Pause)."
        self.info_cards["mdp"].configure(text=mdp_text)
        for key, label in self.info_cards.items():
            label.master.configure(bg=p["card"], highlightbackground=p["line"])
            label.master.winfo_children()[0].configure(bg=p["card"], fg=p["ink"])
            label.configure(bg=p["card"], fg=p["muted"])
        self.map_canvas.configure(bg=p["floor"])
        self.draw_map()

    def draw_map(self):
        c = self.map_canvas
        c.delete("all")
        if not self.floor:
            return
        p = self.palette
        size = self.floor.size
        tile = self.zoom
        width_cells = min(size, max(1, self.MAP_W // tile))
        map_height = self.MAP_H - 34
        height_cells = min(size, max(1, map_height // tile))
        target_x, target_y = self.player_position
        if self.motion_active and self.motion_from and self.motion_to:
            from_x, from_y = self.motion_from
            to_x, to_y = self.motion_to
            robot_cell_x = from_x + (to_x - from_x) * self.motion_fraction
            robot_cell_y = from_y + (to_y - from_y) * self.motion_fraction
        else:
            robot_cell_x, robot_cell_y = target_x, target_y
        left = max(0, min(size - width_cells, round(robot_cell_x) - width_cells // 2))
        top = max(0, min(size - height_cells, round(robot_cell_y) - height_cells // 2))
        if size <= width_cells:
            left = 0
        if size <= height_cells:
            top = 0
        offset_x = (self.MAP_W - min(size, width_cells) * tile) // 2
        offset_y = 34 + (map_height - min(size, height_cells) * tile) // 2
        route_cells = set(self.route) if (self.show_hint or
                      (self.state == "challenge" and self.challenge_kind == "BFS")) else set()
        family = p["family"]
        for y in range(top, min(size, top + height_cells)):
            for x in range(left, min(size, left + width_cells)):
                cell = (x, y)
                x1 = offset_x + (x - left) * tile
                y1 = offset_y + (y - top) * tile
                wall = cell in self.floor.walls
                fill = p["wall"] if wall else p["floor"]
                c.create_rectangle(x1, y1, x1 + tile, y1 + tile, fill=fill,
                                   outline=p["line"] if tile >= 18 else fill, width=1)
                if not wall and family == 1 and tile >= 22:
                    c.create_rectangle(x1+3,y1+3,x1+7,y1+7,fill=p["line"],outline="")
                elif not wall and family == 2 and tile >= 22:
                    c.create_line(x1+3,y1+tile-5,x1+tile-3,y1+tile-5,fill=p["line"])
                elif not wall and family == 3 and tile >= 22:
                    c.create_oval(x1+4,y1+4,x1+9,y1+9,fill=p["path"],outline="")
                if cell in route_cells and not wall:
                    margin = max(1, tile // 3)
                    c.create_oval(x1+margin,y1+margin,x1+tile-margin,y1+tile-margin,
                                  fill=p["path"],outline="")
                if cell == self.floor.start or cell in self.floor.wards.values():
                    if tile >= 24:
                        label = "S" if cell == self.floor.start else "A" if cell == self.floor.wards["A"] else "B"
                        c.create_rectangle(x1+2,y1+2,x1+tile-2,y1+tile-2,
                                           outline=p["accent"],width=2)
                        c.create_text(x1+tile/2,y1+tile/2,text=label,fill=p["ink"],
                                      font=("Segoe UI",max(10,min(18,tile//3)),"bold"))
        robot_x = offset_x + (robot_cell_x - left) * tile + tile/2
        robot_y = offset_y + (robot_cell_y - top) * tile + tile/2
        marker_radius = max(17, min(tile * .48, 34))
        c.create_oval(robot_x-marker_radius, robot_y-marker_radius,
                      robot_x+marker_radius, robot_y+marker_radius,
                      fill=p["highlight"], outline=p["accent"], width=3)
        self.draw_character(c, robot_x, robot_y, max(30, min(tile * .75, 55)),
                            self.robot_name, p["accent"])
        c.create_line(robot_x, robot_y, robot_x+self.facing[0]*marker_radius*1.7,
                      robot_y+self.facing[1]*marker_radius*1.7,
                      fill=p["ink"], width=3, arrow=tk.LAST)
        c.create_rectangle(0, 0, self.MAP_W, 28, fill=p["card"], outline="")
        c.create_text(12, 14, anchor="w", text=f"{self.floor.size}×{self.floor.size} station    Ambulance {target_x},{target_y}    Ward {self.target} →",
                      fill=p["ink"], font=("Segoe UI", 10))
        progress = 1 - (len(self.route) - 1) / max(1, self.start_distance)
        progress = max(0, min(1, progress))
        c.create_rectangle(0, self.MAP_H-7, self.MAP_W, self.MAP_H,
                           fill=p["line"], outline="")
        c.create_rectangle(0, self.MAP_H-7, self.MAP_W*progress, self.MAP_H,
                           fill=p["accent"], outline="")

    @staticmethod
    def draw_character(canvas, x, y, scale, name, accent):
        s = scale / 55
        hull = "#c5d1cc"
        glass = "#476973"
        cross = "#a86d69"
        dark = "#1a3034"
        canvas.create_polygon(x,y-26*s,x+13*s,y-12*s,x+13*s,y+16*s,
                              x-13*s,y+16*s,x-13*s,y-12*s,
                              fill=hull,outline=dark,width=2)
        canvas.create_polygon(x,y-22*s,x+9*s,y-12*s,x-9*s,y-12*s,
                              fill=glass,outline=dark,width=1)
        for side in (-1,1):
            canvas.create_rectangle(x+(side*13-5)*s,y+1*s,x+(side*13+5)*s,y+14*s,
                                    fill=accent,outline=dark,width=1)
            canvas.create_oval(x+(side*13-4)*s,y+14*s,x+(side*13+4)*s,y+22*s,
                               fill="#667b83",outline=dark,width=1)
        canvas.create_rectangle(x-3*s,y-5*s,x+3*s,y+10*s,fill=cross,outline="")
        canvas.create_rectangle(x-8*s,y+0*s,x+8*s,y+5*s,fill=cross,outline="")
        canvas.create_line(x-11*s,y-13*s,x-18*s,y-20*s,fill=accent,width=2)
        canvas.create_line(x+11*s,y-13*s,x+18*s,y-20*s,fill=accent,width=2)

    def show_tutorial(self):
        p = self.palette
        window = tk.Toplevel(self.root)
        window.title("How to play Orbital Ambulance")
        window.geometry("700x590")
        window.configure(bg=p["background"])
        dark_titlebar(window)
        content = (
            "HOW TO PLAY\n\n"
            "1. On the menu, choose a map size. Random picks a new size on every level. "
            "A 5×5 station can be followed by a 100×100 station. Click Ready · start mission.\n\n"
            "2. First solve the BFS route question. A correct answer shows the explanation and "
            "moves the space ambulance one step. Then close every Signal Interference tab "
            "by clicking its ×. Level 1 has five tabs and every later level adds one. "
            "After clearing the tabs, use arrow keys, W/A/S/D, or the direction buttons. "
            "The BFS route hint starts off. Press H to reveal it; each activation costs "
            "half the level's starting Energy. Turning it off is free.\n\n"
            "3. Face a corridor and press E (or click Scan) to read its sensor. Every move also scans "
            "automatically. Bayes updates the free-hallway probability. HMM uses the latest three reports. "
            "MDP recommends moving or waiting, but YOU choose the action.\n\n"
            "4. Bayes and HMM questions appear later along the route. The MDP question appears "
            "before the final delivery step. Each correct answer unlocks one step and shows the "
            "calculation. Between questions, every arrow press moves one tile if the map cell is open. "
            "Only visible walls stop movement. "
            "A sensor warning never locks the controls; moving against MDP advice uses extra Energy. "
            "Press Space (or Wait) if you want another scan before moving. Reaching the ward completes "
            "the level; the next level starts automatically.\n\n"
            "5. Click Pause, or press Esc, to stop the game. Resume, restart the level, "
            "or return to the main menu.\n\n"
            "6. The menu has separate Background music and Sound effects switches. "
            "There are 30 levels. Each changes the station map. Difficulty rises through more walls "
            "and less reliable sensing. A random visual look is chosen on every level.\n\n"
            "PROJECT NOTE\nTopic 14 requires BFS, Bayes and MDP. HMM is an extra demonstration. "
            "All probabilities and rewards are teaching assumptions; no patient data is used."
        )
        area = ScrolledText(window, wrap="word", bg=p["card"], fg=p["ink"],
                            font=("Segoe UI", 11), padx=20, pady=18, relief="flat")
        area.insert("1.0", content)
        area.configure(state="disabled")
        area.pack(fill="both", expand=True, padx=20, pady=(20, 10))
        tk.Button(window, text="Close", command=window.destroy, bg=p["accent"], fg="white",
                  font=("Segoe UI", 11, "bold"), relief="flat", padx=20, pady=8).pack(pady=(0, 18))


def main():
    root = tk.Tk()
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()
