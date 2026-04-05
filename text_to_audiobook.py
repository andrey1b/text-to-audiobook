"""
Конвертер текстовых книг в аудиокниги (с графическим интерфейсом).

Использует edge-tts (онлайн, Microsoft Edge TTS) и pyttsx3/SAPI (оффлайн)
для озвучки. Поддерживает русский, английский и другие языки.

Установка зависимостей:
    pip install edge-tts pydub customtkinter chardet pyttsx3

Использование:
    python text_to_audiobook.py              — запуск с GUI
    python text_to_audiobook.py book.txt     — командная строка
    python text_to_audiobook.py --list-voices ru
"""

import argparse
import asyncio
import json
import os
import re
import socket
import sys
import textwrap
import threading
from pathlib import Path

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

if not EDGE_TTS_AVAILABLE and not PYTTSX3_AVAILABLE:
    print("Ошибка: ни один TTS-движок не установлен.")
    print("Установите хотя бы один:")
    print("  pip install edge-tts      (онлайн, высокое качество)")
    print("  pip install pyttsx3       (оффлайн, Windows SAPI)")
    sys.exit(1)

APP_VERSION = "33"

# ── Режимы TTS ──────────────────────────────────────────────────────

TTS_MODE_AUTO = "auto"
TTS_MODE_ONLINE = "online"
TTS_MODE_OFFLINE = "offline"
TTS_MODE_PIPER = "piper"

# ── Голоса по умолчанию ──────────────────────────────────────────────

DEFAULT_VOICES = {
    "ru": "ru-RU-DmitryNeural",
    "en": "en-US-GuyNeural",
}

# Популярные голоса для GUI (имя, ShortName)
VOICE_PRESETS = [
    ("Дмитрий (рус. муж.)", "ru-RU-DmitryNeural"),
    ("Светлана (рус. жен.)", "ru-RU-SvetlanaNeural"),
    ("Guy (англ. муж.)", "en-US-GuyNeural"),
    ("Jenny (англ. жен.)", "en-US-JennyNeural"),
]

# ── Оффлайн-голоса (Windows SAPI) ────────────────────────────────────

OFFLINE_VOICE_PRESETS: list[tuple[str, str]] = []  # заполняется при инициализации


def _init_offline_voices():
    """Находит установленные SAPI-голоса и создаёт список пресетов."""
    global OFFLINE_VOICE_PRESETS
    if not PYTTSX3_AVAILABLE:
        return
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices") or []
        for v in voices:
            # Определяем язык из id голоса
            vid = v.id.lower()
            name = v.name
            if "russian" in vid or "ru-ru" in vid or "русск" in name.lower():
                tag = "рус."
            elif "english" in vid or "en-us" in vid or "en-gb" in vid:
                tag = "англ."
            else:
                continue  # Пропускаем голоса других языков
            display = f"[Оффлайн] {name} ({tag})"
            OFFLINE_VOICE_PRESETS.append((display, v.id))
        engine.stop()
    except Exception:
        pass


_init_offline_voices()


# ── Piper TTS (нейросетевой оффлайн) ────────────────────────────────

PIPER_VOICE_PRESETS: list[tuple[str, str]] = []  # (display_name, model_path)


def _find_piper_dir() -> str | None:
    """Ищет папку 'piper' рядом с exe / скриптом."""
    # Рядом с exe (PyInstaller)
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    piper_dir = os.path.join(base, "piper")
    if os.path.isdir(piper_dir):
        return piper_dir
    return None


def _find_piper_exe() -> str | None:
    """Ищет piper.exe."""
    piper_dir = _find_piper_dir()
    if piper_dir:
        exe = os.path.join(piper_dir, "piper.exe")
        if os.path.isfile(exe):
            return exe
    return None


def _init_piper_voices():
    """Находит модели Piper (.onnx) и создаёт список пресетов (только ru/en)."""
    global PIPER_VOICE_PRESETS
    piper_dir = _find_piper_dir()
    if not piper_dir:
        return
    if not _find_piper_exe():
        return

    import glob
    for onnx_path in glob.glob(os.path.join(piper_dir, "*.onnx")):
        json_path = onnx_path + ".json"
        if not os.path.isfile(json_path):
            continue

        filename = os.path.splitext(os.path.basename(onnx_path))[0]

        # Определяем язык: ru_RU-dmitri-medium → ru
        lower = filename.lower()
        if lower.startswith("ru_ru") or lower.startswith("ru-ru"):
            lang_tag = "рус."
        elif lower.startswith("en_us") or lower.startswith("en_gb") or \
             lower.startswith("en-us") or lower.startswith("en-gb"):
            lang_tag = "англ."
        else:
            continue  # Пропускаем другие языки

        # Извлекаем имя голоса: ru_RU-dmitri-medium → dmitri
        parts = filename.replace("_", "-").split("-")
        short_name = parts[2] if len(parts) >= 3 else filename

        display = f"[Piper] {short_name} ({lang_tag})"
        PIPER_VOICE_PRESETS.append((display, onnx_path))


_init_piper_voices()

PIPER_AVAILABLE = _find_piper_exe() is not None and len(PIPER_VOICE_PRESETS) > 0


