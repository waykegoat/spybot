#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time

print("=" * 50)
print("🤖 Бот 'Универсальный Шпион' запускается...")
print(f"Время запуска: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)

try:
    # Загружаем модули в правильном порядке
    from database import load_global_stats, global_stats
    print("✅ database.py загружен")
    
    # Импортируем handlers и callbacks для регистрации обработчиков
    import handlers
    import callbacks
    print("✅ handlers.py и callbacks.py загружены")
    
    from bot_instance import bot
    print("✅ bot_instance.py загружен")
    
    print("✅ Все модули загружены успешно")
    
except Exception as e:
    print(f"❌ Ошибка загрузки модулей: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Загрузка статистики
try:
    load_global_stats()
    print("✅ Статистика загружена")
except Exception as e:
    print(f"⚠️ Ошибка загрузки статистики: {e}")

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("📊 Статистика бота:")
    print(f"   Всего игр: {global_stats.get('total_games', 0)}")
    print(f"   Уникальных игроков: {global_stats.get('total_players', 0)}")
    print(f"   Активных лобби: {global_stats.get('active_lobbies', 0)}")
    print(f"   Время работы: {int((time.time() - global_stats.get('start_time', time.time())) // 3600)}ч")
    print("=" * 50)
    
    print("\n🔄 Бот запускает polling...")
    print("ℹ️ Ожидание сообщений...")
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"❌ Ошибка в infinity_polling: {e}")
        import traceback
        traceback.print_exc()
        print("🔄 Перезапуск через 5 секунд...")
        time.sleep(5)