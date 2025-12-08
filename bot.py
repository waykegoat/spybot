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

print("=" * 50)
print("🤖 Бот 'Универсальный Шпион' запускается...")
print(f"👑 Администратор: {ADMIN_ID}")
print("=" * 50)


bot = telebot.TeleBot(API_TOKEN, parse_mode='HTML')

# ============ ПРОВЕРКА ПОДПИСКИ ============
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@dimbub')
CHANNEL_URL = os.getenv('CHANNEL_URL', 'https://t.me/dimbub')
CHANNEL_ID = os.getenv('CHANNEL_ID', '-1003369490880')

try:
    CHANNEL_ID = int(CHANNEL_ID)
except ValueError:
    pass

def check_subscription(user_id):
    """Проверяет, подписан ли пользователь на канал"""
    
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        status = member.status
        is_subscribed = status in ['creator', 'administrator', 'member']
        return is_subscribed
        
    except Exception as e:
        print(f"❌ Ошибка проверки подписки: {type(e).__name__}: {e}")
        return False

def require_subscription(func):
    """Декоратор для проверки подписки"""
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        
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
            return
        
        return func(message, *args, **kwargs)
    
    return wrapper

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def handle_check_subscription(call):
    """Обработчик кнопки "Я подписался" """
    user_id = call.from_user.id
    
    if check_subscription(user_id):
        bot.answer_callback_query(call.id, "✅ Спасибо за подписку!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
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

lobbies = {}
user_to_lobby = {}
all_players = set()
lobby_stats = {}
chat_messages = defaultdict(deque)

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
    if theme == 'custom' and custom_word:
        return custom_word
    
    if theme in THEMES:
        words = THEMES[theme]
        if words:
            return random.choice(words)
    
    return "Неизвестное слово"

def save_global_stats():
    try:
        with open('global_stats.json', 'w', encoding='utf-8') as f:
            json.dump(global_stats, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_global_stats():
    global global_stats
    try:
        if os.path.exists('global_stats.json'):
            with open('global_stats.json', 'r', encoding='utf-8') as f:
                loaded_stats = json.load(f)
                for key in global_stats:
                    if key in loaded_stats:
                        global_stats[key] = loaded_stats[key]
    except:
        pass

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
        except:
            pass

# Клавиатуры
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("🎮 Создать лобби"),
        types.KeyboardButton("🔗 Войти в лобби"),
        types.KeyboardButton("📖 Правила"),
        types.KeyboardButton("ℹ️ Помощь"),
        types.KeyboardButton("👑 Админ-панель")
    )
    return keyboard

def get_lobby_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("🎮 Меню лобби"),
        types.KeyboardButton("👥 Список игроков"),
        types.KeyboardButton("🎨 Сменить тему"),
        types.KeyboardButton("💬 Чат лобби"),
        types.KeyboardButton("❌ Покинуть лобби")
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
        types.KeyboardButton("👥 Список игроков"),
        types.KeyboardButton("❌ Выйти из игры")
    )
    return keyboard

def create_lobby_menu(lobby_code):
    """Инлайн-меню лобби (без кнопок выхода и списка игроков)"""
    lobby = lobbies[lobby_code]
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    if not lobby['game_started']:
        keyboard.add(
            types.InlineKeyboardButton("▶️ Начать игру", callback_data=f"start_{lobby_code}"),
            types.InlineKeyboardButton("🎨 Сменить тему", callback_data=f"theme_menu_{lobby_code}")
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
            types.InlineKeyboardButton("🏁 Завершить раунд", callback_data=f"end_round_{lobby_code}"),
            types.InlineKeyboardButton("🔄 Новый раунд", callback_data=f"new_round_{lobby_code}")
        )
    
    keyboard.add(
        types.InlineKeyboardButton("💬 Чат лобби", callback_data=f"lobby_chat_{lobby_code}"),
    )
    
    return keyboard

def create_theme_keyboard(lobby_code):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    keyboard.add(
        types.InlineKeyboardButton("🎮 Dota 2 Герои", callback_data=f"settheme_dota2_{lobby_code}"),
        types.InlineKeyboardButton("👑 Clash Royale", callback_data=f"settheme_clashroyale_{lobby_code}")
    )
    keyboard.add(
        types.InlineKeyboardButton("⭐ Brawl Stars", callback_data=f"settheme_brawlstars_{lobby_code}"),
        types.InlineKeyboardButton("📍 Локации", callback_data=f"settheme_locations_{lobby_code}")
    )
    keyboard.add(
        types.InlineKeyboardButton("✏️ Своя тема", callback_data=f"settheme_custom_{lobby_code}"),
        types.InlineKeyboardButton("🔙 Назад", callback_data=f"menu_{lobby_code}")
    )
    
    return keyboard

def create_voting_keyboard(lobby_code, user_id):
    lobby = lobbies[lobby_code]
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    for player in lobby['players']:
        if player['id'] != user_id and player['is_playing']:
            keyboard.add(
                types.InlineKeyboardButton(
                    f"👤 {player['name']}", 
                    callback_data=f"vote_{player['id']}_{lobby_code}"
                )
            )
    
    keyboard.add(
        types.InlineKeyboardButton("✖️ Никто", callback_data=f"vote_none_{lobby_code}"),
        types.InlineKeyboardButton("🔙 Назад", callback_data=f"game_menu_{lobby_code}")
    )
    
    return keyboard