def synthesize_chunk_piper(
    text: str, model_path: str, speed_pct: int, output_path: str, log_func=None
):
    """Синтез через Piper TTS. Блокирующий вызов."""
    import subprocess

    piper_exe = _find_piper_exe()
    if not piper_exe:
        raise RuntimeError("piper.exe не найден. Поместите Piper TTS в папку 'piper'.")
    if not os.path.isfile(model_path):
        raise RuntimeError(f"Модель Piper не найдена: {model_path}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    wav_path = output_path.replace(".mp3", "_piper_tmp.wav")

    # length_scale: speed_pct -50..+50 → 1.5..0.5
    length_scale = 1.0 - (speed_pct / 100.0)
    length_scale = max(0.3, min(2.0, length_scale))

    try:
        result = subprocess.run(
            [
                piper_exe,
                "--model", model_path,
                "--output_file", wav_path,
                "--length_scale", f"{length_scale:.2f}",
                "--sentence_silence", "0.3",
            ],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=300,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Piper ошибка (код {result.returncode}): {stderr}")

        if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
            raise RuntimeError("Piper не создал аудиофайл.")

        # WAV → MP3
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_wav(wav_path)
            audio.export(output_path, format="mp3", bitrate="48k")
        except ImportError:
            import shutil
            shutil.move(wav_path, output_path)
            return
    finally:
        try:
            if os.path.exists(wav_path):
                os.remove(wav_path)
        except OSError:
            pass


def _find_piper_model_for(edge_voice: str) -> str:
    """Подбирает Piper-модель по языку Edge-голоса."""
    lang = edge_voice.split("-")[0].lower() if edge_voice else ""
    for _, model_path in PIPER_VOICE_PRESETS:
        fname = os.path.basename(model_path).lower()
        if lang == "ru" and ("ru_ru" in fname or "ru-ru" in fname):
            return model_path
        if lang == "en" and ("en_us" in fname or "en_gb" in fname or "en-us" in fname or "en-gb" in fname):
            return model_path
    if PIPER_VOICE_PRESETS:
        return PIPER_VOICE_PRESETS[0][1]
    return ""


# ── Проверка интернет-подключения ────────────────────────────────────


def check_internet(timeout: float = 3.0) -> bool:
    """Проверяет доступность интернета (пробует подключиться к серверу Bing)."""
    try:
        socket.create_connection(("speech.platform.bing.com", 443), timeout=timeout).close()
        return True
    except OSError:
        return False


def resolve_tts_mode(mode: str, log_func=None) -> str:
    """Определяет фактический режим TTS из 'auto'."""
    msg = log_func or (lambda m: None)
    if mode == TTS_MODE_ONLINE:
        if not EDGE_TTS_AVAILABLE:
            msg("edge-tts не установлен! Переключаюсь на оффлайн.")
            return TTS_MODE_OFFLINE
        return TTS_MODE_ONLINE
    if mode == TTS_MODE_PIPER:
        if PIPER_AVAILABLE:
            return TTS_MODE_PIPER
        msg("Piper TTS не найден! Переключаюсь на SAPI.")
        return TTS_MODE_OFFLINE
    if mode == TTS_MODE_OFFLINE:
        if not PYTTSX3_AVAILABLE:
            msg("pyttsx3 не установлен! Переключаюсь на онлайн.")
            return TTS_MODE_ONLINE
        return TTS_MODE_OFFLINE
    # auto: онлайн → piper → sapi
    msg("Проверка интернет-подключения...")
    if EDGE_TTS_AVAILABLE and check_internet():
        msg("Интернет доступен → режим: Онлайн (Edge TTS)")
        return TTS_MODE_ONLINE
    elif PIPER_AVAILABLE:
        msg(f"Интернет недоступен → режим: Piper TTS (моделей: {len(PIPER_VOICE_PRESETS)})")
        return TTS_MODE_PIPER
    elif PYTTSX3_AVAILABLE:
        msg("Интернет недоступен → режим: Оффлайн (Windows SAPI)")
        return TTS_MODE_OFFLINE
    else:
        msg("Интернет недоступен, оффлайн-движки не найдены.")
        msg("Попробую онлайн (edge-tts)...")
        return TTS_MODE_ONLINE


# ── Разбивка на главы ────────────────────────────────────────────────

CHAPTER_PATTERNS = [
    r"^Глава\s+\d+",
    r"^ГЛАВА\s+\d+",
    r"^Chapter\s+\d+",
    r"^CHAPTER\s+\d+",
    r"^Часть\s+\d+",
    r"^ЧАСТЬ\s+\d+",
    r"^Part\s+\d+",
    r"^PART\s+\d+",
    r"^\d+\.\s+[A-ZА-ЯЁ]",
]


def detect_encoding(file_path: str, log_func=None) -> str:
    """
    Автоматически определяет кодировку текстового файла.
    Проверяет BOM, затем использует chardet, с fallback на utf-8.
    """
    msg = log_func or print

    with open(file_path, "rb") as f:
        raw = f.read()

    # 1. Проверяем BOM (Byte Order Mark)
    if raw[:3] == b"\xef\xbb\xbf":
        msg("Кодировка: UTF-8 (BOM)")
        return "utf-8-sig"
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        msg("Кодировка: UTF-16 (BOM)")
        return "utf-16"

    # 2. chardet — анализ байтов
    try:
        import chardet
        # Для больших файлов анализируем первые 100 КБ
        sample = raw[:102400]
        result = chardet.detect(sample)
        encoding = result.get("encoding", "utf-8") or "utf-8"
        confidence = result.get("confidence", 0) or 0

        # chardet иногда возвращает нестандартные имена
        encoding_map = {
            "windows-1251": "cp1251",
            "Windows-1251": "cp1251",
            "MacCyrillic": "cp1251",
            "maccyrillic": "cp1251",
            "IBM866": "cp866",
            "ibm866": "cp866",
            "ascii": "utf-8",       # ASCII — подмножество UTF-8
            "ISO-8859-5": "iso-8859-5",
            "KOI8-R": "koi8-r",
        }
        encoding = encoding_map.get(encoding, encoding)

        msg(f"Кодировка: {encoding} (уверенность: {confidence:.0%})")

        # Проверяем, что файл действительно читается
        try:
            raw.decode(encoding)
            return encoding
        except (UnicodeDecodeError, LookupError):
            msg(f"  Предположение {encoding} не подошло, пробую utf-8...")

    except ImportError:
        msg("Библиотека chardet не найдена, пробую стандартные кодировки...")

    # 3. Fallback: пробуем по очереди
    for enc in ["utf-8", "cp1251", "cp866", "koi8-r", "iso-8859-5", "latin-1"]:
        try:
            raw.decode(enc)
            msg(f"Кодировка (подбор): {enc}")
            return enc
        except UnicodeDecodeError:
            continue

    msg("Кодировка: не удалось определить, использую utf-8")
    return "utf-8"


def detect_language(text: str) -> str:
    """Простое определение языка по частотности кириллицы."""
    sample = text[:5000]
    cyrillic = sum(1 for c in sample if "\u0400" <= c <= "\u04ff")
    latin = sum(1 for c in sample if "a" <= c.lower() <= "z")
    return "ru" if cyrillic > latin else "en"


def split_into_chapters(text: str) -> list[tuple[str, str]]:
    """Разбивает текст на главы. Возвращает список (название, текст)."""
    combined_pattern = "|".join(f"({p})" for p in CHAPTER_PATTERNS)
    lines = text.split("\n")

    chapters: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        if re.match(combined_pattern, line.strip(), re.IGNORECASE):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    chapters.append((current_title, body))
            current_title = line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            chapters.append((current_title, body))

    if len(chapters) <= 1:
        return [("", text.strip())]

    return chapters


# ── Разбивка длинного текста на части для TTS ────────────────────────

MAX_CHUNK_LEN = 3000


def split_text_into_chunks(text: str, max_len: int = MAX_CHUNK_LEN) -> list[str]:
    """Разбивает текст на части по абзацам, не превышая max_len символов."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(para) > max_len:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sentence in sentences:
                if len(current) + len(sentence) + 1 > max_len:
                    if current:
                        chunks.append(current.strip())
                    current = sentence
                else:
                    current = current + " " + sentence if current else sentence
            continue

        if len(current) + len(para) + 2 > max_len:
            if current:
                chunks.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if current.strip():
        chunks.append(current.strip())

    return chunks


# ── Синтез речи ──────────────────────────────────────────────────────


MAX_RETRIES = 5
RETRY_DELAYS = [5, 15, 30, 60, 120]  # секунды между попытками

# Блокировка для pyttsx3 (он не потокобезопасен)
_pyttsx3_lock = threading.Lock()


def synthesize_chunk_offline(
    text: str, voice_id: str, speed_pct: int, output_path: str, log_func=None
):
    """Оффлайн-синтез через pyttsx3 (Windows SAPI). Блокирующий вызов."""
    msg = log_func or (lambda m: None)
    if not PYTTSX3_AVAILABLE:
        raise RuntimeError("pyttsx3 не установлен для оффлайн-синтеза.")

    # pyttsx3 не потокобезопасен — используем блокировку
    with _pyttsx3_lock:
        engine = pyttsx3.init()
        try:
            # Устанавливаем голос
            engine.setProperty("voice", voice_id)

            # Скорость: pyttsx3 по умолчанию ~200 слов/мин, Edge TTS ~0%
            base_rate = engine.getProperty("rate") or 200
            factor = 1.0 + speed_pct / 100.0
            engine.setProperty("rate", int(base_rate * factor))

            # pyttsx3 сохраняет только в WAV/AIFF — конвертируем в MP3
            wav_path = output_path.replace(".mp3", "_tmp_sapi.wav")
            engine.save_to_file(text, wav_path)
            engine.runAndWait()
        finally:
            engine.stop()

    if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
        raise RuntimeError("SAPI не создал аудиофайл.")

    # Конвертация WAV → MP3
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_wav(wav_path)
        audio.export(output_path, format="mp3", bitrate="48k")
    except ImportError:
        # Без pydub просто переименовываем (будет WAV в .mp3 контейнере)
        import shutil
        shutil.move(wav_path, output_path)
        msg("  (pydub не установлен — сохранено как WAV)")
        return

    # Удаляем временный WAV
    try:
        os.remove(wav_path)
    except OSError:
        pass


async def synthesize_chunk(
    text: str, voice: str, speed: str, output_path: str,
    log_func=None, tts_mode: str = TTS_MODE_ONLINE
):
    """Озвучивает один фрагмент текста.
    tts_mode: 'online' — Edge TTS, 'piper' — Piper TTS, 'offline' — Windows SAPI.
    """
    msg = log_func or (lambda m: None)

    # speed: "+10%" → 10
    try:
        speed_pct = int(speed.replace("%", "").replace("+", ""))
    except ValueError:
        speed_pct = 0

    # ── Piper-режим ──────────────────────────────────────────────
    if tts_mode == TTS_MODE_PIPER:
        model_path = voice
        # Если voice — не путь к файлу, подбираем модель по языку
        if not os.path.isfile(model_path):
            model_path = _find_piper_model_for(voice)
        await asyncio.get_event_loop().run_in_executor(
            None, synthesize_chunk_piper,
            text, model_path, speed_pct, output_path, log_func,
        )
        return

    # ── Оффлайн-режим (SAPI) ────────────────────────────────────
    if tts_mode == TTS_MODE_OFFLINE:
        await asyncio.get_event_loop().run_in_executor(
            None, synthesize_chunk_offline,
            text, voice, speed_pct, output_path, log_func,
        )
        return

    # ── Онлайн-режим (Edge TTS) ──────────────────────────────────
    for attempt in range(MAX_RETRIES + 1):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=speed)
            await communicate.save(output_path)
            return  # успех
        except Exception as e:
            if attempt >= MAX_RETRIES:
                # Последняя попытка — пробуем Piper, затем SAPI
                if PIPER_AVAILABLE:
                    msg("  Все попытки исчерпаны. Переключаюсь на Piper TTS...")
                    model_path = _find_piper_model_for(voice)
                    await asyncio.get_event_loop().run_in_executor(
                        None, synthesize_chunk_piper,
                        text, model_path, speed_pct, output_path, log_func,
                    )
                    return
                if PYTTSX3_AVAILABLE and OFFLINE_VOICE_PRESETS:
                    msg("  Все попытки исчерпаны. Переключаюсь на оффлайн (SAPI)...")
                    offline_voice = _find_offline_voice_for(voice)
                    await asyncio.get_event_loop().run_in_executor(
                        None, synthesize_chunk_offline,
                        offline_voice, offline_voice, speed_pct, output_path, log_func,
                    )
                    return
                msg(f"  ОШИБКА после {MAX_RETRIES + 1} попыток: {e}")
                raise

            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            msg(f"  Сервер недоступен: {e}")
            msg(f"  Повторная попытка через {delay} сек "
                f"({attempt + 1}/{MAX_RETRIES})...")
            await asyncio.sleep(delay)


def _find_offline_voice_for(edge_voice: str) -> str:
    """Подбирает оффлайн SAPI-голос по языку Edge-голоса."""
    # Определяем язык из edge_voice (например "ru-RU-DmitryNeural" → "ru")
    lang = edge_voice.split("-")[0].lower() if edge_voice else ""
    lang_map = {
        "ru": ["russian", "ru-ru", "русск"],
        "en": ["english", "en-us", "en-gb"],
    }
    keywords = lang_map.get(lang, [])

    for _, voice_id in OFFLINE_VOICE_PRESETS:
        vid = voice_id.lower()
        if any(kw in vid for kw in keywords):
            return voice_id

    # Если не нашли — возвращаем первый доступный
    if OFFLINE_VOICE_PRESETS:
        return OFFLINE_VOICE_PRESETS[0][1]
    return ""


async def synthesize_chapter(
    title: str,
    text: str,
    voice: str,
    speed: str,
    output_path: str,
    chapter_num: int,
    total_chapters: int,
    log_func=None,
    tts_mode: str = TTS_MODE_ONLINE,
):
    """Озвучивает одну главу (возможно, из нескольких частей)."""
    label = title if title else f"Часть {chapter_num}"
    msg = f"[{chapter_num}/{total_chapters}] {label}"
    if log_func:
        log_func(msg)
    else:
        print(f"  {msg}")

    chunks = split_text_into_chunks(text)

    if len(chunks) == 1:
        await synthesize_chunk(chunks[0], voice, speed, output_path,
                               log_func=log_func, tts_mode=tts_mode)
        return

    temp_files = []
    for i, chunk in enumerate(chunks):
        temp_path = output_path.replace(".mp3", f"_part{i:04d}.mp3")
        temp_files.append(temp_path)
        frag_msg = f"  фрагмент {i + 1}/{len(chunks)}..."
        if log_func:
            log_func(frag_msg)
        else:
            print(f"    {frag_msg}")
        await synthesize_chunk(chunk, voice, speed, temp_path,
                               log_func=log_func, tts_mode=tts_mode)

    try:
        from pydub import AudioSegment
        combined = AudioSegment.empty()
        for tf in temp_files:
            combined += AudioSegment.from_mp3(tf)
        combined.export(output_path, format="mp3")
    except ImportError:
        with open(output_path, "wb") as out:
            for tf in temp_files:
                with open(tf, "rb") as inp:
                    out.write(inp.read())

    for tf in temp_files:
        try:
            os.remove(tf)
        except OSError:
            pass


async def merge_files(file_list: list[str], output_path: str, log_func=None):
    """Объединяет несколько mp3-файлов в один."""
    msg_func = log_func or print
    try:
        from pydub import AudioSegment
        combined = AudioSegment.empty()
        for f in file_list:
            combined += AudioSegment.from_mp3(f)
        combined.export(output_path, format="mp3")
        msg_func(f"Объединённый файл: {output_path}")
    except ImportError:
        with open(output_path, "wb") as out:
            for f in file_list:
                with open(f, "rb") as inp:
                    out.write(inp.read())
        msg_func(f"Объединённый файл: {output_path}")
        msg_func("(установите pydub для более качественного склеивания)")


async def list_voices(language_filter: str = ""):
    """Показывает доступные голоса."""
    voices = await edge_tts.list_voices()
    if language_filter:
        voices = [
            v for v in voices
            if language_filter.lower() in v["Locale"].lower()
            or language_filter.lower() in v["ShortName"].lower()
        ]
    if not voices:
        print(f"Голоса для '{language_filter}' не найдены.")
        return
    print(f"{'Имя голоса':<35} {'Язык':<10} {'Пол':<10}")
    print("-" * 55)
    for v in sorted(voices, key=lambda x: x["Locale"]):
        print(f"{v['ShortName']:<35} {v['Locale']:<10} {v['Gender']:<10}")


def _format_time(seconds: float) -> str:
    """Форматирует секунды в читаемый вид: '2 ч 15 мин', '3 мин 40 сек' и т.д."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m} мин {s} сек"
    else:
        h, remainder = divmod(seconds, 3600)
        m = remainder // 60
        return f"{h} ч {m} мин"


async def convert_book(
    input_file: str,
    output_dir: str,
    voice: str | None,
    speed: str,
    merge: bool,
    delete_fragments: bool = False,
    no_chapters: bool = False,
    encoding: str = "auto",
    log_func=None,
    progress_func=None,
    time_func=None,
    stop_event: threading.Event | None = None,
    voice_func=None,
    tts_mode: str = TTS_MODE_AUTO,
):
    """Основная функция конвертации.
    voice_func — callable, возвращает текущий голос из GUI.
    tts_mode — 'auto', 'online' или 'offline'.
    """
    import time as _time

    msg = log_func or print

    input_path = Path(input_file)
    if not input_path.exists():
        msg(f"Ошибка: файл '{input_file}' не найден.")
        return

    # Определяем фактический режим TTS
    actual_mode = resolve_tts_mode(tts_mode, log_func=msg)

    msg(f"Чтение файла: {input_file}")

    # Автоопределение кодировки
    if encoding == "auto":
        encoding = detect_encoding(input_file, log_func=msg)

    text = input_path.read_text(encoding=encoding)

    if not text.strip():
        msg("Ошибка: файл пуст.")
        return

    lang = detect_language(text)
    if voice is None:
        if actual_mode == TTS_MODE_PIPER and PIPER_AVAILABLE:
            voice = _find_piper_model_for(
                DEFAULT_VOICES.get(lang, "en-US-GuyNeural"))
        elif actual_mode == TTS_MODE_OFFLINE:
            voice = _find_offline_voice_for(
                DEFAULT_VOICES.get(lang, "en-US-GuyNeural"))
        else:
            voice = DEFAULT_VOICES.get(lang, "en-US-GuyNeural")
    mode_label = {
        TTS_MODE_ONLINE: "Онлайн (Edge TTS)",
        TTS_MODE_PIPER: "Piper TTS (нейросеть, оффлайн)",
        TTS_MODE_OFFLINE: "Оффлайн (Windows SAPI)",
    }.get(actual_mode, "Авто")
    msg(f"Режим: {mode_label}")
    msg(f"Язык: {lang}, голос: {voice}")

    if no_chapters:
        chapters = [("", text.strip())]
    else:
        chapters = split_into_chapters(text)
    msg(f"Найдено глав/частей: {len(chapters)}")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # ── Определение точки возобновления ────────────────────────────

    generated_files = []
    files_to_generate: list[tuple[int, str, str, str]] = []

    # Собираем пути для всех глав
    chapter_paths: list[str] = []
    for i, (title, body) in enumerate(chapters, 1):
        safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)[:50] if title else ""
        filename = f"{i:03d}"
        if safe_title:
            filename += f"_{safe_title}"
        filename += ".mp3"
        chapter_paths.append(str(out_path / filename))

    # Считаем количество .mp3 файлов в папке — это и есть resume_from
    existing_mp3 = len([f for f in os.listdir(out_path) if f.endswith(".mp3")])
    resume_from = min(existing_mp3, len(chapters))

    for i, (title, body) in enumerate(chapters):
        generated_files.append(chapter_paths[i])
        if i >= resume_from:
            files_to_generate.append((i + 1, title, body, chapter_paths[i]))

    skipped = resume_from
    if skipped > 0:
        msg(f"Файлов в папке: {existing_mp3} — продолжение с фрагмента {resume_from + 1}")

    if not files_to_generate:
        msg("\nВсе фрагменты уже сгенерированы!")
        if progress_func:
            progress_func(len(chapters), len(chapters))
        if time_func:
            time_func("")
    else:
        remaining = len(files_to_generate)
        msg(f"Осталось сгенерировать: {remaining}\n")
        msg("Генерация аудио...\n")

        # Таймер для оценки оставшегося времени
        gen_start_time = _time.monotonic()
        chunk_times: list[float] = []

        stopped = False
        for idx, (i, title, body, file_path) in enumerate(files_to_generate, 1):

            # ── Проверка остановки ────────────────────────────
            if stop_event and stop_event.is_set():
                msg("\nОстановлено пользователем. Прогресс сохранён.")
                if time_func:
                    time_func("")
                stopped = True
                break

            chunk_start = _time.monotonic()

            await synthesize_chapter(
                title, body, voice, speed, file_path, i, len(chapters),
                log_func=msg, tts_mode=actual_mode,
            )

            chunk_elapsed = _time.monotonic() - chunk_start
            chunk_times.append(chunk_elapsed)

            done = skipped + idx
            if progress_func:
                progress_func(done, len(chapters))

            # Оценка оставшегося времени (скользящее среднее)
            avg_time = sum(chunk_times) / len(chunk_times)
            left = remaining - idx
            if left > 0 and time_func:
                eta = avg_time * left
                time_func(f"Осталось ~{_format_time(eta)}")
            elif time_func:
                time_func("")

            msg(f"  ({_format_time(chunk_elapsed)} на фрагмент,"
                f" осталось ~{_format_time(avg_time * left) if left > 0 else '0 сек'})\n")

            # Сохраняем прогресс после каждого фрагмента
            add_to_history(input_file, output_dir, voice or "", len(chapters), done)

        if not stopped:
            total_elapsed = _time.monotonic() - gen_start_time
            msg(f"\nГенерация заняла: {_format_time(total_elapsed)}")

    if stopped:
        # Прогресс уже сохранён в цикле — просто выходим
        return None

    # Финальная запись в историю
    add_to_history(input_file, output_dir, voice or "", len(chapters), len(chapters))

    msg(f"\nГотово! Файлы сохранены в: {out_path.resolve()}")

    merged_path = None
    if merge and len(generated_files) > 1:
        merged_path = str(out_path / f"{input_path.stem}_full.mp3")
        if os.path.exists(merged_path):
            os.remove(merged_path)
        msg("\nОбъединение фрагментов в один файл...")
        await merge_files(generated_files, merged_path, log_func=msg)

        # Удаление фрагментов после объединения (по выбору пользователя)
        if delete_fragments:
            msg("Удаление фрагментов...")
            deleted_count = 0
            for fpath in generated_files:
                try:
                    if os.path.exists(fpath):
                        os.remove(fpath)
                        deleted_count += 1
                except OSError:
                    pass
            msg(f"Удалено фрагментов: {deleted_count}")
        else:
            msg("Фрагменты сохранены для дальнейшего использования.")
    else:
        msg("Фрагменты сохранены для дальнейшего использования.")

    # Считаем размер оставшихся файлов
    all_files = [merged_path] if merged_path and delete_fragments else generated_files
    if merged_path and not delete_fragments:
        all_files = generated_files + [merged_path]
    total_size = sum(os.path.getsize(f) for f in all_files if f and os.path.exists(f))
    file_count = sum(1 for f in all_files if f and os.path.exists(f))
    msg(f"\nВсего файлов: {file_count}")
    msg(f"Общий размер: {total_size / (1024 * 1024):.1f} МБ")

    # Возвращаем информацию о результатах
    return {
        "output_dir": str(out_path.resolve()),
        "merged_file": merged_path,
        "total_files": file_count,
        "total_size_mb": round(total_size / (1024 * 1024), 1),
        "book_name": input_path.stem,
    }


# ══════════════════════════════════════════════════════════════════════
#  История проектов (последние книги)
# ══════════════════════════════════════════════════════════════════════

MAX_HISTORY = 10  # максимум записей в истории


def _history_path() -> Path:
    """Путь к файлу истории (ищет в нескольких местах)."""
    name = "audiobook_history.json"
    # Кандидаты: рядом с exe, рядом со скриптом, в CWD
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).parent / name)
    else:
        candidates.append(Path(__file__).parent / name)
    candidates.append(Path.cwd() / name)
    # Возвращаем первый существующий или первый кандидат (для записи)
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


