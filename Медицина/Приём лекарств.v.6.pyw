"""
Інтерактивний графік прийому ліків v5
- Історія прийому по днях
- Нагадування за розкладом (вкл/викл)
- Експорт звіту для лікаря (HTML)
- Клікабельні назви препаратів — пошук в інтернеті
- Пошук в аптеках (tabletki.ua)
Бучин Андрій Петрович, 1954 р.н. | Складено: квітень 2026
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
import calendar
import webbrowser
import winsound
import urllib.parse
from datetime import datetime, timedelta

# --- Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0] if sys.argv[0] else __file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "med_state_v5.json")

# --- Colors ---
C = {
    "bg": "#F5F0EB",
    "header_bg": "#2C3E50",
    "header_fg": "#FFFFFF",
    "morning_accent": "#388E3C",
    "day_accent": "#F57F17",
    "evening_accent": "#1565C0",
    "sos_accent": "#C62828",
    "card_bg": "#FFFFFF",
    "text": "#212121",
    "subtext": "#616161",
    "border": "#E0E0E0",
    "purchased_on": "#4CAF50",
    "taken_on": "#2196F3",
    "course_long": "#388E3C",
    "course_2m": "#F57F17",
    "course_short": "#C62828",
    "course_need": "#7B1FA2",
    "expand_bg": "#FAFAFA",
    "notes_bg": "#FFF9C4",
    "date_nav_bg": "#34495E",
    "cal_full": "#4CAF50",
    "cal_partial": "#FFC107",
    "cal_empty": "#EEEEEE",
    "cal_none": "#FFFFFF",
    "cal_today_border": "#2196F3",
    "stat_good": "#4CAF50",
    "stat_warn": "#FF9800",
    "stat_bad": "#F44336",
    "reminder_on": "#4CAF50",
    "reminder_off": "#9E9E9E",
    "toast_bg": "#1565C0",
    "toast_fg": "#FFFFFF",
}

COURSE_COLORS = {
    "long": C["course_long"], "2m": C["course_2m"],
    "short": C["course_short"], "need": C["course_need"],
}

# --- Medication data ---
MEDICATIONS = [
    {
        "section": "РАНОК (сніданок 09:00 - 10:00)", "section_key": "morning",
        "items": [
            {"id": "tamsin", "time": "08:30", "time_note": "до їжі",
             "name": "Тамсін Форте", "subtitle": "", "note": "Натщесерце",
             "course": "Тривало", "course_type": "long", "pharmacy": "Тамсін Форте",
             "description": "Тамсулозин - альфа-1-адреноблокатор.\nПризначення: лікування ДГПЗ.\nПрийом: натщесерце, за 30 хв до їжі.\nПобічні ефекти: запаморочення, зниження АТ."},
            {"id": "olidetrim", "time": "09:00", "time_note": "з їжею",
             "name": "Олідетрім 4000", "subtitle": "вітамін D3",
             "note": "З їжею, що містить жири", "course": "2 міс, потім 2000 тривало", "course_type": "2m",
             "pharmacy": "Олідетрім 4000",
             "description": "Вітамін D3 4000 МО.\nПрийом: з їжею з жирами.\nКурс: 4000 МО — 2 міс, потім 2000 МО тривало.\nКонтроль: 25(OH)D через 2-3 міс."},
            {"id": "vitk2", "time": "09:00", "time_note": "з їжею",
             "name": "Вітамін К2", "subtitle": "", "note": "Разом з D3, з їжею",
             "course": "Тривало", "course_type": "long", "pharmacy": "Вітамін К2",
             "description": "Менахінон (К2, MK-7).\nСпрямовує кальцій у кістки, запобігає кальцифікації артерій.\nПрийом: разом з D3, з їжею."},
            {"id": "glutargin1", "time": "09:00", "time_note": "з їжею",
             "name": "Глутаргін 750 мг", "subtitle": "1-й прийом",
             "note": "Гепатопротектор", "course": "2 місяці", "course_type": "2m",
             "pharmacy": "Глутаргін",
             "description": "Аргініну глутамат 750 мг.\nГепатопротектор. 2 р/день. Курс: 2 міс."},
            {"id": "augmentin", "time": "09:00", "time_note": "з їжею",
             "name": "Аугментин", "subtitle": "антибіотик",
             "note": "З їжею, для захисту ШКТ", "course": "5-7 днів", "course_type": "short",
             "pharmacy": "Аугментин",
             "description": "Амоксицилін + клавуланова к-та.\nАнтибіотик, стоматологічне призначення.\nКурс не переривати! Пробіотик через ~6 год."},
            {"id": "neurorubin1", "time": "10:30", "time_note": "після їжі",
             "name": "Нейрорубін форте", "subtitle": "Лактаб, 1-й прийом",
             "note": "Вітаміни групи В", "course": "2 місяці", "course_type": "2m",
             "pharmacy": "Нейрорубін",
             "description": "Вітаміни B1, B6, B12.\nЛікування невралгій, зниження гомоцистеїну.\n2 р/день, після їжі. Курс: 2 міс."},
            {"id": "serrata", "time": "10:30", "time_note": "після їжі",
             "name": "Серрата", "subtitle": "протинабрякове",
             "note": "Через 30 хв після їжі", "course": "5-7 днів", "course_type": "short",
             "pharmacy": "Серрата",
             "description": "Серратіопептидаза.\nПротинабрякова дія після стоматологічного втручання.\nЧерез 30 хв після їжі. Курс: 5-7 днів."},
        ],
    },
    {
        "section": "ДЕНЬ (обід 14:00 - 15:00)", "section_key": "day",
        "items": [
            {"id": "voger", "time": "13:30", "time_note": "до їжі",
             "name": "Вогер", "subtitle": "", "note": "За 30 хв до їжі, гастропротектор",
             "course": "Тривало", "course_type": "long", "pharmacy": "Вогер",
             "description": "Ребаміпід — гастропротектор.\nЗахист слизової шлунка. За 30 хв до їжі."},
            {"id": "nimesil", "time": "14:00", "time_note": "з їжею",
             "name": "Німесіл", "subtitle": "протизапальне",
             "note": "З їжею або після їжі", "course": "5-7 днів", "course_type": "short",
             "pharmacy": "Німесіл",
             "description": "Німесулід — НПЗП.\nЗнеболення (стоматологічне). З їжею. Курс: 5-7 днів."},
            {"id": "renohels", "time": "14:00", "time_note": "з їжею",
             "name": "Ренохелс", "subtitle": "нефропротектор",
             "note": "З їжею", "course": "Тривало", "course_type": "long",
             "pharmacy": "Ренохелс",
             "description": "Нефропротектор рослинного походження.\nЗ їжею. Курс: тривало."},
            {"id": "probiotic", "time": "16:00", "time_note": "після їжі",
             "name": "Пробіотик", "subtitle": "",
             "note": "Через 2 год після антибіотика!", "course": "5-7 днів + 1 тиж.", "course_type": "short",
             "pharmacy": "Пробіотик",
             "description": "Лакто-/біфідобактерії.\nЧерез ~6 год після Аугментину.\nКурс: 5-7 днів + 1 тиждень після."},
        ],
    },
    {
        "section": "ВЕЧІР (вечеря 18:00 - 19:00)", "section_key": "evening",
        "items": [
            {"id": "glutargin2", "time": "18:00", "time_note": "з їжею",
             "name": "Глутаргін 750 мг", "subtitle": "2-й прийом",
             "note": "Гепатопротектор", "course": "2 місяці", "course_type": "2m",
             "pharmacy": "Глутаргін",
             "description": "Глутаргін (2-й прийом). Добова доза: 1500 мг."},
            {"id": "pregabalin", "time": "18:00", "time_note": "з їжею",
             "name": "Прегабалін", "subtitle": "невралгія",
             "note": "Дозу уточнити у лікаря", "course": "За призначенням", "course_type": "need",
             "pharmacy": "Прегабалін",
             "description": "Прегабалін — нейропатичний біль.\nДозу призначає лікар. Не припиняти різко!"},
            {"id": "atoris", "time": "20:00", "time_note": "після їжі",
             "name": "Аторіс 20 мг", "subtitle": "статин",
             "note": "Ввечері, статини найефективніші вночі", "course": "Тривало", "course_type": "long",
             "pharmacy": "Аторіс",
             "description": "Аторвастатин 20 мг — статин.\nЗниження холестерину. Ввечері.\nКонтроль: ліпідограма, ГГТ через 2-3 міс."},
            {"id": "clopidogrel", "time": "20:00", "time_note": "після їжі",
             "name": "Клопідогрель 75 мг", "subtitle": "антиагрегант",
             "note": "Ввечері, тривало", "course": "Тривало", "course_type": "long",
             "pharmacy": "Клопідогрель",
             "description": "Антиагрегант. Профілактика тромбоутворення.\nВвечері. Курс: тривало."},
            {"id": "neurorubin2", "time": "20:00", "time_note": "після їжі",
             "name": "Нейрорубін форте", "subtitle": "Лактаб, 2-й прийом",
             "note": "Вітаміни групи В", "course": "2 місяці", "course_type": "2m",
             "pharmacy": "Нейрорубін",
             "description": "Вітаміни B (2-й прийом). Добова доза: 2 таблетки."},
        ],
    },
    {
        "section": "ЗА ПОТРЕБОЮ (SOS)", "section_key": "sos",
        "items": [
            {"id": "captopril", "time": "SOS", "time_note": "",
             "name": "Каптоприл (каптопрес)", "subtitle": "",
             "note": "1 таб під язик при підвищенні АТ", "course": "За потребою", "course_type": "need",
             "pharmacy": "Каптопрес",
             "description": "Каптоприл — екстрене зниження АТ.\n1 таб під язик. Дія через 15-30 хв.\nЯкщо немає ефекту — виклик швидкої."},
        ],
    },
]

IMPORTANT_NOTES = [
    "Роксера виключена зі списку — дублює Аторіс (два статини одночасно НЕ можна).",
    "Аугментин і Пробіотик рознесені на ~6 годин для ефективності пробіотика.",
    "Німесіл на обід, Клопідогрель на вечір — мінімізація ризику кровотечі.",
    "Серрата рознесена з Клопідогрелем (обидва впливають на згортання крові).",
    "Стоматологічні (Аугментин, Німесіл, Серрата, Пробіотик) — 5-7 днів.",
    "Контроль через 2-3 міс: HbA1c, глюкоза, гомоцистеїн, ліпідограма, ГГТ, D3, ТТГ.",
    "Дієта: обмеження тваринних жирів, кави; гіповуглеводна дієта.",
]

ALL_DAILY_IDS = []
for _sec in MEDICATIONS:
    for _item in _sec["items"]:
        if _item["course_type"] != "need":
            ALL_DAILY_IDS.append(_item["id"])

# Build reminder schedule: {time_str: [list of items]}
REMINDER_SCHEDULE = {}
for _sec in MEDICATIONS:
    for _item in _sec["items"]:
        t = _item["time"]
        if t == "SOS":
            continue
        REMINDER_SCHEDULE.setdefault(t, []).append(_item)

REMINDER_TIMES_SORTED = sorted(REMINDER_SCHEDULE.keys())

WEEKDAYS_UA = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
MONTHS_UA = [
    "", "Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
    "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень",
]
MONTHS_UA_GEN = [
    "", "січня", "лютого", "березня", "квітня", "травня", "червня",
    "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
]


def date_key(dt):
    return dt.strftime("%Y-%m-%d")


def format_date_ua(dt):
    return f"{WEEKDAYS_UA[dt.weekday()]}, {dt.day} {MONTHS_UA_GEN[dt.month]} {dt.year}"


# ═════════════════════════════════════════════════════════════════════════
class ToastNotification(tk.Toplevel):
    """Small popup notification in the bottom-right corner."""

    def __init__(self, master, title, message, duration=15000):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=C["toast_bg"])

        # Content
        frame = tk.Frame(self, bg=C["toast_bg"], padx=16, pady=12)
        frame.pack(fill="both", expand=True)

        # Close button
        close_btn = tk.Label(frame, text="\u2715", bg=C["toast_bg"], fg="#B0BEC5",
                             font=("Segoe UI", 10), cursor="hand2")
        close_btn.pack(anchor="ne")
        close_btn.bind("<Button-1>", lambda e: self.destroy())

        tk.Label(frame, text=title, bg=C["toast_bg"], fg=C["toast_fg"],
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(frame, text=message, bg=C["toast_bg"], fg="#E3F2FD",
                 font=("Segoe UI", 10), anchor="w", justify="left",
                 wraplength=350).pack(fill="x", pady=(6, 0))

        # Position bottom-right
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), 380)
        h = self.winfo_reqheight()
        sx = self.winfo_screenwidth()
        sy = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{sx - w - 20}+{sy - h - 60}")

        # Play sound
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        # Auto-dismiss
        self.after(duration, self._safe_destroy)

    def _safe_destroy(self):
        try:
            self.destroy()
        except Exception:
            pass


# ═════════════════════════════════════════════════════════════════════════
class MedicationApp:
    REMINDER_CHECK_INTERVAL = 30_000  # ms (check every 30 sec)

    def __init__(self, root):
        self.root = root
        self.root.title("Графік прийому ліків v5 — Бучин А.П.")
        self.root.configure(bg=C["bg"])
        self.root.geometry("1040x880")
        self.root.minsize(880, 660)

        self.state = self._load_state()
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.cal_year = self.current_date.year
        self.cal_month = self.current_date.month

        self.check_vars = {}
        self.purchased_vars = {}
        self.expanded = {}
        self.detail_frames = {}

        # Reminder state
        self.reminders_enabled = tk.BooleanVar(
            value=self.state.get("_settings", {}).get("reminders_enabled", False))
        self.reminder_advance_min = self.state.get("_settings", {}).get("reminder_advance_min", 5)
        self._shown_reminders_today = set()  # "HH:MM" strings already shown today
        self._last_reminder_date = None

        self._setup_styles()
        self._build_ui()
        self._start_reminder_loop()

    # ─── Styles ──────────────────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=C["bg"])
        style.configure("TNotebook", background=C["bg"])
        style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=[14, 5])

    # ─── Main UI ─────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=C["header_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="ДЕННИЙ ГРАФІК ПРИЙОМУ ЛІКІВ", bg=C["header_bg"],
                 fg=C["header_fg"], font=("Segoe UI", 15, "bold"), pady=8).pack()
        tk.Label(hdr, text="Бучин Андрій Петрович, 1954 р.н.  |  Складено: квітень 2026",
                 bg=C["header_bg"], fg="#B0BEC5", font=("Segoe UI", 9), pady=4).pack()

        # Toolbar: date nav + reminder toggle + export button
        toolbar = tk.Frame(self.root, bg=C["date_nav_bg"], pady=5)
        toolbar.pack(fill="x")

        # Date nav
        btn_prev = tk.Label(toolbar, text=" \u25C0 ", bg="#455A64", fg="white",
                            font=("Segoe UI", 10), cursor="hand2", padx=8, pady=3)
        btn_prev.pack(side="left", padx=(12, 4))
        btn_prev.bind("<Button-1>", lambda e: self._change_date(-1))

        self.date_label = tk.Label(toolbar, text="", bg=C["date_nav_bg"], fg="white",
                                   font=("Segoe UI", 11, "bold"))
        self.date_label.pack(side="left", padx=4)

        btn_next = tk.Label(toolbar, text=" \u25B6 ", bg="#455A64", fg="white",
                            font=("Segoe UI", 10), cursor="hand2", padx=8, pady=3)
        btn_next.pack(side="left", padx=(4, 6))
        btn_next.bind("<Button-1>", lambda e: self._change_date(1))

        btn_today = tk.Label(toolbar, text=" Сьогодні ", bg="#1565C0", fg="white",
                             font=("Segoe UI", 9, "bold"), cursor="hand2", padx=8, pady=3)
        btn_today.pack(side="left", padx=4)
        btn_today.bind("<Button-1>", lambda e: self._go_today())

        # Right side: export + reminder
        self.btn_export = tk.Label(toolbar, text=" \U0001F4C4 Звіт для лікаря ", bg="#00897B", fg="white",
                                   font=("Segoe UI", 9, "bold"), cursor="hand2", padx=8, pady=3)
        self.btn_export.pack(side="right", padx=(4, 12))
        self.btn_export.bind("<Button-1>", lambda e: self._show_export_dialog())

        self.reminder_btn = tk.Label(toolbar, text="", bg=C["reminder_off"], fg="white",
                                     font=("Segoe UI", 9, "bold"), cursor="hand2", padx=8, pady=3)
        self.reminder_btn.pack(side="right", padx=4)
        self.reminder_btn.bind("<Button-1>", lambda e: self._toggle_reminders())
        self._update_reminder_btn()

        # Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self.tab_schedule = tk.Frame(self.notebook, bg=C["bg"])
        self.tab_history = tk.Frame(self.notebook, bg=C["bg"])
        self.notebook.add(self.tab_schedule, text="  Графік прийому  ")
        self.notebook.add(self.tab_history, text="  Історія / Календар  ")
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._on_tab_changed())

        self._build_schedule_tab()
        self._build_history_tab()
        self._refresh_date()

    def _on_tab_changed(self):
        if self.notebook.index("current") == 1:
            self._refresh_calendar()

    # ─── Schedule tab ────────────────────────────────────────────────────
    def _build_schedule_tab(self):
        legend = tk.Frame(self.tab_schedule, bg=C["bg"], pady=4)
        legend.pack(fill="x", padx=20)
        for color, txt in [(C["course_long"], "Тривало"), (C["course_2m"], "2 місяці"),
                           (C["course_short"], "5-7 днів"), (C["course_need"], "За потребою")]:
            f = tk.Frame(legend, bg=C["bg"])
            f.pack(side="left", padx=(0, 18))
            tk.Canvas(f, width=12, height=12, bg=color, highlightthickness=0).pack(side="left", padx=(0, 4))
            tk.Label(f, text=txt, bg=C["bg"], fg=C["text"], font=("Segoe UI", 9)).pack(side="left")

        self.stats_frame = tk.Frame(self.tab_schedule, bg=C["bg"])
        self.stats_frame.pack(fill="x", padx=20, pady=(0, 3))
        self.stats_label = tk.Label(self.stats_frame, text="", bg=C["bg"], fg=C["text"],
                                    font=("Segoe UI", 10))
        self.stats_label.pack(side="left")
        self.stats_bar_canvas = tk.Canvas(self.stats_frame, height=18, bg=C["bg"], highlightthickness=0)
        self.stats_bar_canvas.pack(side="left", fill="x", expand=True, padx=(10, 0))

        container = tk.Frame(self.tab_schedule, bg=C["bg"])
        container.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(container, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable = tk.Frame(self.canvas, bg=C["bg"])
        self.scrollable.bind("<Configure>",
                             lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_win = self.canvas.create_window((0, 0), window=self.scrollable, anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_win, width=e.width))
        self.root.bind_all("<MouseWheel>",
                           lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        for sec in MEDICATIONS:
            self._build_section(self.scrollable, sec)
        self._build_notes(self.scrollable)
        tk.Label(self.scrollable,
                 text="Графік носить інформаційний характер. Перед застосуванням проконсультуйтесь з лікарем.",
                 bg=C["bg"], fg=C["subtext"], font=("Segoe UI", 9, "italic"), pady=10).pack(fill="x", padx=20)

    def _build_section(self, parent, sec):
        accent = C[f"{sec['section_key']}_accent"]
        hdr = tk.Frame(parent, bg=accent)
        hdr.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(hdr, text=sec["section"], bg=accent, fg="white",
                 font=("Segoe UI", 12, "bold"), padx=14, pady=5).pack(anchor="w")
        for item in sec["items"]:
            self._build_card(parent, item, accent)

    def _build_card(self, parent, item, accent):
        mid = item["id"]
        outer = tk.Frame(parent, bg=accent)
        outer.pack(fill="x", padx=16, pady=(2, 0))
        card = tk.Frame(outer, bg=C["card_bg"])
        card.pack(fill="x", padx=(4, 0))
        row = tk.Frame(card, bg=C["card_bg"], pady=5, padx=10)
        row.pack(fill="x")
        row.columnconfigure(1, weight=1)

        tf = tk.Frame(row, bg=C["card_bg"], width=65)
        tf.grid(row=0, column=0, sticky="n", padx=(0, 8))
        tf.grid_propagate(False); tf.configure(height=34)
        tk.Label(tf, text=item["time"], bg=C["card_bg"], fg=accent,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        if item["time_note"]:
            tk.Label(tf, text=item["time_note"], bg=C["card_bg"], fg=C["subtext"],
                     font=("Segoe UI", 8)).pack(anchor="w")

        info = tk.Frame(row, bg=C["card_bg"])
        info.grid(row=0, column=1, sticky="nsew")
        nr = tk.Frame(info, bg=C["card_bg"]); nr.pack(anchor="w")
        name_lbl = tk.Label(nr, text=item["name"], bg=C["card_bg"], fg="#1565C0",
                            font=("Segoe UI", 11, "bold", "underline"), cursor="hand2")
        name_lbl.pack(side="left")
        name_lbl.bind("<Button-1>", lambda e, n=item["name"]: self._search_med(n))
        name_lbl.bind("<Enter>", lambda e, lbl=name_lbl: lbl.configure(fg="#0D47A1"))
        name_lbl.bind("<Leave>", lambda e, lbl=name_lbl: lbl.configure(fg="#1565C0"))
        search_tip = tk.Label(nr, text=" \U0001F50D", bg=C["card_bg"], fg="#90A4AE",
                              font=("Segoe UI", 9), cursor="hand2")
        search_tip.pack(side="left")
        search_tip.bind("<Button-1>", lambda e, n=item["name"]: self._search_med(n))
        if item["subtitle"]:
            tk.Label(nr, text=f"  ({item['subtitle']})", bg=C["card_bg"], fg=C["subtext"],
                     font=("Segoe UI", 9)).pack(side="left")
        tk.Label(info, text=item["note"], bg=C["card_bg"], fg=C["subtext"],
                 font=("Segoe UI", 9), anchor="w").pack(anchor="w")

        badge_col = COURSE_COLORS.get(item["course_type"], C["subtext"])
        bf = tk.Frame(row, bg=C["card_bg"])
        bf.grid(row=0, column=2, sticky="ne", padx=(6, 0))
        tk.Label(bf, text=f" {item['course']} ", bg=badge_col, fg="white",
                 font=("Segoe UI", 8, "bold"), padx=5, pady=1).pack(anchor="e")

        cf = tk.Frame(row, bg=C["card_bg"])
        cf.grid(row=0, column=3, sticky="ne", padx=(10, 0))

        # "Придбано" row with pharmacy button
        p_row = tk.Frame(cf, bg=C["card_bg"])
        p_row.pack(anchor="w")
        p_var = tk.BooleanVar(value=self.state.get("purchased", {}).get(mid, False))
        self.purchased_vars[mid] = p_var
        tk.Checkbutton(p_row, text="Придбано", variable=p_var, bg=C["card_bg"],
                       fg=C["purchased_on"], selectcolor=C["card_bg"], activebackground=C["card_bg"],
                       font=("Segoe UI", 9), command=self._save_state, anchor="w").pack(side="left")
        pharm_name = item.get("pharmacy", item["name"])
        pharm_btn = tk.Label(p_row, text=" \U0001F3E5 Аптеки", bg=C["card_bg"], fg="#00897B",
                             font=("Segoe UI", 8, "underline"), cursor="hand2")
        pharm_btn.pack(side="left", padx=(4, 0))
        pharm_btn.bind("<Button-1>", lambda e, n=pharm_name: self._search_pharmacy(n))
        pharm_btn.bind("<Enter>", lambda e, b=pharm_btn: b.configure(fg="#004D40"))
        pharm_btn.bind("<Leave>", lambda e, b=pharm_btn: b.configure(fg="#00897B"))

        t_var = tk.BooleanVar(value=False)
        self.check_vars[mid] = t_var
        tk.Checkbutton(cf, text="Прийнято", variable=t_var, bg=C["card_bg"],
                       fg=C["taken_on"], selectcolor=C["card_bg"], activebackground=C["card_bg"],
                       font=("Segoe UI", 9), command=self._save_state, anchor="w").pack(anchor="w")

        self.expanded[mid] = False
        tog = tk.Label(row, text="\u25B6 Опис", bg=C["card_bg"], fg=accent,
                       font=("Segoe UI", 9), cursor="hand2")
        tog.grid(row=0, column=4, sticky="se", padx=(8, 0))
        detail = tk.Frame(card, bg=C["expand_bg"], padx=14, pady=6)
        self.detail_frames[mid] = detail
        tk.Label(detail, text=item["description"], bg=C["expand_bg"], fg=C["text"],
                 font=("Segoe UI", 9), justify="left", anchor="nw", wraplength=800).pack(fill="x", anchor="w")
        tog.bind("<Button-1>", lambda e, m=mid, b=tog: self._toggle(m, b))
        tk.Frame(card, bg=C["border"], height=1).pack(fill="x")

    def _toggle(self, mid, btn):
        if self.expanded[mid]:
            self.detail_frames[mid].pack_forget()
            btn.configure(text="\u25B6 Опис"); self.expanded[mid] = False
        else:
            card = self.detail_frames[mid].master
            children = card.pack_slaves(); sep = children[-1]
            sep.pack_forget(); self.detail_frames[mid].pack(fill="x"); sep.pack(fill="x")
            btn.configure(text="\u25BC Опис"); self.expanded[mid] = True

    @staticmethod
    def _search_med(name):
        query = urllib.parse.quote(f"{name} інструкція ціна відгуки")
        webbrowser.open(f"https://www.google.com/search?q={query}")

    @staticmethod
    def _search_pharmacy(name):
        encoded = urllib.parse.quote(name)
        webbrowser.open(f"https://tabletki.ua/uk/search/?q={encoded}")

    def _build_notes(self, parent):
        outer = tk.Frame(parent, bg=C["sos_accent"])
        outer.pack(fill="x", padx=16, pady=(10, 4))
        tk.Label(outer, text="ВАЖЛИВІ ПРИМІТКИ", bg=C["sos_accent"], fg="white",
                 font=("Segoe UI", 11, "bold"), padx=14, pady=5).pack(anchor="w")
        body = tk.Frame(outer, bg=C["notes_bg"])
        body.pack(fill="x", padx=(4, 0))
        for i, note in enumerate(IMPORTANT_NOTES, 1):
            tk.Label(body, text=f"  {i}. {note}", bg=C["notes_bg"], fg=C["text"],
                     font=("Segoe UI", 9), anchor="w", justify="left", wraplength=880,
                     padx=10, pady=2).pack(fill="x", anchor="w")
        tk.Frame(body, bg=C["notes_bg"], height=4).pack()

    # ─── History tab ─────────────────────────────────────────────────────
    def _build_history_tab(self):
        # Scrollable history
        container = tk.Frame(self.tab_history, bg=C["bg"])
        container.pack(fill="both", expand=True)
        self.hist_canvas = tk.Canvas(container, bg=C["bg"], highlightthickness=0)
        hsb = ttk.Scrollbar(container, orient="vertical", command=self.hist_canvas.yview)
        self.hist_scrollable = tk.Frame(self.hist_canvas, bg=C["bg"])
        self.hist_scrollable.bind("<Configure>",
                                  lambda e: self.hist_canvas.configure(scrollregion=self.hist_canvas.bbox("all")))
        self.hist_canvas_win = self.hist_canvas.create_window((0, 0), window=self.hist_scrollable, anchor="nw")
        self.hist_canvas.configure(yscrollcommand=hsb.set)
        self.hist_canvas.pack(side="left", fill="both", expand=True)
        hsb.pack(side="right", fill="y")
        self.hist_canvas.bind("<Configure>",
                              lambda e: self.hist_canvas.itemconfig(self.hist_canvas_win, width=e.width))

        top = self.hist_scrollable

        cal_nav = tk.Frame(top, bg=C["bg"])
        cal_nav.pack(fill="x", padx=20, pady=(10, 0))
        self.btn_prev_m = tk.Label(cal_nav, text="  \u25C0  ", bg="#455A64", fg="white",
                                   font=("Segoe UI", 11), cursor="hand2", padx=8, pady=2)
        self.btn_prev_m.pack(side="left")
        self.btn_prev_m.bind("<Button-1>", lambda e: self._change_cal_month(-1))
        self.cal_title = tk.Label(cal_nav, text="", bg=C["bg"], fg=C["text"],
                                  font=("Segoe UI", 14, "bold"))
        self.cal_title.pack(side="left", expand=True)
        self.btn_next_m = tk.Label(cal_nav, text="  \u25B6  ", bg="#455A64", fg="white",
                                   font=("Segoe UI", 11), cursor="hand2", padx=8, pady=2)
        self.btn_next_m.pack(side="left")
        self.btn_next_m.bind("<Button-1>", lambda e: self._change_cal_month(1))

        self.cal_frame = tk.Frame(top, bg=C["bg"])
        self.cal_frame.pack(fill="x", padx=20, pady=(8, 0))

        leg_frame = tk.Frame(top, bg=C["bg"])
        leg_frame.pack(fill="x", padx=20, pady=(6, 0))
        for color, txt in [(C["cal_full"], "Всі прийняті"), (C["cal_partial"], "Частково"),
                           (C["cal_empty"], "Пропущено"), (C["cal_none"], "Немає даних")]:
            f = tk.Frame(leg_frame, bg=C["bg"]); f.pack(side="left", padx=(0, 14))
            tk.Canvas(f, width=14, height=14, bg=color, highlightthickness=1,
                      highlightbackground=C["border"]).pack(side="left", padx=(0, 4))
            tk.Label(f, text=txt, bg=C["bg"], fg=C["text"], font=("Segoe UI", 9)).pack(side="left")

        tk.Label(top, text="Статистика за місяць:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", padx=20, pady=(12, 4))
        self.month_stats_frame = tk.Frame(top, bg=C["bg"])
        self.month_stats_frame.pack(fill="x", padx=20)

        tk.Label(top, text="Деталі обраного дня:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", padx=20, pady=(12, 4))
        self.day_detail_frame = tk.Frame(top, bg=C["card_bg"], relief="groove", bd=1)
        self.day_detail_frame.pack(fill="x", padx=20)
        tk.Label(self.day_detail_frame, text="  Оберіть день у календарі",
                 bg=C["card_bg"], fg=C["subtext"], font=("Segoe UI", 10), pady=10, anchor="w").pack(fill="x")

        # Spacer
        tk.Frame(top, bg=C["bg"], height=20).pack()

    def _refresh_calendar(self):
        for w in self.cal_frame.winfo_children():
            w.destroy()
        self.cal_title.configure(text=f"{MONTHS_UA[self.cal_month]} {self.cal_year}")

        for i, wd in enumerate(WEEKDAYS_UA):
            tk.Label(self.cal_frame, text=wd, bg=C["bg"], fg=C["subtext"],
                     font=("Segoe UI", 9, "bold"), width=6).grid(row=0, column=i, padx=2, pady=2)

        cal = calendar.monthcalendar(self.cal_year, self.cal_month)
        today = datetime.now()
        total = len(ALL_DAILY_IDS)

        for r, week in enumerate(cal):
            for col, day in enumerate(week):
                if day == 0:
                    tk.Label(self.cal_frame, text="", bg=C["bg"], width=6).grid(
                        row=r+1, column=col, padx=2, pady=2)
                    continue
                dt = datetime(self.cal_year, self.cal_month, day)
                dk = date_key(dt)
                dd = self.state.get(dk, {})
                taken_n = sum(1 for mid in ALL_DAILY_IDS if dd.get(f"{mid}_taken", False))
                if taken_n == 0 and not dd:      bg_c = C["cal_none"]
                elif taken_n == 0:                bg_c = C["cal_empty"]
                elif taken_n == total:            bg_c = C["cal_full"]
                else:                             bg_c = C["cal_partial"]

                is_today = (dt.date() == today.date())
                brd = C["cal_today_border"] if is_today else C["border"]
                bw = 2 if is_today else 1
                co = tk.Frame(self.cal_frame, bg=brd, padx=bw, pady=bw)
                co.grid(row=r+1, column=col, padx=2, pady=2, sticky="nsew")
                pct_t = f"\n{int(taken_n/total*100)}%" if dd and total else ""
                cell = tk.Label(co, text=f"{day}{pct_t}", bg=bg_c, fg=C["text"],
                                font=("Segoe UI", 9), width=5, height=2, cursor="hand2")
                cell.pack(fill="both", expand=True)
                cell.bind("<Button-1>", lambda e, d=dt: self._show_day_detail(d))

        self._refresh_month_stats()

    def _refresh_month_stats(self):
        for w in self.month_stats_frame.winfo_children():
            w.destroy()
        dim = calendar.monthrange(self.cal_year, self.cal_month)[1]
        total_d, full_d, part_d, empty_d, t_taken, t_poss = 0, 0, 0, 0, 0, 0
        for day in range(1, dim+1):
            dd = self.state.get(date_key(datetime(self.cal_year, self.cal_month, day)), {})
            if not dd: continue
            total_d += 1
            tk_n = sum(1 for m in ALL_DAILY_IDS if dd.get(f"{m}_taken", False))
            t_taken += tk_n; t_poss += len(ALL_DAILY_IDS)
            if tk_n == len(ALL_DAILY_IDS): full_d += 1
            elif tk_n > 0: part_d += 1
            else: empty_d += 1
        if total_d == 0:
            tk.Label(self.month_stats_frame, text="Немає даних за цей місяць",
                     bg=C["bg"], fg=C["subtext"], font=("Segoe UI", 10)).pack(anchor="w")
            return
        pct = int(t_taken / t_poss * 100) if t_poss else 0
        sc = C["stat_good"] if pct >= 80 else C["stat_warn"] if pct >= 50 else C["stat_bad"]
        tk.Label(self.month_stats_frame,
                 text=f"Днів: {total_d}  |  Повний: {full_d}  |  Частково: {part_d}  |  Пропущено: {empty_d}  |  Виконання: {pct}%",
                 bg=C["bg"], fg=C["text"], font=("Segoe UI", 10)).pack(anchor="w")
        bar = tk.Frame(self.month_stats_frame, bg=C["border"], height=20)
        bar.pack(fill="x", pady=(4, 0)); bar.pack_propagate(False)
        if pct > 0:
            tk.Frame(bar, bg=sc).place(relwidth=pct/100, relheight=1.0)
        tk.Label(bar, text=f"{pct}%", bg=sc if pct > 15 else C["border"],
                 fg="white" if pct > 15 else C["text"],
                 font=("Segoe UI", 9, "bold")).place(relx=0.5, rely=0.5, anchor="center")

    def _show_day_detail(self, dt):
        dk = date_key(dt); dd = self.state.get(dk, {})
        for w in self.day_detail_frame.winfo_children(): w.destroy()
        tk.Label(self.day_detail_frame, text=format_date_ua(dt), bg=C["header_bg"],
                 fg=C["header_fg"], font=("Segoe UI", 11, "bold"), padx=12, pady=5).pack(fill="x")
        if not dd:
            tk.Label(self.day_detail_frame, text="  Немає даних.", bg=C["card_bg"],
                     fg=C["subtext"], font=("Segoe UI", 10), pady=8, anchor="w").pack(fill="x")
            return
        for sec in MEDICATIONS:
            accent = C[f"{sec['section_key']}_accent"]
            sf = tk.Frame(self.day_detail_frame, bg=C["card_bg"])
            sf.pack(fill="x", padx=10, pady=(3, 0))
            tk.Label(sf, text=sec["section"], bg=C["card_bg"], fg=accent,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            for it in sec["items"]:
                taken = dd.get(f"{it['id']}_taken", False)
                mk = "\u2705" if taken else "\u274C"
                tk.Label(sf, text=f"    {mk}  {it['time']}  {it['name']}",
                         bg=C["card_bg"], fg=C["text"] if taken else C["subtext"],
                         font=("Segoe UI", 9), anchor="w").pack(anchor="w")
        tk_n = sum(1 for m in ALL_DAILY_IDS if dd.get(f"{m}_taken", False))
        tot = len(ALL_DAILY_IDS)
        tk.Label(self.day_detail_frame, text=f"  Прийнято: {tk_n}/{tot} ({int(tk_n/tot*100) if tot else 0}%)",
                 bg=C["card_bg"], fg=C["text"], font=("Segoe UI", 10, "bold"), pady=5).pack(fill="x")

    # ─── Date nav ────────────────────────────────────────────────────────
    def _change_date(self, delta):
        self.current_date += timedelta(days=delta); self._refresh_date()

    def _go_today(self):
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.cal_year = self.current_date.year; self.cal_month = self.current_date.month
        self._refresh_date()

    def _refresh_date(self):
        dk = date_key(self.current_date); dd = self.state.get(dk, {})
        is_today = (self.current_date.date() == datetime.now().date())
        ds = format_date_ua(self.current_date)
        if is_today: ds += "  (сьогодні)"
        self.date_label.configure(text=ds)
        for mid, var in self.check_vars.items():
            var.set(dd.get(f"{mid}_taken", False))
        self._update_stats()

    def _update_stats(self):
        dk = date_key(self.current_date); dd = self.state.get(dk, {})
        taken = sum(1 for m in ALL_DAILY_IDS if dd.get(f"{m}_taken", False))
        total = len(ALL_DAILY_IDS); pct = int(taken/total*100) if total else 0
        sc = C["stat_good"] if pct >= 80 else C["stat_warn"] if pct >= 50 else C["stat_bad"]
        self.stats_label.configure(text=f"Прийнято: {taken}/{total}")
        self.stats_bar_canvas.delete("all"); self.stats_bar_canvas.update_idletasks()
        w = self.stats_bar_canvas.winfo_width(); h = 18
        if w > 1:
            self.stats_bar_canvas.create_rectangle(0, 0, w, h, fill=C["border"], outline="")
            if pct > 0:
                self.stats_bar_canvas.create_rectangle(0, 0, int(w*pct/100), h, fill=sc, outline="")
            self.stats_bar_canvas.create_text(w//2, h//2, text=f"{pct}%",
                                              font=("Segoe UI", 9, "bold"),
                                              fill="white" if pct > 15 else C["text"])

    def _change_cal_month(self, delta):
        self.cal_month += delta
        if self.cal_month > 12: self.cal_month = 1; self.cal_year += 1
        elif self.cal_month < 1: self.cal_month = 12; self.cal_year -= 1
        self._refresh_calendar()

    # ═══ REMINDERS ═══════════════════════════════════════════════════════
    def _toggle_reminders(self):
        self.reminders_enabled.set(not self.reminders_enabled.get())
        self._update_reminder_btn()
        self._save_settings()
        status = "увімкнено" if self.reminders_enabled.get() else "вимкнено"
        ToastNotification(self.root, "Нагадування", f"Нагадування {status}.", duration=4000)

    def _update_reminder_btn(self):
        if self.reminders_enabled.get():
            self.reminder_btn.configure(text="\U0001F514 Нагадування: ВКЛ", bg=C["reminder_on"])
        else:
            self.reminder_btn.configure(text="\U0001F515 Нагадування: ВИКЛ", bg=C["reminder_off"])

    def _start_reminder_loop(self):
        self._check_reminders()
        self.root.after(self.REMINDER_CHECK_INTERVAL, self._start_reminder_loop)

    def _check_reminders(self):
        if not self.reminders_enabled.get():
            return

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # Reset shown set on new day
        if self._last_reminder_date != today_str:
            self._shown_reminders_today.clear()
            self._last_reminder_date = today_str

        current_minutes = now.hour * 60 + now.minute
        advance = self.reminder_advance_min

        for time_str in REMINDER_TIMES_SORTED:
            if time_str in self._shown_reminders_today:
                continue

            parts = time_str.split(":")
            sched_minutes = int(parts[0]) * 60 + int(parts[1])
            trigger_minutes = sched_minutes - advance

            # Show reminder if we're within the window [trigger, trigger + 5 min]
            if trigger_minutes <= current_minutes <= trigger_minutes + 5:
                items = REMINDER_SCHEDULE[time_str]
                names = "\n".join(f"\u2022 {it['name']}" + (f" ({it['subtitle']})" if it['subtitle'] else "")
                                  for it in items)
                title = f"\u23F0 Час прийому ліків — {time_str}"
                msg = f"Необхідно прийняти:\n{names}"
                ToastNotification(self.root, title, msg, duration=60000)
                self._shown_reminders_today.add(time_str)

    # ═══ EXPORT REPORT ═══════════════════════════════════════════════════
    def _show_export_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Експорт звіту для лікаря")
        dlg.geometry("460x340")
        dlg.configure(bg=C["bg"])
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        tk.Label(dlg, text="Експорт звіту для лікаря", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 14, "bold")).pack(pady=(16, 8))

        tk.Label(dlg, text="Оберіть період:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=20)

        # Date range selection
        range_frame = tk.Frame(dlg, bg=C["bg"])
        range_frame.pack(fill="x", padx=20, pady=8)

        tk.Label(range_frame, text="З:", bg=C["bg"], fg=C["text"], font=("Segoe UI", 10)).grid(
            row=0, column=0, padx=(0, 6))
        from_day = tk.Spinbox(range_frame, from_=1, to=31, width=3, font=("Segoe UI", 10))
        from_day.grid(row=0, column=1, padx=2)
        from_month = tk.Spinbox(range_frame, from_=1, to=12, width=3, font=("Segoe UI", 10))
        from_month.grid(row=0, column=2, padx=2)
        from_year = tk.Spinbox(range_frame, from_=2024, to=2030, width=5, font=("Segoe UI", 10))
        from_year.grid(row=0, column=3, padx=2)

        tk.Label(range_frame, text="  По:", bg=C["bg"], fg=C["text"], font=("Segoe UI", 10)).grid(
            row=0, column=4, padx=(10, 6))
        to_day = tk.Spinbox(range_frame, from_=1, to=31, width=3, font=("Segoe UI", 10))
        to_day.grid(row=0, column=5, padx=2)
        to_month = tk.Spinbox(range_frame, from_=1, to=12, width=3, font=("Segoe UI", 10))
        to_month.grid(row=0, column=6, padx=2)
        to_year = tk.Spinbox(range_frame, from_=2024, to=2030, width=5, font=("Segoe UI", 10))
        to_year.grid(row=0, column=7, padx=2)

        # Defaults: first date with data → today
        today = datetime.now()
        all_dates = sorted([k for k in self.state if k not in ("purchased", "_settings") and "-" in k])
        if all_dates:
            fd = datetime.strptime(all_dates[0], "%Y-%m-%d")
        else:
            fd = today - timedelta(days=30)

        from_day.delete(0, "end"); from_day.insert(0, fd.day)
        from_month.delete(0, "end"); from_month.insert(0, fd.month)
        from_year.delete(0, "end"); from_year.insert(0, fd.year)
        to_day.delete(0, "end"); to_day.insert(0, today.day)
        to_month.delete(0, "end"); to_month.insert(0, today.month)
        to_year.delete(0, "end"); to_year.insert(0, today.year)

        # Quick range buttons
        qf = tk.Frame(dlg, bg=C["bg"])
        qf.pack(fill="x", padx=20, pady=4)

        def set_range(days_back):
            s = today - timedelta(days=days_back)
            from_day.delete(0, "end"); from_day.insert(0, s.day)
            from_month.delete(0, "end"); from_month.insert(0, s.month)
            from_year.delete(0, "end"); from_year.insert(0, s.year)

        for label, d in [("7 днів", 7), ("14 днів", 14), ("30 днів", 30), ("Весь час", 365)]:
            b = tk.Label(qf, text=f" {label} ", bg="#455A64", fg="white",
                         font=("Segoe UI", 9), cursor="hand2", padx=6, pady=2)
            b.pack(side="left", padx=(0, 6))
            b.bind("<Button-1>", lambda e, dd=d: set_range(dd))

        # Options
        include_notes_var = tk.BooleanVar(value=True)
        tk.Checkbutton(dlg, text="Включити список препаратів з описами", variable=include_notes_var,
                       bg=C["bg"], fg=C["text"], font=("Segoe UI", 10),
                       selectcolor=C["bg"], activebackground=C["bg"]).pack(anchor="w", padx=20, pady=(8, 0))

        include_purchase_var = tk.BooleanVar(value=True)
        tk.Checkbutton(dlg, text="Включити статус придбання", variable=include_purchase_var,
                       bg=C["bg"], fg=C["text"], font=("Segoe UI", 10),
                       selectcolor=C["bg"], activebackground=C["bg"]).pack(anchor="w", padx=20, pady=2)

        def do_export():
            try:
                dt_from = datetime(int(from_year.get()), int(from_month.get()), int(from_day.get()))
                dt_to = datetime(int(to_year.get()), int(to_month.get()), int(to_day.get()))
            except ValueError:
                messagebox.showerror("Помилка", "Невірна дата", parent=dlg)
                return
            if dt_from > dt_to:
                messagebox.showerror("Помилка", "Дата 'З' має бути раніше дати 'По'", parent=dlg)
                return
            path = filedialog.asksaveasfilename(
                parent=dlg, title="Зберегти звіт",
                initialdir=SCRIPT_DIR,
                initialfile=f"Звіт_прийому_ліків_{date_key(dt_from)}_{date_key(dt_to)}.html",
                filetypes=[("HTML файл", "*.html")],
                defaultextension=".html",
            )
            if not path:
                return
            html = self._generate_report_html(dt_from, dt_to,
                                              include_notes_var.get(), include_purchase_var.get())
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            dlg.destroy()
            webbrowser.open(path)

        btn_frame = tk.Frame(dlg, bg=C["bg"])
        btn_frame.pack(fill="x", padx=20, pady=(14, 10))

        export_btn = tk.Label(btn_frame, text="  \U0001F4C4  Створити звіт  ", bg="#00897B", fg="white",
                              font=("Segoe UI", 11, "bold"), cursor="hand2", padx=12, pady=6)
        export_btn.pack(side="left")
        export_btn.bind("<Button-1>", lambda e: do_export())

        cancel_btn = tk.Label(btn_frame, text="  Скасувати  ", bg="#455A64", fg="white",
                              font=("Segoe UI", 10), cursor="hand2", padx=10, pady=6)
        cancel_btn.pack(side="right")
        cancel_btn.bind("<Button-1>", lambda e: dlg.destroy())

    def _generate_report_html(self, dt_from, dt_to, include_notes, include_purchase):
        total_ids = len(ALL_DAILY_IDS)

        # Collect daily data
        days_data = []
        d = dt_from
        while d <= dt_to:
            dk = date_key(d)
            dd = self.state.get(dk, {})
            taken_n = sum(1 for m in ALL_DAILY_IDS if dd.get(f"{m}_taken", False))
            days_data.append((d, dk, dd, taken_n))
            d += timedelta(days=1)

        total_days = len(days_data)
        days_with_data = [x for x in days_data if x[2]]
        total_taken = sum(x[3] for x in days_data)
        total_possible = len(days_with_data) * total_ids if days_with_data else 1
        pct_overall = int(total_taken / total_possible * 100) if total_possible else 0

        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<title>Звіт прийому ліків — Бучин А.П.</title>
<style>
  @media print {{ @page {{ margin: 15mm; }} }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #212121; max-width: 900px; margin: 0 auto; padding: 20px; }}
  h1 {{ color: #2C3E50; border-bottom: 3px solid #2C3E50; padding-bottom: 8px; font-size: 22px; }}
  h2 {{ color: #1565C0; margin-top: 24px; font-size: 16px; }}
  h3 {{ color: #388E3C; font-size: 14px; margin-top: 16px; }}
  .patient-info {{ background: #ECEFF1; padding: 12px 16px; border-radius: 6px; margin: 12px 0; }}
  .summary-box {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 12px 0; }}
  .stat-card {{ background: #F5F5F5; border-left: 4px solid #2196F3; padding: 10px 16px; border-radius: 4px; min-width: 140px; }}
  .stat-card .value {{ font-size: 22px; font-weight: bold; }}
  .stat-card .label {{ font-size: 12px; color: #616161; }}
  .stat-good {{ border-left-color: #4CAF50; }}
  .stat-warn {{ border-left-color: #FF9800; }}
  .stat-bad {{ border-left-color: #F44336; }}
  table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 13px; }}
  th {{ background: #2C3E50; color: white; padding: 8px 6px; text-align: left; font-size: 12px; }}
  td {{ padding: 6px; border-bottom: 1px solid #E0E0E0; }}
  tr:nth-child(even) {{ background: #FAFAFA; }}
  .taken {{ color: #4CAF50; font-weight: bold; }}
  .missed {{ color: #F44336; }}
  .no-data {{ color: #9E9E9E; font-style: italic; }}
  .pct-bar {{ display: inline-block; height: 14px; border-radius: 3px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; color: white; font-size: 11px; font-weight: bold; }}
  .badge-long {{ background: #388E3C; }} .badge-2m {{ background: #F57F17; }}
  .badge-short {{ background: #C62828; }} .badge-need {{ background: #7B1FA2; }}
  .footer {{ margin-top: 30px; padding-top: 12px; border-top: 1px solid #E0E0E0; font-size: 11px; color: #9E9E9E; text-align: center; }}
  .purchase-yes {{ color: #4CAF50; }} .purchase-no {{ color: #F44336; }}
  .section-label {{ font-weight: bold; padding: 4px 8px; color: white; border-radius: 3px; margin: 8px 0 4px; display: inline-block; font-size: 12px; }}
  .morning {{ background: #388E3C; }} .day {{ background: #F57F17; }}
  .evening {{ background: #1565C0; }} .sos {{ background: #C62828; }}
  .med-desc {{ font-size: 12px; color: #616161; margin: 2px 0 6px 20px; white-space: pre-line; }}
</style>
</head>
<body>
<h1>\U0001F4CB Звіт прийому ліків</h1>
<div class="patient-info">
  <strong>Пацієнт:</strong> Бучин Андрій Петрович, 1954 р.н.<br>
  <strong>Період:</strong> {format_date_ua(dt_from)} — {format_date_ua(dt_to)}<br>
  <strong>Дата звіту:</strong> {format_date_ua(datetime.now())}<br>
  <strong>Графік складено:</strong> квітень 2026
</div>

<h2>\U0001F4CA Загальна статистика</h2>
<div class="summary-box">
  <div class="stat-card {'stat-good' if pct_overall >= 80 else 'stat-warn' if pct_overall >= 50 else 'stat-bad'}">
    <div class="value">{pct_overall}%</div><div class="label">Загальне виконання</div>
  </div>
  <div class="stat-card">
    <div class="value">{len(days_with_data)}</div><div class="label">Днів з даними</div>
  </div>
  <div class="stat-card stat-good">
    <div class="value">{sum(1 for x in days_data if x[3] == total_ids and x[2])}</div><div class="label">Повний прийом</div>
  </div>
  <div class="stat-card stat-warn">
    <div class="value">{sum(1 for x in days_data if 0 < x[3] < total_ids and x[2])}</div><div class="label">Частковий</div>
  </div>
  <div class="stat-card stat-bad">
    <div class="value">{sum(1 for x in days_data if x[3] == 0 and x[2])}</div><div class="label">Пропущено</div>
  </div>
</div>
"""
        # Per-medication stats
        html += "<h2>\U0001F48A Виконання по препаратах</h2>\n<table>\n"
        html += "<tr><th>Препарат</th><th>Курс</th><th>Прийнято днів</th><th>Пропущено</th><th>%</th></tr>\n"
        for sec in MEDICATIONS:
            for it in sec["items"]:
                if it["course_type"] == "need":
                    continue
                mid = it["id"]
                taken_days = sum(1 for _, _, dd, _ in days_data if dd.get(f"{mid}_taken", False))
                data_days = len(days_with_data)
                missed = data_days - taken_days
                mp = int(taken_days / data_days * 100) if data_days else 0
                badge_cls = f"badge-{it['course_type']}"
                html += f"<tr><td><strong>{it['name']}</strong>"
                if it['subtitle']:
                    html += f" <small>({it['subtitle']})</small>"
                html += f"</td><td><span class='badge {badge_cls}'>{it['course']}</span></td>"
                html += f"<td class='taken'>{taken_days}</td><td class='missed'>{missed}</td>"
                bar_color = '#4CAF50' if mp >= 80 else '#FF9800' if mp >= 50 else '#F44336'
                html += f"<td>{mp}% <span class='pct-bar' style='width:{max(mp,2)}px;background:{bar_color}'></span></td></tr>\n"
        html += "</table>\n"

        # Daily log
        html += "<h2>\U0001F4C5 Щоденний журнал</h2>\n<table>\n"
        html += "<tr><th>Дата</th>"
        # Short med names as columns
        short_names = []
        for sec in MEDICATIONS:
            for it in sec["items"]:
                if it["course_type"] != "need":
                    short_names.append((it["id"], it["name"][:12]))
        for _, sn in short_names:
            html += f"<th style='font-size:10px;writing-mode:vertical-lr;text-orientation:mixed;height:80px'>{sn}</th>"
        html += "<th>%</th></tr>\n"

        for dt, dk, dd, taken_n in days_data:
            pct_d = int(taken_n / total_ids * 100) if total_ids else 0
            html += f"<tr><td style='white-space:nowrap'>{dt.strftime('%d.%m')}<br><small>{WEEKDAYS_UA[dt.weekday()]}</small></td>"
            if not dd:
                for _ in short_names:
                    html += "<td class='no-data'>—</td>"
                html += "<td class='no-data'>—</td></tr>\n"
                continue
            for mid, _ in short_names:
                if dd.get(f"{mid}_taken", False):
                    html += "<td class='taken'>\u2713</td>"
                else:
                    html += "<td class='missed'>\u2717</td>"
            bar_c = '#4CAF50' if pct_d >= 80 else '#FF9800' if pct_d >= 50 else '#F44336'
            html += f"<td><strong>{pct_d}%</strong></td></tr>\n"
        html += "</table>\n"

        # Purchase status
        if include_purchase:
            purchased = self.state.get("purchased", {})
            html += "<h2>\U0001F6D2 Статус придбання</h2>\n<table>\n"
            html += "<tr><th>Препарат</th><th>Курс</th><th>Придбано</th></tr>\n"
            for sec in MEDICATIONS:
                for it in sec["items"]:
                    p = purchased.get(it["id"], False)
                    cls = "purchase-yes" if p else "purchase-no"
                    txt = "\u2713 Так" if p else "\u2717 Ні"
                    badge_cls = f"badge-{it['course_type']}"
                    html += f"<tr><td><strong>{it['name']}</strong></td>"
                    html += f"<td><span class='badge {badge_cls}'>{it['course']}</span></td>"
                    html += f"<td class='{cls}'>{txt}</td></tr>\n"
            html += "</table>\n"

        # Medication descriptions
        if include_notes:
            html += "<h2>\U0001F4D6 Список препаратів</h2>\n"
            for sec in MEDICATIONS:
                sk = sec["section_key"]
                html += f"<div class='section-label {sk}'>{sec['section']}</div>\n"
                for it in sec["items"]:
                    html += f"<p style='margin:4px 0 0 10px'><strong>{it['name']}</strong>"
                    if it['subtitle']: html += f" ({it['subtitle']})"
                    html += f" — {it['note']}</p>\n"
                    html += f"<div class='med-desc'>{it['description']}</div>\n"

        # Important notes
        html += "<h2>\u26A0\uFE0F Важливі примітки</h2>\n<ol>\n"
        for note in IMPORTANT_NOTES:
            html += f"<li>{note}</li>\n"
        html += "</ol>\n"

        html += f"""
<div class="footer">
  Графік носить інформаційний характер. Перед застосуванням проконсультуйтесь з лікарем.<br>
  Звіт сформовано автоматично — {datetime.now().strftime('%d.%m.%Y %H:%M')}
</div>
</body></html>"""
        return html

    # ─── State ───────────────────────────────────────────────────────────
    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_state(self):
        dk = date_key(self.current_date)
        if dk not in self.state: self.state[dk] = {}
        for mid, var in self.check_vars.items():
            self.state[dk][f"{mid}_taken"] = var.get()
        if "purchased" not in self.state: self.state["purchased"] = {}
        for mid, var in self.purchased_vars.items():
            self.state["purchased"][mid] = var.get()
        self._save_settings()
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        self._update_stats()

    def _save_settings(self):
        self.state["_settings"] = {
            "reminders_enabled": self.reminders_enabled.get(),
            "reminder_advance_min": self.reminder_advance_min,
        }
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    app = MedicationApp(root)
    root.mainloop()
