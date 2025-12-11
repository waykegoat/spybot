import telebot
from config import API_TOKEN

bot = telebot.TeleBot(API_TOKEN, parse_mode='HTML')

from database import load_global_stats
from handlers import *
from callbacks import *

if __name__ == '__main__':
    print("=" * 50)
    print("🤖 Бот 'Универсальный Шпион' запускается...")
    print("=" * 50)
    
    load_global_stats()
    
    print("🔄 Бот запущен и готов к работе!")
    print("📊 Загруженная статистика:")
    print(f"   Всего игр: {global_stats['total_games']}")
    print(f"   Уникальных игроков: {global_stats['total_players']}")
    print(f"   Активных лобби: {global_stats['active_lobbies']}")
    print("=" * 50)
    
    bot.infinity_polling()