_history_load_error = ""  # для диагностики в GUI


def load_history() -> list[dict]:
    """Загружает историю проектов."""
    global _history_load_error
    path = _history_path()
    if not path.exists():
        _history_load_error = f"файл не найден: {path}"
        return []
    try:
        raw = path.read_text(encoding="utf-8-sig")
        data = json.loads(raw)
        if isinstance(data, list):
            _history_load_error = ""
            return data
        _history_load_error = f"не список: {type(data)}"
        return []
    except Exception as e:
        _history_load_error = str(e)
        return []


def save_history(history: list[dict]):
    """Сохраняет историю проектов."""
    path = _history_path()
    try:
        path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def add_to_history(
    input_file: str,
    output_dir: str,
    voice: str,
    total_chapters: int,
    done_chapters: int,
):
    """Добавляет или обновляет запись в истории."""
    history = load_history()

    # Нормализуем путь для сравнения
    norm_input = os.path.normpath(input_file)

    # Ищем существующую запись
    existing = None
    for entry in history:
        if os.path.normpath(entry.get("input_file", "")) == norm_input:
            existing = entry
            break

    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if existing:
        existing["output_dir"] = output_dir
        existing["voice"] = voice
        existing["total_chapters"] = total_chapters
        existing["done_chapters"] = done_chapters
        existing["finished"] = done_chapters >= total_chapters
        existing["last_used"] = now
        # Поднимаем наверх
        history.remove(existing)
        history.insert(0, existing)
    else:
        history.insert(0, {
            "input_file": input_file,
            "output_dir": output_dir,
            "voice": voice,
            "total_chapters": total_chapters,
            "done_chapters": done_chapters,
            "finished": done_chapters >= total_chapters,
            "last_used": now,
            "book_name": Path(input_file).stem,
        })

    # Обрезаем до лимита
    history = history[:MAX_HISTORY]
    save_history(history)