def create_game_menu_keyboard(lobby_code):
    """Инлайн-меню игры (без кнопок выхода и списка игроков)"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    keyboard.add(
        types.InlineKeyboardButton("🕵️ Голосовать", callback_data=f"vote_menu_{lobby_code}"),
        types.InlineKeyboardButton("👁️ Посмотреть голоса", callback_data=f"view_votes_{lobby_code}")
    )
    keyboard.add(
        types.InlineKeyboardButton("📊 Статистика раунда", callback_data=f"round_stats_{lobby_code}"),
        types.InlineKeyboardButton("💬 Чат лобби", callback_data=f"game_chat_{lobby_code}")
    )
    keyboard.add(
        types.InlineKeyboardButton("❌ Сдаться", callback_data=f"surrender_{lobby_code}"),
        types.InlineKeyboardButton("🔙 В меню лобби", callback_data=f"menu_{lobby_code}")
    )
    
    return keyboard

def create_host_options_keyboard():
    """Клавиатура для выбора действий после закрытия лобби ведущим"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🎮 Создать новое лобби", callback_data="create_new_lobby"),
        types.InlineKeyboardButton("📊 Глобальная статистика", callback_data="global_stats"),
        types.InlineKeyboardButton("📖 Правила игры", callback_data="show_rules"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_to_main")
    )
    return keyboard

# Основные обработчики команд
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

<b>Используйте кнопки ниже для навигации!</b>
    """
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.message_handler(commands=['new'])
@require_subscription
def handle_new(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if user_id in user_to_lobby:
        lobby_code = user_to_lobby[user_id]
        bot.send_message(message.chat.id, 
                        f"⚠️ Вы уже находитесь в лобби {lobby_code}. Покиньте его сначала.")
        return
    
    lobby_code = generate_lobby_code()
    
    lobbies[lobby_code] = {
        'host_id': user_id,
        'players': [{
            'id': user_id,
            'name': user_name,
            'is_host': True,
            'is_playing': True,
            'is_alive': True
        }],
        'game_started': False,
        'all_spies_mode': False,
        'spy_id': None,
        'previous_spy_id': None,
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
    
    lobby_stats[lobby_code] = {
        'games_played': 0,
        'spy_wins': 0,
        'players_wins': 0,
        'rounds_played': 0
    }
    
    info_text = f"""
<b>✅ Лобби создано!</b>

Код лобби: <code>{lobby_code}</code>

Отправьте этот код друзьям:
<code>/join {lobby_code}</code>

<b>Игроки в лобби (1/7):</b>
👑 {user_name} (Ведущий)

<b>Используйте кнопки ниже для управления:</b>
    """
    
    bot.send_message(message.chat.id, info_text, reply_markup=get_lobby_keyboard())
    bot.send_message(message.chat.id, "🎮 Меню лобби:", reply_markup=create_lobby_menu(lobby_code))
    
    save_global_stats()

@bot.message_handler(commands=['join'])
@require_subscription
def handle_join(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if user_id in user_to_lobby:
        lobby_code = user_to_lobby[user_id]
        bot.send_message(message.chat.id, 
                        f"⚠️ Вы уже находитесь в лобби {lobby_code}.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, 
                        "⚠️ Укажите код лобби!\nПример: <code>/join ABC123</code>")
        return
    
    lobby_code = parts[1].upper().strip()
    
    if lobby_code not in lobbies:
        bot.send_message(message.chat.id, 
                        f"⚠️ Лобби с кодом <code>{lobby_code}</code> не найдено!")
        return
    
    lobby = lobbies[lobby_code]
    
    if lobby['game_started']:
        bot.send_message(message.chat.id, 
                        f"⚠️ Игра в лобби {lobby_code} уже начата!")
        return
    
    if len(lobby['players']) >= 7:
        bot.send_message(message.chat.id, 
                        f"⚠️ В лобби {lobby_code} уже максимальное количество игроков (7/7)!")
        return
    
    for player in lobby['players']:
        if player['id'] == user_id:
            bot.send_message(message.chat.id, 
                            f"⚠️ Вы уже в этом лобби!")
            return
    
    lobby['players'].append({
        'id': user_id,
        'name': user_name,
        'is_host': False,
        'is_playing': True,
        'is_alive': True
    })
    
    user_to_lobby[user_id] = lobby_code
    
    if user_id not in all_players:
        all_players.add(user_id)
        global_stats['total_players'] = len(all_players)
    
    players_list = "\n".join([f"{'👑' if p['is_host'] else '👤'} {p['name']}" 
                             for p in lobby['players']])
    
    welcome_text = f"""
<b>✅ Вы присоединились к лобби {lobby_code}!</b>

<b>Игроки в лобби ({len(lobby['players'])}/7):</b>
{players_list}

<b>Ведущий:</b> {next(p['name'] for p in lobby['players'] if p['is_host'])}

