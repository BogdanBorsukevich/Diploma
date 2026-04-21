#!/usr/bin/env bash
# ╔══════════════════════════════════════════════╗
# ║  ЛогістикаКомплекс — Скрипт запуску          ║
# ╚══════════════════════════════════════════════╝
set -e
cd "$(dirname "$0")"

echo ""
echo "  🗺️  ЛогістикаКомплекс — Тестувально-навчальна система"
echo "  ────────────────────────────────────────────────────"

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "  ❌ Python 3 не знайдено. Встановіть Python 3.9+"
  exit 1
fi

# Install deps
echo "  📦 Встановлення залежностей..."
pip3 install -r requirements.txt -q --break-system-packages 2>/dev/null || \
  pip3 install -r requirements.txt -q

echo "  ✅ Залежності встановлено"
echo ""
echo "  🚀 Запуск сервера на http://localhost:5000"
echo "  ℹ️  Для зупинки натисніть Ctrl+C"
echo ""

cd backend
python3 app.py
