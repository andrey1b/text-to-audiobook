"""
med_utils.py — Вспомогательный модуль для медицинских приложений
═══════════════════════════════════════════════════════════════════
Этот модуль содержит переиспользуемые компоненты, которые могут
пригодиться в разных программах:

  1. ЦВЕТОВАЯ ПАЛИТРА (COLORS)         — единый набор цветов
  2. КОНСТАНТЫ ДАТ                      — дни недели, месяцы на русском
  3. УТИЛИТЫ ДАТ (date_key, format_date_ru) — форматирование дат
  4. ScrollableFrame                    — прокручиваемый контейнер для tkinter
  5. ToastNotification                  — всплывающие уведомления
  6. generate_report_html()             — генерация HTML-отчёта

Использование в другом скрипте:
    from med_utils import COLORS, ScrollableFrame, ToastNotification
    from med_utils import date_key, format_date_ru
"""

# ═══════════════════════════════════════════════════════════════════════════
# ИМПОРТ МОДУЛЕЙ
# ═══════════════════════════════════════════════════════════════════════════
# Импортируем только то, что нужно этому модулю.
# tkinter — для виджетов (ScrollableFrame, ToastNotification).
# Остальные — стандартные утилиты Python.

import tkinter as tk
from tkinter import ttk
import winsound
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════════════════
# РАЗДЕЛ 1: ЦВЕТОВАЯ ПАЛИТРА
# ═══════════════════════════════════════════════════════════════════════════
# Единый словарь (dict) цветов приложения в формате HEX (#RRGGBB).
# Вынесение цветов в одно место — паттерн «единый источник правды»:
# при смене темы достаточно изменить значения здесь.
#
# Другие программы могут импортировать COLORS и использовать
# ту же цветовую схему для единообразия интерфейса.

COLORS = {
    # --- Общие ---
    "bg": "#F5F0EB",              # Фон приложения (тёплый бежевый)
    "header_bg": "#2C3E50",       # Фон заголовка (тёмно-синий)
    "header_fg": "#FFFFFF",       # Текст заголовка (белый)
    "card_bg": "#FFFFFF",         # Фон карточки (белый)
    "text": "#212121",            # Основной текст (почти чёрный)
    "subtext": "#616161",         # Второстепенный текст (серый)
    "border": "#E0E0E0",         # Цвет границ (светло-серый)

    # --- Акценты секций дня ---
    "morning_accent": "#388E3C",  # Утро (зелёный)
    "day_accent": "#F57F17",      # День (оранжевый)
    "evening_accent": "#1565C0",  # Вечер (синий)
    "sos_accent": "#C62828",      # SOS (красный)

    # --- Чекбоксы ---
    "purchased_on": "#4CAF50",    # «Приобретено» (зелёный)
    "taken_on": "#2196F3",        # «Принято» (голубой)

    # --- Бейджи курсов ---
    "course_long": "#388E3C",     # Длительно (зелёный)
    "course_2m": "#F57F17",       # 2 месяца (оранжевый)
    "course_short": "#C62828",    # 5-7 дней (красный)
    "course_need": "#7B1FA2",     # По потребности (фиолетовый)

    # --- Интерфейс ---
    "expand_bg": "#FAFAFA",       # Фон раскрытого описания
    "notes_bg": "#FFF9C4",        # Фон примечаний (светло-жёлтый)
    "date_nav_bg": "#34495E",     # Фон навигации по датам

    # --- Календарь ---
    "cal_full": "#4CAF50",        # Все приняты (зелёный)
    "cal_partial": "#FFC107",     # Частично (жёлтый)
    "cal_empty": "#EEEEEE",      # Пропущено (серый)
    "cal_none": "#FFFFFF",        # Нет данных (белый)
    "cal_today_border": "#2196F3",# Рамка сегодняшнего дня

    # --- Статистика ---
    "stat_good": "#4CAF50",       # ≥80% (зелёный)
    "stat_warn": "#FF9800",       # ≥50% (оранжевый)
    "stat_bad": "#F44336",        # <50% (красный)

    # --- Напоминания ---
    "reminder_on": "#4CAF50",     # Включены (зелёный)
    "reminder_off": "#9E9E9E",    # Выключены (серый)

    # --- Всплывающие уведомления ---
    "toast_bg": "#1565C0",        # Фон (синий)
    "toast_fg": "#FFFFFF",        # Текст (белый)
}