def get_last_unfinished() -> dict | None:
    """Возвращает последнюю незаконченную книгу или None."""
    for entry in load_history():
        if not entry.get("finished", True):
            if os.path.exists(entry.get("input_file", "")):
                return entry
    return None


# ══════════════════════════════════════════════════════════════════════
#  GUI (CustomTkinter — современный интерфейс)
# ══════════════════════════════════════════════════════════════════════


def run_gui():
    """Запускает современный графический интерфейс."""
    import tkinter as tk
    from tkinter import filedialog, messagebox

    try:
        import customtkinter as ctk
    except ImportError:
        print("Ошибка: библиотека customtkinter не установлена.")
        print("Установите её командой: pip install customtkinter")
        sys.exit(1)

    # ── Цвета и константы ─────────────────────────────────────────────

    ACCENT = "#6C63FF"          # фиолетовый акцент
    ACCENT_HOVER = "#5A52D5"
    SUCCESS = "#2ECC71"
    BG_DARK = "#1A1A2E"
    BG_CARD = "#16213E"
    BG_INPUT = "#0F3460"
    TEXT_PRIMARY = "#EAEAEA"
    TEXT_SECONDARY = "#A0A0B8"
    LOG_BG = "#0D1B2A"
    LOG_FG = "#89CFF0"

    # ── Настройка темы ────────────────────────────────────────────────

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title(f"Text to Audiobook v{APP_VERSION} (Python) — Online + Piper + Offline")
    root.geometry("720x850")
    root.minsize(680, 780)
    root.configure(fg_color=BG_DARK)

    # ── Переменные ────────────────────────────────────────────────────

    var_input = tk.StringVar()
    var_output = tk.StringVar()
    var_voice_idx = tk.IntVar(value=0)
    var_speed = tk.DoubleVar(value=0)
    var_merge = tk.BooleanVar(value=True)
    var_delete_fragments = tk.BooleanVar(value=False)
    var_no_chapters = tk.BooleanVar(value=False)
    var_encoding = tk.StringVar(value="auto")
    var_tts_mode = tk.StringVar(value=TTS_MODE_AUTO)
    is_converting = False
    stop_event = threading.Event()

    # ── Вспомогательные функции для карточек ──────────────────────────

    def make_card(parent, **kwargs):
        return ctk.CTkFrame(
            parent, fg_color=BG_CARD, corner_radius=14, **kwargs
        )

    def make_label(parent, text, **kwargs):
        return ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
            **kwargs,
        )

    def make_combo(parent, values, command=None, width=None, height=34, **kwargs):
        """Создаёт стилизованный CTkComboBox с единым оформлением."""
        opts = dict(
            fg_color=BG_INPUT, border_color=ACCENT, border_width=1,
            button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_hover_color=ACCENT,
            text_color=TEXT_PRIMARY, corner_radius=10,
            height=height, state="readonly",
        )
        if width is not None:
            opts["width"] = width
        if command is not None:
            opts["command"] = command
        opts.update(kwargs)
        return ctk.CTkComboBox(parent, values=values, **opts)

    def make_button(parent, text, command, width=120, height=42, **kwargs):
        """Создаёт стилизованный CTkButton с единым оформлением."""
        opts = dict(
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="#FFFFFF", corner_radius=10,
            font=ctk.CTkFont(size=13),
            width=width, height=height,
            command=command,
        )
        opts.update(kwargs)
        return ctk.CTkButton(parent, text=text, **opts)

    def make_ghost_button(parent, text, command, width=120, height=34, **kwargs):
        """Создаёт бесцветную кнопку с рамкой (для Json, Пауза, Открыть папку)."""
        return make_button(
            parent, text=text, command=command, width=width, height=height,
            fg_color=BG_CARD, hover_color=BG_INPUT,
            border_color=ACCENT, border_width=1,
            text_color=TEXT_PRIMARY, **kwargs,
        )

    def make_checkbox(parent, text, variable):
        """Создаёт стилизованный CTkCheckBox."""
        return ctk.CTkCheckBox(
            parent, text=text, variable=variable,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            border_color=TEXT_SECONDARY, text_color=TEXT_PRIMARY,
            corner_radius=6, font=ctk.CTkFont(size=13),
        )

    # ── Загрузка проекта из истории ──────────────────────────────────

    def load_project(entry: dict):
        """Заполняет поля из записи истории."""
        input_file = entry.get("input_file", "")
        var_input.set(input_file)
        var_output.set(entry.get("output_dir", ""))
        voice = entry.get("voice", "")
        for i, (_, short) in enumerate(ALL_VOICES):
            if short == voice:
                var_voice_idx.set(i)
                combo_voice.set(voice_names[i])
                break
        # Загружаем текст книги
        if input_file and os.path.isfile(input_file):
            load_book_preview(input_file)

    # ── Загрузка истории ─────────────────────────────────────────────

    history = load_history()
    unfinished = get_last_unfinished()

    # ── Разделяемая панель: настройки (верх) + лог (низ) ──────────────

    paned = tk.PanedWindow(
        root, orient="vertical", sashwidth=6, sashrelief="flat",
        bg="#2A2A40", borderwidth=0, opaqueresize=True,
    )
    paned.pack(fill="both", expand=True, padx=0, pady=0)

    top_wrapper = tk.Frame(paned, bg=BG_DARK)
    bottom_wrapper = tk.Frame(paned, bg=BG_DARK)
    paned.add(top_wrapper, minsize=200, height=500, stretch="always")
    paned.add(bottom_wrapper, minsize=150, stretch="always")

    top_frame = ctk.CTkFrame(top_wrapper, fg_color=BG_DARK)
    top_frame.pack(fill="both", expand=True)

    bottom_frame = ctk.CTkFrame(bottom_wrapper, fg_color=BG_DARK)
    bottom_frame.pack(fill="both", expand=True)

    # ── Карточка настроек ───────────────────────────────────────────

    card_settings = make_card(top_frame)
    card_settings.pack(fill="x", padx=24, pady=(8, 3))

    # --- История ---
    row_hist = ctk.CTkFrame(card_settings, fg_color="transparent")
    row_hist.pack(fill="x", padx=16, pady=(10, 4))

    # Только input_file в списке
    history_labels = [e.get("input_file", "?") for e in history] if history else []

    def on_history_select(choice: str):
        if not history:
            return
        idx = history_labels.index(choice) if choice in history_labels else -1
        if 0 <= idx < len(history):
            load_project(history[idx])

    combo_history = make_combo(
        row_hist,
        values=history_labels if history_labels else ["(нет истории)"],
        command=on_history_select,
    )
    if history:
        combo_history.set("Выберите из истории...")
    else:
        combo_history.set("(нет истории)")
    combo_history.pack(side="left", fill="x", expand=True, padx=(0, 8))

    def open_history_json():
        hp = _history_path()
        if hp and hp.exists():
            os.startfile(str(hp))
        else:
            messagebox.showinfo("Файл не найден", "audiobook_history.json не найден.")

    make_ghost_button(row_hist, "Json", open_history_json, width=60).pack(side="right")

    # --- Исходный файл ---
    row_file = ctk.CTkFrame(card_settings, fg_color="transparent")
    row_file.pack(fill="x", padx=16, pady=(4, 4))

    entry_input = ctk.CTkEntry(
        row_file, textvariable=var_input,
        placeholder_text="Выберите .txt файл...",
        fg_color=BG_INPUT, border_color=ACCENT, border_width=1,
        text_color=TEXT_PRIMARY, corner_radius=10, height=34,
    )
    entry_input.pack(side="left", fill="x", expand=True, padx=(0, 8))

    def auto_select_voice(file_path: str):
        """Определяет язык файла и ставит мужской голос по умолчанию."""
        try:
            enc = detect_encoding(file_path)
            sample = Path(file_path).read_text(encoding=enc)[:5000]
            lang = detect_language(sample)
            default_voice = DEFAULT_VOICES.get(lang)
            if default_voice:
                for i, (name, short) in enumerate(ALL_VOICES):
                    if short == default_voice:
                        var_voice_idx.set(i)
                        combo_voice.set(voice_names[i])
                        return
        except Exception:
            pass

    def get_current_voice() -> str:
        """Возвращает текущий голос из GUI (для смены при паузе)."""
        idx = var_voice_idx.get()
        if 0 <= idx < len(ALL_VOICES):
            return ALL_VOICES[idx][1]
        return ""

    def browse_input():
        path = filedialog.askopenfilename(
            title="Выберите текстовый файл",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
            parent=root,
        )
        if path:
            var_input.set(path)
            if not var_output.get():
                var_output.set(str(Path(path).parent / (Path(path).stem + "_audio")))
            auto_select_voice(path)
            load_book_preview(path)

    make_button(
        row_file, text="Файл", width=80, height=34,
        command=browse_input,
    ).pack(side="right")

    # --- Папка для аудиофайлов ---
    row_out = ctk.CTkFrame(card_settings, fg_color="transparent")
    row_out.pack(fill="x", padx=16, pady=(4, 6))

    entry_output = ctk.CTkEntry(
        row_out, textvariable=var_output,
        placeholder_text="Папка сохранения...",
        fg_color=BG_INPUT, border_color=ACCENT, border_width=1,
        text_color=TEXT_PRIMARY, corner_radius=10, height=34,
    )
    entry_output.pack(side="left", fill="x", expand=True, padx=(0, 8))

    def browse_output():
        # Определяем начальную папку для диалога
        initial = var_output.get().strip() or var_input.get().strip()
        if initial and os.path.isfile(initial):
            initial = os.path.dirname(initial)
        if initial and not os.path.isdir(initial):
            initial = os.path.dirname(initial) if os.path.isdir(os.path.dirname(initial)) else ""
        initial = initial or os.path.expanduser("~")
        root.update()
        path = filedialog.askdirectory(
            title="Выберите папку для сохранения",
            initialdir=initial, parent=root,
        )
        if path:
            var_output.set(path)

    make_button(
        row_out, text="Папка", width=80, height=34,
        command=browse_output,
    ).pack(side="right")

    # --- Режим TTS + Голос (одна строка) ---
    row_mode = ctk.CTkFrame(card_settings, fg_color="transparent")
    row_mode.pack(fill="x", padx=16, pady=(4, 4))

    make_label(row_mode, "Режим").pack(side="left", padx=(0, 12))

    OFFLINE_COLOR = "#27AE60"

    mode_names = {
        TTS_MODE_AUTO: "Авто (онлайн → Piper → SAPI)",
        TTS_MODE_ONLINE: "Онлайн (Edge TTS)",
        TTS_MODE_PIPER: "Piper TTS (нейросеть, оффлайн)",
        TTS_MODE_OFFLINE: "Оффлайн (Windows SAPI)",
    }
    mode_values = list(mode_names.keys())
    mode_labels = list(mode_names.values())

    lbl_mode_status = ctk.CTkLabel(
        row_mode, text="",
        font=ctk.CTkFont(size=12),
        text_color=TEXT_SECONDARY,
    )

    # Объединяем онлайн, piper и оффлайн голоса
    ALL_VOICES = VOICE_PRESETS + PIPER_VOICE_PRESETS + OFFLINE_VOICE_PRESETS
    voice_names = [name for name, _ in ALL_VOICES]

    def update_voice_list(mode: str):
        """Обновляет список голосов в зависимости от режима."""
        nonlocal ALL_VOICES, voice_names
        if mode == TTS_MODE_PIPER:
            ALL_VOICES = PIPER_VOICE_PRESETS + VOICE_PRESETS + OFFLINE_VOICE_PRESETS
        elif mode == TTS_MODE_OFFLINE:
            ALL_VOICES = OFFLINE_VOICE_PRESETS + PIPER_VOICE_PRESETS + VOICE_PRESETS
        else:
            ALL_VOICES = VOICE_PRESETS + PIPER_VOICE_PRESETS + OFFLINE_VOICE_PRESETS
        voice_names = [name for name, _ in ALL_VOICES]
        combo_voice.configure(values=voice_names)
        if voice_names:
            combo_voice.set(voice_names[0])
            var_voice_idx.set(0)

    def on_mode_change(choice: str):
        idx = mode_labels.index(choice) if choice in mode_labels else 0
        mode = mode_values[idx]
        var_tts_mode.set(mode)
        update_voice_list(mode)
        if mode == TTS_MODE_PIPER:
            cnt = len(PIPER_VOICE_PRESETS)
            if cnt:
                lbl_mode_status.configure(
                    text=f"Piper моделей: {cnt}",
                    text_color=OFFLINE_COLOR,
                )
            else:
                lbl_mode_status.configure(
                    text="Piper не найден!",
                    text_color="#E74C3C",
                )
        elif mode == TTS_MODE_OFFLINE:
            cnt = len(OFFLINE_VOICE_PRESETS)
            lbl_mode_status.configure(
                text=f"SAPI-голосов: {cnt}" if cnt else "SAPI не найдены!",
                text_color=OFFLINE_COLOR if cnt else "#E74C3C",
            )
        elif mode == TTS_MODE_ONLINE:
            lbl_mode_status.configure(text="Требуется интернет", text_color=TEXT_SECONDARY)
        else:
            lbl_mode_status.configure(text="")

    combo_mode = make_combo(
        row_mode, values=mode_labels, width=260,
        command=on_mode_change,
    )
    combo_mode.set(mode_labels[0])
    combo_mode.pack(side="left")

    make_label(row_mode, "Голос").pack(side="left", padx=(16, 12))

    combo_voice = make_combo(
        row_mode, values=voice_names,
        command=lambda choice: var_voice_idx.set(voice_names.index(choice)),
    )
    combo_voice.set(voice_names[0])
    combo_voice.pack(side="left", fill="x", expand=True)

    lbl_mode_status.pack(side="left", padx=(12, 0))
    on_mode_change(mode_labels[0])

    # --- Скорость + Кодировка (одна строка) ---
    row_speed = ctk.CTkFrame(card_settings, fg_color="transparent")
    row_speed.pack(fill="x", padx=16, pady=(4, 4))

    make_label(row_speed, "Скорость").pack(side="left", padx=(0, 12))

    lbl_speed_val = ctk.CTkLabel(
        row_speed, text="Норм.",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color=ACCENT, width=60,
    )

    slider_speed = ctk.CTkSlider(
        row_speed, from_=-50, to=50, variable=var_speed,
        width=280, height=18,
        fg_color=BG_INPUT, progress_color=ACCENT,
        button_color=TEXT_PRIMARY, button_hover_color=ACCENT,
    )
    slider_speed.pack(side="left")

    lbl_speed_val.pack(side="left", padx=(12, 0))

    make_label(row_speed, "Кодировка").pack(side="left", padx=(24, 12))

    combo_enc = make_combo(
        row_speed,
        values=["auto", "utf-8", "cp1251", "cp866", "koi8-r", "latin-1", "utf-16"],
        width=110, variable=var_encoding,
    )
    combo_enc.pack(side="left")

    def update_speed_label(*_):
        val = int(var_speed.get())
        if val == 0:
            lbl_speed_val.configure(text="Норм.")
        elif val > 0:
            lbl_speed_val.configure(text=f"+{val}%")
        else:
            lbl_speed_val.configure(text=f"{val}%")

    var_speed.trace_add("write", update_speed_label)

    # --- Чекбоксы ---
    row_checks = ctk.CTkFrame(card_settings, fg_color="transparent")
    row_checks.pack(fill="x", padx=16, pady=(2, 4))

    make_checkbox(row_checks, "Объединить главы в один файл", var_merge).pack(side="left", padx=(0, 20))
    make_checkbox(row_checks, "Не разбивать на главы", var_no_chapters).pack(side="left", padx=(0, 20))
    make_checkbox(row_checks, "Удалить фрагменты", var_delete_fragments).pack(side="left")

    def open_output_folder():
        folder = var_output.get().strip()
        if folder and Path(folder).exists():
            if sys.platform == "win32":
                os.startfile(folder)
            else:
                os.system(f'xdg-open "{folder}"')
        else:
            messagebox.showinfo("Папка не найдена", "Сначала выполните конвертацию.")

    # ── Обновление кнопок при старте/завершении ─────────────────────

    def set_buttons_converting(active: bool):
        if active:
            btn_start.configure(state="disabled", text="Конвертация...")
        else:
            btn_start.configure(state="normal", text="Создать аудио")

    # ── Диалог завершения конвертации ───────────────────────────────

    WARN_COLOR = "#E67E22"
    WARN_HOVER = "#D35400"

    def show_completion_dialog(result):
        """Показывает модальное окно с результатами конвертации."""
        dlg = ctk.CTkToplevel(root)
        dlg.title("Конвертация завершена")
        dlg.resizable(False, False)
        dlg.configure(fg_color=BG_DARK)
        dlg.attributes("-topmost", True)

        dw, dh = 460, 320
        dx = root.winfo_x() + (root.winfo_width() // 2) - (dw // 2)
        dy = root.winfo_y() + (root.winfo_height() // 2) - (dh // 2)
        dlg.geometry(f"{dw}x{dh}+{dx}+{dy}")

        ctk.CTkLabel(
            dlg, text="✔  Конвертация завершена!",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=SUCCESS,
        ).pack(pady=(24, 16))

        # Информация о результате
        info_frame = ctk.CTkFrame(dlg, fg_color=BG_CARD, corner_radius=12)
        info_frame.pack(fill="x", padx=28, pady=(0, 16))

        lines = [
            ("Книга:", result.get("book_name", "—")),
            ("Файлов создано:", str(result.get("total_files", 0))),
            ("Общий размер:", f"{result.get('total_size_mb', 0)} МБ"),
        ]
        if result.get("merged_file"):
            lines.append(("Итоговый файл:", Path(result["merged_file"]).name))

        for label_text, value_text in lines:
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=label_text,
                         font=ctk.CTkFont(size=13),
                         text_color=TEXT_SECONDARY).pack(side="left")
            ctk.CTkLabel(row, text=value_text,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=TEXT_PRIMARY).pack(side="right")

        # Кнопки диалога
        btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_frame.pack(fill="x", padx=28, pady=(0, 20))

        merged = result.get("merged_file")
        out_dir = result.get("output_dir", "")

        if merged and Path(merged).exists():
            def open_file():
                os.startfile(merged)
                dlg.destroy()
            make_button(
                btn_frame, text="▶  Открыть аудиофайл", width=180, height=38,
                font=ctk.CTkFont(size=13, weight="bold"),
                command=open_file,
            ).pack(side="left", padx=(0, 8))

        if out_dir and Path(out_dir).exists():
            def open_folder():
                os.startfile(out_dir)
                dlg.destroy()
            make_button(
                btn_frame, text="📁  Открыть папку", width=150, height=38,
                fg_color=WARN_COLOR, hover_color=WARN_HOVER,
                command=open_folder,
            ).pack(side="left", padx=(0, 8))

        make_button(
            btn_frame, text="Закрыть", width=90, height=38,
            fg_color=BG_INPUT, hover_color=BG_CARD,
            text_color=TEXT_SECONDARY,
            command=dlg.destroy,
        ).pack(side="right")

        dlg.grab_set()

    # ── Запуск конвертации ──────────────────────────────────────────

    def start_conversion():
        """Валидация полей, сброс UI и запуск convert_book в отдельном потоке."""
        nonlocal is_converting

        input_file = var_input.get().strip()
        output_dir = var_output.get().strip()

        if not input_file:
            messagebox.showwarning("Внимание", "Выберите исходный файл.")
            return
        if not Path(input_file).exists():
            messagebox.showerror("Ошибка", f"Файл не найден:\n{input_file}")
            return
        if not output_dir:
            messagebox.showwarning("Внимание", "Укажите папку для сохранения.")
            return

        _, voice_short = ALL_VOICES[var_voice_idx.get()]
        speed_val = int(var_speed.get())
        speed_str = f"+{speed_val}%" if speed_val >= 0 else f"{speed_val}%"

        log_text.config(state="normal")
        log_text.delete("1.0", "end")
        log_text.config(state="disabled")
        progress_bar.set(0)
        progress_bar.configure(progress_color=ACCENT)
        lbl_percent.configure(text="0%", text_color=ACCENT)
        lbl_eta.configure(text="")

        stop_event.clear()
        is_converting = True
        root.after(0, lambda: set_buttons_converting(True))

        def run_in_thread():
            nonlocal is_converting
            try:
                result = asyncio.run(
                    convert_book(
                        input_file=input_file,
                        output_dir=output_dir,
                        voice=voice_short,
                        speed=speed_str,
                        merge=var_merge.get(),
                        delete_fragments=var_delete_fragments.get(),
                        no_chapters=var_no_chapters.get(),
                        encoding=var_encoding.get(),
                        log_func=log,
                        progress_func=set_progress,
                        time_func=set_eta,
                        stop_event=stop_event,
                        voice_func=get_current_voice,
                        tts_mode=var_tts_mode.get(),
                    )
                )
                if result and not stop_event.is_set():
                    root.after(0, lambda: show_completion_dialog(result))
            except Exception as e:
                log(f"\nОшибка: {e}")
            finally:
                is_converting = False
                root.after(0, lambda: set_buttons_converting(False))

        threading.Thread(target=run_in_thread, daemon=True).start()

    # ── Текст книги (заполняет свободное место верхней панели) ────────

    card_book = make_card(top_frame)
    card_book.pack(fill="both", expand=True, padx=24, pady=(3, 3))

    row_book_header = ctk.CTkFrame(card_book, fg_color="transparent")
    row_book_header.pack(fill="x", padx=16, pady=(8, 4))

    make_label(row_book_header, "Текст книги").pack(side="left")

    # ── Шрифт текстбоксов (книга + лог) ─────────────────────────────
    import tkinter.font as tkfont
    _available = tkfont.families(root)

    _mono_fonts = []
    for fn in ["Cascadia Code", "Consolas", "Courier New", "Lucida Console",
               "DejaVu Sans Mono", "Source Code Pro"]:
        if fn in _available:
            _mono_fonts.append(fn)
    if not _mono_fonts:
        _mono_fonts = ["Courier New"]

    _text_font_name = _mono_fonts[0]
    _text_font_size = 14

    def _apply_font():
        """Применяет текущий шрифт к обоим текстбоксам."""
        font = (_text_font_name, _text_font_size)
        book_text.config(font=font)
        log_text.config(font=font)

    def on_text_font_change(choice):
        nonlocal _text_font_name
        _text_font_name = choice
        _apply_font()

    def on_text_font_size(choice):
        nonlocal _text_font_size
        _text_font_size = int(choice)
        _apply_font()

    make_label(row_book_header, "Размер").pack(side="right", padx=(8, 0))
    combo_text_font_size = make_combo(
        row_book_header,
        values=["11", "12", "13", "14", "15", "16", "18", "20", "22", "24"],
        width=70, height=28,
        command=on_text_font_size,
    )
    combo_text_font_size.set(str(_text_font_size))
    combo_text_font_size.pack(side="right")

    make_label(row_book_header, "Шрифт").pack(side="right", padx=(16, 8))
    combo_text_font = make_combo(
        row_book_header, values=_mono_fonts, width=170, height=28,
        command=on_text_font_change,
    )
    combo_text_font.set(_text_font_name)
    combo_text_font.pack(side="right")

    lbl_book_info = ctk.CTkLabel(
        row_book_header, text="",
        font=ctk.CTkFont(size=12),
        text_color=TEXT_SECONDARY,
    )
    lbl_book_info.pack(side="right", padx=(0, 16))

    book_text = tk.Text(
        card_book, wrap="word", state="disabled",
        bg=LOG_BG, fg="#D0D0D0",
        font=(_text_font_name, _text_font_size),
        insertbackground="#D0D0D0", selectbackground=ACCENT,
        relief="flat", borderwidth=0, padx=12, pady=8,
    )
    book_text.pack(fill="both", expand=True, padx=16, pady=(0, 10))

    def load_book_preview(file_path: str):
        """Загружает текст книги в текстбокс."""
        try:
            enc = detect_encoding(file_path)
            text = Path(file_path).read_text(encoding=enc)
            chars = len(text)
            lines_count = text.count("\n") + 1
            lbl_book_info.configure(
                text=f"{lines_count} строк, {chars} символов, {enc}"
            )
            book_text.config(state="normal")
            book_text.delete("1.0", "end")
            book_text.insert("1.0", text)
            book_text.config(state="disabled")
        except Exception as e:
            book_text.config(state="normal")
            book_text.delete("1.0", "end")
            book_text.insert("1.0", f"Ошибка чтения: {e}")
            book_text.config(state="disabled")
            lbl_book_info.configure(text="")

    # ── Карточка: Прогресс и лог ────────────────────────────────────

    card_progress = make_card(bottom_frame)
    card_progress.pack(fill="both", expand=True, padx=24, pady=(6, 16))

    row_progress_header = ctk.CTkFrame(card_progress, fg_color="transparent")
    row_progress_header.pack(fill="x", padx=16, pady=(12, 6))

    btn_start = make_button(
        row_progress_header, text="Создать аудио", width=130, height=30,
        font=ctk.CTkFont(size=13, weight="bold"),
        command=start_conversion,
    )
    btn_start.pack(side="left")

    btn_open = make_ghost_button(row_progress_header, "Открыть папку", open_output_folder, width=120, height=30)
    btn_open.pack(side="left", padx=(8, 0))

    def test_fragments():
        """Проверяет готовые фрагменты в папке и выводит отчёт в лог."""
        output_dir = var_output.get().strip()
        input_file = var_input.get().strip()
        if not input_file or not Path(input_file).exists():
            log("Сначала выберите исходный файл.")
            return
        if not output_dir or not Path(output_dir).exists():
            log("Папка для аудиофайлов не найдена.")
            return

        enc = var_encoding.get()
        if enc == "auto":
            enc = detect_encoding(input_file)
        text = Path(input_file).read_text(encoding=enc)
        if var_no_chapters.get():
            chapters = [("", text.strip())]
        else:
            chapters = split_into_chapters(text)

        out_path = Path(output_dir)
        MIN_SIZE = 1024
        ready, missing, broken = 0, 0, 0
        for i, (title, _) in enumerate(chapters, 1):
            safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)[:50] if title else ""
            fn = f"{i:03d}"
            if safe_title:
                fn += f"_{safe_title}"
            fn += ".mp3"
            fp = out_path / fn
            if fp.exists():
                if fp.stat().st_size >= MIN_SIZE:
                    ready += 1
                else:
                    broken += 1
                    log(f"  ⚠ Фрагмент {i}: слишком мал ({fp.stat().st_size} байт)")
            else:
                missing += 1

        total = len(chapters)
        log(f"\n═══ Тест фрагментов ═══")
        log(f"Всего глав: {total}")
        log(f"Готово: {ready}  |  Отсутствует: {missing}  |  Повреждён: {broken}")
        if missing == 0 and broken == 0:
            log("✔ Все фрагменты на месте!")
        else:
            log(f"Следующий для генерации: фрагмент {ready + 1}")

    make_ghost_button(row_progress_header, "Тестировать", test_fragments, width=110, height=30).pack(side="left", padx=(8, 0))

    make_label(row_progress_header, "Прогресс").pack(side="left", padx=(12, 0))

    lbl_eta = ctk.CTkLabel(
        row_progress_header, text="",
        font=ctk.CTkFont(size=13),
        text_color=TEXT_SECONDARY,
    )
    lbl_eta.pack(side="right", padx=(0, 16))

    lbl_percent = ctk.CTkLabel(
        row_progress_header, text="0%",
        font=ctk.CTkFont(size=13, weight="bold"),
        text_color=ACCENT,
    )
    lbl_percent.pack(side="right")

    progress_bar = ctk.CTkProgressBar(
        card_progress, height=10, corner_radius=5,
        fg_color=BG_INPUT, progress_color=ACCENT,
    )
    progress_bar.pack(fill="x", padx=16, pady=(0, 8))
    progress_bar.set(0)

    log_text = tk.Text(
        card_progress, wrap="word", state="disabled",
        bg=LOG_BG, fg=LOG_FG,
        font=(_text_font_name, _text_font_size),
        insertbackground=LOG_FG, selectbackground=ACCENT,
        relief="flat", borderwidth=0, padx=12, pady=8,
    )
    log_text.pack(fill="both", expand=True, padx=16, pady=(0, 14))

    # ── Функции логирования и прогресса ────────────────────────────

    def log(message: str):
        def _append():
            log_text.config(state="normal")
            log_text.insert("end", message + "\n")
            log_text.see("end")
            log_text.config(state="disabled")
        root.after(0, _append)

    def set_progress(current: int, total: int):
        def _update():
            frac = current / total if total else 0
            progress_bar.set(frac)
            lbl_percent.configure(text=f"{int(frac * 100)}%")
            if current >= total:
                progress_bar.configure(progress_color=SUCCESS)
                lbl_percent.configure(text_color=SUCCESS)
                lbl_eta.configure(text="")
        root.after(0, _update)

    def set_eta(text: str):
        root.after(0, lambda: lbl_eta.configure(text=text))

    # ── Центрируем и запускаем ────────────────────────────────────────

    root.update_idletasks()
    w, h = 720, 850
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    # Начальное положение разделителя: 70% настройки / 30% лог
    def _set_initial_sash():
        try:
            total_h = paned.winfo_height()
            if total_h > 100:
                paned.sash_place(0, 0, int(total_h * 0.70))
        except Exception:
            pass

    root.after(100, _set_initial_sash)
    root.after(500, _set_initial_sash)

    root.mainloop()


