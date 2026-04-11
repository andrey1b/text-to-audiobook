"""
Интерактивный график приёма лекарств v9
═══════════════════════════════════════════
Возможности:
  - Карточки препаратов с чекбоксами «Приобретено» и «Принято»
  - Раскрывающееся описание каждого препарата
  - История приёма по дням с календарём
  - Напоминания по расписанию (вкл/выкл)
  - Экспорт отчёта для врача (HTML)
  - Кликабельные названия — поиск в интернете и аптеках
  - Вкладка «Финансы» — учёт расходов на лекарства

Пациент: Бучин Андрей Петрович, 1954 г.р. | Составлено: апрель 2026

Версия 9: русский язык, модульная структура (med_utils.py),
           обучающие комментарии для изучения Python.
"""

# ═══════════════════════════════════════════════════════════════════════════
# РАЗДЕЛ 1: ИМПОРТ МОДУЛЕЙ
# ═══════════════════════════════════════════════════════════════════════════
# import — подключает модуль (файл с готовым кодом).
# from X import Y — импортирует конкретные имена из модуля X.
#
# Стандартные модули Python (встроены, устанавливать не нужно):
#   tkinter    — графический интерфейс (окна, кнопки, поля)
#   json       — чтение/запись данных в формате JSON
#   os, sys    — работа с файлами и системой
#   calendar   — генерация календарной сетки
#   webbrowser — открытие ссылок в браузере
#   urllib      — кодирование строк для URL
#   datetime   — работа с датой и временем
#
# Наш собственный модуль:
#   med_utils  — вспомогательные компоненты (см. med_utils.py)
# ═══════════════════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
import calendar
import webbrowser
import urllib.parse
from datetime import datetime, timedelta

# Импорт из нашего вспомогательного модуля (med_utils.py).
# Модуль должен лежать в той же папке, что и этот скрипт.
# «as C» — создаём короткий псевдоним для словаря цветов.
from med_utils import (
    COLORS as C,            # Цветовая палитра
    COURSE_COLORS,           # Цвета бейджей курсов
    WEEKDAYS_RU,             # Дни недели на русском
    MONTHS_RU,               # Месяцы (именительный падеж)
    MONTHS_RU_GEN,           # Месяцы (родительный падеж)
    date_key,                # datetime → "YYYY-MM-DD"
    format_date_ru,          # datetime → "Пн, 5 апреля 2026"
    ScrollableFrame,         # Прокручиваемый контейнер
    ToastNotification,       # Всплывающие уведомления
    generate_report_html,    # Генерация HTML-отчёта
)


# ═══════════════════════════════════════════════════════════════════════════
# РАЗДЕЛ 2: ПУТИ К ФАЙЛАМ
# ═══════════════════════════════════════════════════════════════════════════
# SCRIPT_DIR — папка, в которой лежит скрипт (или .exe).
# STATE_FILE — файл для сохранения состояния (JSON).
# os.path.join() — безопасно объединяет части пути.

SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0] if sys.argv[0] else __file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "med_state_v9.json")


# ═══════════════════════════════════════════════════════════════════════════
# РАЗДЕЛ 3: ДАННЫЕ О ЛЕКАРСТВАХ
# ═══════════════════════════════════════════════════════════════════════════
# MEDICATIONS — список (list) секций дня, каждая содержит препараты.
# Структура каждого препарата:
#   id          — уникальный ключ для сохранения состояния
#   time        — время приёма
#   time_note   — «до еды» / «с едой» / «после еды»
#   name        — торговое название
#   subtitle    — дополнительная подпись
#   note        — краткое указание
#   course      — длительность курса (текст бейджа)
#   course_type — тип: "long"/"2m"/"short"/"need" (определяет цвет)
#   pharmacy    — название для поиска в аптеке
#   description — полное описание (раскрывается по клику)

