#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import telebot
from telebot import types
import random
import json
import time
from datetime import datetime
from collections import defaultdict, deque
import os

# ============ КОНФИГУРАЦИЯ ДЛЯ RAILWAY ============#

API_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

if not API_TOKEN:
    print("❌ ОШИБКА: Не найден BOT_TOKEN в переменных окружения!")
    print("В Railway Dashboard:")
    print("1. Откройте проект")
    print("2. Нажмите 'Variables'")
    print("3. Добавьте BOT_TOKEN = ваш_токен")
    exit(1)

if not ADMIN_ID:
    print("❌ ОШИБКА: Не найден ADMIN_ID в переменных окружения!")
    print("В Railway Dashboard добавьте ADMIN_ID = ваш_id")
    exit(1)

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    print("❌ ОШИБКА: ADMIN_ID должен быть числом!")
    exit(1)

print("✅ Конфигурация загружена из переменных окружения Railway")


try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    print("❌ ОШИБКА: ADMIN_ID должен быть числом!")
    exit(1)

print("=" * 50)
print("🤖 Бот 'Универсальный Шпион' запускается...")
print(f"👑 Администратор: {ADMIN_ID}")
print("=" * 50)


bot = telebot.TeleBot(API_TOKEN, parse_mode='HTML')

# ============ ПРОВЕРКА ПОДПИСКИ ============
# Получаем настройки канала из .env
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@dimbub')
CHANNEL_URL = os.getenv('CHANNEL_URL', 'https://t.me/dimbub')
CHANNEL_ID = os.getenv('CHANNEL_ID', '-1003369490880')

# Преобразуем CHANNEL_ID в число если нужно
try:
    CHANNEL_ID = int(CHANNEL_ID)
except ValueError:
    pass

def check_subscription(user_id):
    """Проверяет, подписан ли пользователь на канал"""
    print(f"🔍 Проверяем подписку для {user_id}")
    
    # ДЛЯ ТЕСТА - закомментируйте return True когда будете готовы
    # return True  # ← ЗАКОММЕНТИРУЙТЕ ЭТУ СТРОЧКУ ДЛЯ ТЕСТА!
    
    try:
        # Убедитесь, что CHANNEL_ID правильный
        print(f"Канал ID: {CHANNEL_ID}, тип: {type(CHANNEL_ID)}")
        
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        status = member.status
        print(f"Статус пользователя {user_id}: {status}")
        
        is_subscribed = status in ['creator', 'administrator', 'member']
        print(f"Результат проверки: {is_subscribed}")
        
        return is_subscribed
        
    except Exception as e:
        print(f"❌ Ошибка проверки подписки: {type(e).__name__}: {e}")
        return False

def require_subscription(func):
    """Декоратор для проверки подписки - РАБОЧАЯ ВЕРСИЯ"""
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        print(f"\n{'='*50}")
        print(f"🔍 ДЕКОРАТОР: Проверяем {user_id} ({user_name})")
        print(f"Команда: {message.text}")
        
        # Проверяем подписку
        if not check_subscription(user_id):
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL),
                types.InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")
            )
            
            bot.send_message(
                message.chat.id,
                f"<b>📢 Для использования бота нужно подписаться на наш канал!</b>\n\n"
                f"Канал: {CHANNEL_USERNAME}\n"
                f"После подписки нажмите '✅ Я подписался'",
                reply_markup=keyboard
            )
            print(f"❌ Пользователь {user_id} не подписан, блокируем")
            print(f"{'='*50}\n")
            return  # НЕ вызываем функцию
        
        print(f"✅ Пользователь {user_id} подписан, выполняем команду")
        print(f"{'='*50}\n")
        return func(message, *args, **kwargs)  # Вызываем если есть подписка
    
    return wrapper

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def handle_check_subscription(call):
    """Обработчик кнопки "Я подписался" """
    user_id = call.from_user.id
    
    if check_subscription(user_id):
        bot.answer_callback_query(call.id, "✅ Спасибо за подписку!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        # Показываем основное меню
        bot.send_message(
            call.message.chat.id,
            "🎮 <b>Добро пожаловать!</b> Теперь вы можете использовать бота.",
            reply_markup=get_main_keyboard()
        )
    else:
        bot.answer_callback_query(
            call.id,
            "❌ Вы ещё не подписались!",
            show_alert=True
        )

# Структуры данных
global_stats = {
    'total_games': 0,
    'total_players': 0,
    'total_lobbies': 0,
    'all_spies_rounds': 0,
    'spy_wins': 0,
    'players_wins': 0,
    'active_lobbies': 0,
    'start_time': time.time()
}

lobbies = {}  # код_лобби -> данные лобби
user_to_lobby = {}  # user_id -> код_лобби
all_players = set()  # Все уникальные игроки
lobby_stats = {}  # код_лобби -> статистика лобби
chat_messages = defaultdict(deque)  # код_лобби -> последние сообщения
pending_chat_messages = {}  # user_id -> (код_лобби, сообщение)

# Списки слов по темам
THEMES = {
    'dota2': [
        "Pudge", "Invoker", "Juggernaut", "Lina", "Crystal Maiden", "Anti-Mage",
        "Axe", "Zeus", "Slark", "Phantom Assassin", "Terrorblade", "Sven",
        "Tiny", "Mirana", "Windranger", "Riki", "Bounty Hunter", "Ursa",
        "Shadow Fiend", "Templar Assassin", "Ember Spirit", "Storm Spirit",
        "Earth Spirit", "Io", "Chen", "Enchantress", "Meepo", "Arc Warden",
        "Techies", "Rubick", "Dark Willow", "Monkey King", "Mars", "Void Spirit",
        "Dawnbreaker", "Marci", "Primal Beast", "Muerta", "Drow Ranger", "Luna",
        "Medusa", "Naga Siren", "Phantom Lancer", "Razor", "Spectre", "Troll Warlord",
        "Viper", "Weaver", "Necrophos", "Queen of Pain", "Tinker"
    ],
    
    'clashroyale': [
        "Рыцарь", "Лучники", "Ведьма", "Принц", "Голем", "Пекка", "Гигант",
        "Лава-щенок", "Минер", "Баллон", "Волшебник", "Стрелок", "Мега-рыцарь",
        "Электро-дракон", "Ледяной дух", "Огненный дух", "Хог Райдер", 
        "Королева лучников", "Король-скелет", "Принцесса", "Ледяной голем",
        "Лава-гончая", "Бэби-дракон", "Валькирия", "Охотник за головами",
        "Тёмный принц", "Банда скелетов", "Ведьма-лекарь", "Электрический дух",
        "Ледяная ведьма", "Огненная собака", "Магнит", "Пекарь", "Каньонир",
        "Гоблинская бочка", "Летающий котел", "Летающий дракон", "Зомби",
        "Призрак", "Скелет-дракон", "Мини-пекка", "Гигантский скелет",
        "Трёхглавый дракон", "Колдун", "Ниндзя", "Пирамида", "Робот",
        "Супер-минион", "Танк", "Варвар"
    ],
    
    'brawlstars': [
        "Шэлли", "Кольт", "Булл", "Брок", "Эль Примо", "Роза", "Леон", "Спайк",
        "Кроу", "Джесси", "Нита", "Динамик", "Тик", "8-Бит", "Эмз", "Стью",
        "Поко", "Фрэнк", "Пенни", "Дэррил", "Карл", "Джекки", "Гейл", "Нанни",
        "Эдгар", "Байрон", "Гром", "Грифф", "Белл", "Эш", "Мэг", "Лола", "Фэнг",
        "Ева", "Джанет", "Отис", "Сэм", "Гас", "Бонни", "Честер", "Грей", "Мэнди",
        "Р-T", "Уиллоу", "Дуг", "Чак", "Мэйси", "Перл", "Ларри и Лори", "Хэнк"
    ],
    
    'locations': [
        "Больница", "Ресторан", "Школа", "Тюрьма", "Космическая станция",
        "Банк", "Супермаркет", "Аэропорт", "Отель", "Кинотеатр", "Театр",
        "Музей", "Библиотека", "Спортзал", "Бассейн", "Пляж", "Горнолыжный курорт",
        "Зоопарк", "Парк развлечений", "Церковь", "Торговый центр", "Стадион",
        "Подводная лодка", "Пустыня", "Джунгли", "Горы", "Пещера", "Замок",
        "Деревня", "Город", "Ферма", "Лаборатория", "Фабрика", "Строительная площадка",
        "Кладбище", "Остров", "Вокзал", "Метро", "Автобус", "Самолёт", "Корабль",
        "Поезд", "Такси", "Кафе", "Бар", "Ночной клуб", "Спа-салон", "Парикмахерская",
        "Сауна", "Боулинг"
    ]
}

# Вспомогательные функции
def is_admin(user_id):
    return user_id == ADMIN_ID

def generate_lobby_code():
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    numbers = '0123456789'
    while True:
        code = ''.join(random.choices(letters, k=3)) + ''.join(random.choices(numbers, k=3))
        if code not in lobbies:
            return code

def get_theme_name(theme_code):
    theme_names = {
        'dota2': '🎮 Dota 2 Герои',
        'clashroyale': '👑 Clash Royale',
        'brawlstars': '⭐ Brawl Stars',
        'locations': '📍 Локации',
        'custom': '✏️ Своя тема'
    }
    return theme_names.get(theme_code, 'Неизвестная тема')

def get_random_word(theme, custom_word=None):
    print(f"🔍 Выбираем слово для темы: {theme}")
    
    if theme == 'custom' and custom_word:
        print(f"✅ Возвращаем своё слово: {custom_word}")
        return custom_word
    
    if theme in THEMES:
        words = THEMES[theme]
        print(f"✅ Тема найдена, слов доступно: {len(words)}")
        
        if words:  # Проверяем, что список не пустой
            word = random.choice(words)
            print(f"✅ Выбрано слово: {word}")
            return word
        else:
            print(f"❌ Список слов для темы {theme} пуст!")
            return "Неизвестное слово"
    
    print(f"❌ Тема {theme} не найдена!")
    return "Неизвестное слово"

def save_global_stats():
    try:
        with open('global_stats.json', 'w', encoding='utf-8') as f:
            json.dump(global_stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения статистики: {e}")

def load_global_stats():
    global global_stats
    try:
        if os.path.exists('global_stats.json'):
            with open('global_stats.json', 'r', encoding='utf-8') as f:
                loaded_stats = json.load(f)

                for key in global_stats:
                    if key in loaded_stats:
                        global_stats[key] = loaded_stats[key]
    except Exception as e:
        print(f"Ошибка загрузки статистики: {e}")

def add_chat_message(lobby_code, user_name, message):
    if lobby_code not in chat_messages:
        chat_messages[lobby_code] = deque(maxlen=50)
    chat_messages[lobby_code].append({
        'user': user_name,
        'message': message,
        'time': time.time()
    })

def broadcast_to_lobby(lobby_code, message, keyboard=None, exclude_user=None):
    lobby = lobbies.get(lobby_code)
    if not lobby:
        return
    
    for player in lobby['players']:
        if exclude_user and player['id'] == exclude_user:
            continue
        try:
            if keyboard:
                bot.send_message(player['id'], message, reply_markup=keyboard)
            else:
                bot.send_message(player['id'], message)
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {player['id']}: {e}")

def broadcast_to_all(message, keyboard=None):
    for user_id in all_players:
        try:
            if keyboard:
                bot.send_message(user_id, message, reply_markup=keyboard)
            else:
                bot.send_message(user_id, message)
        except Exception as e:
            print(f"Ошибка массовой рассылки пользователю {user_id}: {e}")

def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("🎮 Создать лобби"),
        types.KeyboardButton("🔗 Войти в лобби"),
        types.KeyboardButton("📖 Правила"),
        types.KeyboardButton("ℹ️ Помощь")
    )
    return keyboard

def get_lobby_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("🎮 Меню лобби"),
        types.KeyboardButton("👥 Список игроков"),
        types.KeyboardButton("⚙️ Настройки темы"),
        types.KeyboardButton("💬 Чат лобби")
    )
    return keyboard

