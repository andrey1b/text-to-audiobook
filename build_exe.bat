@echo off
chcp 65001 >nul
title Сборка Text-to-Audiobook.exe

echo ══════════════════════════════════════════════════
echo   Сборка Text-to-Audiobook в .exe
echo ══════════════════════════════════════════════════
echo.

:: Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python с https://python.org
    echo Обязательно отметьте "Add Python to PATH"
    pause
    exit /b 1
)

echo [1/3] Установка зависимостей...
pip install edge-tts pydub pyinstaller --quiet
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости.
    pause
    exit /b 1
)

echo [2/3] Сборка .exe (это может занять 1-2 минуты)...
pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "Text-to-Audiobook" ^
    --icon=NONE ^
    --hidden-import=edge_tts ^
    --hidden-import=edge_tts.communicate ^
    --hidden-import=pydub ^
    --hidden-import=certifi ^
    --collect-all edge_tts ^
    text_to_audiobook.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сборка не удалась. Смотрите ошибки выше.
    pause
    exit /b 1
)

echo.
echo [3/3] Готово!
echo ══════════════════════════════════════════════════
echo   Файл: dist\Text-to-Audiobook.exe
echo ══════════════════════════════════════════════════
echo.

:: Открываем папку с результатом
explorer dist

pause