MEDICATIONS = [
    {
        "section": "УТРО (завтрак 09:00 - 10:00)", "section_key": "morning",
        "items": [
            {"id": "tamsin", "time": "08:30", "time_note": "до еды",
             "name": "Тамсін Форте", "subtitle": "", "note": "Натощак",
             "course": "Длительно", "course_type": "long", "pharmacy": "Тамсін Форте",
             "description": "Тамсулозин — альфа-1-адреноблокатор.\nНазначение: лечение ДГПЖ.\nПриём: натощак, за 30 мин до еды.\nПобочные эффекты: головокружение, снижение АД."},
            {"id": "olidetrim", "time": "09:00", "time_note": "с едой",
             "name": "Олідетрім 4000", "subtitle": "витамин D3",
             "note": "С едой, содержащей жиры", "course": "2 мес, затем 2000 длительно", "course_type": "2m",
             "pharmacy": "Олідетрім 4000",
             "description": "Витамин D3 4000 МЕ.\nПриём: с едой, содержащей жиры.\nКурс: 4000 МЕ — 2 мес, затем 2000 МЕ длительно.\nКонтроль: 25(OH)D через 2-3 мес."},
            {"id": "vitk2", "time": "09:00", "time_note": "с едой",
             "name": "Вітамін К2", "subtitle": "", "note": "Вместе с D3, с едой",
             "course": "Длительно", "course_type": "long", "pharmacy": "Вітамін К2",
             "description": "Менахинон (К2, MK-7).\nНаправляет кальций в кости, предотвращает кальцификацию артерий.\nПриём: вместе с D3, с едой."},
            {"id": "glutargin1", "time": "09:00", "time_note": "с едой",
             "name": "Глутаргін 750 мг", "subtitle": "1-й приём",
             "note": "Гепатопротектор", "course": "2 месяца", "course_type": "2m",
             "pharmacy": "Глутаргін",
             "description": "Аргинина глутамат 750 мг.\nГепатопротектор. 2 р/день. Курс: 2 мес."},
            {"id": "augmentin", "time": "09:00", "time_note": "с едой",
             "name": "Аугментин", "subtitle": "антибиотик",
             "note": "С едой, для защиты ЖКТ", "course": "5-7 дней", "course_type": "short",
             "pharmacy": "Аугментин",
             "description": "Амоксициллин + клавулановая к-та.\nАнтибиотик, стоматологическое назначение.\nКурс не прерывать! Пробиотик через ~6 ч."},
            {"id": "neurorubin1", "time": "10:30", "time_note": "после еды",
             "name": "Нейрорубін форте", "subtitle": "Лактаб, 1-й приём",
             "note": "Витамины группы В", "course": "2 месяца", "course_type": "2m",
             "pharmacy": "Нейрорубін",
             "description": "Витамины B1, B6, B12.\nЛечение невралгий, снижение гомоцистеина.\n2 р/день, после еды. Курс: 2 мес."},
            {"id": "serrata", "time": "10:30", "time_note": "после еды",
             "name": "Серрата", "subtitle": "противоотёчное",
             "note": "Через 30 мин после еды", "course": "5-7 дней", "course_type": "short",
             "pharmacy": "Серрата",
             "description": "Серратиопептидаза.\nПротивоотёчное действие после стоматологического вмешательства.\nЧерез 30 мин после еды. Курс: 5-7 дней."},
        ],
    },
    {
        "section": "ДЕНЬ (обед 14:00 - 15:00)", "section_key": "day",
        "items": [
            {"id": "voger", "time": "13:30", "time_note": "до еды",
             "name": "Вогер", "subtitle": "", "note": "За 30 мин до еды, гастропротектор",
             "course": "Длительно", "course_type": "long", "pharmacy": "Вогер",
             "description": "Ребамипид — гастропротектор.\nЗащита слизистой желудка. За 30 мин до еды."},
            {"id": "nimesil", "time": "14:00", "time_note": "с едой",
             "name": "Німесіл", "subtitle": "противовоспалительное",
             "note": "С едой или после еды", "course": "5-7 дней", "course_type": "short",
             "pharmacy": "Німесіл",
             "description": "Нимесулид — НПВП.\nОбезболивание (стоматологическое). С едой. Курс: 5-7 дней."},
            {"id": "renohels", "time": "14:00", "time_note": "с едой",
             "name": "Ренохелс", "subtitle": "нефропротектор",
             "note": "С едой", "course": "Длительно", "course_type": "long",
             "pharmacy": "Ренохелс",
             "description": "Нефропротектор растительного происхождения.\nС едой. Курс: длительно."},
            {"id": "probiotic", "time": "16:00", "time_note": "после еды",
             "name": "Пробіотик", "subtitle": "",
             "note": "Через 2 ч после антибиотика!", "course": "5-7 дней + 1 нед.", "course_type": "short",
             "pharmacy": "Пробіотик",
             "description": "Лакто-/бифидобактерии.\nЧерез ~6 ч после Аугментина.\nКурс: 5-7 дней + 1 неделя после."},
        ],
    },
    {
        "section": "ВЕЧЕР (ужин 18:00 - 19:00)", "section_key": "evening",
        "items": [
            {"id": "glutargin2", "time": "18:00", "time_note": "с едой",
             "name": "Глутаргін 750 мг", "subtitle": "2-й приём",
             "note": "Гепатопротектор", "course": "2 месяца", "course_type": "2m",
             "pharmacy": "Глутаргін",
             "description": "Глутаргін (2-й приём). Суточная доза: 1500 мг."},
            {"id": "pregabalin", "time": "18:00", "time_note": "с едой",
             "name": "Прегабалін", "subtitle": "невралгия",
             "note": "Дозу уточнить у врача", "course": "По назначению", "course_type": "need",
             "pharmacy": "Прегабалін",
             "description": "Прегабалин — нейропатическая боль.\nДозу назначает врач. Не прекращать резко!"},
            {"id": "atoris", "time": "20:00", "time_note": "после еды",
             "name": "Аторіс 20 мг", "subtitle": "статин",
             "note": "Вечером, статины наиболее эффективны ночью", "course": "Длительно", "course_type": "long",
             "pharmacy": "Аторіс",
             "description": "Аторвастатин 20 мг — статин.\nСнижение холестерина. Вечером.\nКонтроль: липидограмма, ГГТ через 2-3 мес."},
            {"id": "clopidogrel", "time": "20:00", "time_note": "после еды",
             "name": "Клопідогрель 75 мг", "subtitle": "антиагрегант",
             "note": "Вечером, длительно", "course": "Длительно", "course_type": "long",
             "pharmacy": "Клопідогрель",
             "description": "Антиагрегант. Профилактика тромбообразования.\nВечером. Курс: длительно."},
            {"id": "neurorubin2", "time": "20:00", "time_note": "после еды",
             "name": "Нейрорубін форте", "subtitle": "Лактаб, 2-й приём",
             "note": "Витамины группы В", "course": "2 месяца", "course_type": "2m",
             "pharmacy": "Нейрорубін",
             "description": "Витамины B (2-й приём). Суточная доза: 2 таблетки."},
        ],
    },
    {
        "section": "ПО НЕОБХОДИМОСТИ (SOS)", "section_key": "sos",
        "items": [
            {"id": "captopril", "time": "SOS", "time_note": "",
             "name": "Каптоприл (каптопрес)", "subtitle": "",
             "note": "1 таб под язык при повышении АД", "course": "По необходимости", "course_type": "need",
             "pharmacy": "Каптопрес",
             "description": "Каптоприл — экстренное снижение АД.\n1 таб под язык. Действие через 15-30 мин.\nЕсли нет эффекта — вызов скорой."},
        ],
    },
]

# --- Важные примечания ---
IMPORTANT_NOTES = [
    "Роксера исключена из списка — дублирует Аторіс (два статина одновременно НЕЛЬЗЯ).",
    "Аугментин и Пробіотик разнесены на ~6 часов для эффективности пробиотика.",
    "Німесіл на обед, Клопідогрель на ужин — минимизация риска кровотечения.",
    "Серрата разнесена с Клопідогрелем (оба влияют на свёртывание крови).",
    "Стоматологические (Аугментин, Німесіл, Серрата, Пробіотик) — 5-7 дней.",
    "Контроль через 2-3 мес: HbA1c, глюкоза, гомоцистеин, липидограмма, ГГТ, D3, ТТГ.",
    "Диета: ограничение животных жиров, кофе; гипоуглеводная диета.",
]