def get_game_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("🎮 Меню игры"),
        types.KeyboardButton("🕵️ Голосовать"),
        types.KeyboardButton("✏️ Изменить голос"),
        types.KeyboardButton("👁️ Посмотреть голоса"),
        types.KeyboardButton("💬 Чат лобби"),
        types.KeyboardButton("👥 Список игроков")
    )
    return keyboard

def create_lobby_menu(lobby_code):
    lobby = lobbies[lobby_code]
    keyboard = types.InlineKeyboardMarkup()
    
    if not lobby['game_started']:
        keyboard.add(
            types.InlineKeyboardButton("▶️ Начать игру", callback_data=f"start_game_{lobby_code}"),
            types.InlineKeyboardButton("⚙️ Настройки", callback_data=f"settings_{lobby_code}")
        )
        keyboard.add(
            types.InlineKeyboardButton(f"{'✅' if lobby['host_is_player'] else '❌'} Ведущий играет", 
                                      callback_data=f"toggle_host_{lobby_code}"),
            types.InlineKeyboardButton(f"{'✅' if lobby['auto_close'] else '❌'} Авто-закрытие", 
                                      callback_data=f"toggle_auto_{lobby_code}")
        )
    else:
        keyboard.add(
            types.InlineKeyboardButton("⏹️ Завершить игру", callback_data=f"end_game_{lobby_code}"),
            types.InlineKeyboardButton("📊 Статистика", callback_data=f"stats_{lobby_code}")
        )
    
    keyboard.add(
        types.InlineKeyboardButton("👥 Список игроков", callback_data=f"players_{lobby_code}"),
        types.InlineKeyboardButton("❌ Выйти из лобби", callback_data=f"leave_{lobby_code}")
    )
    
    return keyboard

def create_theme_keyboard(lobby_code):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    print(f"🔍 Создаю клавиатуру тем для лобби {lobby_code}")
    
    try:
        # Dota 2
        keyboard.add(
            types.InlineKeyboardButton("🎮 Dota 2 Герои", callback_data=f"theme_dota2_{lobby_code}")
        )
        print("✅ Добавлена кнопка Dota 2")
        
        # Clash Royale
        keyboard.add(
            types.InlineKeyboardButton("👑 Clash Royale", callback_data=f"theme_clashroyale_{lobby_code}")
        )
        print("✅ Добавлена кнопка Clash Royale")
        
        # Brawl Stars  
        keyboard.add(
            types.InlineKeyboardButton("⭐ Brawl Stars", callback_data=f"theme_brawlstars_{lobby_code}")
        )
        print("✅ Добавлена кнопка Brawl Stars")
        
        # Локации
        keyboard.add(
            types.InlineKeyboardButton("📍 Локации", callback_data=f"theme_locations_{lobby_code}")
        )
        print("✅ Добавлена кнопка Локации")
        
        # Своя тема
        keyboard.add(
            types.InlineKeyboardButton("✏️ Своя тема", callback_data=f"theme_custom_{lobby_code}")
        )
        
        # Назад
        keyboard.add(
            types.InlineKeyboardButton("🔙 Назад", callback_data=f"menu_{lobby_code}")
        )
        
    except Exception as e:
        print(f"❌ Ошибка создания клавиатуры: {e}")
    
    return keyboard

def create_voting_keyboard(lobby_code, user_id):
    lobby = lobbies[lobby_code]
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    for player in lobby['players']:
        if player['id'] != user_id and player['is_playing']:
            keyboard.add(
                types.InlineKeyboardButton(
                    f"👤 {player['name']}", 
                    callback_data=f"vote_{lobby_code}_{player['id']}"
                )
            )
    
    keyboard.add(
        types.InlineKeyboardButton("✖️ Никто", callback_data=f"vote_none_{lobby_code}"),
        types.InlineKeyboardButton("🔙 Назад", callback_data=f"game_menu_{lobby_code}")
    )
    
    return keyboard

def create_game_menu_keyboard(lobby_code):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("🕵️ Голосовать", callback_data=f"vote_menu_{lobby_code}"),
        types.InlineKeyboardButton("👁️ Посмотреть голоса", callback_data=f"view_votes_{lobby_code}")
    )
    keyboard.add(
        types.InlineKeyboardButton("📊 Статистика раунда", callback_data=f"round_stats_{lobby_code}"),
        types.InlineKeyboardButton("👥 Список игроков", callback_data=f"game_players_{lobby_code}")
    )
    keyboard.add(
        types.InlineKeyboardButton("❌ Сдаться", callback_data=f"surrender_{lobby_code}"),
        types.InlineKeyboardButton("🏁 Завершить раунд", callback_data=f"end_round_{lobby_code}")
    )
    return keyboard