<b>Используйте кнопки ниже:</b>
    """
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_lobby_keyboard())
    bot.send_message(message.chat.id, "🎮 Меню лобби:", reply_markup=create_lobby_menu(lobby_code))
    
    broadcast_to_lobby(lobby_code, 
                      f"👤 <b>{user_name}</b> присоединился к лобби!\nТеперь игроков: {len(lobby['players'])}/7",
                      exclude_user=user_id)
    
    save_global_stats()

@bot.message_handler(commands=['leave'])
def handle_leave(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if user_id not in user_to_lobby:
        bot.send_message(message.chat.id, "⚠️ Вы не находитесь в лобби!")
        return
    
    lobby_code = user_to_lobby[user_id]
    
    if lobby_code not in lobbies:
        del user_to_lobby[user_id]
        bot.send_message(message.chat.id, "⚠️ Лобби больше не существует!")
        bot.send_message(message.chat.id, "Главное меню:", reply_markup=get_main_keyboard())
        return
    
    lobby = lobbies[lobby_code]
    is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
    
    if is_host:
        # Ведущий покидает - закрываем лобби
        for player in lobby['players']:
            if player['id'] != user_id:
                try:
                    bot.send_message(player['id'], 
                                   f"⚠️ Лобби {lobby_code} закрыто, потому что ведущий покинул игру.")
                except:
                    pass
            if player['id'] in user_to_lobby:
                del user_to_lobby[player['id']]
        
        del lobbies[lobby_code]
        if lobby_code in lobby_stats:
            del lobby_stats[lobby_code]
        if lobby_code in chat_messages:
            del chat_messages[lobby_code]
        
        global_stats['active_lobbies'] = len(lobbies)
        
        # Показываем ведущему опции после закрытия лобби
        bot.send_message(message.chat.id, 
                        "✅ Вы закрыли лобби и вышли из игры.\n\n<b>Что вы хотите сделать дальше?</b>",
                        reply_markup=create_host_options_keyboard())
        
    else:
        # Обычный игрок покидает
        lobby['players'] = [p for p in lobby['players'] if p['id'] != user_id]
        del user_to_lobby[user_id]
        
        bot.send_message(message.chat.id, f"✅ Вы покинули лобби {lobby_code}.")
        bot.send_message(message.chat.id, "Главное меню:", reply_markup=get_main_keyboard())
        
        broadcast_to_lobby(lobby_code, 
                          f"👤 <b>{user_name}</b> покинул лобби.\nОсталось игроков: {len(lobby['players'])}/7",
                          exclude_user=user_id)
        
        if lobby['game_started'] and len([p for p in lobby['players'] if p['is_playing']]) < 3:
            lobby['game_started'] = False
            broadcast_to_lobby(lobby_code, 
                              "⚠️ Игра завершена, потому что осталось меньше 3 игроков.")
    
    if lobby_code in lobbies and not lobbies[lobby_code]['players']:
        del lobbies[lobby_code]
        if lobby_code in lobby_stats:
            del lobby_stats[lobby_code]
        if lobby_code in chat_messages:
            del chat_messages[lobby_code]
        global_stats['active_lobbies'] = len(lobbies)
    
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
   • Один из игроков (шпион) НЕ знает слово
   • Шпион должен скрывать это
   • Остальные должны вычислить шпиона

2. <b>Ход игры:</b>
   • Каждый раунд - новое слово и шпион
   • Игроки по очереди описывают слово
   • После обсуждения - голосование
   • Если шпиона вычислили - побеждают игроки
   • Если шпион остался незамеченным - побеждает шпион

3. <b>Особенности:</b>
   • Каждый 5-й раунд - все шпионы
   • Максимум 7 игроков в лобби

<b>Удачи в игре! 🎮</b>
    """
    bot.send_message(message.chat.id, rules_text)

@bot.message_handler(commands=['chat'])
def handle_chat(message):
    user_id = message.from_user.id
    
    if user_id not in user_to_lobby:
        bot.send_message(message.chat.id, "⚠️ Вы не находитесь в лобби!")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, 
                        "⚠️ Укажите текст сообщения!\nПример: <code>/chat Привет всем!</code>")
        return
    
    chat_message = parts[1]
    lobby_code = user_to_lobby[user_id]
    user_name = message.from_user.first_name
    
    add_chat_message(lobby_code, user_name, chat_message)
    bot.send_message(message.chat.id, "✅ Сообщение отправлено в чат лобби!")
    
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
    
    player = next((p for p in lobby['players'] if p['id'] == user_id), None)
    if not player or not player['is_playing']:
        bot.send_message(message.chat.id, "⚠️ Вы не участвуете в этой игре!")
        return
    
    bot.send_message(message.chat.id, 
                    "🕵️ <b>Голосование за шпиона:</b>\nВыберите игрока:",
                    reply_markup=create_voting_keyboard(lobby_code, user_id))

