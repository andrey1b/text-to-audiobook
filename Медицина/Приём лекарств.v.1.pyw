"""
Інтерактивний графік прийому ліків
Бучин Андрій Петрович, 1954 р.н. | Складено: квітень 2026
"""

import tkinter as tk
from tkinter import ttk, font as tkfont
import json
import os
import sys

# --- Шлях для збереження стану ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0] if sys.argv[0] else __file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "med_state.json")

# --- Кольори ---
COLORS = {
    "bg": "#F5F0EB",
    "header_bg": "#2C3E50",
    "header_fg": "#FFFFFF",
    "morning": "#E8F5E9",
    "morning_accent": "#388E3C",
    "day": "#FFF8E1",
    "day_accent": "#F57F17",
    "evening": "#E3F2FD",
    "evening_accent": "#1565C0",
    "sos": "#FFEBEE",
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
}

# --- Дані препаратів ---
MEDICATIONS = [
    {
        "section": "РАНОК (сніданок 09:00 - 10:00)",
        "section_key": "morning",
        "items": [
            {
                "id": "tamsin",
                "time": "08:30",
                "time_note": "до їжі",
                "name": "Тамсін Форте",
                "subtitle": "",
                "note": "Натщесерце",
                "course": "Тривало",
                "course_type": "long",
                "description": (
                    "Тамсулозин (Тамсін Форте) - альфа-1-адреноблокатор.\n"
                    "Призначення: лікування симптомів доброякісної гіперплазії передміхурової залози (ДГПЗ).\n"
                    "Механізм: розслаблює гладкі м'язи передміхурової залози та шийки сечового міхура, "
                    "полегшуючи сечовипускання.\n"
                    "Прийом: натщесерце, за 30 хв до їжі, не розжовувати.\n"
                    "Побічні ефекти: запаморочення, зниження АТ, закладеність носа."
                ),
            },
            {
                "id": "olidetrim",
                "time": "09:00",
                "time_note": "з їжею",
                "name": "Олідетрім 4000",
                "subtitle": "вітамін D3",
                "note": "З їжею, що містить жири",
                "course": "2 міс, потім 2000 тривало",
                "course_type": "2m",
                "description": (
                    "Холекальциферол (вітамін D3) 4000 МО.\n"
                    "Призначення: корекція дефіциту вітаміну D, підтримка кісткової тканини, "
                    "імунної системи, серцево-судинної системи.\n"
                    "Механізм: регулює обмін кальцію і фосфору, підтримує мінералізацію кісток.\n"
                    "Прийом: з їжею, що містить жири (для кращого засвоєння).\n"
                    "Курс: 4000 МО - 2 місяці, потім перехід на підтримуючу дозу 2000 МО тривало.\n"
                    "Контроль: рівень 25(OH)D у крові через 2-3 місяці."
                ),
            },
            {
                "id": "vitk2",
                "time": "09:00",
                "time_note": "з їжею",
                "name": "Вітамін К2",
                "subtitle": "",
                "note": "Разом з D3, з їжею",
                "course": "Тривало",
                "course_type": "long",
                "description": (
                    "Менахінон (вітамін К2, MK-7).\n"
                    "Призначення: спрямовує кальцій у кістки, запобігає відкладенню кальцію "
                    "у судинах (кальцифікації артерій).\n"
                    "Механізм: активує білки остеокальцин (кістки) та матриксний Gla-білок (судини).\n"
                    "Синергія з D3: вітамін D підвищує засвоєння кальцію, К2 забезпечує його "
                    "правильний розподіл.\n"
                    "Прийом: разом з D3, з їжею, що містить жири."
                ),
            },
            {
                "id": "glutargin1",
                "time": "09:00",
                "time_note": "з їжею",
                "name": "Глутаргін 750 мг",
                "subtitle": "1-й прийом",
                "note": "Гепатопротектор",
                "course": "2 місяці",
                "course_type": "2m",
                "description": (
                    "Аргініну глутамат 750 мг.\n"
                    "Призначення: гепатопротекція - захист та відновлення клітин печінки.\n"
                    "Механізм: нейтралізує аміак, покращує метаболічні процеси в печінці, "
                    "має антиоксидантну та мембраностабілізуючу дію.\n"
                    "Додатково: покращує мікроциркуляцію, знижує рівень гомоцистеїну.\n"
                    "Прийом: 2 рази на день (ранок + вечір), з їжею.\n"
                    "Курс: 2 місяці."
                ),
            },
            {
                "id": "augmentin",
                "time": "09:00",
                "time_note": "з їжею",
                "name": "Аугментин",
                "subtitle": "антибіотик",
                "note": "З їжею, для захисту ШКТ",
                "course": "5-7 днів",
                "course_type": "short",
                "description": (
                    "Амоксицилін + клавуланова кислота (Аугментин).\n"
                    "Призначення: антибіотик широкого спектру дії. У даному випадку - "
                    "стоматологічне призначення (після стоматологічного втручання).\n"
                    "Механізм: амоксицилін порушує синтез клітинної стінки бактерій, "
                    "клавуланова кислота захищає від бета-лактамаз.\n"
                    "Прийом: з їжею для зменшення подразнення ШКТ.\n"
                    "Важливо: приймати через рівні проміжки часу, курс не переривати!\n"
                    "Пробіотик приймати через ~6 годин після антибіотика."
                ),
            },
            {
                "id": "neurorubin1",
                "time": "10:30",
                "time_note": "після їжі",
                "name": "Нейрорубін форте",
                "subtitle": "Лактаб, 1-й прийом",
                "note": "Вітаміни групи В",
                "course": "2 місяці",
                "course_type": "2m",
                "description": (
                    "Комплекс вітамінів групи В (B1, B6, B12) у високих дозах.\n"
                    "Призначення: лікування невралгій, невритів, полінейропатій, "
                    "зниження рівня гомоцистеїну.\n"
                    "Механізм: В1 (тіамін) - вуглеводний обмін нервової тканини; "
                    "В6 (піридоксин) - метаболізм амінокислот; В12 (ціанокобаламін) - "
                    "мієлінізація нервових волокон.\n"
                    "Прийом: 2 рази на день (ранок + вечір), після їжі.\n"
                    "Курс: 2 місяці."
                ),
            },
            {
                "id": "serrata",
                "time": "10:30",
                "time_note": "після їжі",
                "name": "Серрата",
                "subtitle": "протинабрякове",
                "note": "Через 30 хв після їжі",
                "course": "5-7 днів",
                "course_type": "short",
                "description": (
                    "Серратіопептидаза - протеолітичний фермент.\n"
                    "Призначення: протинабрякова, протизапальна дія. "
                    "Стоматологічне призначення - зменшення набряку після втручання.\n"
                    "Механізм: розщеплює некротизовані тканини, фібринові згустки, "
                    "зменшує набряк та запалення.\n"
                    "Прийом: через 30 хв після їжі.\n"
                    "Важливо: рознесено з Клопідогрелем по часу, оскільки обидва "
                    "впливають на згортання крові.\n"
                    "Курс: 5-7 днів."
                ),
            },
        ],
    },
    {
        "section": "ДЕНЬ (обід 14:00 - 15:00)",
        "section_key": "day",
        "items": [
            {
                "id": "voger",
                "time": "13:30",
                "time_note": "до їжі",
                "name": "Вогер",
                "subtitle": "",
                "note": "За 30 хв до їжі, гастропротектор",
                "course": "Тривало",
                "course_type": "long",
                "description": (
                    "Ребаміпід (Вогер) - гастропротектор.\n"
                    "Призначення: захист слизової оболонки шлунка, профілактика "
                    "НПЗП-гастропатії (при прийомі Німесілу).\n"
                    "Механізм: стимулює синтез простагландинів у слизовій шлунка, "
                    "покращує мікроциркуляцію, прискорює загоєння ерозій.\n"
                    "Прийом: за 30 хв до їжі.\n"
                    "Особливість: на відміну від ІПП, не порушує кислотність шлунка."
                ),
            },
            {
                "id": "nimesil",
                "time": "14:00",
                "time_note": "з їжею",
                "name": "Німесіл",
                "subtitle": "протизапальне",
                "note": "З їжею або після їжі",
                "course": "5-7 днів",
                "course_type": "short",
                "description": (
                    "Німесулід (Німесіл) - нестероїдний протизапальний засіб (НПЗП).\n"
                    "Призначення: знеболення, протизапальна дія. "
                    "Стоматологічне призначення.\n"
                    "Механізм: селективний інгібітор ЦОГ-2, зменшує біль та запалення "
                    "з меншим впливом на ШКТ порівняно з неселективними НПЗП.\n"
                    "Прийом: з їжею або після їжі (для захисту шлунка).\n"
                    "Важливо: призначений на обід, а Клопідогрель - на вечір "
                    "(мінімізація ризику кровотечі).\n"
                    "Курс: 5-7 днів."
                ),
            },
            {
                "id": "renohels",
                "time": "14:00",
                "time_note": "з їжею",
                "name": "Ренохелс",
                "subtitle": "нефропротектор",
                "note": "З їжею",
                "course": "Тривало",
                "course_type": "long",
                "description": (
                    "Ренохелс - комплексний нефропротектор на рослинній основі.\n"
                    "Призначення: підтримка функції нирок, профілактика нефропатії.\n"
                    "Механізм: покращує нирковий кровоток, має антиоксидантну та "
                    "протизапальну дію на тканину нирок.\n"
                    "Прийом: з їжею.\n"
                    "Курс: тривало."
                ),
            },
            {
                "id": "probiotic",
                "time": "16:00",
                "time_note": "після їжі",
                "name": "Пробіотик",
                "subtitle": "",
                "note": "Через 2 год після антибіотика!",
                "course": "5-7 днів + 1 тиж.",
                "course_type": "short",
                "description": (
                    "Пробіотик (лакто- та біфідобактерії).\n"
                    "Призначення: відновлення мікрофлори кишечника під час та після "
                    "курсу антибіотиків.\n"
                    "Механізм: заселення кишечника корисними бактеріями, конкуренція "
                    "з патогенною флорою, підтримка імунітету.\n"
                    "Прийом: через 2 години після антибіотика (Аугментин о 09:00, "
                    "пробіотик о 16:00 - рознесення ~6 годин).\n"
                    "Курс: 5-7 днів прийому антибіотика + 1 тиждень після завершення."
                ),
            },
        ],
    },
    {
        "section": "ВЕЧІР (вечеря 18:00 - 19:00)",
        "section_key": "evening",
        "items": [
            {
                "id": "glutargin2",
                "time": "18:00",
                "time_note": "з їжею",
                "name": "Глутаргін 750 мг",
                "subtitle": "2-й прийом",
                "note": "Гепатопротектор",
                "course": "2 місяці",
                "course_type": "2m",
                "description": (
                    "Аргініну глутамат 750 мг (другий прийом).\n"
                    "Див. опис ранкового прийому.\n"
                    "Разова доза: 750 мг, добова: 1500 мг (750 мг x 2)."
                ),
            },
            {
                "id": "pregabalin",
                "time": "18:00",
                "time_note": "з їжею",
                "name": "Прегабалін",
                "subtitle": "невралгія",
                "note": "Дозу уточнити у лікаря",
                "course": "За призначенням",
                "course_type": "need",
                "description": (
                    "Прегабалін - протиепілептичний засіб, що застосовується "
                    "для лікування нейропатичного болю.\n"
                    "Призначення: невралгія, нейропатичний біль.\n"
                    "Механізм: зв'язується з альфа-2-дельта субодиницею "
                    "кальцієвих каналів у ЦНС, зменшуючи вивільнення "
                    "збуджуючих нейромедіаторів.\n"
                    "Прийом: з їжею, дозу призначає лікар індивідуально.\n"
                    "Побічні ефекти: сонливість, запаморочення.\n"
                    "Важливо: не припиняти різко, знижувати дозу поступово!"
                ),
            },
            {
                "id": "atoris",
                "time": "20:00",
                "time_note": "після їжі",
                "name": "Аторіс 20 мг",
                "subtitle": "статин",
                "note": "Ввечері, статини найефективніші вночі",
                "course": "Тривало",
                "course_type": "long",
                "description": (
                    "Аторвастатин (Аторіс) 20 мг - статин.\n"
                    "Призначення: зниження холестерину, профілактика "
                    "атеросклерозу та серцево-судинних подій.\n"
                    "Механізм: інгібітор ГМГ-КоА-редуктази, блокує синтез "
                    "холестерину в печінці, знижує ЛПНЩ ('поганий' холестерин).\n"
                    "Прийом: ввечері (синтез холестерину найактивніший вночі).\n"
                    "Контроль: ліпідограма, ГГТ через 2-3 місяці.\n"
                    "Примітка: Роксера виключена зі списку - два статини "
                    "одночасно приймати НЕ можна."
                ),
            },
            {
                "id": "clopidogrel",
                "time": "20:00",
                "time_note": "після їжі",
                "name": "Клопідогрель 75 мг",
                "subtitle": "антиагрегант",
                "note": "Ввечері, тривало",
                "course": "Тривало",
                "course_type": "long",
                "description": (
                    "Клопідогрель 75 мг - антиагрегант (антитромбоцитарний засіб).\n"
                    "Призначення: профілактика тромбоутворення, зниження ризику "
                    "інфаркту та інсульту.\n"
                    "Механізм: незворотно блокує рецептори ADP (P2Y12) на тромбоцитах, "
                    "перешкоджаючи їх агрегації.\n"
                    "Прийом: ввечері. Рознесений з Німесілом (обід) для мінімізації "
                    "ризику кровотечі.\n"
                    "Важливо: рознесений із Серратою по часу (обидва впливають "
                    "на згортання крові).\n"
                    "Курс: тривало."
                ),
            },
            {
                "id": "neurorubin2",
                "time": "20:00",
                "time_note": "після їжі",
                "name": "Нейрорубін форте",
                "subtitle": "Лактаб, 2-й прийом",
                "note": "Вітаміни групи В",
                "course": "2 місяці",
                "course_type": "2m",
                "description": (
                    "Комплекс вітамінів групи В (другий прийом).\n"
                    "Див. опис ранкового прийому.\n"
                    "Разова доза: 1 таблетка, добова: 2 таблетки."
                ),
            },
        ],
    },
    {
        "section": "ЗА ПОТРЕБОЮ (SOS)",
        "section_key": "sos",
        "items": [
            {
                "id": "captopril",
                "time": "SOS",
                "time_note": "",
                "name": "Каптоприл (каптопрес)",
                "subtitle": "",
                "note": "1 таб під язик при підвищенні АТ",
                "course": "За потребою",
                "course_type": "need",
                "description": (
                    "Каптоприл (Каптопрес) - інгібітор АПФ швидкої дії.\n"
                    "Призначення: екстрене зниження артеріального тиску.\n"
                    "Механізм: блокує ангіотензинперетворюючий фермент, "
                    "зменшує утворення ангіотензину II, розширює судини.\n"
                    "Прийом: 1 таблетка під язик (сублінгвально) при підвищенні АТ.\n"
                    "Початок дії: 15-30 хв при сублінгвальному прийомі.\n"
                    "Важливо: контроль АТ через 30 хв після прийому. "
                    "Якщо ефекту немає - виклик швидкої допомоги."
                ),
            },
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


class MedicationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Графік прийому ліків - Бучин А.П.")
        self.root.configure(bg=COLORS["bg"])
        self.root.geometry("980x820")
        self.root.minsize(800, 600)

        self.state = self._load_state()
        self.check_vars = {}
        self.expanded = {}
        self.detail_frames = {}

        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame", background=COLORS["bg"])
        self.style.configure("Card.TFrame", background=COLORS["card_bg"])
        self.style.configure(
            "Header.TLabel",
            background=COLORS["header_bg"],
            foreground=COLORS["header_fg"],
            font=("Segoe UI", 16, "bold"),
            padding=(20, 12),
        )
        self.style.configure(
            "SubHeader.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["text"],
            font=("Segoe UI", 10),
            padding=(20, 4),
        )
        self.style.configure(
            "Section.TLabel",
            font=("Segoe UI", 13, "bold"),
            padding=(12, 8),
        )
        self.style.configure(
            "Time.TLabel",
            font=("Segoe UI Semibold", 12),
            background=COLORS["card_bg"],
        )
        self.style.configure(
            "TimeNote.TLabel",
            font=("Segoe UI", 9),
            foreground=COLORS["subtext"],
            background=COLORS["card_bg"],
        )
        self.style.configure(
            "MedName.TLabel",
            font=("Segoe UI", 12, "bold"),
            background=COLORS["card_bg"],
            foreground=COLORS["text"],
        )
        self.style.configure(
            "MedSub.TLabel",
            font=("Segoe UI", 9),
            background=COLORS["card_bg"],
            foreground=COLORS["subtext"],
        )
        self.style.configure(
            "Note.TLabel",
            font=("Segoe UI", 10),
            background=COLORS["card_bg"],
            foreground=COLORS["subtext"],
            wraplength=280,
        )
        self.style.configure(
            "Course.TLabel",
            font=("Segoe UI Semibold", 9),
            padding=(6, 2),
        )

    def _build_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg=COLORS["header_bg"])
        header_frame.pack(fill="x")
        tk.Label(
            header_frame,
            text="ДЕННИЙ ГРАФІК ПРИЙОМУ ЛІКІВ",
            bg=COLORS["header_bg"],
            fg=COLORS["header_fg"],
            font=("Segoe UI", 16, "bold"),
            pady=10,
        ).pack()
        tk.Label(
            header_frame,
            text="Бучин Андрій Петрович, 1954 р.н.  |  Складено: квітень 2026",
            bg=COLORS["header_bg"],
            fg="#B0BEC5",
            font=("Segoe UI", 10),
            pady=8,
        ).pack()

        # Legend
        legend_frame = tk.Frame(self.root, bg=COLORS["bg"], pady=6)
        legend_frame.pack(fill="x", padx=20)
        legends = [
            (COLORS["course_long"], "Тривало"),
            (COLORS["course_2m"], "2 місяці"),
            (COLORS["course_short"], "5-7 днів"),
            (COLORS["course_need"], "За потребою"),
        ]
        for color, text in legends:
            f = tk.Frame(legend_frame, bg=COLORS["bg"])
            f.pack(side="left", padx=(0, 24))
            tk.Canvas(f, width=12, height=12, bg=color, highlightthickness=0).pack(
                side="left", padx=(0, 4)
            )
            tk.Label(f, text=text, bg=COLORS["bg"], fg=COLORS["text"],
                     font=("Segoe UI", 9)).pack(side="left")

        # Scrollable area
        container = tk.Frame(self.root, bg=COLORS["bg"])
        container.pack(fill="both", expand=True, padx=0, pady=0)

        self.canvas = tk.Canvas(container, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable = tk.Frame(self.canvas, bg=COLORS["bg"])

        self.scrollable.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self._bind_mousewheel(self.canvas)

        # Build sections
        for section_data in MEDICATIONS:
            self._build_section(self.scrollable, section_data)

        # Important notes
        self._build_notes(self.scrollable)

        # Footer
        tk.Label(
            self.scrollable,
            text="Графік носить інформаційний характер. Перед застосуванням проконсультуйтесь з лікарем.",
            bg=COLORS["bg"],
            fg=COLORS["subtext"],
            font=("Segoe UI", 9, "italic"),
            pady=12,
        ).pack(fill="x", padx=20)

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        widget.bind("<Enter>", lambda e: self._bind_all_mousewheel())
        widget.bind("<Leave>", lambda e: self._unbind_all_mousewheel())

    def _bind_all_mousewheel(self):
        self.root.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))

    def _unbind_all_mousewheel(self):
        self.root.unbind_all("<MouseWheel>")

    def _build_section(self, parent, section_data):
        key = section_data["section_key"]
        accent = COLORS[f"{key}_accent"]
        bg = COLORS[key]

        # Section header
        section_header = tk.Frame(parent, bg=accent)
        section_header.pack(fill="x", padx=16, pady=(14, 0))
        tk.Label(
            section_header,
            text=section_data["section"],
            bg=accent,
            fg="white",
            font=("Segoe UI", 13, "bold"),
            padx=16,
            pady=8,
        ).pack(anchor="w")

        # Items
        for item in section_data["items"]:
            self._build_card(parent, item, bg, accent)

    def _build_card(self, parent, item, section_bg, accent):
        med_id = item["id"]

        # Card container with colored left border
        outer = tk.Frame(parent, bg=accent, padx=0, pady=0)
        outer.pack(fill="x", padx=16, pady=(2, 0))

        card = tk.Frame(outer, bg=COLORS["card_bg"], padx=0, pady=0)
        card.pack(fill="x", padx=(4, 0), pady=0)

        # Main row
        row = tk.Frame(card, bg=COLORS["card_bg"], pady=8, padx=12)
        row.pack(fill="x")
        row.columnconfigure(1, weight=1)

        # Time column
        time_frame = tk.Frame(row, bg=COLORS["card_bg"], width=70)
        time_frame.grid(row=0, column=0, sticky="n", padx=(0, 10))
        time_frame.grid_propagate(False)
        time_frame.configure(height=40)
        tk.Label(
            time_frame,
            text=item["time"],
            bg=COLORS["card_bg"],
            fg=accent,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")
        if item["time_note"]:
            tk.Label(
                time_frame,
                text=item["time_note"],
                bg=COLORS["card_bg"],
                fg=COLORS["subtext"],
                font=("Segoe UI", 8),
            ).pack(anchor="w")

        # Med info column
        info_frame = tk.Frame(row, bg=COLORS["card_bg"])
        info_frame.grid(row=0, column=1, sticky="nsew")

        name_row = tk.Frame(info_frame, bg=COLORS["card_bg"])
        name_row.pack(anchor="w")
        tk.Label(
            name_row,
            text=item["name"],
            bg=COLORS["card_bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")
        if item["subtitle"]:
            tk.Label(
                name_row,
                text=f"  ({item['subtitle']})",
                bg=COLORS["card_bg"],
                fg=COLORS["subtext"],
                font=("Segoe UI", 9),
            ).pack(side="left")

        tk.Label(
            info_frame,
            text=item["note"],
            bg=COLORS["card_bg"],
            fg=COLORS["subtext"],
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(anchor="w")

        # Course badge
        course_colors = {
            "long": COLORS["course_long"],
            "2m": COLORS["course_2m"],
            "short": COLORS["course_short"],
            "need": COLORS["course_need"],
        }
        badge_color = course_colors.get(item["course_type"], COLORS["subtext"])
        badge_frame = tk.Frame(row, bg=COLORS["card_bg"])
        badge_frame.grid(row=0, column=2, sticky="ne", padx=(8, 0))

        badge = tk.Label(
            badge_frame,
            text=f" {item['course']} ",
            bg=badge_color,
            fg="white",
            font=("Segoe UI", 8, "bold"),
            padx=6,
            pady=2,
        )
        badge.pack(anchor="e")

        # Checkboxes
        checks_frame = tk.Frame(row, bg=COLORS["card_bg"])
        checks_frame.grid(row=0, column=3, sticky="ne", padx=(12, 0))

        purchased_var = tk.BooleanVar(value=self.state.get(f"{med_id}_purchased", False))
        taken_var = tk.BooleanVar(value=self.state.get(f"{med_id}_taken", False))
        self.check_vars[f"{med_id}_purchased"] = purchased_var
        self.check_vars[f"{med_id}_taken"] = taken_var

        p_cb = tk.Checkbutton(
            checks_frame,
            text="Придбано",
            variable=purchased_var,
            bg=COLORS["card_bg"],
            fg=COLORS["purchased_on"],
            selectcolor=COLORS["card_bg"],
            activebackground=COLORS["card_bg"],
            font=("Segoe UI", 9),
            command=self._save_state,
            anchor="w",
        )
        p_cb.pack(anchor="w")

        t_cb = tk.Checkbutton(
            checks_frame,
            text="Прийнято",
            variable=taken_var,
            bg=COLORS["card_bg"],
            fg=COLORS["taken_on"],
            selectcolor=COLORS["card_bg"],
            activebackground=COLORS["card_bg"],
            font=("Segoe UI", 9),
            command=self._save_state,
            anchor="w",
        )
        t_cb.pack(anchor="w")

        # Expand/collapse button
        self.expanded[med_id] = False
        toggle_btn = tk.Label(
            row,
            text="\u25B6 Опис",
            bg=COLORS["card_bg"],
            fg=accent,
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        toggle_btn.grid(row=0, column=4, sticky="se", padx=(10, 0))

        # Detail frame (hidden)
        detail = tk.Frame(card, bg=COLORS["expand_bg"], padx=16, pady=8)
        self.detail_frames[med_id] = detail

        desc_label = tk.Label(
            detail,
            text=item["description"],
            bg=COLORS["expand_bg"],
            fg=COLORS["text"],
            font=("Segoe UI", 9),
            justify="left",
            anchor="nw",
            wraplength=800,
        )
        desc_label.pack(fill="x", anchor="w")

        toggle_btn.bind("<Button-1>", lambda e, mid=med_id, btn=toggle_btn, a=accent: self._toggle(mid, btn, a))

        # Separator
        tk.Frame(card, bg=COLORS["border"], height=1).pack(fill="x")

    def _toggle(self, med_id, btn, accent):
        if self.expanded[med_id]:
            self.detail_frames[med_id].pack_forget()
            btn.configure(text="\u25B6 Опис")
            self.expanded[med_id] = False
        else:
            # Insert detail before the separator (last child)
            card = self.detail_frames[med_id].master
            children = card.pack_slaves()
            # Unpack separator, pack detail, repack separator
            sep = children[-1]
            sep.pack_forget()
            self.detail_frames[med_id].pack(fill="x")
            sep.pack(fill="x")
            btn.configure(text="\u25BC Опис")
            self.expanded[med_id] = True

    def _build_notes(self, parent):
        notes_outer = tk.Frame(parent, bg=COLORS["sos_accent"])
        notes_outer.pack(fill="x", padx=16, pady=(14, 4))

        tk.Label(
            notes_outer,
            text="ВАЖЛИВІ ПРИМІТКИ",
            bg=COLORS["sos_accent"],
            fg="white",
            font=("Segoe UI", 12, "bold"),
            padx=16,
            pady=6,
        ).pack(anchor="w")

        notes_body = tk.Frame(notes_outer, bg=COLORS["notes_bg"])
        notes_body.pack(fill="x", padx=(4, 0))

        for i, note in enumerate(IMPORTANT_NOTES, 1):
            tk.Label(
                notes_body,
                text=f"  {i}. {note}",
                bg=COLORS["notes_bg"],
                fg=COLORS["text"],
                font=("Segoe UI", 9),
                anchor="w",
                justify="left",
                wraplength=880,
                padx=12,
                pady=2,
            ).pack(fill="x", anchor="w")

        tk.Frame(notes_body, bg=COLORS["notes_bg"], height=6).pack()

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_state(self):
        state = {}
        for key, var in self.check_vars.items():
            state[key] = var.get()
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
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