def create_admin_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("📊 Глобальная статистика", callback_data="admin_stats"),
        types.InlineKeyboardButton("📢 Массовая рассылка", callback_data="admin_broadcast")
    )
    keyboard.add(
        types.InlineKeyboardButton("🎮 Активные лобби", callback_data="admin_lobbies"),
        types.InlineKeyboardButton("🔄 Сбросить статистику", callback_data="admin_reset")
    )
    keyboard.add(
        types.InlineKeyboardButton("💾 Сохранить данные", callback_data="admin_save"),
        types.InlineKeyboardButton("❌ Закрыть панель", callback_data="admin_close")
    )
    return keyboard

# Обработчики команд
@bot.message_handler(commands=['start', 'help'])
@require_subscription
def handle_start(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if user_id not in all_players:
        all_players.add(user_id)
        global_stats['total_players'] = len(all_players)
    
    welcome_text = f"""
<b>🎮 Добро пожаловать в игру "Универсальный Шпион"!</b>

{user_name}, вы находитесь в главном меню бота.

<b>Основные команды:</b>
/new - создать новое лобби
/join [код] - войти в лобби
/leave - покинуть лобби
/menu - меню лобби/игры
/chat [текст] - отправить сообщение в чат лобби
/rules - правила игры
/vote - голосовать за шпиона

<b>Используйте кнопки ниже или команды для навигации!</b>
    """
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.message_handler(commands=['new'])
@require_subscription
def handle_new(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Проверяем, находится ли пользователь уже в лобби
    if user_id in user_to_lobby:
        lobby_code = user_to_lobby[user_id]
        bot.send_message(message.chat.id, 
                        f"⚠️ Вы уже находитесь в лобби {lobby_code}. Покиньте его сначала командой /leave")
        return
    
    # Создаем новое лобби
    lobby_code = generate_lobby_code()
    
    lobbies[lobby_code] = {
        'host_id': user_id,
        'players': [{
            'id': user_id,
            'name': user_name,
            'is_host': True,
            'is_playing': True
        }],
        'game_started': False,
        'all_spies_mode': False,
        'spy_id': None,
        'word': None,
        'theme': 'dota2',
        'custom_word': None,
        'votes': {},
        'round_number': 0,
        'voting_history': [],
        'created_time': time.time(),
        'auto_close': True,
        'host_is_player': True
    }
    
    user_to_lobby[user_id] = lobby_code
    global_stats['total_lobbies'] += 1
    global_stats['active_lobbies'] = len(lobbies)
    
    # Создаем статистику для лобби
    lobby_stats[lobby_code] = {
        'games_played': 0,
        'spy_wins': 0,
        'players_wins': 0,
        'rounds_played': 0
    }
    
    # Информационное сообщение
    info_text = f"""
<b>✅ Лобби создано!</b>

Код лобби: <code>{lobby_code}</code>

Отправьте этот код друзьям, чтобы они могли присоединиться:
<code>/join {lobby_code}</code>

Или они могут просто нажать кнопку "🔗 Войти в лобби" и ввести код.

<b>Игроки в лобби (1/7):</b>
👑 {user_name} (Ведущий)

<b>Используйте кнопки ниже для управления лобби:</b>
    """
    
    bot.send_message(message.chat.id, info_text, reply_markup=get_lobby_keyboard())
    bot.send_message(message.chat.id, "🎮 Меню лобби:", reply_markup=create_lobby_menu(lobby_code))
    
    save_global_stats()

@bot.message_handler(commands=['join'])
@require_subscription
def handle_join(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Проверяем, находится ли пользователь уже в лобби
    if user_id in user_to_lobby:
        lobby_code = user_to_lobby[user_id]
        bot.send_message(message.chat.id, 
                        f"⚠️ Вы уже находитесь в лобби {lobby_code}. Покиньте его сначала командой /leave")
        return
    
    # Получаем код лобби из сообщения
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, 
                        "⚠️ Укажите код лобби!\nПример: <code>/join ABC123</code>")
        return
    
    lobby_code = parts[1].upper().strip()
    
    # Проверяем существование лобби
    if lobby_code not in lobbies:
        bot.send_message(message.chat.id, 
                        f"⚠️ Лобби с кодом <code>{lobby_code}</code> не найдено!")
        return
    
    lobby = lobbies[lobby_code]
    
    # Проверяем, не начата ли уже игра
    if lobby['game_started']:
        bot.send_message(message.chat.id, 
                        f"⚠️ Игра в лобби {lobby_code} уже начата! Присоединиться нельзя.")
        return
    
    # Проверяем количество игроков
    if len(lobby['players']) >= 7:
        bot.send_message(message.chat.id, 
                        f"⚠️ В лобби {lobby_code} уже максимальное количество игроков (7/7)!")
        return
    
    # Проверяем, не находится ли игрок уже в лобби
    for player in lobby['players']:
        if player['id'] == user_id:
            bot.send_message(message.chat.id, 
                            f"⚠️ Вы уже в этом лобби!")
            return
    
    # Добавляем игрока в лобби
    lobby['players'].append({
        'id': user_id,
        'name': user_name,
        'is_host': False,
        'is_playing': True
    })
    
    user_to_lobby[user_id] = lobby_code
    
    # Обновляем статистику
    if user_id not in all_players:
        all_players.add(user_id)
        global_stats['total_players'] = len(all_players)
    
    # Отправляем сообщение новому игроку
    players_list = "\n".join([f"{'👑' if p['is_host'] else '👤'} {p['name']}" 
                             for p in lobby['players']])
    
    welcome_text = f"""
<b>✅ Вы присоединились к лобби {lobby_code}!</b>

<b>Игроки в лобби ({len(lobby['players'])}/7):</b>
{players_list}

<b>Ведущий:</b> {next(p['name'] for p in lobby['players'] if p['is_host'])}

<b>Используйте кнопки ниже для взаимодействия:</b>
    """
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_lobby_keyboard())
    bot.send_message(message.chat.id, "🎮 Меню лобби:", reply_markup=create_lobby_menu(lobby_code))
    
    # Уведомляем других игроков
    broadcast_to_lobby(lobby_code, 
                      f"👤 <b>{user_name}</b> присоединился к лобби!\nТеперь игроков: {len(lobby['players'])}/7",
                      exclude_user=user_id)
    
    save_global_stats()

@bot.message_handler(commands=['leave'])
def handle_leave(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Проверяем, находится ли пользователь в лобби
    if user_id not in user_to_lobby:
        bot.send_message(message.chat.id, "⚠️ Вы не находитесь в лобби!")
        return
    
    lobby_code = user_to_lobby[user_id]
    lobby = lobbies[lobby_code]
    
    # Если пользователь - ведущий
    is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
    
    if is_host:
        # Ведущий покидает лобби - закрываем лобби
        for player in lobby['players']:
            if player['id'] != user_id:
                try:
                    bot.send_message(player['id'], 
                                   f"⚠️ Лобби {lobby_code} закрыто, потому что ведущий покинул игру.")
                except:
                    pass
            # Удаляем маппинг
            if player['id'] in user_to_lobby:
                del user_to_lobby[player['id']]
        
        # Удаляем лобби
        del lobbies[lobby_code]
        del lobby_stats[lobby_code]
        if lobby_code in chat_messages:
            del chat_messages[lobby_code]
        
        global_stats['active_lobbies'] = len(lobbies)
        
        bot.send_message(message.chat.id, "✅ Вы закрыли лобби и вышли из игры.")
        
    else:
        # Обычный игрок покидает лобби
        lobby['players'] = [p for p in lobby['players'] if p['id'] != user_id]
        del user_to_lobby[user_id]
        
        bot.send_message(message.chat.id, f"✅ Вы покинули лобби {lobby_code}.")
        
        # Уведомляем других игроков
        broadcast_to_lobby(lobby_code, 
                          f"👤 <b>{user_name}</b> покинул лобби.\nОсталось игроков: {len(lobby['players'])}/7",
                          exclude_user=user_id)
        
        # Если игра начата и игроков стало меньше 3, завершаем игру
        if lobby['game_started'] and len(lobby['players']) < 3:
            lobby['game_started'] = False
            broadcast_to_lobby(lobby_code, 
                              "⚠️ Игра завершена, потому что осталось меньше 3 игроков.")
    
    # Если в лобби не осталось игроков, удаляем его
    if not lobby['players']:
        del lobbies[lobby_code]
        del lobby_stats[lobby_code]
        if lobby_code in chat_messages:
            del chat_messages[lobby_code]
        global_stats['active_lobbies'] = len(lobbies)
    
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=get_main_keyboard())
    save_global_stats()

@bot.message_handler(commands=['menu'])
@require_subscription
def handle_menu(message):
    user_id = message.from_user.id
    
    if user_id not in user_to_lobby:
        bot.send_message(message.chat.id, "⚠️ Вы не находитесь в лобби!")
        return
    
    lobby_code = user_to_lobby[user_id]
    lobby = lobbies[lobby_code]
    
    if lobby['game_started']:
        bot.send_message(message.chat.id, "🎮 Меню игры:", reply_markup=create_game_menu_keyboard(lobby_code))
    else:
        bot.send_message(message.chat.id, "🎮 Меню лобби:", reply_markup=create_lobby_menu(lobby_code))

@bot.message_handler(commands=['rules'])
def handle_rules(message):
    rules_text = """
<b>📖 Правила игры "Шпион":</b>

1. <b>Цель игры:</b>
   • Игроки получают слово из выбранной темы
   • Один из игроков (шпион) НЕ знает слово
   • Шпион должен скрывать, что он не знает слово
   • Остальные игроки должны вычислить шпиона

2. <b>Ход игры:</b>
   • Каждый раунд выбирается новое слово и шпион
   • Игроки по очереди описывают слово, не называя его прямо
   • После обсуждения проходит голосование за шпиона
   • Если шпиона вычислили - побеждают игроки
   • Если шпион остался незамеченным - побеждает шпион

3. <b>Особенности:</b>
   • Каждый 5-й раунд - секретный (все игроки шпионы)
   • Ведущий может участвовать в игре или только наблюдать
   • Максимум 7 игроков в лобби

4. <b>Как играть:</b>
   • Создайте лобби командой /new
   • Пригласите друзей с помощью кода лобби
   • Выберите тему игры
   • Начните игру когда все готовы

<b>Удачи в игре! 🎮</b>
    """
    bot.send_message(message.chat.id, rules_text)

@bot.message_handler(commands=['chat'])
def handle_chat(message):
    user_id = message.from_user.id
    
    if user_id not in user_to_lobby:
        bot.send_message(message.chat.id, "⚠️ Вы не находитесь в лобби!")
        return
    
    # Получаем текст сообщения
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, 
                        "⚠️ Укажите текст сообщения!\nПример: <code>/chat Привет всем!</code>")
        return
    
    chat_message = parts[1]
    lobby_code = user_to_lobby[user_id]
    lobby = lobbies[lobby_code]
    user_name = message.from_user.first_name
    
    # Добавляем сообщение в историю
    add_chat_message(lobby_code, user_name, chat_message)
    
    # Отправляем подтверждение
    bot.send_message(message.chat.id, "✅ Сообщение отправлено в чат лобби!")
    
    # Рассылаем сообщение другим игрокам
    broadcast_to_lobby(lobby_code, 
                      f"💬 <b>{user_name}:</b> {chat_message}",
                      exclude_user=user_id)