# Соответствие типа курса → цвет бейджа
COURSE_COLORS = {
    "long": COLORS["course_long"],
    "2m": COLORS["course_2m"],
    "short": COLORS["course_short"],
    "need": COLORS["course_need"],
}


# ═══════════════════════════════════════════════════════════════════════════
# РАЗДЕЛ 2: КОНСТАНТЫ ДАТ (русский язык)
# ═══════════════════════════════════════════════════════════════════════════
# Массивы названий дней недели и месяцев на русском языке.
# Индексация совпадает с datetime: weekday() → 0=Пн, month → 1=Январь.

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

MONTHS_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

# Родительный падеж (для формата «5 апреля 2026»)
MONTHS_RU_GEN = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


# ═══════════════════════════════════════════════════════════════════════════
# РАЗДЕЛ 3: УТИЛИТЫ ДАТ
# ═══════════════════════════════════════════════════════════════════════════

def date_key(dt):
    """Преобразует datetime → строку 'YYYY-MM-DD' (ключ для словаря).

    Пример:
        >>> from datetime import datetime
        >>> date_key(datetime(2026, 4, 10))
        '2026-04-10'
    """
    return dt.strftime("%Y-%m-%d")


def format_date_ru(dt):
    """Форматирует дату в читаемый вид: 'Чт, 10 апреля 2026'.

    Пример:
        >>> from datetime import datetime
        >>> format_date_ru(datetime(2026, 4, 10))
        'Пт, 10 апреля 2026'
    """
    return f"{WEEKDAYS_RU[dt.weekday()]}, {dt.day} {MONTHS_RU_GEN[dt.month]} {dt.year}"


# ═══════════════════════════════════════════════════════════════════════════
# РАЗДЕЛ 4: ПРОКРУЧИВАЕМЫЙ ФРЕЙМ (ScrollableFrame)
# ═══════════════════════════════════════════════════════════════════════════
# В tkinter нет встроенного прокручиваемого контейнера для виджетов.
# Стандартный подход:
#   1. Canvas (холст) — поддерживает прокрутку
#   2. Frame (рамка) — размещается внутри Canvas
#   3. Scrollbar — подключается к Canvas
#
# ScrollableFrame инкапсулирует этот паттерн в удобный класс.
# Вместо повторения 10+ строк кода — одна строка:
#   sf = ScrollableFrame(parent)
#   sf.pack(fill="both", expand=True)
#   tk.Label(sf.interior, text="Контент").pack()

class ScrollableFrame(tk.Frame):
    """Прокручиваемый контейнер для tkinter-виджетов.

    Использование:
        sf = ScrollableFrame(parent, orient="vertical")
        sf.pack(fill="both", expand=True)
        # Добавляйте виджеты в sf.interior (не в сам sf!)
        tk.Label(sf.interior, text="Привет!").pack()

    Параметры:
        parent  — родительский виджет
        orient  — направление прокрутки:
                  "vertical" (по умолчанию), "horizontal", "both"
        bg      — цвет фона (по умолчанию из COLORS["bg"])
    """

    def __init__(self, parent, orient="vertical", bg=None, **kwargs):
        bg = bg or COLORS["bg"]
        super().__init__(parent, bg=bg, **kwargs)

        # Создаём Canvas и полосы прокрутки
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)

        # Вертикальная прокрутка
        if orient in ("vertical", "both"):
            self._vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
            self._vsb.pack(side="right", fill="y")
            self.canvas.configure(yscrollcommand=self._vsb.set)

        # Горизонтальная прокрутка
        if orient in ("horizontal", "both"):
            self._hsb = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
            self._hsb.pack(side="bottom", fill="x")
            self.canvas.configure(xscrollcommand=self._hsb.set)

        self.canvas.pack(side="left", fill="both", expand=True)

        # interior — фрейм для размещения контента
        self.interior = tk.Frame(self.canvas, bg=bg)
        self._interior_id = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")

        # Обновление области прокрутки при изменении размера содержимого
        self.interior.bind("<Configure>",
                           lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Растягивание interior по ширине canvas
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._interior_id, width=e.width))

    def bind_mousewheel(self, root):
        """Привязывает прокрутку колесом мыши к этому контейнеру.
        root — корневое окно (tk.Tk) для bind_all."""
        root.bind_all("<MouseWheel>",
                       lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))


