# config.py
import os

# Попробуем загрузить из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env файл загружен")
except ImportError:
    print("⚠️ python-dotenv не установлен, используем переменные окружения")

class Config:
    # Получаем токен из переменных окружения
    API_TOKEN = os.getenv('BOT_TOKEN')
    
    # Если токен не найден, попробуем получить напрямую
    if not API_TOKEN:
        print("❌ BOT_TOKEN не найден в переменных окружения")
        print("Установите переменную окружения или создайте .env файл")
        API_TOKEN = None
    
    # Получаем ID администратора
    ADMIN_ID = os.getenv('ADMIN_ID')
    if ADMIN_ID:
        ADMIN_ID = int(ADMIN_ID)
    else:
        ADMIN_ID = None