@bot.message_handler(commands=['vote'])
def handle_vote(message):
    user_id = message.from_user.id
    
    if user_id not in user_to_lobby:
        bot.send_message(message.chat.id, "⚠️ Вы не находитесь в лобби!")
        return
    
    lobby_code = user_to_lobby[user_id]
    lobby = lobbies[lobby_code]
    
    if not lobby['game_started']:
        bot.send_message(message.chat.id, "⚠️ Игра еще не начата!")
        return
    
    # Показываем клавиатуру для голосования
    bot.send_message(message.chat.id, 
                    "🕵️ <b>Голосование за шпиона:</b>\nВыберите игрока, который по вашему мнению является шпионом:",
                    reply_markup=create_voting_keyboard(lobby_code, user_id))

# Админ команды
@bot.message_handler(commands=['waykegoat'])
def handle_admin(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "⚠️ У вас нет прав администратора!")
        return
    
    admin_text = """
<b>🔧 Админ-панель "Универсальный Шпион"</b>

Выберите действие:
    """
    bot.send_message(message.chat.id, admin_text, reply_markup=create_admin_keyboard())

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "⚠️ У вас нет прав администратора!")
        return
    
    # Получаем текст рассылки
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, 
                        "⚠️ Укажите текст для рассылки!\nПример: <code>/broadcast Важное обновление!</code>")
        return
    
    broadcast_text = parts[1]
    bot.send_message(message.chat.id, f"📢 Начинаю массовую рассылку: {broadcast_text}")
    
    # Выполняем рассылку
    broadcast_to_all(f"📢 <b>Важное сообщение от администратора:</b>\n\n{broadcast_text}")
    
    bot.send_message(message.chat.id, f"✅ Рассылка завершена! Отправлено {len(all_players)} пользователям.")

# Обработчик текстовых сообщений (для кнопок)
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text
    
    if text == "🎮 Создать лобби":
        handle_new(message)
    
    elif text == "🔗 Войти в лобби":
        bot.send_message(message.chat.id, 
                        "Введите код лобби для входа:\nПример: <code>ABC123</code>")
        bot.register_next_step_handler(message, process_join_code)
    
    elif text == "📖 Правила":
        handle_rules(message)
    
    elif text == "ℹ️ Помощь":
        handle_start(message)
    
    elif text == "🎮 Меню лобби":
        handle_menu(message)
    
    elif text == "👥 Список игроков":
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            lobby = lobbies[lobby_code]
            
            players_list = "\n".join([
                f"{'👑' if p['is_host'] else '👤'} {p['name']}" + 
                ("" if lobby['game_started'] else f" {'🎮' if p['is_playing'] else '👁️'}")
                for p in lobby['players']
            ])
            
            status = "🟢 Игра начата" if lobby['game_started'] else "🟡 Ожидание"
            bot.send_message(message.chat.id, 
                           f"<b>👥 Игроки в лобби {lobby_code} ({len(lobby['players'])}/7):</b>\n\n{players_list}\n\nСтатус: {status}")
    
    elif text == "⚙️ Настройки темы":
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            lobby = lobbies[lobby_code]
            
            # Проверяем, является ли пользователь ведущим
            is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
            
            if not is_host:
                bot.send_message(message.chat.id, 
                               f"⚠️ Только ведущий может менять настройки темы!")
                return
            
            current_theme = get_theme_name(lobby['theme'])
            if lobby['theme'] == 'custom' and lobby['custom_word']:
                current_word = f"\nТекущее слово: <code>{lobby['custom_word']}</code>"
            else:
                current_word = ""
            
            theme_text = f"""
<b>⚙️ Настройки темы:</b>

Текущая тема: {current_theme}
{current_word}

Выберите новую тему:
            """
            bot.send_message(message.chat.id, theme_text, reply_markup=create_theme_keyboard(lobby_code))
    
    elif text == "💬 Чат лобби":
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            
            # Показываем историю чата
            if lobby_code in chat_messages and chat_messages[lobby_code]:
                history = ""
                for msg in list(chat_messages[lobby_code])[-10:]:  # Последние 10 сообщений
                    time_str = datetime.fromtimestamp(msg['time']).strftime('%H:%M')
                    history += f"<b>{msg['user']}</b> ({time_str}): {msg['message']}\n"
                
                bot.send_message(message.chat.id, 
                               f"<b>💬 История чата (последние 10 сообщений):</b>\n\n{history}")
            else:
                bot.send_message(message.chat.id, "💬 В чате пока нет сообщений.")
    
    elif text == "🎮 Меню игры":
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            lobby = lobbies[lobby_code]
            
            if lobby['game_started']:
                bot.send_message(message.chat.id, "🎮 Меню игры:", reply_markup=create_game_menu_keyboard(lobby_code))
            else:
                bot.send_message(message.chat.id, "⚠️ Игра еще не начата!")
    
    elif text == "🕵️ Голосовать":
        handle_vote(message)
    
    elif text == "✏️ Изменить голос":
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            lobby = lobbies[lobby_code]
            
            if not lobby['game_started']:
                bot.send_message(message.chat.id, "⚠️ Игра еще не начата!")
                return
            
            # Удаляем предыдущий голос
            if user_id in lobby['votes']:
                del lobby['votes'][user_id]
                bot.send_message(message.chat.id, "✅ Ваш предыдущий голос удален.")
            
            # Показываем клавиатуру для нового голоса
            bot.send_message(message.chat.id, 
                            "🕵️ <b>Голосование за шпиона:</b>\nВыберите игрока, который по вашему мнению является шпионом:",
                            reply_markup=create_voting_keyboard(lobby_code, user_id))
    
    elif text == "👁️ Посмотреть голоса":
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            lobby = lobbies[lobby_code]
            
            if not lobby['game_started']:
                bot.send_message(message.chat.id, "⚠️ Игра еще не начата!")
                return
            
            # Показываем текущие голоса
            votes_text = "<b>👁️ Текущие голоса:</b>\n\n"
            
            if not lobby['votes']:
                votes_text += "Пока никто не проголосовал."
            else:
                # Группируем голоса по игрокам
                vote_counts = defaultdict(list)
                for voter_id, voted_id in lobby['votes'].items():
                    voter_name = next((p['name'] for p in lobby['players'] if p['id'] == voter_id), "Неизвестный")
                    if voted_id == 'none':
                        vote_counts['Никто'].append(voter_name)
                    else:
                        voted_name = next((p['name'] for p in lobby['players'] if p['id'] == voted_id), "Неизвестный")
                        vote_counts[voted_name].append(voter_name)
                
                for voted_player, voters in vote_counts.items():
                    votes_text += f"<b>{voted_player}:</b> {len(voters)} голосов\n"
                    if len(voters) <= 5:  # Показываем имена, если их не много
                        votes_text += f"Проголосовали: {', '.join(voters)}\n"
                    votes_text += "\n"
            
            bot.send_message(message.chat.id, votes_text)
    
    else:
        # Если пользователь в лобби, предлагаем отправить сообщение в чат
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            bot.send_message(message.chat.id, 
                           f"Хотите отправить это сообщение в чат лобби?\n\n<code>{text}</code>",
                           reply_markup=types.InlineKeyboardMarkup().add(
                               types.InlineKeyboardButton("✅ Да", callback_data=f"send_chat_{lobby_code}_{text[:100]}"),
                               types.InlineKeyboardButton("❌ Нет", callback_data="cancel_chat")
                           ))
        else:
            bot.send_message(message.chat.id, 
                           "Используйте кнопки ниже или команды для навигации:", 
                           reply_markup=get_main_keyboard())