# ═══════════════════════════════════════════════════════════════════════════
# РАЗДЕЛ 4: ВСПОМОГАТЕЛЬНЫЕ СТРУКТУРЫ
# ═══════════════════════════════════════════════════════════════════════════

# Список ID ежедневных препаратов (исключая «по потребности»)
ALL_DAILY_IDS = []
for _sec in MEDICATIONS:
    for _item in _sec["items"]:
        if _item["course_type"] != "need":
            ALL_DAILY_IDS.append(_item["id"])

# Расписание напоминаний: {время: [препараты]}
REMINDER_SCHEDULE = {}
for _sec in MEDICATIONS:
    for _item in _sec["items"]:
        t = _item["time"]
        if t == "SOS":
            continue
        REMINDER_SCHEDULE.setdefault(t, []).append(_item)

REMINDER_TIMES_SORTED = sorted(REMINDER_SCHEDULE.keys())


# ═══════════════════════════════════════════════════════════════════════════
# РАЗДЕЛ 5: ОСНОВНОЙ КЛАСС ПРИЛОЖЕНИЯ
# ═══════════════════════════════════════════════════════════════════════════

class MedicationApp:
    """Главный класс приложения — управляет интерфейсом и состоянием."""

    REMINDER_CHECK_INTERVAL = 30_000  # мс (проверка каждые 30 сек)

    def __init__(self, root):
        """Инициализация: загрузка состояния, построение интерфейса."""
        self.root = root
        self.root.title("График приёма лекарств v9 — Бучин А.П.")
        self.root.configure(bg=C["bg"])
        self.root.geometry("1040x880")
        self.root.minsize(880, 660)

        self.state = self._load_state()
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.cal_year = self.current_date.year
        self.cal_month = self.current_date.month

        # Словари переменных виджетов
        self.check_vars = {}       # {med_id: BooleanVar} — «Принято»
        self.purchased_vars = {}   # {med_id: BooleanVar} — «Приобретено»
        self.expanded = {}         # {med_id: bool} — описание развёрнуто?
        self.detail_frames = {}    # {med_id: Frame} — фреймы описаний

        # Состояние напоминаний
        self.reminders_enabled = tk.BooleanVar(
            value=self.state.get("_settings", {}).get("reminders_enabled", False))
        self.reminder_advance_min = self.state.get("_settings", {}).get("reminder_advance_min", 5)
        self._shown_reminders_today = set()
        self._last_reminder_date = None

        self._setup_styles()
        self._build_ui()
        self._start_reminder_loop()

    # ─── Стили ──────────────────────────────────────────────────────────
    def _setup_styles(self):
        """Настройка стилей ttk-виджетов."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=C["bg"])
        style.configure("TNotebook", background=C["bg"])
        style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=[14, 5])

    # ─── Главный интерфейс ──────────────────────────────────────────────
    def _build_ui(self):
        """Создаёт заголовок, панель инструментов и вкладки."""

        # === Заголовок ===
        hdr = tk.Frame(self.root, bg=C["header_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="ДНЕВНОЙ ГРАФИК ПРИЁМА ЛЕКАРСТВ", bg=C["header_bg"],
                 fg=C["header_fg"], font=("Segoe UI", 15, "bold"), pady=8).pack()
        tk.Label(hdr, text="Бучин Андрей Петрович, 1954 г.р.  |  Составлено: апрель 2026",
                 bg=C["header_bg"], fg="#B0BEC5", font=("Segoe UI", 9), pady=4).pack()

        # === Панель инструментов ===
        toolbar = tk.Frame(self.root, bg=C["date_nav_bg"], pady=5)
        toolbar.pack(fill="x")

        # Навигация по датам: ◀ [дата] ▶ [Сегодня]
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

        btn_today = tk.Label(toolbar, text=" Сегодня ", bg="#1565C0", fg="white",
                             font=("Segoe UI", 9, "bold"), cursor="hand2", padx=8, pady=3)
        btn_today.pack(side="left", padx=4)
        btn_today.bind("<Button-1>", lambda e: self._go_today())

        # Правая часть: экспорт + напоминания
        self.btn_export = tk.Label(toolbar, text=" \U0001F4C4 Отчёт для врача ", bg="#00897B", fg="white",
                                   font=("Segoe UI", 9, "bold"), cursor="hand2", padx=8, pady=3)
        self.btn_export.pack(side="right", padx=(4, 12))
        self.btn_export.bind("<Button-1>", lambda e: self._show_export_dialog())

        self.reminder_btn = tk.Label(toolbar, text="", bg=C["reminder_off"], fg="white",
                                     font=("Segoe UI", 9, "bold"), cursor="hand2", padx=8, pady=3)
        self.reminder_btn.pack(side="right", padx=4)
        self.reminder_btn.bind("<Button-1>", lambda e: self._toggle_reminders())
        self._update_reminder_btn()

        # === Вкладки ===
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self.tab_schedule = tk.Frame(self.notebook, bg=C["bg"])
        self.tab_history = tk.Frame(self.notebook, bg=C["bg"])
        self.tab_finance = tk.Frame(self.notebook, bg=C["bg"])
        self.notebook.add(self.tab_schedule, text="  График приёма  ")
        self.notebook.add(self.tab_history, text="  История / Календарь  ")
        self.notebook.add(self.tab_finance, text="  Финансы  ")
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._on_tab_changed())

        self._build_schedule_tab()
        self._build_history_tab()
        self._build_finance_tab()
        self._refresh_date()

    def _on_tab_changed(self):
        idx = self.notebook.index("current")
        if idx == 1:
            self._refresh_calendar()
        elif idx == 2:
            self._refresh_finance_table()

    # ═══════════════════════════════════════════════════════════════════════
    # РАЗДЕЛ 6: ВКЛАДКА «ГРАФИК ПРИЁМА»
    # ═══════════════════════════════════════════════════════════════════════

    def _build_schedule_tab(self):
        """Легенда, статистика и прокручиваемый список карточек."""

        # Легенда курсов
        legend = tk.Frame(self.tab_schedule, bg=C["bg"], pady=4)
        legend.pack(fill="x", padx=20)
        for color, txt in [(C["course_long"], "Длительно"), (C["course_2m"], "2 месяца"),
                           (C["course_short"], "5-7 дней"), (C["course_need"], "По потребности")]:
            f = tk.Frame(legend, bg=C["bg"])
            f.pack(side="left", padx=(0, 18))
            tk.Canvas(f, width=12, height=12, bg=color, highlightthickness=0).pack(side="left", padx=(0, 4))
            tk.Label(f, text=txt, bg=C["bg"], fg=C["text"], font=("Segoe UI", 9)).pack(side="left")

        # Статистика за день
        self.stats_frame = tk.Frame(self.tab_schedule, bg=C["bg"])
        self.stats_frame.pack(fill="x", padx=20, pady=(0, 3))
        self.stats_label = tk.Label(self.stats_frame, text="", bg=C["bg"], fg=C["text"],
                                    font=("Segoe UI", 10))
        self.stats_label.pack(side="left")
        self.stats_bar_canvas = tk.Canvas(self.stats_frame, height=18, bg=C["bg"], highlightthickness=0)
        self.stats_bar_canvas.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Прокручиваемая область — теперь используем ScrollableFrame из med_utils
        self.schedule_scroll = ScrollableFrame(self.tab_schedule)
        self.schedule_scroll.pack(fill="both", expand=True)
        self.schedule_scroll.bind_mousewheel(self.root)
        self.scrollable = self.schedule_scroll.interior  # Для обратной совместимости

        # Секции с карточками
        for sec in MEDICATIONS:
            self._build_section(self.scrollable, sec)
        self._build_notes(self.scrollable)

        tk.Label(self.scrollable,
                 text="График носит информационный характер. Перед применением проконсультируйтесь с врачом.",
                 bg=C["bg"], fg=C["subtext"], font=("Segoe UI", 9, "italic"), pady=10).pack(fill="x", padx=20)

    def _build_section(self, parent, sec):
        """Заголовок секции + карточки препаратов."""
        accent = C[f"{sec['section_key']}_accent"]
        hdr = tk.Frame(parent, bg=accent)
        hdr.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(hdr, text=sec["section"], bg=accent, fg="white",
                 font=("Segoe UI", 12, "bold"), padx=14, pady=5).pack(anchor="w")
        for item in sec["items"]:
            self._build_card(parent, item, accent)

    def _build_card(self, parent, item, accent):
        """Карточка одного препарата."""
        mid = item["id"]

        outer = tk.Frame(parent, bg=accent)
        outer.pack(fill="x", padx=16, pady=(2, 0))
        card = tk.Frame(outer, bg=C["card_bg"])
        card.pack(fill="x", padx=(4, 0))

        row = tk.Frame(card, bg=C["card_bg"], pady=5, padx=10)
        row.pack(fill="x")
        row.columnconfigure(1, weight=1)

        # Время
        tf = tk.Frame(row, bg=C["card_bg"], width=65)
        tf.grid(row=0, column=0, sticky="n", padx=(0, 8))
        tf.grid_propagate(False); tf.configure(height=34)
        tk.Label(tf, text=item["time"], bg=C["card_bg"], fg=accent,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        if item["time_note"]:
            tk.Label(tf, text=item["time_note"], bg=C["card_bg"], fg=C["subtext"],
                     font=("Segoe UI", 8)).pack(anchor="w")

        # Название (кликабельное)
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

        # Бейдж курса
        badge_col = COURSE_COLORS.get(item["course_type"], C["subtext"])
        bf = tk.Frame(row, bg=C["card_bg"])
        bf.grid(row=0, column=2, sticky="ne", padx=(6, 0))
        tk.Label(bf, text=f" {item['course']} ", bg=badge_col, fg="white",
                 font=("Segoe UI", 8, "bold"), padx=5, pady=1).pack(anchor="e")

        # Чекбоксы
        cf = tk.Frame(row, bg=C["card_bg"])
        cf.grid(row=0, column=3, sticky="ne", padx=(10, 0))

        p_row = tk.Frame(cf, bg=C["card_bg"])
        p_row.pack(anchor="w")
        p_var = tk.BooleanVar(value=self.state.get("purchased", {}).get(mid, False))
        self.purchased_vars[mid] = p_var
        tk.Checkbutton(p_row, text="Приобретено", variable=p_var, bg=C["card_bg"],
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
        tk.Checkbutton(cf, text="Принято", variable=t_var, bg=C["card_bg"],
                       fg=C["taken_on"], selectcolor=C["card_bg"], activebackground=C["card_bg"],
                       font=("Segoe UI", 9), command=self._save_state, anchor="w").pack(anchor="w")

        # Раскрывающееся описание
        self.expanded[mid] = False
        tog = tk.Label(row, text="\u25B6 Описание", bg=C["card_bg"], fg=accent,
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
            btn.configure(text="\u25B6 Описание"); self.expanded[mid] = False
        else:
            card = self.detail_frames[mid].master
            children = card.pack_slaves(); sep = children[-1]
            sep.pack_forget(); self.detail_frames[mid].pack(fill="x"); sep.pack(fill="x")
            btn.configure(text="\u25BC Описание"); self.expanded[mid] = True

    @staticmethod
    def _search_med(name):
        query = urllib.parse.quote(f"{name} инструкция цена отзывы")
        webbrowser.open(f"https://www.google.com/search?q={query}")

    @staticmethod
    def _search_pharmacy(name):
        encoded = urllib.parse.quote(name)
        webbrowser.open(f"https://tabletki.ua/uk/search/?q={encoded}")

    def _build_notes(self, parent):
        outer = tk.Frame(parent, bg=C["sos_accent"])
        outer.pack(fill="x", padx=16, pady=(10, 4))
        tk.Label(outer, text="ВАЖНЫЕ ПРИМЕЧАНИЯ", bg=C["sos_accent"], fg="white",
                 font=("Segoe UI", 11, "bold"), padx=14, pady=5).pack(anchor="w")
        body = tk.Frame(outer, bg=C["notes_bg"])
        body.pack(fill="x", padx=(4, 0))
        for i, note in enumerate(IMPORTANT_NOTES, 1):
            tk.Label(body, text=f"  {i}. {note}", bg=C["notes_bg"], fg=C["text"],
                     font=("Segoe UI", 9), anchor="w", justify="left", wraplength=880,
                     padx=10, pady=2).pack(fill="x", anchor="w")
        tk.Frame(body, bg=C["notes_bg"], height=4).pack()

    # ═══════════════════════════════════════════════════════════════════════
    # РАЗДЕЛ 7: ВКЛАДКА «ИСТОРИЯ / КАЛЕНДАРЬ»
    # ═══════════════════════════════════════════════════════════════════════

    def _build_history_tab(self):
        # Прокручиваемая область — через ScrollableFrame
        self.hist_scroll = ScrollableFrame(self.tab_history)
        self.hist_scroll.pack(fill="both", expand=True)
        top = self.hist_scroll.interior

        # Навигация по месяцам
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

        # Легенда
        leg_frame = tk.Frame(top, bg=C["bg"])
        leg_frame.pack(fill="x", padx=20, pady=(6, 0))
        for color, txt in [(C["cal_full"], "Все приняты"), (C["cal_partial"], "Частично"),
                           (C["cal_empty"], "Пропущено"), (C["cal_none"], "Нет данных")]:
            f = tk.Frame(leg_frame, bg=C["bg"]); f.pack(side="left", padx=(0, 14))
            tk.Canvas(f, width=14, height=14, bg=color, highlightthickness=1,
                      highlightbackground=C["border"]).pack(side="left", padx=(0, 4))
            tk.Label(f, text=txt, bg=C["bg"], fg=C["text"], font=("Segoe UI", 9)).pack(side="left")

        tk.Label(top, text="Статистика за месяц:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", padx=20, pady=(12, 4))
        self.month_stats_frame = tk.Frame(top, bg=C["bg"])
        self.month_stats_frame.pack(fill="x", padx=20)

        tk.Label(top, text="Детали выбранного дня:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", padx=20, pady=(12, 4))
        self.day_detail_frame = tk.Frame(top, bg=C["card_bg"], relief="groove", bd=1)
        self.day_detail_frame.pack(fill="x", padx=20)
        tk.Label(self.day_detail_frame, text="  Выберите день в календаре",
                 bg=C["card_bg"], fg=C["subtext"], font=("Segoe UI", 10), pady=10, anchor="w").pack(fill="x")
        tk.Frame(top, bg=C["bg"], height=20).pack()

    def _refresh_calendar(self):
        for w in self.cal_frame.winfo_children():
            w.destroy()
        self.cal_title.configure(text=f"{MONTHS_RU[self.cal_month]} {self.cal_year}")
        for i, wd in enumerate(WEEKDAYS_RU):
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
            tk.Label(self.month_stats_frame, text="Нет данных за этот месяц",
                     bg=C["bg"], fg=C["subtext"], font=("Segoe UI", 10)).pack(anchor="w")
            return
        pct = int(t_taken / t_poss * 100) if t_poss else 0
        sc = C["stat_good"] if pct >= 80 else C["stat_warn"] if pct >= 50 else C["stat_bad"]
        tk.Label(self.month_stats_frame,
                 text=f"Дней: {total_d}  |  Полный: {full_d}  |  Частично: {part_d}  |  Пропущено: {empty_d}  |  Выполнение: {pct}%",
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
        tk.Label(self.day_detail_frame, text=format_date_ru(dt), bg=C["header_bg"],
                 fg=C["header_fg"], font=("Segoe UI", 11, "bold"), padx=12, pady=5).pack(fill="x")
        if not dd:
            tk.Label(self.day_detail_frame, text="  Нет данных.", bg=C["card_bg"],
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
        tk.Label(self.day_detail_frame, text=f"  Принято: {tk_n}/{tot} ({int(tk_n/tot*100) if tot else 0}%)",
                 bg=C["card_bg"], fg=C["text"], font=("Segoe UI", 10, "bold"), pady=5).pack(fill="x")

    # ═══════════════════════════════════════════════════════════════════════
    # РАЗДЕЛ 8: ВКЛАДКА «ФИНАНСЫ»
    # ═══════════════════════════════════════════════════════════════════════

    def _build_finance_tab(self):
        self._fin_meds = []
        seen = set()
        for sec in MEDICATIONS:
            for it in sec["items"]:
                if it["id"] not in seen:
                    self._fin_meds.append({"id": it["id"], "name": it["name"],
                                           "subtitle": it.get("subtitle", "")})
                    seen.add(it["id"])
        self._fin_data = self.state.get("_finance", {"dates": [], "cells": {}})

        hdr = tk.Frame(self.tab_finance, bg=C["header_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="УЧЁТ РАСХОДОВ НА ЛЕКАРСТВА", bg=C["header_bg"], fg=C["header_fg"],
                 font=("Segoe UI", 13, "bold"), pady=8, padx=16).pack(side="left")

        tb = tk.Frame(self.tab_finance, bg=C["date_nav_bg"], pady=5)
        tb.pack(fill="x")
        add_btn = tk.Label(tb, text=" + Добавить дату ", bg="#00897B", fg="white",
                           font=("Segoe UI", 10, "bold"), cursor="hand2", padx=10, pady=3)
        add_btn.pack(side="left", padx=(16, 6))
        add_btn.bind("<Button-1>", lambda e: self._fin_add_date())
        del_btn = tk.Label(tb, text=" - Удалить последнюю ", bg="#C62828", fg="white",
                           font=("Segoe UI", 9), cursor="hand2", padx=8, pady=3)
        del_btn.pack(side="left", padx=4)
        del_btn.bind("<Button-1>", lambda e: self._fin_del_date())
        self._fin_total_label = tk.Label(tb, text="", bg=C["date_nav_bg"], fg="#FFC107",
                                         font=("Segoe UI", 12, "bold"))
        self._fin_total_label.pack(side="right", padx=16)
        tk.Label(tb, text="Итого:", bg=C["date_nav_bg"], fg="#B0BEC5",
                 font=("Segoe UI", 10)).pack(side="right")

        # Прокручиваемая таблица — через ScrollableFrame
        self.fin_scroll = ScrollableFrame(self.tab_finance, orient="both")
        self.fin_scroll.pack(fill="both", expand=True)
        self._fin_table_frame = self.fin_scroll.interior

        self._fin_entries = {}
        self._fin_col_totals = {}
        self._fin_row_totals = {}
        self._refresh_finance_table()

    def _refresh_finance_table(self):
        for w in self._fin_table_frame.winfo_children():
            w.destroy()
        self._fin_entries.clear()
        self._fin_col_totals.clear()
        self._fin_row_totals.clear()

        dates = self._fin_data.get("dates", [])
        cells = self._fin_data.get("cells", {})
        meds = self._fin_meds
        hdr_bg = "#37474F"; hdr_fg = "white"; cell_bg = "white"; tot_bg = "#ECEFF1"

        tk.Label(self._fin_table_frame, text="№", bg=hdr_bg, fg=hdr_fg,
                 font=("Segoe UI", 9, "bold"), width=3, relief="ridge").grid(row=0, column=0, sticky="nsew")
        tk.Label(self._fin_table_frame, text="Препарат", bg=hdr_bg, fg=hdr_fg,
                 font=("Segoe UI", 9, "bold"), width=22, anchor="w", padx=6,
                 relief="ridge").grid(row=0, column=1, sticky="nsew")
        for ci, d in enumerate(dates):
            tk.Label(self._fin_table_frame, text=d, bg=hdr_bg, fg=hdr_fg,
                     font=("Segoe UI", 9, "bold"), width=10, relief="ridge"
                     ).grid(row=0, column=ci + 2, sticky="nsew")
        tk.Label(self._fin_table_frame, text="Итого", bg="#1B5E20", fg="white",
                 font=("Segoe UI", 9, "bold"), width=10, relief="ridge"
                 ).grid(row=0, column=len(dates) + 2, sticky="nsew")

        for ri, med in enumerate(meds):
            mid = med["id"]; row = ri + 1
            tk.Label(self._fin_table_frame, text=str(row), bg=tot_bg, fg=C["text"],
                     font=("Segoe UI", 9), width=3, relief="ridge"
                     ).grid(row=row, column=0, sticky="nsew")
            name_text = med["name"]
            if med["subtitle"]: name_text += f" ({med['subtitle']})"
            tk.Label(self._fin_table_frame, text=name_text, bg=cell_bg, fg=C["text"],
                     font=("Segoe UI", 9), anchor="w", padx=6, relief="ridge"
                     ).grid(row=row, column=1, sticky="nsew")
            for ci, d in enumerate(dates):
                val = cells.get(mid, {}).get(d, "")
                sv = tk.StringVar(value=str(val) if val != "" else "")
                self._fin_entries[(mid, d)] = sv
                e = tk.Entry(self._fin_table_frame, textvariable=sv, width=10,
                             font=("Segoe UI", 9), justify="right", relief="ridge", bg=cell_bg)
                e.grid(row=row, column=ci + 2, sticky="nsew")
                e.bind("<FocusOut>", lambda ev: self._fin_recalc())
                e.bind("<Return>", lambda ev: self._fin_recalc())
            rt = tk.Label(self._fin_table_frame, text="0.00", bg="#E8F5E9", fg="#1B5E20",
                          font=("Segoe UI", 9, "bold"), width=10, anchor="e", padx=6, relief="ridge")
            rt.grid(row=row, column=len(dates) + 2, sticky="nsew")
            self._fin_row_totals[mid] = rt

        total_row = len(meds) + 1
        tk.Label(self._fin_table_frame, text="", bg=tot_bg, relief="ridge"
                 ).grid(row=total_row, column=0, sticky="nsew")
        tk.Label(self._fin_table_frame, text="Итого по дате:", bg=tot_bg, fg=C["text"],
                 font=("Segoe UI", 9, "bold"), anchor="w", padx=6, relief="ridge"
                 ).grid(row=total_row, column=1, sticky="nsew")
        for ci, d in enumerate(dates):
            ct = tk.Label(self._fin_table_frame, text="0.00", bg=tot_bg, fg="#0D47A1",
                          font=("Segoe UI", 9, "bold"), width=10, anchor="e", padx=6, relief="ridge")
            ct.grid(row=total_row, column=ci + 2, sticky="nsew")
            self._fin_col_totals[d] = ct
        self._fin_grand_label = tk.Label(self._fin_table_frame, text="0.00",
                                         bg="#1B5E20", fg="white",
                                         font=("Segoe UI", 10, "bold"), width=10,
                                         anchor="e", padx=6, relief="ridge")
        self._fin_grand_label.grid(row=total_row, column=len(dates) + 2, sticky="nsew")
        self._fin_recalc()

    def _fin_recalc(self):
        dates = self._fin_data.get("dates", [])
        cells = self._fin_data.get("cells", {})
        grand = 0.0
        for med in self._fin_meds:
            mid = med["id"]; row_sum = 0.0
            if mid not in cells: cells[mid] = {}
            for d in dates:
                key = (mid, d)
                if key in self._fin_entries:
                    raw = self._fin_entries[key].get().strip()
                    try:
                        val = float(raw.replace(",", ".")) if raw else 0.0
                    except ValueError:
                        val = 0.0
                    cells[mid][d] = val if val else ""
                    row_sum += val
            if mid in self._fin_row_totals:
                self._fin_row_totals[mid].configure(text=f"{row_sum:.2f}" if row_sum else "")
            grand += row_sum
        for d in dates:
            col_sum = 0.0
            for med in self._fin_meds:
                v = cells.get(med["id"], {}).get(d, "")
                if v:
                    try: col_sum += float(v)
                    except (ValueError, TypeError): pass
            if d in self._fin_col_totals:
                self._fin_col_totals[d].configure(text=f"{col_sum:.2f}" if col_sum else "")
        if hasattr(self, "_fin_grand_label"):
            self._fin_grand_label.configure(text=f"{grand:.2f}")
        self._fin_total_label.configure(text=f"{grand:.2f} грн")
        self._fin_data["cells"] = cells
        self.state["_finance"] = self._fin_data
        self._persist_state()

    def _fin_add_date(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Добавить дату")
        dlg.geometry("300x140")
        dlg.configure(bg=C["bg"])
        dlg.resizable(False, False)
        dlg.transient(self.root); dlg.grab_set()
        tk.Label(dlg, text="Введите дату (ДД.ММ.ГГГГ):", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 10)).pack(pady=(16, 6), padx=20, anchor="w")
        today = datetime.now()
        date_var = tk.StringVar(value=today.strftime("%d.%m.%Y"))
        entry = tk.Entry(dlg, textvariable=date_var, font=("Segoe UI", 11), width=14)
        entry.pack(padx=20, anchor="w")
        entry.select_range(0, "end"); entry.focus_set()

        def confirm():
            val = date_var.get().strip()
            if not val: return
            if val not in self._fin_data["dates"]:
                self._fin_data["dates"].append(val)
                self.state["_finance"] = self._fin_data
                self._persist_state()
            dlg.destroy()
            self._refresh_finance_table()

        entry.bind("<Return>", lambda e: confirm())
        tk.Label(dlg, text="  OK  ", bg="#00897B", fg="white", font=("Segoe UI", 10, "bold"),
                 cursor="hand2", padx=12, pady=4).pack(pady=10)
        dlg.winfo_children()[-1].bind("<Button-1>", lambda e: confirm())

    def _fin_del_date(self):
        dates = self._fin_data.get("dates", [])
        if not dates: return
        removed = dates.pop()
        for mid in self._fin_data.get("cells", {}):
            self._fin_data["cells"][mid].pop(removed, None)
        self.state["_finance"] = self._fin_data
        self._persist_state()
        self._refresh_finance_table()

    def _persist_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════
    # РАЗДЕЛ 9: НАВИГАЦИЯ ПО ДАТАМ
    # ═══════════════════════════════════════════════════════════════════════

    def _change_date(self, delta):
        self.current_date += timedelta(days=delta); self._refresh_date()

    def _go_today(self):
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.cal_year = self.current_date.year; self.cal_month = self.current_date.month
        self._refresh_date()

    def _refresh_date(self):
        dk = date_key(self.current_date); dd = self.state.get(dk, {})
        is_today = (self.current_date.date() == datetime.now().date())
        ds = format_date_ru(self.current_date)
        if is_today: ds += "  (сегодня)"
        self.date_label.configure(text=ds)
        for mid, var in self.check_vars.items():
            var.set(dd.get(f"{mid}_taken", False))
        self._update_stats()

    def _update_stats(self):
        dk = date_key(self.current_date); dd = self.state.get(dk, {})
        taken = sum(1 for m in ALL_DAILY_IDS if dd.get(f"{m}_taken", False))
        total = len(ALL_DAILY_IDS); pct = int(taken/total*100) if total else 0
        sc = C["stat_good"] if pct >= 80 else C["stat_warn"] if pct >= 50 else C["stat_bad"]
        self.stats_label.configure(text=f"Принято: {taken}/{total}")
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

    # ═══════════════════════════════════════════════════════════════════════
    # РАЗДЕЛ 10: НАПОМИНАНИЯ
    # ═══════════════════════════════════════════════════════════════════════

    def _toggle_reminders(self):
        self.reminders_enabled.set(not self.reminders_enabled.get())
        self._update_reminder_btn()
        self._save_settings()
        status = "включены" if self.reminders_enabled.get() else "выключены"
        ToastNotification(self.root, "Напоминания", f"Напоминания {status}.", duration=4000)

    def _update_reminder_btn(self):
        if self.reminders_enabled.get():
            self.reminder_btn.configure(text="\U0001F514 Напоминания: ВКЛ", bg=C["reminder_on"])
        else:
            self.reminder_btn.configure(text="\U0001F515 Напоминания: ВЫКЛ", bg=C["reminder_off"])

    def _start_reminder_loop(self):
        self._check_reminders()
        self.root.after(self.REMINDER_CHECK_INTERVAL, self._start_reminder_loop)

    def _check_reminders(self):
        if not self.reminders_enabled.get():
            return
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
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
            if trigger_minutes <= current_minutes <= trigger_minutes + 5:
                items = REMINDER_SCHEDULE[time_str]
                names = "\n".join(f"\u2022 {it['name']}" + (f" ({it['subtitle']})" if it['subtitle'] else "")
                                  for it in items)
                title = f"\u23F0 Время приёма лекарств — {time_str}"
                msg = f"Необходимо принять:\n{names}"
                ToastNotification(self.root, title, msg, duration=60000)
                self._shown_reminders_today.add(time_str)

    # ═══════════════════════════════════════════════════════════════════════
    # РАЗДЕЛ 11: ЭКСПОРТ ОТЧЁТА
    # ═══════════════════════════════════════════════════════════════════════

    def _show_export_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Экспорт отчёта для врача")
        dlg.geometry("460x340")
        dlg.configure(bg=C["bg"])
        dlg.resizable(False, False)
        dlg.transient(self.root); dlg.grab_set()

        tk.Label(dlg, text="Экспорт отчёта для врача", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 14, "bold")).pack(pady=(16, 8))
        tk.Label(dlg, text="Выберите период:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=20)

        range_frame = tk.Frame(dlg, bg=C["bg"])
        range_frame.pack(fill="x", padx=20, pady=8)
        today = datetime.now()
        all_dates = sorted([k for k in self.state if k not in ("purchased", "_settings") and "-" in k])
        fd = datetime.strptime(all_dates[0], "%Y-%m-%d") if all_dates else today - timedelta(days=30)

        var_from_day = tk.StringVar(value=str(fd.day))
        var_from_month = tk.StringVar(value=str(fd.month))
        var_from_year = tk.StringVar(value=str(fd.year))
        var_to_day = tk.StringVar(value=str(today.day))
        var_to_month = tk.StringVar(value=str(today.month))
        var_to_year = tk.StringVar(value=str(today.year))

        tk.Label(range_frame, text="С:", bg=C["bg"], fg=C["text"], font=("Segoe UI", 10)).grid(row=0, column=0, padx=(0, 6))
        tk.Spinbox(range_frame, from_=1, to=31, width=3, font=("Segoe UI", 10), textvariable=var_from_day).grid(row=0, column=1, padx=2)
        tk.Spinbox(range_frame, from_=1, to=12, width=3, font=("Segoe UI", 10), textvariable=var_from_month).grid(row=0, column=2, padx=2)
        tk.Spinbox(range_frame, from_=2024, to=2030, width=5, font=("Segoe UI", 10), textvariable=var_from_year).grid(row=0, column=3, padx=2)
        tk.Label(range_frame, text="  По:", bg=C["bg"], fg=C["text"], font=("Segoe UI", 10)).grid(row=0, column=4, padx=(10, 6))
        tk.Spinbox(range_frame, from_=1, to=31, width=3, font=("Segoe UI", 10), textvariable=var_to_day).grid(row=0, column=5, padx=2)
        tk.Spinbox(range_frame, from_=1, to=12, width=3, font=("Segoe UI", 10), textvariable=var_to_month).grid(row=0, column=6, padx=2)
        tk.Spinbox(range_frame, from_=2024, to=2030, width=5, font=("Segoe UI", 10), textvariable=var_to_year).grid(row=0, column=7, padx=2)

        qf = tk.Frame(dlg, bg=C["bg"])
        qf.pack(fill="x", padx=20, pady=4)

        def set_range(days_back):
            s = today - timedelta(days=days_back)
            var_from_day.set(str(s.day)); var_from_month.set(str(s.month)); var_from_year.set(str(s.year))

        for label, d in [("7 дней", 7), ("14 дней", 14), ("30 дней", 30), ("Всё время", 365)]:
            b = tk.Label(qf, text=f" {label} ", bg="#455A64", fg="white",
                         font=("Segoe UI", 9), cursor="hand2", padx=6, pady=2)
            b.pack(side="left", padx=(0, 6))
            b.bind("<Button-1>", lambda e, dd=d: set_range(dd))

        include_notes_var = tk.BooleanVar(value=True)
        tk.Checkbutton(dlg, text="Включить список препаратов с описаниями", variable=include_notes_var,
                       bg=C["bg"], fg=C["text"], font=("Segoe UI", 10),
                       selectcolor=C["bg"], activebackground=C["bg"]).pack(anchor="w", padx=20, pady=(8, 0))
        include_purchase_var = tk.BooleanVar(value=True)
        tk.Checkbutton(dlg, text="Включить статус приобретения", variable=include_purchase_var,
                       bg=C["bg"], fg=C["text"], font=("Segoe UI", 10),
                       selectcolor=C["bg"], activebackground=C["bg"]).pack(anchor="w", padx=20, pady=2)

        def do_export():
            try:
                dt_from = datetime(int(var_from_year.get()), int(var_from_month.get()), int(var_from_day.get()))
                dt_to = datetime(int(var_to_year.get()), int(var_to_month.get()), int(var_to_day.get()))
            except ValueError:
                messagebox.showerror("Ошибка", "Неверная дата", parent=dlg); return
            if dt_from > dt_to:
                messagebox.showerror("Ошибка", "Дата «С» должна быть раньше даты «По»", parent=dlg); return
            path = filedialog.asksaveasfilename(
                parent=dlg, title="Сохранить отчёт", initialdir=SCRIPT_DIR,
                initialfile=f"Отчёт_приёма_лекарств_{date_key(dt_from)}_{date_key(dt_to)}.html",
                filetypes=[("HTML файл", "*.html")], defaultextension=".html")
            if not path: return
            # Используем generate_report_html() из med_utils
            html = generate_report_html(
                patient_name="Бучин А.П.",
                patient_info="Бучин Андрей Петрович, 1954 г.р.",
                period_info="апрель 2026",
                medications=MEDICATIONS,
                all_daily_ids=ALL_DAILY_IDS,
                important_notes=IMPORTANT_NOTES,
                state=self.state,
                dt_from=dt_from, dt_to=dt_to,
                include_notes=include_notes_var.get(),
                include_purchase=include_purchase_var.get(),
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            dlg.destroy()
            webbrowser.open(path)

        btn_frame = tk.Frame(dlg, bg=C["bg"])
        btn_frame.pack(fill="x", padx=20, pady=(14, 10))
        export_btn = tk.Label(btn_frame, text="  \U0001F4C4  Создать отчёт  ", bg="#00897B", fg="white",
                              font=("Segoe UI", 11, "bold"), cursor="hand2", padx=12, pady=6)
        export_btn.pack(side="left")
        export_btn.bind("<Button-1>", lambda e: do_export())
        cancel_btn = tk.Label(btn_frame, text="  Отмена  ", bg="#455A64", fg="white",
                              font=("Segoe UI", 10), cursor="hand2", padx=10, pady=6)
        cancel_btn.pack(side="right")
        cancel_btn.bind("<Button-1>", lambda e: dlg.destroy())

    # ═══════════════════════════════════════════════════════════════════════
    # РАЗДЕЛ 12: СОХРАНЕНИЕ И ЗАГРУЗКА СОСТОЯНИЯ
    # ═══════════════════════════════════════════════════════════════════════

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
        self._persist_state()
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


# ═══════════════════════════════════════════════════════════════════════════
# ТОЧКА ВХОДА
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    app = MedicationApp(root)
    root.mainloop()
