"""
Інтерактивний графік прийому ліків v2 — з історією прийому по днях
Бучин Андрій Петрович, 1954 р.н. | Складено: квітень 2026
"""

import tkinter as tk
from tkinter import ttk
import json
import os
import sys
import calendar
from datetime import datetime, timedelta

# --- Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0] if sys.argv[0] else __file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "med_state_v2.json")

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
    "today_highlight": "#E8F5E9",
    "cal_full": "#4CAF50",
    "cal_partial": "#FFC107",
    "cal_empty": "#EEEEEE",
    "cal_none": "#FFFFFF",
    "cal_today_border": "#2196F3",
    "tab_active": "#FFFFFF",
    "tab_inactive": "#CFD8DC",
    "stat_good": "#4CAF50",
    "stat_warn": "#FF9800",
    "stat_bad": "#F44336",
}

COURSE_COLORS = {
    "long": C["course_long"],
    "2m": C["course_2m"],
    "short": C["course_short"],
    "need": C["course_need"],
}

# --- Medication data ---
MEDICATIONS = [
    {
        "section": "РАНОК (сніданок 09:00 - 10:00)",
        "section_key": "morning",
        "items": [
            {"id": "tamsin", "time": "08:30", "time_note": "до їжі",
             "name": "Тамсін Форте", "subtitle": "", "note": "Натщесерце",
             "course": "Тривало", "course_type": "long",
             "description": "Тамсулозин (Тамсін Форте) - альфа-1-адреноблокатор.\nПризначення: лікування симптомів доброякісної гіперплазії передміхурової залози (ДГПЗ).\nМеханізм: розслаблює гладкі м'язи передміхурової залози та шийки сечового міхура, полегшуючи сечовипускання.\nПрийом: натщесерце, за 30 хв до їжі, не розжовувати.\nПобічні ефекти: запаморочення, зниження АТ, закладеність носа."},
            {"id": "olidetrim", "time": "09:00", "time_note": "з їжею",
             "name": "Олідетрім 4000", "subtitle": "вітамін D3",
             "note": "З їжею, що містить жири", "course": "2 міс, потім 2000 тривало", "course_type": "2m",
             "description": "Холекальциферол (вітамін D3) 4000 МО.\nПризначення: корекція дефіциту вітаміну D, підтримка кісткової тканини, імунної системи.\nПрийом: з їжею, що містить жири (для кращого засвоєння).\nКурс: 4000 МО - 2 місяці, потім 2000 МО тривало.\nКонтроль: рівень 25(OH)D у крові через 2-3 місяці."},
            {"id": "vitk2", "time": "09:00", "time_note": "з їжею",
             "name": "Вітамін К2", "subtitle": "", "note": "Разом з D3, з їжею",
             "course": "Тривало", "course_type": "long",
             "description": "Менахінон (вітамін К2, MK-7).\nПризначення: спрямовує кальцій у кістки, запобігає кальцифікації артерій.\nСинергія з D3: вітамін D підвищує засвоєння кальцію, К2 забезпечує його правильний розподіл.\nПрийом: разом з D3, з їжею, що містить жири."},
            {"id": "glutargin1", "time": "09:00", "time_note": "з їжею",
             "name": "Глутаргін 750 мг", "subtitle": "1-й прийом",
             "note": "Гепатопротектор", "course": "2 місяці", "course_type": "2m",
             "description": "Аргініну глутамат 750 мг.\nПризначення: гепатопротекція - захист та відновлення клітин печінки.\nМеханізм: нейтралізує аміак, покращує метаболічні процеси в печінці.\nПрийом: 2 рази на день (ранок + вечір), з їжею. Курс: 2 місяці."},
            {"id": "augmentin", "time": "09:00", "time_note": "з їжею",
             "name": "Аугментин", "subtitle": "антибіотик",
             "note": "З їжею, для захисту ШКТ", "course": "5-7 днів", "course_type": "short",
             "description": "Амоксицилін + клавуланова кислота.\nПризначення: антибіотик широкого спектру, стоматологічне призначення.\nПрийом: з їжею, через рівні проміжки часу, курс не переривати!\nПробіотик приймати через ~6 годин після антибіотика."},
            {"id": "neurorubin1", "time": "10:30", "time_note": "після їжі",
             "name": "Нейрорубін форте", "subtitle": "Лактаб, 1-й прийом",
             "note": "Вітаміни групи В", "course": "2 місяці", "course_type": "2m",
             "description": "Комплекс вітамінів групи В (B1, B6, B12) у високих дозах.\nПризначення: лікування невралгій, невритів, зниження гомоцистеїну.\nПрийом: 2 рази на день, після їжі. Курс: 2 місяці."},
            {"id": "serrata", "time": "10:30", "time_note": "після їжі",
             "name": "Серрата", "subtitle": "протинабрякове",
             "note": "Через 30 хв після їжі", "course": "5-7 днів", "course_type": "short",
             "description": "Серратіопептидаза - протеолітичний фермент.\nПризначення: протинабрякова, протизапальна дія після стоматологічного втручання.\nПрийом: через 30 хв після їжі.\nВажливо: рознесено з Клопідогрелем (обидва впливають на згортання крові). Курс: 5-7 днів."},
        ],
    },
    {
        "section": "ДЕНЬ (обід 14:00 - 15:00)",
        "section_key": "day",
        "items": [
            {"id": "voger", "time": "13:30", "time_note": "до їжі",
             "name": "Вогер", "subtitle": "", "note": "За 30 хв до їжі, гастропротектор",
             "course": "Тривало", "course_type": "long",
             "description": "Ребаміпід (Вогер) - гастропротектор.\nПризначення: захист слизової шлунка, профілактика НПЗП-гастропатії.\nМеханізм: стимулює синтез простагландинів у слизовій шлунка.\nПрийом: за 30 хв до їжі."},
            {"id": "nimesil", "time": "14:00", "time_note": "з їжею",
             "name": "Німесіл", "subtitle": "протизапальне",
             "note": "З їжею або після їжі", "course": "5-7 днів", "course_type": "short",
             "description": "Німесулід - НПЗП, селективний інгібітор ЦОГ-2.\nПризначення: знеболення, протизапальна дія (стоматологічне).\nПрийом: з їжею. Призначений на обід, Клопідогрель - на вечір (мінімізація ризику кровотечі). Курс: 5-7 днів."},
            {"id": "renohels", "time": "14:00", "time_note": "з їжею",
             "name": "Ренохелс", "subtitle": "нефропротектор",
             "note": "З їжею", "course": "Тривало", "course_type": "long",
             "description": "Ренохелс - комплексний нефропротектор на рослинній основі.\nПризначення: підтримка функції нирок.\nПрийом: з їжею. Курс: тривало."},
            {"id": "probiotic", "time": "16:00", "time_note": "після їжі",
             "name": "Пробіотик", "subtitle": "",
             "note": "Через 2 год після антибіотика!", "course": "5-7 днів + 1 тиж.", "course_type": "short",
             "description": "Пробіотик (лакто- та біфідобактерії).\nПризначення: відновлення мікрофлори під час антибіотикотерапії.\nПрийом: через ~6 годин після Аугментину.\nКурс: 5-7 днів + 1 тиждень після завершення антибіотика."},
        ],
    },
    {
        "section": "ВЕЧІР (вечеря 18:00 - 19:00)",
        "section_key": "evening",
        "items": [
            {"id": "glutargin2", "time": "18:00", "time_note": "з їжею",
             "name": "Глутаргін 750 мг", "subtitle": "2-й прийом",
             "note": "Гепатопротектор", "course": "2 місяці", "course_type": "2m",
             "description": "Аргініну глутамат 750 мг (другий прийом).\nДив. опис ранкового прийому.\nРазова доза: 750 мг, добова: 1500 мг."},
            {"id": "pregabalin", "time": "18:00", "time_note": "з їжею",
             "name": "Прегабалін", "subtitle": "невралгія",
             "note": "Дозу уточнити у лікаря", "course": "За призначенням", "course_type": "need",
             "description": "Прегабалін - для лікування нейропатичного болю.\nМеханізм: зв'язується з кальцієвими каналами у ЦНС.\nПрийом: з їжею, дозу призначає лікар.\nВажливо: не припиняти різко, знижувати дозу поступово!"},
            {"id": "atoris", "time": "20:00", "time_note": "після їжі",
             "name": "Аторіс 20 мг", "subtitle": "статин",
             "note": "Ввечері, статини найефективніші вночі", "course": "Тривало", "course_type": "long",
             "description": "Аторвастатин 20 мг - статин.\nПризначення: зниження холестерину, профілактика атеросклерозу.\nПрийом: ввечері (синтез холестерину найактивніший вночі).\nКонтроль: ліпідограма, ГГТ через 2-3 місяці.\nРоксера виключена - два статини одночасно НЕ можна."},
            {"id": "clopidogrel", "time": "20:00", "time_note": "після їжі",
             "name": "Клопідогрель 75 мг", "subtitle": "антиагрегант",
             "note": "Ввечері, тривало", "course": "Тривало", "course_type": "long",
             "description": "Клопідогрель 75 мг - антиагрегант.\nПризначення: профілактика тромбоутворення.\nМеханізм: блокує рецептори ADP на тромбоцитах.\nПрийом: ввечері, рознесений з Німесілом та Серратою. Курс: тривало."},
            {"id": "neurorubin2", "time": "20:00", "time_note": "після їжі",
             "name": "Нейрорубін форте", "subtitle": "Лактаб, 2-й прийом",
             "note": "Вітаміни групи В", "course": "2 місяці", "course_type": "2m",
             "description": "Комплекс вітамінів групи В (другий прийом).\nДив. опис ранкового прийому.\nДобова доза: 2 таблетки."},
        ],
    },
    {
        "section": "ЗА ПОТРЕБОЮ (SOS)",
        "section_key": "sos",
        "items": [
            {"id": "captopril", "time": "SOS", "time_note": "",
             "name": "Каптоприл (каптопрес)", "subtitle": "",
             "note": "1 таб під язик при підвищенні АТ", "course": "За потребою", "course_type": "need",
             "description": "Каптоприл - інгібітор АПФ швидкої дії.\nПризначення: екстрене зниження АТ.\nПрийом: 1 таблетка під язик. Початок дії: 15-30 хв.\nВажливо: контроль АТ через 30 хв. Якщо немає ефекту - виклик швидкої допомоги."},
        ],
    },
]

