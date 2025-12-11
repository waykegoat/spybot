# bot_instance.py
import telebot
from config import API_TOKEN

# Создаем глобальный объект бота
bot = telebot.TeleBot(API_TOKEN, parse_mode='HTML')
print("✅ Объект бота создан в bot_instance.py")