# ══════════════════════════════════════════════════════════════════════
#  CLI (argparse)
# ══════════════════════════════════════════════════════════════════════


def main_cli():
    parser = argparse.ArgumentParser(
        description="Конвертер текстовых книг в аудиокниги",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Примеры:
              python text_to_audiobook.py                              — запуск GUI
              python text_to_audiobook.py book.txt                     — конвертация
              python text_to_audiobook.py book.txt --voice ru-RU-SvetlanaNeural
              python text_to_audiobook.py book.txt --speed "+20%%" --merge
              python text_to_audiobook.py --list-voices ru
        """),
    )
    parser.add_argument("input", nargs="?", help="Путь к текстовому файлу (без аргумента — запуск GUI)")
    parser.add_argument("-o", "--output", default=None, help="Папка для выходных файлов")
    parser.add_argument("-v", "--voice", default=None, help="Имя голоса (например, ru-RU-DmitryNeural)")
    parser.add_argument("-s", "--speed", default="+0%%", help='Скорость речи ("+10%%", "-20%%")')
    parser.add_argument("--merge", action="store_true", help="Объединить все главы в один файл")
    parser.add_argument("--no-chapters", action="store_true", help="Не разбивать на главы")
    parser.add_argument("--encoding", default="auto", help="Кодировка файла (по умолчанию: auto — автоопределение)")
    parser.add_argument("--list-voices", nargs="?", const="", default=None, metavar="LANG",
                        help="Показать доступные голоса")
    parser.add_argument("--tts-mode", default="auto",
                        choices=["auto", "online", "offline"],
                        help="Режим TTS: auto (по умолчанию), online (Edge TTS), offline (SAPI)")
    parser.add_argument("--gui", action="store_true", help="Принудительно открыть GUI")

    args = parser.parse_args()

    # Показать голоса
    if args.list_voices is not None:
        asyncio.run(list_voices(args.list_voices))
        return

    # Если не передан файл — открываем GUI
    if not args.input or args.gui:
        run_gui()
        return

    # CLI-режим
    output_dir = args.output or str(Path(args.input).parent / (Path(args.input).stem + "_audio"))
    asyncio.run(
        convert_book(
            input_file=args.input,
            output_dir=output_dir,
            voice=args.voice,
            speed=args.speed,
            merge=args.merge,
            no_chapters=args.no_chapters,
            encoding=args.encoding,
            tts_mode=args.tts_mode,
        )
    )


if __name__ == "__main__":
    main_cli()