# Обработчик текстовых сообщений (кнопки)
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text
    
    if text == "🎮 Создать лобби":
        handle_new(message)
    
    elif text == "🔗 Войти в лобби":
        bot.send_message(message.chat.id, 
                        "Введите код лобби:\nПример: <code>ABC123</code>")
        bot.register_next_step_handler(message, process_join_code)
    
    elif text == "📖 Правила":
        handle_rules(message)
    
    elif text == "ℹ️ Помощь":
        handle_start(message)
    
    elif text == "👑 Админ-панель":
        if is_admin(user_id):
            bot.send_message(message.chat.id, "🔧 Админ-панель:", 
                           reply_markup=types.InlineKeyboardMarkup().add(
                               types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
                               types.InlineKeyboardButton("🎮 Лобби", callback_data="admin_lobbies")
                           ))
        else:
            bot.send_message(message.chat.id, "⚠️ У вас нет прав администратора!")
    
    elif text == "🎮 Меню лобби":
        handle_menu(message)
    
    elif text == "👥 Список игроков":
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            lobby = lobbies[lobby_code]
            
            players_list = []
            for p in lobby['players']:
                status = ""
                if lobby['game_started']:
                    status = " 🎮" if p['is_playing'] else " 👁️"
                players_list.append(f"{'👑' if p['is_host'] else '👤'} {p['name']}{status}")
            
            status = "🟢 Игра начата" if lobby['game_started'] else "🟡 Ожидание"
            bot.send_message(message.chat.id, 
                           f"<b>👥 Игроки в лобби {lobby_code} ({len(lobby['players'])}/7):</b>\n\n" +
                           "\n".join(players_list) + f"\n\nСтатус: {status}")
    
    elif text == "🎨 Сменить тему":
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            lobby = lobbies[lobby_code]
            
            is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
            if not is_host:
                bot.send_message(message.chat.id, 
                               f"⚠️ Только ведущий может менять тему!")
                return
            
            current_theme = get_theme_name(lobby['theme'])
            if lobby['theme'] == 'custom' and lobby['custom_word']:
                current_word = f"\nТекущее слово: <code>{lobby['custom_word']}</code>"
            else:
                current_word = ""
            
            theme_text = f"""
<b>🎨 Смена темы:</b>

Текущая тема: {current_theme}
{current_word}

Выберите новую тему:
            """
            bot.send_message(message.chat.id, theme_text, reply_markup=create_theme_keyboard(lobby_code))
    
    elif text == "💬 Чат лобби":
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            
            if lobby_code in chat_messages and chat_messages[lobby_code]:
                history = ""
                for msg in list(chat_messages[lobby_code])[-10:]:
                    time_str = datetime.fromtimestamp(msg['time']).strftime('%H:%M')
                    history += f"<b>{msg['user']}</b> ({time_str}): {msg['message']}\n"
                
                bot.send_message(message.chat.id, 
                               f"<b>💬 История чата:</b>\n\n{history}")
            else:
                bot.send_message(message.chat.id, "💬 В чате пока нет сообщений.")
    
    elif text == "❌ Покинуть лобби":
        handle_leave(message)
    
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
            
            player = next((p for p in lobby['players'] if p['id'] == user_id), None)
            if not player or not player['is_playing']:
                bot.send_message(message.chat.id, "⚠️ Вы не участвуете в этой игре!")
                return
            
            if user_id in lobby['votes']:
                del lobby['votes'][user_id]
                bot.send_message(message.chat.id, "✅ Ваш предыдущий голос удален.")
            
            bot.send_message(message.chat.id, 
                            "🕵️ <b>Голосование за шпиона:</b>\nВыберите игрока:",
                            reply_markup=create_voting_keyboard(lobby_code, user_id))
    
    elif text == "👁️ Посмотреть голоса":
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            lobby = lobbies[lobby_code]
            
            if not lobby['game_started']:
                bot.send_message(message.chat.id, "⚠️ Игра еще не начата!")
                return
            
            votes_text = "<b>👁️ Текущие голоса:</b>\n\n"
            
            if not lobby['votes']:
                votes_text += "Пока никто не проголосовал."
            else:
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
            
            bot.send_message(message.chat.id, votes_text)
    
    elif text == "❌ Выйти из игры":
        handle_leave(message)
    
    else:
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            truncated_text = text[:100] + "..." if len(text) > 100 else text
            
            # Обрезаем текст для callback данных
            callback_text = text[:100]  # Максимум 100 символов для callback
            
            bot.send_message(message.chat.id, 
                           f"Отправить в чат лобби?\n\n<code>{truncated_text}</code>",
                           reply_markup=types.InlineKeyboardMarkup().add(
                               types.InlineKeyboardButton("✅ Да", callback_data=f"send_{lobby_code}_{callback_text}"),
                               types.InlineKeyboardButton("❌ Нет", callback_data="cancel")
                           ))
        else:
            bot.send_message(message.chat.id, 
                           "Используйте кнопки ниже:", 
                           reply_markup=get_main_keyboard())

def process_join_code(message):
    user_id = message.from_user.id
    lobby_code = message.text.upper().strip()
    
    if len(lobby_code) != 6 or not lobby_code[:3].isalpha() or not lobby_code[3:].isdigit():
        bot.send_message(message.chat.id, 
                        "⚠️ Неверный формат кода! Пример: <code>ABC123</code>")
        return
    
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
        bot.send_message(message.chat.id, f"⚠️ Лобби <code>{lobby_code}</code> не найдено!")