# ═══════════════════════════════════════════════════════════════════════════
# РАЗДЕЛ 5: ВСПЛЫВАЮЩЕЕ УВЕДОМЛЕНИЕ (ToastNotification)
# ═══════════════════════════════════════════════════════════════════════════
# Маленькое окно в правом нижнем углу экрана, которое появляется
# поверх всех окон и автоматически исчезает через заданное время.
#
# Использование:
#   ToastNotification(root, "Заголовок", "Текст сообщения", duration=5000)

class ToastNotification(tk.Toplevel):
    """Всплывающее уведомление (toast) в правом нижнем углу экрана.

    Параметры:
        master   — родительское окно
        title    — заголовок уведомления
        message  — текст сообщения
        duration — время показа в мс (по умолчанию 15000 = 15 сек)
        bg       — цвет фона (по умолчанию из COLORS)
        fg       — цвет текста (по умолчанию из COLORS)
    """

    def __init__(self, master, title, message, duration=15000,
                 bg=None, fg=None):
        super().__init__(master)

        bg = bg or COLORS["toast_bg"]
        fg = fg or COLORS["toast_fg"]

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=bg)

        frame = tk.Frame(self, bg=bg, padx=16, pady=12)
        frame.pack(fill="both", expand=True)

        # Кнопка закрытия
        close_btn = tk.Label(frame, text="\u2715", bg=bg, fg="#B0BEC5",
                             font=("Segoe UI", 10), cursor="hand2")
        close_btn.pack(anchor="ne")
        close_btn.bind("<Button-1>", lambda e: self.destroy())

        # Заголовок
        tk.Label(frame, text=title, bg=bg, fg=fg,
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")

        # Текст
        tk.Label(frame, text=message, bg=bg, fg="#E3F2FD",
                 font=("Segoe UI", 10), anchor="w", justify="left",
                 wraplength=350).pack(fill="x", pady=(6, 0))

        # Позиционирование в правом нижнем углу
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), 380)
        h = self.winfo_reqheight()
        sx = self.winfo_screenwidth()
        sy = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{sx - w - 20}+{sy - h - 60}")

        # Звуковой сигнал
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        # Автоматическое закрытие
        self.after(duration, self._safe_destroy)

    def _safe_destroy(self):
        """Безопасное закрытие окна."""
        try:
            self.destroy()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# РАЗДЕЛ 6: ГЕНЕРАТОР HTML-ОТЧЁТА
# ═══════════════════════════════════════════════════════════════════════════
# Функция generate_report_html() создаёт HTML-файл с отчётом о приёме
# лекарств за период. Может использоваться любой программой, которая
# работает с расписанием приёма лекарств.