def process_join_code(message):
    user_id = message.from_user.id
    lobby_code = message.text.upper().strip()
    
    # Проверяем формат кода (3 буквы + 3 цифры)
    if len(lobby_code) != 6 or not lobby_code[:3].isalpha() or not lobby_code[3:].isdigit():
        bot.send_message(message.chat.id, 
                        "⚠️ Неверный формат кода! Код должен состоять из 3 букв и 3 цифр (например: ABC123)")
        return
    
    # Пытаемся присоединиться
    if lobby_code in lobbies:
        handle_join(types.Message(
            message_id=message.message_id,
            from_user=message.from_user,
            date=message.date,
            chat=message.chat,
            content_type='text',
            options={},
            json_string='',
            text=f"/join {lobby_code}"
        ))
    else:
        bot.send_message(message.chat.id, f"⚠️ Лобби с кодом <code>{lobby_code}</code> не найдено!")

# Обработчик callback-запросов
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    
    # Обработка меню лобби
    if data.startswith('menu_'):
        lobby_code = data[5:]
        if lobby_code in lobbies and user_id in user_to_lobby and user_to_lobby[user_id] == lobby_code:
            bot.edit_message_text("🎮 Меню лобби:", 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=create_lobby_menu(lobby_code))
    
    # Обработка начала игры
    elif data.startswith('start_game_'):
        lobby_code = data[11:]
        if lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            
            # Проверяем, является ли пользователь ведущим
            is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
            if not is_host:
                bot.answer_callback_query(call.id, "⚠️ Только ведущий может начать игру!")
                return
            
            # Проверяем количество игроков
            playing_players = [p for p in lobby['players'] if p['is_playing']]
            if len(playing_players) < 3:
                bot.answer_callback_query(call.id, "⚠️ Для начала игры нужно минимум 3 игрока!")
                return
            
            # Начинаем игру
            lobby['game_started'] = True
            lobby['round_number'] = 1
            global_stats['total_games'] += 1
            
            # Начинаем первый раунд
            start_round(lobby_code)
            
            bot.answer_callback_query(call.id, "✅ Игра начата!")
    
    # Обработка настроек
    elif data.startswith('settings_'):
        lobby_code = data[10:]
        if lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            
            # Проверяем, является ли пользователь ведущим
            is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
            if not is_host:
                bot.answer_callback_query(call.id, "⚠️ Только ведущий может менять настройки!")
                return
            
            current_theme = get_theme_name(lobby['theme'])
            if lobby['theme'] == 'custom' and lobby['custom_word']:
                current_word = f"\nТекущее слово: <code>{lobby['custom_word']}</code>"
            else:
                current_word = ""
            
            theme_text = f"""
<b>⚙️ Настройки темы:</b>

Текущая тема: {current_theme}
{current_word}

Выберите новую тему:
            """
            bot.edit_message_text(theme_text, 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=create_theme_keyboard(lobby_code))
    
    # Обработка переключения роли ведущего
    elif data.startswith('toggle_host_'):
        lobby_code = data[12:]
        if lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            
            # Проверяем, является ли пользователь ведущим
            is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
            if not is_host:
                bot.answer_callback_query(call.id, "⚠️ Только ведущий может менять эту настройку!")
                return
            
            # Переключаем настройку
            lobby['host_is_player'] = not lobby['host_is_player']
            
            # Обновляем статус ведущего в списке игроков
            for player in lobby['players']:
                if player['is_host']:
                    player['is_playing'] = lobby['host_is_player']
            
            bot.edit_message_reply_markup(call.message.chat.id, 
                                         call.message.message_id,
                                         reply_markup=create_lobby_menu(lobby_code))
            bot.answer_callback_query(call.id, 
                                     f"✅ Ведущий теперь {'участвует' if lobby['host_is_player'] else 'не участвует'} в игре!")
    
    # Обработка переключения авто-закрытия
    elif data.startswith('toggle_auto_'):
        lobby_code = data[12:]
        if lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            
            # Проверяем, является ли пользователь ведущим
            is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
            if not is_host:
                bot.answer_callback_query(call.id, "⚠️ Только ведущий может менять эту настройку!")
                return
            
            # Переключаем настройку
            lobby['auto_close'] = not lobby['auto_close']
            bot.edit_message_reply_markup(call.message.chat.id, 
                                         call.message.message_id,
                                         reply_markup=create_lobby_menu(lobby_code))
            bot.answer_callback_query(call.id, 
                                     f"✅ Авто-закрытие {'включено' if lobby['auto_close'] else 'выключено'}!")
    
    # Обработка выбора темы
        # Обработка выбора темы
    elif data.startswith('theme_'):
        print(f"\n{'='*50}")
        print(f"🔍 CALLBACK ТЕМЫ: {data}")
        
        parts = data.split('_')
        print(f"🔍 Части: {parts}")
        
        if len(parts) >= 3:
            theme = parts[1]
            lobby_code = '_'.join(parts[2:])
            
            print(f"🔍 Тема: {theme}, Лобби: {lobby_code}")
            print(f"🔍 Доступные темы: {list(THEMES.keys())}")
            
            # ВАЖНО: Проверяем существует ли тема
            if theme not in THEMES and theme != 'custom':
                print(f"❌ ОШИБКА: Тема '{theme}' не найдена!")
                bot.answer_callback_query(call.id, "❌ Ошибка темы!")
                return
            
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                print(f"✅ Лобби найдено, ID: {lobby_code}")
                
                # Проверяем, является ли пользователь ведущим
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    print(f"❌ Пользователь {user_id} не ведущий")
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может менять тему!")
                    return
                
                print(f"✅ Пользователь {user_id} - ведущий")
                
                # Устанавливаем тему
                lobby['theme'] = theme
                print(f"✅ Установлена тема: {theme}")
                
                # Если выбрана своя тема, запрашиваем слово
                if theme == 'custom':
                    print(f"🔍 Выбрана своя тема, запрашиваем слово")
                    msg = bot.send_message(call.message.chat.id, 
                                         "✏️ Введите слово для игры:")
                    
                    def process_custom_word(message):
                        if message.text:
                            lobby['custom_word'] = message.text.strip()
                            print(f"✅ Установлено своё слово: {lobby['custom_word']}")
                            bot.send_message(message.chat.id, 
                                           f"✅ Слово установлено: <code>{lobby['custom_word']}</code>")
                            bot.send_message(message.chat.id, 
                                           "🎮 Меню лобби:", 
                                           reply_markup=create_lobby_menu(lobby_code))
                    
                    bot.register_next_step_handler(msg, process_custom_word)
                    bot.answer_callback_query(call.id, "✏️ Введите слово")
                    
                else:
                    # Для обычных тем
                    theme_name = get_theme_name(theme)
                    print(f"✅ Устанавливаем тему: {theme_name}")
                    
                    bot.answer_callback_query(call.id, f"✅ Тема: {theme_name}")
                    bot.edit_message_text(
                        f"✅ Тема установлена: {theme_name}\n\n🎮 Меню лобби:", 
                        call.message.chat.id, 
                        call.message.message_id,
                        reply_markup=create_lobby_menu(lobby_code)
                    )
            else:
                print(f"❌ Лобби {lobby_code} не найдено!")
                bot.answer_callback_query(call.id, "❌ Ошибка: лобби не найдено")
    
    # Обработка голосования
    elif data.startswith('vote_'):
        parts = data.split('_')
        if len(parts) >= 2:
            lobby_code = parts[-1]
            
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                if not lobby['game_started']:
                    bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
                    return
                
                # Проверяем, может ли пользователь голосовать
                player = next((p for p in lobby['players'] if p['id'] == user_id), None)
                if not player or not player['is_playing']:
                    bot.answer_callback_query(call.id, "⚠️ Вы не можете голосовать!")
                    return
                
                # Обрабатываем голос
                if parts[1] == 'none':
                    lobby['votes'][user_id] = 'none'
                    bot.answer_callback_query(call.id, "✅ Вы проголосовали за НИКОГО")
                else:
                    voted_id = int(parts[1])
                    
                    # Проверяем, существует ли игрок
                    voted_player = next((p for p in lobby['players'] if p['id'] == voted_id), None)
                    if not voted_player or not voted_player['is_playing']:
                        bot.answer_callback_query(call.id, "⚠️ Нельзя проголосовать за этого игрока!")
                        return
                    
                    lobby['votes'][user_id] = voted_id
                    bot.answer_callback_query(call.id, f"✅ Вы проголосовали за {voted_player['name']}")
                
                # Проверяем, все ли проголосовали
                check_voting_complete(lobby_code)
    
    # Обработка меню игры
    elif data.startswith('game_menu_'):
        lobby_code = data[10:]
        if lobby_code in lobbies and user_id in user_to_lobby and user_to_lobby[user_id] == lobby_code:
            bot.edit_message_text("🎮 Меню игры:", 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=create_game_menu_keyboard(lobby_code))
    
    # Обработка меню голосования
    elif data.startswith('vote_menu_'):
        lobby_code = data[10:]
        if lobby_code in lobbies and user_id in user_to_lobby and user_to_lobby[user_id] == lobby_code:
            lobby = lobbies[lobby_code]
            
            if not lobby['game_started']:
                bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
                return
            
            bot.edit_message_text("🕵️ <b>Голосование за шпиона:</b>\nВыберите игрока, который по вашему мнению является шпионом:", 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=create_voting_keyboard(lobby_code, user_id))
    
    # Обработка просмотра голосов
    elif data.startswith('view_votes_'):
        lobby_code = data[11:]
        if lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            
            if not lobby['game_started']:
                bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
                return
            
            # Показываем текущие голоса
            votes_text = "<b>👁️ Текущие голоса:</b>\n\n"
            
            if not lobby['votes']:
                votes_text += "Пока никто не проголосовал."
            else:
                # Группируем голоса по игрокам
                vote_counts = defaultdict(list)
                for voter_id, voted_id in lobby['votes'].items():
                    voter_name = next((p['name'] for p in lobby['players'] if p['id'] == voter_id), "Неизвестный")
                    if voted_id == 'none':
                        vote_counts['Никто'].append(voter_name)
                    else:
                        voted_name = next((p['name'] for p in lobby['players'] if p['id'] == voted_id), "Неизвестный")
                        vote_counts[voted_name].append(voter_name)
                
                for voted_player, voters in vote_counts.items():
                    votes_text += f"<b>{voted_player}:</b> {len(voters)} голосов\n"
                    if len(voters) <= 5:
                        votes_text += f"Проголосовали: {', '.join(voters)}\n"
                    votes_text += "\n"
            
            bot.edit_message_text(votes_text, 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=types.InlineKeyboardMarkup().add(
                                    types.InlineKeyboardButton("🔙 Назад", callback_data=f"game_menu_{lobby_code}")
                                ))
    
    # Обработка завершения раунда
    elif data.startswith('end_round_'):
        lobby_code = data[10:]
        if lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            
            # Проверяем, является ли пользователь ведущим
            is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
            if not is_host:
                bot.answer_callback_query(call.id, "⚠️ Только ведущий может завершить раунд!")
                return
            
            # Завершаем раунд принудительно
            end_round(lobby_code)
            bot.answer_callback_query(call.id, "✅ Раунд завершен!")
    
    # Обработка выхода из лобби
    elif data.startswith('leave_'):
        lobby_code = data[6:]
        if lobby_code in lobbies and user_id in user_to_lobby and user_to_lobby[user_id] == lobby_code:
            # Вызываем команду /leave
            handle_leave(types.Message(
                message_id=call.message.message_id,
                from_user=call.from_user,
                date=call.message.date,
                chat=call.message.chat,
                content_type='text',
                options={},
                json_string='',
                text='/leave'
            ))
    
    # Обработка отправки сообщения в чат
    elif data.startswith('send_chat_'):
        parts = data.split('_', 3)
        if len(parts) == 4:
            lobby_code = parts[2]
            chat_message = parts[3]
            
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                user_name = call.from_user.first_name
                
                # Добавляем сообщение в историю
                add_chat_message(lobby_code, user_name, chat_message)
                
                # Рассылаем сообщение другим игрокам
                broadcast_to_lobby(lobby_code, 
                                  f"💬 <b>{user_name}:</b> {chat_message}",
                                  exclude_user=user_id)
                
                bot.answer_callback_query(call.id, "✅ Сообщение отправлено в чат!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
    
    elif data == 'cancel_chat':
        bot.answer_callback_query(call.id, "❌ Сообщение не отправлено")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    # Админ-панель
    elif data == 'admin_stats':
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "⚠️ У вас нет прав администратора!")
            return
        
        uptime = time.time() - global_stats['start_time']
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        
        stats_text = f"""
<b>📊 Глобальная статистика бота:</b>

🎮 Всего игр: {global_stats['total_games']}
👥 Уникальных игроков: {global_stats['total_players']}
🏠 Создано лобби: {global_stats['total_lobbies']}
🕵️ Секретных раундов: {global_stats['all_spies_rounds']}

🏆 Побед шпионов: {global_stats['spy_wins']}
🎯 Побед игроков: {global_stats['players_wins']}

🔴 Активных лобби: {global_stats['active_lobbies']}
⏱️ Время работы: {hours}ч {minutes}м

📅 Статистика сохранена: {datetime.now().strftime('%d.%m.%Y %H:%M')}
        """
        
        bot.edit_message_text(stats_text, 
                            call.message.chat.id, 
                            call.message.message_id,
                            reply_markup=create_admin_keyboard())
    
    elif data == 'admin_broadcast':
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "⚠️ У вас нет прав администратора!")
            return
        
        bot.send_message(call.message.chat.id, 
                        "📢 Введите текст для массовой рассылки:")
        
        def process_broadcast(message):
            broadcast_text = message.text
            bot.send_message(message.chat.id, 
                           f"📢 Начинаю массовую рассылку: {broadcast_text}")
            
            # Выполняем рассылку
            success_count = 0
            fail_count = 0
            
            for user_id in all_players:
                try:
                    bot.send_message(user_id, 
                                   f"📢 <b>Важное сообщение от администратора:</b>\n\n{broadcast_text}")
                    success_count += 1
                except Exception as e:
                    print(f"Ошибка рассылки пользователю {user_id}: {e}")
                    fail_count += 1
            
            bot.send_message(message.chat.id, 
                           f"✅ Рассылка завершена!\nУспешно: {success_count}\nНе удалось: {fail_count}")
        
        bot.register_next_step_handler(call.message, process_broadcast)
    
    elif data == 'admin_lobbies':
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "⚠️ У вас нет прав администратора!")
            return
        
        if not lobbies:
            lobbies_text = "🔴 Активных лобби нет"
        else:
            lobbies_text = "<b>🎮 Активные лобби:</b>\n\n"
            for code, lobby in lobbies.items():
                created_time = datetime.fromtimestamp(lobby['created_time']).strftime('%H:%M')
                players_count = len(lobby['players'])
                status = "🟢 Игра" if lobby['game_started'] else "🟡 Ожидание"
                
                lobbies_text += f"<code>{code}</code> - {players_count}/7 игроков\n"
                lobbies_text += f"Ведущий: {lobby['players'][0]['name']}\n"
                lobbies_text += f"Создано: {created_time} | Статус: {status}\n"
                lobbies_text += f"Раунд: {lobby['round_number']}\n"
                lobbies_text += "─" * 20 + "\n"
        
        bot.edit_message_text(lobbies_text, 
                            call.message.chat.id, 
                            call.message.message_id,
                            reply_markup=create_admin_keyboard())
    
    elif data == 'admin_reset':
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "⚠️ У вас нет прав администратора!")
            return
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("✅ Да, сбросить", callback_data="admin_reset_confirm"),
            types.InlineKeyboardButton("❌ Нет, отмена", callback_data="admin_stats")
        )
        
        bot.edit_message_text("⚠️ <b>Вы уверены, что хотите сбросить всю статистику?</b>\n\nЭто действие нельзя отменить!", 
                            call.message.chat.id, 
                            call.message.message_id,
                            reply_markup=keyboard)
    
    elif data == 'admin_reset_confirm':
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "⚠️ У вас нет прав администратора!")
            return
        
        # Сбрасываем статистику
        global_stats.update({
            'total_games': 0,
            'total_players': 0,
            'total_lobbies': 0,
            'all_spies_rounds': 0,
            'spy_wins': 0,
            'players_wins': 0,
            'active_lobbies': 0,
            'start_time': time.time()
        })
        
        all_players.clear()
        
        bot.answer_callback_query(call.id, "✅ Статистика сброшена!")
        bot.edit_message_text("✅ Статистика успешно сброшена!", 
                            call.message.chat.id, 
                            call.message.message_id,
                            reply_markup=create_admin_keyboard())
    
    elif data == 'admin_save':
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "⚠️ У вас нет прав администратора!")
            return
        
        save_global_stats()
        bot.answer_callback_query(call.id, "✅ Данные сохранены!")
    
    elif data == 'admin_close':
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "⚠️ У вас нет прав администратора!")
            return
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    # Обработка других callback-действий
    elif data.startswith('end_game_'):
        lobby_code = data[9:]
        if lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            
            # Проверяем, является ли пользователь ведущим
            is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
            if not is_host:
                bot.answer_callback_query(call.id, "⚠️ Только ведущий может завершить игру!")
                return
            
            # Завершаем игру
            lobby['game_started'] = False
            lobby['votes'] = {}
            
            # Рассылаем уведомление
            broadcast_to_lobby(lobby_code, 
                              "⚠️ <b>Игра завершена ведущим!</b>\n\nВсе игроки возвращены в лобби.")
            
            bot.answer_callback_query(call.id, "✅ Игра завершена!")
            bot.edit_message_text("✅ Игра завершена! Игроки возвращены в лобби.", 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=create_lobby_menu(lobby_code))
    
    elif data.startswith('stats_'):
        lobby_code = data[6:]
        if lobby_code in lobbies and lobby_code in lobby_stats:
            stats = lobby_stats[lobby_code]
            stats_text = f"""
<b>📊 Статистика лобби {lobby_code}:</b>

🎮 Сыграно игр: {stats['games_played']}
🕵️ Побед шпионов: {stats['spy_wins']}
🎯 Побед игроков: {stats['players_wins']}
🔁 Сыграно раундов: {stats['rounds_played']}

Текущий раунд: {lobbies[lobby_code]['round_number']}
            """
            bot.edit_message_text(stats_text, 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=types.InlineKeyboardMarkup().add(
                                    types.InlineKeyboardButton("🔙 Назад", callback_data=f"menu_{lobby_code}")
                                ))
    
    elif data.startswith('players_'):
        lobby_code = data[8:]
        if lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            
            players_list = "\n".join([
                f"{'👑' if p['is_host'] else '👤'} {p['name']}" + 
                ("" if not lobby['game_started'] else f" {'🎮' if p['is_playing'] else '👁️'}")
                for p in lobby['players']
            ])
            
            status = "🟢 Игра начата" if lobby['game_started'] else "🟡 Ожидание"
            players_text = f"""
<b>👥 Игроки в лобби {lobby_code} ({len(lobby['players'])}/7):</b>

{players_list}

Статус: {status}
            """
            bot.edit_message_text(players_text, 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=types.InlineKeyboardMarkup().add(
                                    types.InlineKeyboardButton("🔙 Назад", callback_data=f"menu_{lobby_code}")
                                ))
    
    elif data.startswith('game_players_'):
        lobby_code = data[13:]
        if lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            
            players_list = "\n".join([
                f"{'👑' if p['is_host'] else '👤'} {p['name']} {'🎮' if p['is_playing'] else '👁️'}"
                for p in lobby['players']
            ])
            
            players_text = f"""
<b>👥 Игроки в игре ({len([p for p in lobby['players'] if p['is_playing']])} играющих):</b>

{players_list}
            """
            bot.edit_message_text(players_text, 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=types.InlineKeyboardMarkup().add(
                                    types.InlineKeyboardButton("🔙 Назад", callback_data=f"game_menu_{lobby_code}")
                                ))
    
    elif data.startswith('round_stats_'):
        lobby_code = data[12:]
        if lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            
            if not lobby['game_started']:
                bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
                return
            
            # Находим шпиона
            spy_name = "Неизвестно"
            if lobby['spy_id']:
                spy = next((p for p in lobby['players'] if p['id'] == lobby['spy_id']), None)
                if spy:
                    spy_name = spy['name']
            
            stats_text = f"""
<b>📊 Статистика раунда:</b>

Раунд: {lobby['round_number']}
Тема: {get_theme_name(lobby['theme'])}
Слово: <code>{lobby['word']}</code>
Шпион: {spy_name}

Режим: {'🕵️ Все шпионы' if lobby['all_spies_mode'] else '🎮 Обычный'}

Проголосовало: {len(lobby['votes'])}/{len([p for p in lobby['players'] if p['is_playing']])}
            """
            bot.edit_message_text(stats_text, 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=types.InlineKeyboardMarkup().add(
                                    types.InlineKeyboardButton("🔙 Назад", callback_data=f"game_menu_{lobby_code}")
                                ))
    
    elif data.startswith('surrender_'):
        lobby_code = data[10:]
        if lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            
            if not lobby['game_started']:
                bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
                return
            
            # Находим игрока
            player = next((p for p in lobby['players'] if p['id'] == user_id), None)
            if not player or not player['is_playing']:
                bot.answer_callback_query(call.id, "⚠️ Вы не участвуете в игре!")
                return
            
            # Показываем подтверждение
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton("✅ Да, сдаюсь", callback_data=f"surrender_confirm_{lobby_code}"),
                types.InlineKeyboardButton("❌ Нет, отмена", callback_data=f"game_menu_{lobby_code}")
            )
            
            bot.edit_message_text(f"⚠️ <b>{player['name']}, вы уверены, что хотите сдаться?</b>\n\nЭто приведет к вашей дисквалификации из текущей игры.", 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=keyboard)
    
    elif data.startswith('surrender_confirm_'):
        lobby_code = data[18:]
        if lobby_code in lobbies:
            lobby = lobbies[lobby_code]
            
            # Находим игрока
            player = next((p for p in lobby['players'] if p['id'] == user_id), None)
            if player:
                player['is_playing'] = False
                
                # Уведомляем всех
                broadcast_to_lobby(lobby_code, 
                                  f"⚠️ <b>{player['name']} сдался и выбывает из игры!</b>")
                
                bot.answer_callback_query(call.id, "✅ Вы сдались и выбыли из игры!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
                
                # Проверяем, не осталось ли достаточно игроков
                playing_players = [p for p in lobby['players'] if p['is_playing']]
                if len(playing_players) < 3:
                    lobby['game_started'] = False
                    broadcast_to_lobby(lobby_code, 
                                      "⚠️ Игра завершена, потому что осталось меньше 3 игроков!")

# Игровая логика
def start_round(lobby_code):
    lobby = lobbies[lobby_code]
    
    # Сбрасываем голоса
    lobby['votes'] = {}
    
    # Определяем режим игры (каждый 5-й раунд - все шпионы)
    lobby['all_spies_mode'] = (lobby['round_number'] % 5 == 0)
    if lobby['all_spies_mode']:
        global_stats['all_spies_rounds'] += 1
    
    # Выбираем слово
    lobby['word'] = get_random_word(lobby['theme'], lobby['custom_word'])
    
    # Выбираем шпиона (или все шпионы)
    playing_players = [p for p in lobby['players'] if p['is_playing']]
    
    if lobby['all_spies_mode']:
        lobby['spy_id'] = None  # Все шпионы
        spy_text = "🕵️ <b>СЕКРЕТНЫЙ РАУНД!</b> ВСЕ игроки - шпионы!"
    else:
        # Выбираем случайного шпиона
        spy = random.choice(playing_players)
        lobby['spy_id'] = spy['id']
        spy_text = f"Один из игроков - <b>ШПИОН</b>! 🕵️"
    
    # Отправляем информацию игрокам
    for player in playing_players:
        player_name = player['name']
        
        if lobby['all_spies_mode']:
            # В режиме "все шпионы" никто не знает слово
            message = f"""
<b>🎮 Раунд {lobby['round_number']} начался!</b>

{spy_text}

Тема: <b>{get_theme_name(lobby['theme'])}</b>

⚠️ <b>Вы не знаете слово!</b>
Все игроки в этом раунде - шпионы.

Ваша задача - вычислить, что другие игроки ТОЖЕ не знают слово и вести себя соответственно.
            """
        elif player['id'] == lobby['spy_id']:
            # Сообщение для шпиона
            message = f"""
<b>🎮 Раунд {lobby['round_number']} начался!</b>

{spy_text}

Тема: <b>{get_theme_name(lobby['theme'])}</b>

⚠️ <b>ВЫ - ШПИОН!</b> 🕵️

Вы НЕ знаете слово.

Слово, которое знают другие игроки: <code>?? ??? ??</code>

Ваша задача - скрыть, что вы не знаете слово, и попытаться вычислить, что это за слово.
            """
        else:
            # Сообщение для обычного игрока
            message = f"""
<b>🎮 Раунд {lobby['round_number']} начался!</b>

{spy_text}

Тема: <b>{get_theme_name(lobby['theme'])}</b>

✅ <b>Вы знаете слово!</b>

Слово: <code>{lobby['word']}</code>

Ваша задача - описать слово так, чтобы другие игроки поняли, что вы знаете его, но не называть прямо.
А также вычислить, кто НЕ знает слово (шпиона).
            """
        
        try:
            bot.send_message(player['id'], message, reply_markup=get_game_keyboard())
        except Exception as e:
            print(f"Ошибка отправки сообщения игроку {player['id']}: {e}")
    
    # Добавляем в статистику
    lobby_stats[lobby_code]['rounds_played'] += 1
    
    # Записываем в историю голосований
    lobby['voting_history'].append({
        'round': lobby['round_number'],
        'word': lobby['word'],
        'spy_id': lobby['spy_id'],
        'all_spies': lobby['all_spies_mode'],
        'votes': {},
        'result': None
    })
    
    save_global_stats()

def check_voting_complete(lobby_code):
    lobby = lobbies[lobby_code]
    
    # Проверяем, все ли игроки проголосовали
    playing_players = [p for p in lobby['players'] if p['is_playing']]
    voted_players = len(lobby['votes'])
    total_players = len(playing_players)
    
    if voted_players == total_players:
        # Все проголосовали, завершаем раунд
        end_round(lobby_code)
    elif voted_players >= total_players - 1 and lobby['auto_close']:
        # Все кроме одного проголосовали и включено авто-закрытие
        end_round(lobby_code)

def end_round(lobby_code):
    lobby = lobbies[lobby_code]
    
    # Подсчитываем голоса
    vote_counts = defaultdict(int)
    for voted_id in lobby['votes'].values():
        if voted_id == 'none':
            vote_counts['none'] += 1
        else:
            vote_counts[voted_id] += 1
    
    # Определяем победителя
    playing_players = [p for p in lobby['players'] if p['is_playing']]
    
    if lobby['all_spies_mode']:
        # В режиме "все шпионы"
        if vote_counts:
            # Ищем, за кого больше всего голосов
            max_votes = max(vote_counts.values())
            most_voted = [k for k, v in vote_counts.items() if v == max_votes]
            
            if len(most_voted) == 1 and most_voted[0] != 'none':
                # Кого-то выбрали - шпионы проиграли
                winner = "players"
                winner_text = "🎯 <b>ИГРОКИ ВЫИГРАЛИ!</b>\nОни смогли выбрать 'шпиона', хотя все были шпионами!"
                global_stats['players_wins'] += 1
                lobby_stats[lobby_code]['players_wins'] += 1
            else:
                # Никого не выбрали или выбрали "никто" - шпионы выиграли
                winner = "spies"
                winner_text = "🕵️ <b>ШПИОНЫ ВЫИГРАЛИ!</b>\nНикто не был разоблачен, хотя все были шпионами!"
                global_stats['spy_wins'] += 1
                lobby_stats[lobby_code]['spy_wins'] += 1
        else:
            # Никто не проголосовал
            winner = "spies"
            winner_text = "🕵️ <b>ШПИОНЫ ВЫИГРАЛИ!</b>\nНикто не проголосовал!"
            global_stats['spy_wins'] += 1
            lobby_stats[lobby_code]['spy_wins'] += 1
    else:
        # Обычный режим
        if lobby['spy_id'] in vote_counts and vote_counts[lobby['spy_id']] > 0:
            # Шпиона нашли
            winner = "players"
            winner_text = "🎯 <b>ИГРОКИ ВЫИГРАЛИ!</b>\nОни нашли шпиона!"
            global_stats['players_wins'] += 1
            lobby_stats[lobby_code]['players_wins'] += 1
        else:
            # Шпиона не нашли
            winner = "spy"
            
            # Находим имя шпиона
            spy_name = "Неизвестный"
            spy = next((p for p in playing_players if p['id'] == lobby['spy_id']), None)
            if spy:
                spy_name = spy['name']
            
            winner_text = f"🕵️ <b>ШПИОН ВЫИГРАЛ!</b>\n{spy_name} остался незамеченным!"
            global_stats['spy_wins'] += 1
            lobby_stats[lobby_code]['spy_wins'] += 1
    
    # Формируем результаты голосования
    results_text = f"""
<b>🏁 Раунд {lobby['round_number']} завершен!</b>

Тема: <b>{get_theme_name(lobby['theme'])}</b>
Слово: <code>{lobby['word']}</code>

<b>Результаты голосования:</b>
"""
    
    # Добавляем голоса
    for player in playing_players:
        if player['id'] in lobby['votes']:
            voted_id = lobby['votes'][player['id']]
            if voted_id == 'none':
                vote_for = "НИКОГО"
            else:
                voted_player = next((p for p in playing_players if p['id'] == voted_id), None)
                vote_for = voted_player['name'] if voted_player else "Неизвестный"
        else:
            vote_for = "НЕ ГОЛОСОВАЛ"
        
        results_text += f"👤 {player['name']} → {vote_for}\n"
    
    results_text += f"\n{winner_text}"
    
    # Добавляем информацию о шпионе (если не режим "все шпионы")
    if not lobby['all_spies_mode'] and lobby['spy_id']:
        spy = next((p for p in playing_players if p['id'] == lobby['spy_id']), None)
        if spy:
            results_text += f"\n\n🕵️ Шпион был: <b>{spy['name']}</b>"
    
    # Рассылаем результаты
    broadcast_to_lobby(lobby_code, results_text, keyboard=get_game_keyboard())
    
    # Обновляем историю голосований
    if lobby['voting_history']:
        lobby['voting_history'][-1]['votes'] = dict(lobby['votes'])
        lobby['voting_history'][-1]['result'] = winner
    
    # Подготавливаем следующий раунд
    lobby['round_number'] += 1
    lobby['votes'] = {}
    
    # Проверяем, не нужно ли завершить игру
    if lobby['round_number'] > 20:  # Максимум 20 раундов
        lobby['game_started'] = False
        final_text = """
<b>🎮 Игра завершена!</b>

Игра автоматически завершена после 20 раундов.

Спасибо за игру! 🎉
        """
        broadcast_to_lobby(lobby_code, final_text, keyboard=get_lobby_keyboard())
    
    save_global_stats()

# Запуск бота
if __name__ == '__main__':
    print("=" * 50)
    print("🤖 Бот 'Универсальный Шпион' запускается...")
    print(f"👑 Администратор: {ADMIN_ID}")
    print("=" * 50)
    
    # Загружаем сохраненную статистику
    load_global_stats()
    
    # Запускаем бота
    print("🔄 Бот запущен и готов к работе!")
    print("📊 Загруженная статистика:")
    print(f"   Всего игр: {global_stats['total_games']}")
    print(f"   Уникальных игроков: {global_stats['total_players']}")
    print(f"   Активных лобби: {global_stats['active_lobbies']}")
    print("=" * 50)
    
    bot.infinity_polling()