IMPORTANT_NOTES = [
    "Роксера виключена зі списку - дублює Аторіс (два статини одночасно приймати НЕ можна).",
    "Аугментин і Пробіотик рознесені на ~6 годин для збереження ефективності пробіотика.",
    "Німесіл призначений на обід, а Клопідогрель - на вечір (мінімізація ризику кровотечі).",
    "Серрата рознесена з Клопідогрелем по часу (обидва впливають на згортання крові).",
    "Стоматологічні препарати (Аугментин, Німесіл, Серрата, Пробіотик) - коротким курсом 5-7 днів.",
    "Контроль аналізів через 2-3 місяці: глікований гемоглобін, глюкоза, гомоцистеїн, ліпідограма, ГГТ, віт D3, ТТГ.",
    "Дієта: обмеження тваринних жирів, кави; гіповуглеводна дієта.",
]

# All med IDs (excluding SOS — it's "as needed", not daily)
ALL_DAILY_IDS = []
for sec in MEDICATIONS:
    for item in sec["items"]:
        if item["course_type"] != "need":
            ALL_DAILY_IDS.append(item["id"])

WEEKDAYS_UA = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
MONTHS_UA = [
    "", "Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
    "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень",
]


def date_key(dt):
    return dt.strftime("%Y-%m-%d")