# CSS-стили для HTML-отчёта (вынесены отдельно для читаемости)
REPORT_CSS = """
  @media print { @page { margin: 15mm; } }
  body { font-family: 'Segoe UI', Arial, sans-serif; color: #212121; max-width: 900px; margin: 0 auto; padding: 20px; }
  h1 { color: #2C3E50; border-bottom: 3px solid #2C3E50; padding-bottom: 8px; font-size: 22px; }
  h2 { color: #1565C0; margin-top: 24px; font-size: 16px; }
  h3 { color: #388E3C; font-size: 14px; margin-top: 16px; }
  .patient-info { background: #ECEFF1; padding: 12px 16px; border-radius: 6px; margin: 12px 0; }
  .summary-box { display: flex; gap: 16px; flex-wrap: wrap; margin: 12px 0; }
  .stat-card { background: #F5F5F5; border-left: 4px solid #2196F3; padding: 10px 16px; border-radius: 4px; min-width: 140px; }
  .stat-card .value { font-size: 22px; font-weight: bold; }
  .stat-card .label { font-size: 12px; color: #616161; }
  .stat-good { border-left-color: #4CAF50; }
  .stat-warn { border-left-color: #FF9800; }
  .stat-bad { border-left-color: #F44336; }
  table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 13px; }
  th { background: #2C3E50; color: white; padding: 8px 6px; text-align: left; font-size: 12px; }
  td { padding: 6px; border-bottom: 1px solid #E0E0E0; }
  tr:nth-child(even) { background: #FAFAFA; }
  .taken { color: #4CAF50; font-weight: bold; }
  .missed { color: #F44336; }
  .no-data { color: #9E9E9E; font-style: italic; }
  .pct-bar { display: inline-block; height: 14px; border-radius: 3px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; color: white; font-size: 11px; font-weight: bold; }
  .badge-long { background: #388E3C; } .badge-2m { background: #F57F17; }
  .badge-short { background: #C62828; } .badge-need { background: #7B1FA2; }
  .footer { margin-top: 30px; padding-top: 12px; border-top: 1px solid #E0E0E0; font-size: 11px; color: #9E9E9E; text-align: center; }
  .purchase-yes { color: #4CAF50; } .purchase-no { color: #F44336; }
  .section-label { font-weight: bold; padding: 4px 8px; color: white; border-radius: 3px; margin: 8px 0 4px; display: inline-block; font-size: 12px; }
  .morning { background: #388E3C; } .day { background: #F57F17; }
  .evening { background: #1565C0; } .sos { background: #C62828; }
  .med-desc { font-size: 12px; color: #616161; margin: 2px 0 6px 20px; white-space: pre-line; }
"""


def generate_report_html(*, patient_name, patient_info, period_info,
                         medications, all_daily_ids, important_notes,
                         state, dt_from, dt_to,
                         include_notes=True, include_purchase=True):
    """Генерирует HTML-отчёт о приёме лекарств за период.

    Параметры (именованные, через *):
        patient_name    — ФИО пациента
        patient_info    — краткая информация (год рождения и т.п.)
        period_info     — когда составлен график
        medications     — список секций с препаратами (структура MEDICATIONS)
        all_daily_ids   — список ID ежедневных препаратов
        important_notes — список строк с примечаниями
        state           — словарь состояния (данные за дни, покупки)
        dt_from, dt_to  — границы периода (datetime)
        include_notes   — включить описания препаратов (bool)
        include_purchase — включить статус покупки (bool)

    Возвращает:
        str — полный HTML-документ
    """
    total_ids = len(all_daily_ids)

    # Сбор данных за каждый день
    days_data = []
    d = dt_from
    while d <= dt_to:
        dk = date_key(d)
        dd = state.get(dk, {})
        taken_n = sum(1 for m in all_daily_ids if dd.get(f"{m}_taken", False))
        days_data.append((d, dk, dd, taken_n))
        d += timedelta(days=1)

    days_with_data = [x for x in days_data if x[2]]
    total_taken = sum(x[3] for x in days_data)
    total_possible = len(days_with_data) * total_ids if days_with_data else 1
    pct_overall = int(total_taken / total_possible * 100) if total_possible else 0

    # === HTML ===
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Отчёт приёма лекарств — {patient_name}</title>
<style>{REPORT_CSS}</style>
</head>
<body>
<h1>\U0001F4CB Отчёт приёма лекарств</h1>
<div class="patient-info">
  <strong>Пациент:</strong> {patient_info}<br>
  <strong>Период:</strong> {format_date_ru(dt_from)} — {format_date_ru(dt_to)}<br>
  <strong>Дата отчёта:</strong> {format_date_ru(datetime.now())}<br>
  <strong>График составлен:</strong> {period_info}
</div>

