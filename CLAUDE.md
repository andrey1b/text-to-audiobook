# Text to Audiobook — правила работы с Git

## Ветки и коммиты

- Каждое изменение кода делать в **отдельной ветке** от `main`.
- Имя ветки: `feature/<краткое-описание>` или `fix/<краткое-описание>`.
  Примеры: `feature/book-preview`, `fix/resume-logic`.
- Коммитить только файл `text_to_audiobook.py` (основной) и файлы C# проекта.
- Резервные копии `text_to_audiobook_v*.py`, папки `build/`, `dist/`, `__pycache__/` **не коммитить**.

## Pull Requests

- После завершения работы в ветке — создавать **Pull Request в `main`** на GitHub.
- Заголовок PR: краткое описание изменения (на русском или английском).
- В описании PR указывать: что изменено и почему.
- Не мержить PR самостоятельно — ждать подтверждения пользователя.

## Структура проекта

- `text_to_audiobook.py` — основной файл Python-версии (текущая версия).
- `TextToAudiobookCSharp/` — C#/WPF версия проекта.
- `CLAUDE.md` — этот файл с правилами.
- `.gitignore` — исключения для Git.

## Сборка exe

```
python -m PyInstaller --noconfirm --onefile --windowed \
  --name "Text-to-Audiobook_vNN_Python" \
  --add-data "dist/piper;piper" \
  text_to_audiobook.py
```