def format_date_ua(dt):
    months_gen = [
        "", "січня", "лютого", "березня", "квітня", "травня", "червня",
        "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
    ]
    wd = WEEKDAYS_UA[dt.weekday()]
    return f"{wd}, {dt.day} {months_gen[dt.month]} {dt.year}"


class MedicationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Графік прийому ліків v2 - Бучин А.П.")
        self.root.configure(bg=C["bg"])
        self.root.geometry("1020x860")
        self.root.minsize(860, 650)

        self.state = self._load_state()  # {date_key: {med_id_taken: bool, ...}, "purchased": {med_id: bool}}
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.cal_year = self.current_date.year
        self.cal_month = self.current_date.month
        self.check_vars = {}
        self.purchased_vars = {}
        self.expanded = {}
        self.detail_frames = {}

        self._setup_styles()
        self._build_ui()

    # ─── Styles ──────────────────────────────────────────────────────────
    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame", background=C["bg"])
        self.style.configure("TNotebook", background=C["bg"])
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=[16, 6])

    # ─── UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=C["header_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="ДЕННИЙ ГРАФІК ПРИЙОМУ ЛІКІВ", bg=C["header_bg"],
                 fg=C["header_fg"], font=("Segoe UI", 15, "bold"), pady=8).pack()
        tk.Label(hdr, text="Бучин Андрій Петрович, 1954 р.н.  |  Складено: квітень 2026",
                 bg=C["header_bg"], fg="#B0BEC5", font=("Segoe UI", 9), pady=4).pack()

        # Date navigation bar
        self.date_bar = tk.Frame(self.root, bg=C["date_nav_bg"], pady=6)
        self.date_bar.pack(fill="x")

        btn_prev = tk.Label(self.date_bar, text="  \u25C0  Попередній день  ", bg="#455A64", fg="white",
                            font=("Segoe UI", 10), cursor="hand2", padx=10, pady=4)
        btn_prev.pack(side="left", padx=(20, 6))
        btn_prev.bind("<Button-1>", lambda e: self._change_date(-1))

        self.date_label = tk.Label(self.date_bar, text="", bg=C["date_nav_bg"], fg="white",
                                   font=("Segoe UI", 12, "bold"))
        self.date_label.pack(side="left", expand=True)

        btn_today = tk.Label(self.date_bar, text="  Сьогодні  ", bg="#1565C0", fg="white",
                             font=("Segoe UI", 10, "bold"), cursor="hand2", padx=10, pady=4)
        btn_today.pack(side="left", padx=6)
        btn_today.bind("<Button-1>", lambda e: self._go_today())

        btn_next = tk.Label(self.date_bar, text="  Наступний день  \u25B6  ", bg="#455A64", fg="white",
                            font=("Segoe UI", 10), cursor="hand2", padx=10, pady=4)
        btn_next.pack(side="left", padx=(6, 20))
        btn_next.bind("<Button-1>", lambda e: self._change_date(1))

        # Tabs: Schedule / History
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self.tab_schedule = tk.Frame(self.notebook, bg=C["bg"])
        self.tab_history = tk.Frame(self.notebook, bg=C["bg"])
        self.notebook.add(self.tab_schedule, text="  Графік прийому  ")
        self.notebook.add(self.tab_history, text="  Історія / Календар  ")

        self._build_schedule_tab()
        self._build_history_tab()
        self._refresh_date()

    # ─── Schedule tab ────────────────────────────────────────────────────
    def _build_schedule_tab(self):
        # Legend
        legend = tk.Frame(self.tab_schedule, bg=C["bg"], pady=4)
        legend.pack(fill="x", padx=20)
        for color, text in [(C["course_long"], "Тривало"), (C["course_2m"], "2 місяці"),
                            (C["course_short"], "5-7 днів"), (C["course_need"], "За потребою")]:
            f = tk.Frame(legend, bg=C["bg"])
            f.pack(side="left", padx=(0, 20))
            tk.Canvas(f, width=12, height=12, bg=color, highlightthickness=0).pack(side="left", padx=(0, 4))
            tk.Label(f, text=text, bg=C["bg"], fg=C["text"], font=("Segoe UI", 9)).pack(side="left")

        # Stats bar
        self.stats_frame = tk.Frame(self.tab_schedule, bg=C["bg"])
        self.stats_frame.pack(fill="x", padx=20, pady=(0, 4))
        self.stats_label = tk.Label(self.stats_frame, text="", bg=C["bg"], fg=C["text"],
                                    font=("Segoe UI", 10))
        self.stats_label.pack(side="left")
        self.stats_bar_canvas = tk.Canvas(self.stats_frame, height=18, bg=C["bg"], highlightthickness=0)
        self.stats_bar_canvas.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Scrollable content
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

        # Mouse wheel
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
        hdr.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(hdr, text=sec["section"], bg=accent, fg="white",
                 font=("Segoe UI", 12, "bold"), padx=14, pady=6).pack(anchor="w")
        for item in sec["items"]:
            self._build_card(parent, item, accent)

    def _build_card(self, parent, item, accent):
        mid = item["id"]
        outer = tk.Frame(parent, bg=accent)
        outer.pack(fill="x", padx=16, pady=(2, 0))

        card = tk.Frame(outer, bg=C["card_bg"])
        card.pack(fill="x", padx=(4, 0))

        row = tk.Frame(card, bg=C["card_bg"], pady=6, padx=10)
        row.pack(fill="x")
        row.columnconfigure(1, weight=1)

        # Time
        tf = tk.Frame(row, bg=C["card_bg"], width=65)
        tf.grid(row=0, column=0, sticky="n", padx=(0, 8))
        tf.grid_propagate(False)
        tf.configure(height=36)
        tk.Label(tf, text=item["time"], bg=C["card_bg"], fg=accent,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        if item["time_note"]:
            tk.Label(tf, text=item["time_note"], bg=C["card_bg"], fg=C["subtext"],
                     font=("Segoe UI", 8)).pack(anchor="w")

        # Name & note
        info = tk.Frame(row, bg=C["card_bg"])
        info.grid(row=0, column=1, sticky="nsew")
        nr = tk.Frame(info, bg=C["card_bg"])
        nr.pack(anchor="w")
        tk.Label(nr, text=item["name"], bg=C["card_bg"], fg=C["text"],
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        if item["subtitle"]:
            tk.Label(nr, text=f"  ({item['subtitle']})", bg=C["card_bg"], fg=C["subtext"],
                     font=("Segoe UI", 9)).pack(side="left")
        tk.Label(info, text=item["note"], bg=C["card_bg"], fg=C["subtext"],
                 font=("Segoe UI", 9), anchor="w").pack(anchor="w")

        # Course badge
        badge_col = COURSE_COLORS.get(item["course_type"], C["subtext"])
        bf = tk.Frame(row, bg=C["card_bg"])
        bf.grid(row=0, column=2, sticky="ne", padx=(6, 0))
        tk.Label(bf, text=f" {item['course']} ", bg=badge_col, fg="white",
                 font=("Segoe UI", 8, "bold"), padx=5, pady=1).pack(anchor="e")

        # Checkboxes
        cf = tk.Frame(row, bg=C["card_bg"])
        cf.grid(row=0, column=3, sticky="ne", padx=(10, 0))

        p_var = tk.BooleanVar(value=self.state.get("purchased", {}).get(mid, False))
        self.purchased_vars[mid] = p_var
        tk.Checkbutton(cf, text="Придбано", variable=p_var, bg=C["card_bg"],
                       fg=C["purchased_on"], selectcolor=C["card_bg"], activebackground=C["card_bg"],
                       font=("Segoe UI", 9), command=self._save_state, anchor="w").pack(anchor="w")

        t_var = tk.BooleanVar(value=False)
        self.check_vars[mid] = t_var
        tk.Checkbutton(cf, text="Прийнято", variable=t_var, bg=C["card_bg"],
                       fg=C["taken_on"], selectcolor=C["card_bg"], activebackground=C["card_bg"],
                       font=("Segoe UI", 9), command=self._save_state, anchor="w").pack(anchor="w")

        # Expand button
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
            btn.configure(text="\u25B6 Опис")
            self.expanded[mid] = False
        else:
            card = self.detail_frames[mid].master
            children = card.pack_slaves()
            sep = children[-1]
            sep.pack_forget()
            self.detail_frames[mid].pack(fill="x")
            sep.pack(fill="x")
            btn.configure(text="\u25BC Опис")
            self.expanded[mid] = True

    def _build_notes(self, parent):
        outer = tk.Frame(parent, bg=C["sos_accent"])
        outer.pack(fill="x", padx=16, pady=(12, 4))
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
        top = tk.Frame(self.tab_history, bg=C["bg"])
        top.pack(fill="x", padx=20, pady=10)

        # Calendar navigation
        cal_nav = tk.Frame(top, bg=C["bg"])
        cal_nav.pack(fill="x")

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

        # Calendar grid
        self.cal_frame = tk.Frame(top, bg=C["bg"])
        self.cal_frame.pack(fill="x", pady=(8, 0))

        # Legend for calendar
        leg_frame = tk.Frame(top, bg=C["bg"])
        leg_frame.pack(fill="x", pady=(8, 0))
        for color, text in [(C["cal_full"], "Всі прийняті"), (C["cal_partial"], "Частково"),
                            (C["cal_empty"], "Нічого не прийнято"), (C["cal_none"], "Немає даних")]:
            f = tk.Frame(leg_frame, bg=C["bg"])
            f.pack(side="left", padx=(0, 16))
            tk.Canvas(f, width=14, height=14, bg=color, highlightthickness=1,
                      highlightbackground=C["border"]).pack(side="left", padx=(0, 4))
            tk.Label(f, text=text, bg=C["bg"], fg=C["text"], font=("Segoe UI", 9)).pack(side="left")

        # Monthly summary
        tk.Label(top, text="Статистика за місяць:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", pady=(14, 4))
        self.month_stats_frame = tk.Frame(top, bg=C["bg"])
        self.month_stats_frame.pack(fill="x")

        # Day detail
        tk.Label(top, text="Деталі обраного дня:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", pady=(14, 4))
        self.day_detail_frame = tk.Frame(top, bg=C["card_bg"], relief="groove", bd=1)
        self.day_detail_frame.pack(fill="x")
        self.day_detail_label = tk.Label(self.day_detail_frame, text="Оберіть день у календарі",
                                         bg=C["card_bg"], fg=C["subtext"],
                                         font=("Segoe UI", 10), pady=10, padx=14, anchor="w", justify="left")
        self.day_detail_label.pack(fill="x")

    def _refresh_calendar(self):
        for w in self.cal_frame.winfo_children():
            w.destroy()

        self.cal_title.configure(text=f"{MONTHS_UA[self.cal_month]} {self.cal_year}")

        # Weekday headers
        for i, wd in enumerate(WEEKDAYS_UA):
            tk.Label(self.cal_frame, text=wd, bg=C["bg"], fg=C["subtext"],
                     font=("Segoe UI", 9, "bold"), width=6).grid(row=0, column=i, padx=2, pady=2)

        cal = calendar.monthcalendar(self.cal_year, self.cal_month)
        today = datetime.now()

        for r, week in enumerate(cal):
            for col, day in enumerate(week):
                if day == 0:
                    tk.Label(self.cal_frame, text="", bg=C["bg"], width=6).grid(
                        row=r + 1, column=col, padx=2, pady=2)
                    continue

                dt = datetime(self.cal_year, self.cal_month, day)
                dk = date_key(dt)
                day_data = self.state.get(dk, {})

                # Calculate completion
                taken_count = sum(1 for mid in ALL_DAILY_IDS if day_data.get(f"{mid}_taken", False))
                total = len(ALL_DAILY_IDS)

                if taken_count == 0 and not day_data:
                    bg_color = C["cal_none"]
                elif taken_count == 0:
                    bg_color = C["cal_empty"]
                elif taken_count == total:
                    bg_color = C["cal_full"]
                else:
                    bg_color = C["cal_partial"]

                is_today = (dt.date() == today.date())
                border_color = C["cal_today_border"] if is_today else C["border"]
                border_w = 2 if is_today else 1

                cell_outer = tk.Frame(self.cal_frame, bg=border_color, padx=border_w, pady=border_w)
                cell_outer.grid(row=r + 1, column=col, padx=2, pady=2, sticky="nsew")

                pct_text = ""
                if day_data:
                    pct = int(taken_count / total * 100) if total else 0
                    pct_text = f"\n{pct}%"

                cell = tk.Label(cell_outer, text=f"{day}{pct_text}", bg=bg_color,
                                fg=C["text"], font=("Segoe UI", 9), width=5, height=2,
                                cursor="hand2")
                cell.pack(fill="both", expand=True)
                cell.bind("<Button-1>", lambda e, d=dt: self._show_day_detail(d))

        self._refresh_month_stats()

    def _refresh_month_stats(self):
        for w in self.month_stats_frame.winfo_children():
            w.destroy()

        days_in_month = calendar.monthrange(self.cal_year, self.cal_month)[1]
        total_days_with_data = 0
        full_days = 0
        partial_days = 0
        empty_days = 0
        total_taken = 0
        total_possible = 0

        for day in range(1, days_in_month + 1):
            dk = date_key(datetime(self.cal_year, self.cal_month, day))
            day_data = self.state.get(dk, {})
            if not day_data:
                continue
            total_days_with_data += 1
            taken = sum(1 for mid in ALL_DAILY_IDS if day_data.get(f"{mid}_taken", False))
            total_taken += taken
            total_possible += len(ALL_DAILY_IDS)
            if taken == len(ALL_DAILY_IDS):
                full_days += 1
            elif taken > 0:
                partial_days += 1
            else:
                empty_days += 1

        if total_days_with_data == 0:
            tk.Label(self.month_stats_frame, text="Немає даних за цей місяць",
                     bg=C["bg"], fg=C["subtext"], font=("Segoe UI", 10)).pack(anchor="w")
            return

        pct = int(total_taken / total_possible * 100) if total_possible else 0

        # Stats text
        stats_text = (
            f"Днів з даними: {total_days_with_data}  |  "
            f"Повний прийом: {full_days}  |  "
            f"Частково: {partial_days}  |  "
            f"Пропущено: {empty_days}  |  "
            f"Загальне виконання: {pct}%"
        )
        if pct >= 80:
            stat_color = C["stat_good"]
        elif pct >= 50:
            stat_color = C["stat_warn"]
        else:
            stat_color = C["stat_bad"]

        tk.Label(self.month_stats_frame, text=stats_text, bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 10)).pack(anchor="w")

        # Progress bar
        bar_frame = tk.Frame(self.month_stats_frame, bg=C["border"], height=20)
        bar_frame.pack(fill="x", pady=(4, 0))
        bar_frame.pack_propagate(False)
        if pct > 0:
            filled = tk.Frame(bar_frame, bg=stat_color)
            filled.place(relwidth=pct / 100, relheight=1.0)
        tk.Label(bar_frame, text=f"{pct}%", bg=stat_color if pct > 15 else C["border"],
                 fg="white" if pct > 15 else C["text"],
                 font=("Segoe UI", 9, "bold")).place(relx=0.5, rely=0.5, anchor="center")

    def _show_day_detail(self, dt):
        dk = date_key(dt)
        day_data = self.state.get(dk, {})

        for w in self.day_detail_frame.winfo_children():
            w.destroy()

        header = format_date_ua(dt)
        tk.Label(self.day_detail_frame, text=header, bg=C["header_bg"], fg=C["header_fg"],
                 font=("Segoe UI", 11, "bold"), padx=12, pady=6).pack(fill="x")

        if not day_data:
            tk.Label(self.day_detail_frame, text="  Немає даних за цей день.",
                     bg=C["card_bg"], fg=C["subtext"], font=("Segoe UI", 10), pady=10,
                     anchor="w").pack(fill="x")
            return

        for sec in MEDICATIONS:
            accent = C[f"{sec['section_key']}_accent"]
            sec_frame = tk.Frame(self.day_detail_frame, bg=C["card_bg"])
            sec_frame.pack(fill="x", padx=10, pady=(4, 0))
            tk.Label(sec_frame, text=sec["section"], bg=C["card_bg"], fg=accent,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            for item in sec["items"]:
                taken = day_data.get(f"{item['id']}_taken", False)
                mark = "\u2705" if taken else "\u274C"
                tk.Label(sec_frame, text=f"    {mark}  {item['time']}  {item['name']}",
                         bg=C["card_bg"], fg=C["text"] if taken else C["subtext"],
                         font=("Segoe UI", 9), anchor="w").pack(anchor="w")

        taken_count = sum(1 for mid in ALL_DAILY_IDS if day_data.get(f"{mid}_taken", False))
        total = len(ALL_DAILY_IDS)
        pct = int(taken_count / total * 100) if total else 0
        tk.Label(self.day_detail_frame, text=f"  Прийнято: {taken_count}/{total} ({pct}%)",
                 bg=C["card_bg"], fg=C["text"], font=("Segoe UI", 10, "bold"),
                 pady=6).pack(fill="x")

    # Also allow clicking a day in the calendar to navigate the schedule tab to that day
    # (already handled: _show_day_detail shows detail in the history tab)

    # ─── Date navigation ─────────────────────────────────────────────────
    def _change_date(self, delta):
        self.current_date += timedelta(days=delta)
        self._refresh_date()

    def _go_today(self):
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.cal_year = self.current_date.year
        self.cal_month = self.current_date.month
        self._refresh_date()

    def _refresh_date(self):
        dk = date_key(self.current_date)
        day_data = self.state.get(dk, {})

        today = datetime.now().date()
        is_today = (self.current_date.date() == today)
        date_str = format_date_ua(self.current_date)
        if is_today:
            date_str += "  (сьогодні)"
        self.date_label.configure(text=date_str)

        # Update taken checkboxes from state
        for mid, var in self.check_vars.items():
            var.set(day_data.get(f"{mid}_taken", False))

        self._update_stats()
        self._refresh_calendar()

    def _update_stats(self):
        dk = date_key(self.current_date)
        day_data = self.state.get(dk, {})
        taken = sum(1 for mid in ALL_DAILY_IDS if day_data.get(f"{mid}_taken", False))
        total = len(ALL_DAILY_IDS)
        pct = int(taken / total * 100) if total else 0

        if pct >= 80:
            color = C["stat_good"]
        elif pct >= 50:
            color = C["stat_warn"]
        else:
            color = C["stat_bad"]

        self.stats_label.configure(text=f"Прийнято: {taken}/{total}")

        self.stats_bar_canvas.delete("all")
        self.stats_bar_canvas.update_idletasks()
        w = self.stats_bar_canvas.winfo_width()
        h = 18
        if w > 1:
            self.stats_bar_canvas.create_rectangle(0, 0, w, h, fill=C["border"], outline="")
            if pct > 0:
                self.stats_bar_canvas.create_rectangle(0, 0, int(w * pct / 100), h, fill=color, outline="")
            self.stats_bar_canvas.create_text(w // 2, h // 2, text=f"{pct}%",
                                              font=("Segoe UI", 9, "bold"),
                                              fill="white" if pct > 15 else C["text"])

    def _change_cal_month(self, delta):
        self.cal_month += delta
        if self.cal_month > 12:
            self.cal_month = 1
            self.cal_year += 1
        elif self.cal_month < 1:
            self.cal_month = 12
            self.cal_year -= 1
        self._refresh_calendar()

    # ─── State persistence ───────────────────────────────────────────────
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

        # Ensure day dict exists
        if dk not in self.state:
            self.state[dk] = {}

        # Save taken state for current date
        for mid, var in self.check_vars.items():
            self.state[dk][f"{mid}_taken"] = var.get()

        # Save purchased state (global, not per-day)
        if "purchased" not in self.state:
            self.state["purchased"] = {}
        for mid, var in self.purchased_vars.items():
            self.state["purchased"][mid] = var.get()

        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        self._update_stats()
        # Don't rebuild the full calendar on every checkbox click — only when switching dates/tabs
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._refresh_calendar())


if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    app = MedicationApp(root)
    root.mainloop()