<h2>\U0001F4CA Общая статистика</h2>
<div class="summary-box">
  <div class="stat-card {'stat-good' if pct_overall >= 80 else 'stat-warn' if pct_overall >= 50 else 'stat-bad'}">
    <div class="value">{pct_overall}%</div><div class="label">Общее выполнение</div>
  </div>
  <div class="stat-card">
    <div class="value">{len(days_with_data)}</div><div class="label">Дней с данными</div>
  </div>
  <div class="stat-card stat-good">
    <div class="value">{sum(1 for x in days_data if x[3] == total_ids and x[2])}</div><div class="label">Полный приём</div>
  </div>
  <div class="stat-card stat-warn">
    <div class="value">{sum(1 for x in days_data if 0 < x[3] < total_ids and x[2])}</div><div class="label">Частичный</div>
  </div>
  <div class="stat-card stat-bad">
    <div class="value">{sum(1 for x in days_data if x[3] == 0 and x[2])}</div><div class="label">Пропущено</div>
  </div>
</div>
"""
    # Статистика по препаратам
    html += "<h2>\U0001F48A Выполнение по препаратам</h2>\n<table>\n"
    html += "<tr><th>Препарат</th><th>Курс</th><th>Принято дней</th><th>Пропущено</th><th>%</th></tr>\n"
    for sec in medications:
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

    # Ежедневный журнал
    html += "<h2>\U0001F4C5 Ежедневный журнал</h2>\n<table>\n"
    html += "<tr><th>Дата</th>"
    short_names = []
    for sec in medications:
        for it in sec["items"]:
            if it["course_type"] != "need":
                short_names.append((it["id"], it["name"][:12]))
    for _, sn in short_names:
        html += f"<th style='font-size:10px;writing-mode:vertical-lr;text-orientation:mixed;height:80px'>{sn}</th>"
    html += "<th>%</th></tr>\n"

    for dt, dk, dd, taken_n in days_data:
        pct_d = int(taken_n / total_ids * 100) if total_ids else 0
        html += f"<tr><td style='white-space:nowrap'>{dt.strftime('%d.%m')}<br><small>{WEEKDAYS_RU[dt.weekday()]}</small></td>"
        if not dd:
            for _ in short_names:
                html += "<td class='no-data'>\u2014</td>"
            html += "<td class='no-data'>\u2014</td></tr>\n"
            continue
        for mid, _ in short_names:
            if dd.get(f"{mid}_taken", False):
                html += "<td class='taken'>\u2713</td>"
            else:
                html += "<td class='missed'>\u2717</td>"
        html += f"<td><strong>{pct_d}%</strong></td></tr>\n"
    html += "</table>\n"

    # Статус приобретения
    if include_purchase:
        purchased = state.get("purchased", {})
        html += "<h2>\U0001F6D2 Статус приобретения</h2>\n<table>\n"
        html += "<tr><th>Препарат</th><th>Курс</th><th>Приобретено</th></tr>\n"
        for sec in medications:
            for it in sec["items"]:
                p = purchased.get(it["id"], False)
                cls = "purchase-yes" if p else "purchase-no"
                txt = "\u2713 Да" if p else "\u2717 Нет"
                badge_cls = f"badge-{it['course_type']}"
                html += f"<tr><td><strong>{it['name']}</strong></td>"
                html += f"<td><span class='badge {badge_cls}'>{it['course']}</span></td>"
                html += f"<td class='{cls}'>{txt}</td></tr>\n"
        html += "</table>\n"

    # Описания препаратов
    if include_notes:
        html += "<h2>\U0001F4D6 Список препаратов</h2>\n"
        for sec in medications:
            sk = sec["section_key"]
            html += f"<div class='section-label {sk}'>{sec['section']}</div>\n"
            for it in sec["items"]:
                html += f"<p style='margin:4px 0 0 10px'><strong>{it['name']}</strong>"
                if it['subtitle']:
                    html += f" ({it['subtitle']})"
                html += f" \u2014 {it['note']}</p>\n"
                html += f"<div class='med-desc'>{it['description']}</div>\n"

    # Важные примечания
    html += "<h2>\u26A0\uFE0F Важные примечания</h2>\n<ol>\n"
    for note in important_notes:
        html += f"<li>{note}</li>\n"
    html += "</ol>\n"

    # Подвал
    html += f"""
<div class="footer">
  График носит информационный характер. Перед применением проконсультируйтесь с врачом.<br>
  Отчёт сформирован автоматически — {datetime.now().strftime('%d.%m.%Y %H:%M')}
</div>
</body></html>"""
    return html