# Основной обработчик callback-запросов (ИСПРАВЛЕННЫЙ!)
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    
    try:
        # ============ ОБЩИЕ КНОПКИ (не зависят от лобби) ============
        
        if data == 'create_new_lobby':
            handle_new(types.Message(
                message_id=call.message.message_id,
                from_user=call.from_user,
                date=call.message.date,
                chat=call.message.chat,
                content_type='text',
                options={},
                json_string='',
                text='/new'
            ))
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return
        
        elif data == 'global_stats':
            uptime = time.time() - global_stats['start_time']
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            
            stats_text = f"""
<b>📊 Глобальная статистика:</b>

🎮 Всего игр: {global_stats['total_games']}
👥 Уникальных игроков: {global_stats['total_players']}
🏠 Создано лобби: {global_stats['total_lobbies']}

🏆 Побед шпионов: {global_stats['spy_wins']}
🎯 Побед игроков: {global_stats['players_wins']}

⏱️ Время работы: {hours}ч {minutes}м
            """
            
            bot.edit_message_text(stats_text, 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=create_host_options_keyboard())
            return
        
        elif data == 'show_rules':
            rules_text = """
<b>📖 Правила игры "Шпион":</b>

1. <b>Цель игры:</b>
   • Один из игроков (шпион) НЕ знает слово
   • Шпион должен скрывать это
   • Остальные должны вычислить шпиона

2. <b>Ход игры:</b>
   • Каждый раунд - новое слово и шпион
   • Игроки по очереди описывают слово
   • После обсуждения - голосование
   • Если шпиона вычислили - побеждают игроки
   • Если шпион остался незамеченным - побеждает шпион

3. <b>Особенности:</b>
   • Каждый 5-й раунд - все шпионы
   • Максимум 7 игроков в лобби

<b>Удачи в игре! 🎮</b>
            """
            bot.edit_message_text(rules_text, 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=create_host_options_keyboard())
            return
        
        elif data == 'go_to_main':
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, 
                           "🏠 <b>Главное меню</b>\n\nВыберите действие:", 
                           reply_markup=get_main_keyboard())
            return
        
        elif data == 'cancel':
            bot.answer_callback_query(call.id, "❌ Отменено")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return
        
        elif data == 'check_subscription':
            handle_check_subscription(call)
            return
        
        elif data in ['admin_stats', 'admin_lobbies', 'admin_close']:
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "⚠️ У вас нет прав!")
                return
            
            if data == 'admin_stats':
                uptime = time.time() - global_stats['start_time']
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                
                stats_text = f"""
<b>📊 Глобальная статистика:</b>

🎮 Всего игр: {global_stats['total_games']}
👥 Уникальных игроков: {global_stats['total_players']}
🏠 Создано лобби: {global_stats['total_lobbies']}

🏆 Побед шпионов: {global_stats['spy_wins']}
🎯 Побед игроков: {global_stats['players_wins']}

🔴 Активных лобби: {global_stats['active_lobbies']}
⏱️ Время работы: {hours}ч {minutes}м
                """
                
                bot.edit_message_text(stats_text, 
                                    call.message.chat.id, 
                                    call.message.message_id,
                                    reply_markup=types.InlineKeyboardMarkup().add(
                                        types.InlineKeyboardButton("🎮 Лобби", callback_data="admin_lobbies"),
                                        types.InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")
                                    ))
            elif data == 'admin_lobbies':
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
                                    reply_markup=types.InlineKeyboardMarkup().add(
                                        types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
                                        types.InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")
                                    ))
            elif data == 'admin_close':
                bot.delete_message(call.message.chat.id, call.message.message_id)
            return
        
        # ============ КНОПКИ, ЗАВИСЯЩИЕ ОТ ЛОББИ ============
        
        # Специальная обработка для кнопок с длинным текстом сообщений
        if data.startswith('send_'):
            parts = data.split('_', 2)  # Делим только на 3 части
            if len(parts) == 3:
                lobby_code = parts[1]
                # Обработка сообщения ниже
                if lobby_code in lobbies:
                    # Здесь просто пропускаем проверку, обработка будет ниже
                    pass
                else:
                    bot.answer_callback_query(call.id, "⚠️ Лобби больше не существует!")
                    bot.edit_message_text(
                        "❌ <b>Лобби больше не существует!</b>",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=types.InlineKeyboardMarkup().add(
                            types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_to_main")
                        )
                    )
                    return
        
        # Определяем lobby_code для других кнопок
        lobby_code = None
        
        # Для кнопок смены темы
        if data.startswith('settheme_'):
            parts = data.split('_')
            if len(parts) >= 3:
                lobby_code = parts[2]
        
        # Для остальных кнопок
        elif '_' in data:
            prefixes = [
                'menu_', 'start_', 'theme_menu_', 'vote_', 'vote_none_',
                'game_menu_', 'vote_menu_', 'end_game_', 'end_round_',
                'new_round_', 'leave_', 'toggle_host_', 'toggle_auto_',
                'view_votes_', 'surrender_', 'lobby_chat_', 'game_chat_',
                'stats_', 'round_stats_'
            ]
            
            for prefix in prefixes:
                if data.startswith(prefix):
                    lobby_code = data[len(prefix):]
                    break
        
        # Проверяем существование лобби
        if lobby_code and lobby_code not in lobbies:
            bot.answer_callback_query(call.id, "⚠️ Лобби больше не существует!")
            bot.edit_message_text(
                "❌ <b>Лобби больше не существует!</b>\n\nВы можете создать новое лобби или вернуться в главное меню.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=types.InlineKeyboardMarkup(row_width=2).add(
                    types.InlineKeyboardButton("🎮 Создать новое лобби", callback_data="create_new_lobby"),
                    types.InlineKeyboardButton("📊 Глобальная статистика", callback_data="global_stats"),
                    types.InlineKeyboardButton("📖 Правила игры", callback_data="show_rules"),
                    types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_to_main")
                )
            )
            return
        
        # ============ ОБРАБОТКА КНОПОК ЛОББИ ============
        
        # Меню лобби
        if data.startswith('menu_'):
            if lobby_code in lobbies:
                bot.edit_message_text("🎮 Меню лобби:", 
                                    call.message.chat.id, 
                                    call.message.message_id,
                                    reply_markup=create_lobby_menu(lobby_code))
        
        # Меню выбора темы
        elif data.startswith('theme_menu_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может менять тему!")
                    return
                
                current_theme = get_theme_name(lobby['theme'])
                theme_text = f"<b>🎨 Выберите тему:</b>\n\nТекущая: {current_theme}"
                bot.edit_message_text(theme_text, 
                                    call.message.chat.id, 
                                    call.message.message_id,
                                    reply_markup=create_theme_keyboard(lobby_code))
        
        # Установить тему
        elif data.startswith('settheme_'):
            parts = data.split('_')
            if len(parts) >= 3:
                theme = parts[1]
                lobby_code = parts[2]
                
                if lobby_code in lobbies:
                    lobby = lobbies[lobby_code]
                    
                    is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                    if not is_host:
                        bot.answer_callback_query(call.id, "⚠️ Только ведущий может менять тему!")
                        return
                    
                    lobby['theme'] = theme
                    
                    if theme == 'custom':
                        msg = bot.send_message(call.message.chat.id, "✏️ Введите слово для игры:")
                        
                        def process_custom_word(message):
                            if message.text:
                                lobby['custom_word'] = message.text.strip()
                                bot.send_message(message.chat.id, 
                                               f"✅ Слово установлено: <code>{lobby['custom_word']}</code>")
                                bot.send_message(message.chat.id, 
                                               "🎮 Меню лобби:", 
                                               reply_markup=create_lobby_menu(lobby_code))
                        
                        bot.register_next_step_handler(msg, process_custom_word)
                        bot.answer_callback_query(call.id, "✏️ Введите слово")
                        
                    else:
                        theme_name = get_theme_name(theme)
                        bot.answer_callback_query(call.id, f"✅ Тема: {theme_name}")
                        bot.edit_message_text(
                            f"✅ Тема установлена: {theme_name}\n\n🎮 Меню лобби:", 
                            call.message.chat.id, 
                            call.message.message_id,
                            reply_markup=create_lobby_menu(lobby_code)
                        )
        
        # Начать игру
        elif data.startswith('start_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может начать игру!")
                    return
                
                playing_players = [p for p in lobby['players'] if p['is_playing']]
                if len(playing_players) < 3:
                    bot.answer_callback_query(call.id, "⚠️ Нужно минимум 3 игрока!")
                    return
                
                lobby['game_started'] = True
                lobby['round_number'] = 1
                global_stats['total_games'] += 1
                lobby_stats[lobby_code]['games_played'] += 1
                
                start_round(lobby_code)
                
                bot.answer_callback_query(call.id, "✅ Игра начата!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
        
        # Голосование
        elif data.startswith('vote_'):
            parts = data.split('_')
            if len(parts) >= 2:
                if parts[1] == 'none':
                    lobby_code = parts[2]
                    if lobby_code in lobbies:
                        lobby = lobbies[lobby_code]
                        
                        if not lobby['game_started']:
                            bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
                            return
                        
                        player = next((p for p in lobby['players'] if p['id'] == user_id), None)
                        if not player or not player['is_playing']:
                            bot.answer_callback_query(call.id, "⚠️ Вы не можете голосовать!")
                            return
                        
                        lobby['votes'][user_id] = 'none'
                        bot.answer_callback_query(call.id, "✅ Вы проголосовали за НИКОГО")
                        check_voting_complete(lobby_code)
                else:
                    try:
                        voted_id = int(parts[1])
                        lobby_code = parts[2]
                        
                        if lobby_code in lobbies:
                            lobby = lobbies[lobby_code]
                            
                            if not lobby['game_started']:
                                bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
                                return
                            
                            player = next((p for p in lobby['players'] if p['id'] == user_id), None)
                            if not player or not player['is_playing']:
                                bot.answer_callback_query(call.id, "⚠️ Вы не можете голосовать!")
                                return
                            
                            voted_player = next((p for p in lobby['players'] if p['id'] == voted_id), None)
                            if not voted_player or not voted_player['is_playing']:
                                bot.answer_callback_query(call.id, "⚠️ Нельзя проголосовать за этого игрока!")
                                return
                            
                            lobby['votes'][user_id] = voted_id
                            bot.answer_callback_query(call.id, f"✅ Вы проголосовали за {voted_player['name']}")
                            check_voting_complete(lobby_code)
                    except ValueError:
                        bot.answer_callback_query(call.id, "⚠️ Ошибка голосования!")
        
        # Меню игры
        elif data.startswith('game_menu_'):
            if lobby_code in lobbies:
                bot.edit_message_text("🎮 Меню игры:", 
                                    call.message.chat.id, 
                                    call.message.message_id,
                                    reply_markup=create_game_menu_keyboard(lobby_code))
        
        # Меню голосования
        elif data.startswith('vote_menu_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                if not lobby['game_started']:
                    bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
                    return
                
                bot.edit_message_text("🕵️ <b>Голосование за шпиона:</b>\nВыберите игрока:", 
                                    call.message.chat.id, 
                                    call.message.message_id,
                                    reply_markup=create_voting_keyboard(lobby_code, user_id))
        
        # Завершить игру
        elif data.startswith('end_game_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может завершить игру!")
                    return
                
                lobby['game_started'] = False
                lobby['votes'] = {}
                lobby['spy_id'] = None
                lobby['word'] = None
                
                broadcast_to_lobby(lobby_code, 
                                  "⚠️ <b>Игра завершена ведущим!</b>",
                                  keyboard=get_lobby_keyboard())
                
                bot.answer_callback_query(call.id, "✅ Игра завершена!")
                bot.edit_message_text("✅ Игра завершена!", 
                                    call.message.chat.id, 
                                    call.message.message_id,
                                    reply_markup=create_lobby_menu(lobby_code))
        
        # Завершить раунд
        elif data.startswith('end_round_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может завершить раунд!")
                    return
                
                end_round(lobby_code)
                bot.answer_callback_query(call.id, "✅ Раунд завершен!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
        
        # Новый раунд
        elif data.startswith('new_round_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может начать новый раунд!")
                    return
                
                start_round(lobby_code)
                bot.answer_callback_query(call.id, "✅ Новый раунд начат!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
        
        # Выйти из лобби (из инлайн-меню)
        elif data.startswith('leave_'):
            if lobby_code in lobbies:
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
                bot.delete_message(call.message.chat.id, call.message.message_id)
        
        # Отправить сообщение в чат (ИСПРАВЛЕНО!)
        elif data.startswith('send_'):
            parts = data.split('_', 2)
            if len(parts) == 3:
                lobby_code = parts[1]
                chat_message = parts[2]
                
                if lobby_code in lobbies:
                    user_name = call.from_user.first_name
                    
                    add_chat_message(lobby_code, user_name, chat_message)
                    broadcast_to_lobby(lobby_code, 
                                      f"💬 <b>{user_name}:</b> {chat_message}",
                                      exclude_user=user_id)
                    
                    bot.answer_callback_query(call.id, "✅ Сообщение отправлено!")
                    bot.delete_message(call.message.chat.id, call.message.message_id)
        
        # Переключить ведущего
        elif data.startswith('toggle_host_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может менять эту настройку!")
                    return
                
                lobby['host_is_player'] = not lobby['host_is_player']
                
                for player in lobby['players']:
                    if player['is_host']:
                        player['is_playing'] = lobby['host_is_player']
                
                bot.edit_message_reply_markup(call.message.chat.id, 
                                             call.message.message_id,
                                             reply_markup=create_lobby_menu(lobby_code))
                bot.answer_callback_query(call.id, 
                                         f"✅ Ведущий теперь {'участвует' if lobby['host_is_player'] else 'не участвует'} в игре!")
        
        # Переключить авто-закрытие
        elif data.startswith('toggle_auto_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может менять эту настройку!")
                    return
                
                lobby['auto_close'] = not lobby['auto_close']
                bot.edit_message_reply_markup(call.message.chat.id, 
                                             call.message.message_id,
                                             reply_markup=create_lobby_menu(lobby_code))
                bot.answer_callback_query(call.id, 
                                         f"✅ Авто-закрытие {'включено' if lobby['auto_close'] else 'выключено'}!")
        
        # Просмотр голосов
        elif data.startswith('view_votes_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                if not lobby['game_started']:
                    bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
                    return
                
                votes_text = "<b>👁️ Текущие голоса:</b>\n\n"
                
                if not lobby['votes']:
                    votes_text += "Пока никто не проголосовал."
                else:
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
        
        # Сдаться
        elif data.startswith('surrender_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                if not lobby['game_started']:
                    bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
                    return
                
                player = next((p for p in lobby['players'] if p['id'] == user_id), None)
                if not player or not player['is_playing']:
                    bot.answer_callback_query(call.id, "⚠️ Вы не участвуете в игре!")
                    return
                
                player['is_playing'] = False
                broadcast_to_lobby(lobby_code, 
                                  f"⚠️ <b>{player['name']} сдался и выбывает из игры!</b>")
                
                bot.answer_callback_query(call.id, "✅ Вы сдались!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
                
                playing_players = [p for p in lobby['players'] if p['is_playing']]
                if len(playing_players) < 3:
                    lobby['game_started'] = False
                    broadcast_to_lobby(lobby_code, 
                                      "⚠️ Игра завершена, осталось меньше 3 игроков!")
        
        # Чат лобби (из меню)
        elif data.startswith('lobby_chat_'):
            if lobby_code in lobbies:
                
                if lobby_code in chat_messages and chat_messages[lobby_code]:
                    history = ""
                    for msg in list(chat_messages[lobby_code])[-10:]:
                        time_str = datetime.fromtimestamp(msg['time']).strftime('%H:%M')
                        history += f"<b>{msg['user']}</b> ({time_str}): {msg['message']}\n"
                    
                    bot.edit_message_text(f"<b>💬 Чат лобби:</b>\n\n{history}", 
                                        call.message.chat.id, 
                                        call.message.message_id,
                                        reply_markup=types.InlineKeyboardMarkup().add(
                                            types.InlineKeyboardButton("🔙 Назад", callback_data=f"menu_{lobby_code}")
                                        ))
                else:
                    bot.edit_message_text("💬 В чате пока нет сообщений.", 
                                        call.message.chat.id, 
                                        call.message.message_id,
                                        reply_markup=types.InlineKeyboardMarkup().add(
                                            types.InlineKeyboardButton("🔙 Назад", callback_data=f"menu_{lobby_code}")
                                        ))
        
        # Чат игры
        elif data.startswith('game_chat_'):
            if lobby_code in lobbies:
                
                if lobby_code in chat_messages and chat_messages[lobby_code]:
                    history = ""
                    for msg in list(chat_messages[lobby_code])[-10:]:
                        time_str = datetime.fromtimestamp(msg['time']).strftime('%H:%M')
                        history += f"<b>{msg['user']}</b> ({time_str}): {msg['message']}\n"
                    
                    bot.edit_message_text(f"<b>💬 Чат лобби:</b>\n\n{history}", 
                                        call.message.chat.id, 
                                        call.message.message_id,
                                        reply_markup=types.InlineKeyboardMarkup().add(
                                            types.InlineKeyboardButton("🔙 Назад", callback_data=f"game_menu_{lobby_code}")
                                        ))
                else:
                    bot.edit_message_text("💬 В чате пока нет сообщений.", 
                                        call.message.chat.id, 
                                        call.message.message_id,
                                        reply_markup=types.InlineKeyboardMarkup().add(
                                            types.InlineKeyboardButton("🔙 Назад", callback_data=f"game_menu_{lobby_code}")
                                        ))
        
        # Статистика лобби
        elif data.startswith('stats_'):
            if lobby_code in lobbies and lobby_code in lobby_stats:
                stats = lobby_stats[lobby_code]
                stats_text = f"""
<b>📊 Статистика лобби:</b>

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
        
        # Статистика раунда
        elif data.startswith('round_stats_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                if not lobby['game_started']:
                    bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
                    return
                
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
    
    except Exception as e:
        print(f"Ошибка в callback: {type(e).__name__}: {e}")
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка!")

# Игровая логика
def start_round(lobby_code):
    lobby = lobbies[lobby_code]
    
    lobby['votes'] = {}
    lobby['all_spies_mode'] = (lobby['round_number'] % 5 == 0)
    if lobby['all_spies_mode']:
        global_stats['all_spies_rounds'] += 1
    
    lobby['word'] = get_random_word(lobby['theme'], lobby['custom_word'])
    
    playing_players = [p for p in lobby['players'] if p['is_playing']]
    
    if lobby['all_spies_mode']:
        lobby['spy_id'] = None
        spy_text = "🕵️ <b>СЕКРЕТНЫЙ РАУНД!</b> ВСЕ игроки - шпионы!"
    else:
        available_players = [p for p in playing_players if p['id'] != lobby.get('previous_spy_id')]
        if not available_players:
            available_players = playing_players
        
        spy = random.choice(available_players)
        lobby['spy_id'] = spy['id']
        lobby['previous_spy_id'] = spy['id']
        spy_text = "Один из игроков - <b>ШПИОН</b>! 🕵️"
    
    for player in playing_players:
        player_name = player['name']
        
        if lobby['all_spies_mode']:
            message = f"""
<b>🎮 Раунд {lobby['round_number']} начался!</b>

{spy_text}

Тема: <b>{get_theme_name(lobby['theme'])}</b>

⚠️ <b>Вы не знаете слово!</b>
Все игроки в этом раунде - шпионы.
            """
        elif player['id'] == lobby['spy_id']:
            message = f"""
<b>🎮 Раунд {lobby['round_number']} начался!</b>

{spy_text}

Тема: <b>{get_theme_name(lobby['theme'])}</b>

⚠️ <b>ВЫ - ШПИОН!</b> 🕵️

Вы НЕ знаете слово.

Слово, которое знают другие: <code>?? ??? ??</code>
            """
        else:
            message = f"""
<b>🎮 Раунд {lobby['round_number']} начался!</b>

{spy_text}

Тема: <b>{get_theme_name(lobby['theme'])}</b>

✅ <b>Вы знаете слово!</b>

Слово: <code>{lobby['word']}</code>

Ваша задача - описать слово и вычислить шпиона.
            """
        
        try:
            bot.send_message(player['id'], message, reply_markup=get_game_keyboard())
        except:
            pass
    
    lobby_stats[lobby_code]['rounds_played'] += 1
    
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
    
    playing_players = [p for p in lobby['players'] if p['is_playing']]
    voted_players = len(lobby['votes'])
    total_players = len(playing_players)
    
    if voted_players == total_players:
        end_round(lobby_code)
    elif voted_players >= total_players - 1 and lobby['auto_close']:
        end_round(lobby_code)

def end_round(lobby_code):
    lobby = lobbies[lobby_code]
    
    vote_counts = defaultdict(int)
    for voted_id in lobby['votes'].values():
        if voted_id == 'none':
            vote_counts['none'] += 1
        else:
            vote_counts[voted_id] += 1
    
    playing_players = [p for p in lobby['players'] if p['is_playing']]
    
    if lobby['all_spies_mode']:
        if vote_counts:
            max_votes = max(vote_counts.values())
            most_voted = [k for k, v in vote_counts.items() if v == max_votes]
            
            if len(most_voted) == 1 and most_voted[0] != 'none':
                winner = "players"
                winner_text = "🎯 <b>ИГРОКИ ВЫИГРАЛИ!</b>\nОни смогли выбрать 'шпиона'!"
                global_stats['players_wins'] += 1
                lobby_stats[lobby_code]['players_wins'] += 1
            else:
                winner = "spies"
                winner_text = "🕵️ <b>ШПИОНЫ ВЫИГРАЛИ!</b>\nНикто не был разоблачен!"
                global_stats['spy_wins'] += 1
                lobby_stats[lobby_code]['spy_wins'] += 1
        else:
            winner = "spies"
            winner_text = "🕵️ <b>ШПИОНЫ ВЫИГРАЛИ!</b>\nНикто не проголосовал!"
            global_stats['spy_wins'] += 1
            lobby_stats[lobby_code]['spy_wins'] += 1
    else:
        if lobby['spy_id'] in vote_counts and vote_counts[lobby['spy_id']] > 0:
            winner = "players"
            winner_text = "🎯 <b>ИГРОКИ ВЫИГРАЛИ!</b>\nОни нашли шпиона!"
            global_stats['players_wins'] += 1
            lobby_stats[lobby_code]['players_wins'] += 1
        else:
            winner = "spy"
            
            spy_name = "Неизвестный"
            spy = next((p for p in playing_players if p['id'] == lobby['spy_id']), None)
            if spy:
                spy_name = spy['name']
            
            winner_text = f"🕵️ <b>ШПИОН ВЫИГРАЛ!</b>\n{spy_name} остался незамеченным!"
            global_stats['spy_wins'] += 1
            lobby_stats[lobby_code]['spy_wins'] += 1
    
    results_text = f"""
<b>🏁 Раунд {lobby['round_number']} завершен!</b>

Тема: <b>{get_theme_name(lobby['theme'])}</b>
Слово: <code>{lobby['word']}</code>

<b>Результаты голосования:</b>
"""
    
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
    
    if not lobby['all_spies_mode'] and lobby['spy_id']:
        spy = next((p for p in playing_players if p['id'] == lobby['spy_id']), None)
        if spy:
            results_text += f"\n\n🕵️ Шпион был: <b>{spy['name']}</b>"
    
    broadcast_to_lobby(lobby_code, results_text, keyboard=get_game_keyboard())
    
    if lobby['voting_history']:
        lobby['voting_history'][-1]['votes'] = dict(lobby['votes'])
        lobby['voting_history'][-1]['result'] = winner
    
    lobby['round_number'] += 1
    lobby['votes'] = {}
    
    time.sleep(5)
    if lobby['game_started']:
        start_round(lobby_code)
    
    if lobby['round_number'] > 20:
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
    
    load_global_stats()
    
    print("🔄 Бот запущен и готов к работе!")
    print("📊 Загруженная статистика:")
    print(f"   Всего игр: {global_stats['total_games']}")
    print(f"   Уникальных игроков: {global_stats['total_players']}")
    print(f"   Активных лобби: {global_stats['active_lobbies']}")
    print("=" * 50)
    
    bot.infinity_polling()