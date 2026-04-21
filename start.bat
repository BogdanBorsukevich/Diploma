@echo off
chcp 65001 >nul
echo.
echo   ЛогістикаКомплекс — Тестувально-навчальна система
echo   ----------------------------------------------------
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   ПОМИЛКА: Python не знайдено. Встановіть Python 3.9+
    pause
    exit /b 1
)

echo   Встановлення залежностей...
pip install -r requirements.txt -q
echo   Залежності встановлено.
echo.
echo   Запуск сервера: http://localhost:5000
echo   Для зупинки натисніть Ctrl+C
echo.
cd backend
python app.py
pause
