import telebot
from telebot import types
from datetime import datetime
from collections import defaultdict

from config import CHANNEL_ID, CHANNEL_URL, CHANNEL_USERNAME, MIN_PLAYERS
from database import *
from utils import *
from keyboards import *
from bot_instance import bot  # Импортируем из главной папки

def require_subscription(func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        
        try:
            member = bot.get_chat_member(CHANNEL_ID, user_id)
            status = member.status
            is_subscribed = status in ['creator', 'administrator', 'member']
        except:
            is_subscribed = False
        
        if not is_subscribed:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL),
                types.InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")
            )
            
            bot.send_message(
                message.chat.id,
                f"📢 Для использования бота нужно подписаться на наш канал!\n\nКанал: {CHANNEL_USERNAME}\nПосле подписки нажмите '✅ Я подписался'",
                reply_markup=keyboard
            )
            return
        
        return func(message, *args, **kwargs)
    
    return wrapper

@bot.message_handler(commands=['start', 'help'])
@require_subscription
def handle_start(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if user_id not in all_players:
        all_players.add(user_id)
        global_stats['total_players'] = len(all_players)
    
    welcome_text = f"""
🎮 Добро пожаловать в игру "Универсальный Шпион"!

{user_name}, вы находитесь в главном меню бота.

Основные команды:
/new - создать новое лобби
/join [код] - войти в лобби
/leave - покинуть лобби
/menu - меню лобби/игры
/chat [текст] - отправить сообщение в чат лобби
/rules - правила игры
/vote - голосовать за шпиона

Также вы можете просто написать код лобби (например: ABC123) чтобы присоединиться!

Используйте кнопки ниже для навигации!
    """
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.message_handler(commands=['new'])
@require_subscription
def handle_new(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if user_id in user_to_lobby:
        lobby_code = user_to_lobby[user_id]
        bot.send_message(message.chat.id, f"⚠️ Вы уже находитесь в лобби {lobby_code}. Покиньте его сначала.")
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
✅ Лобби создано!

Код лобби: <code>{lobby_code}</code>

Отправьте этот код друзьям:
<code>/join {lobby_code}</code>
или просто отправьте код: <code>{lobby_code}</code>

📋 <b>Для начала игры нужно минимум {MIN_PLAYERS} игрока!</b>

Игроки в лобби (1/7):
👑 {user_name} (Ведущий)

Используйте кнопки ниже для управления:
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
        bot.send_message(message.chat.id, f"⚠️ Вы уже находитесь в лобби {lobby_code}.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "⚠️ Укажите код лобби!\nПример: <code>/join ABC123</code>\nИли просто отправьте код: <code>ABC123</code>")
        return
    
    lobby_code = parts[1].upper().strip()
    process_join_user(user_id, user_name, lobby_code, message)

@bot.message_handler(func=lambda message: len(message.text) == 6 and message.text[:3].isalpha() and message.text[3:].isdigit())
@require_subscription
def handle_lobby_code(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if user_id in user_to_lobby:
        lobby_code = user_to_lobby[user_id]
        bot.send_message(message.chat.id, f"⚠️ Вы уже находитесь в лобби {lobby_code}.")
        return
    
    lobby_code = message.text.upper().strip()
    process_join_user(user_id, user_name, lobby_code, message)

def process_join_user(user_id, user_name, lobby_code, message):
    if lobby_code not in lobbies:
        bot.send_message(message.chat.id, f"⚠️ Лобби с кодом <code>{lobby_code}</code> не найдено!")
        return
    
    lobby = lobbies[lobby_code]
    
    if lobby['game_started']:
        bot.send_message(message.chat.id, f"⚠️ Игра в лобби {lobby_code} уже начата!")
        return
    
    if len(lobby['players']) >= 7:
        bot.send_message(message.chat.id, f"⚠️ В лобби {lobby_code} уже максимальное количество игроков (7/7)!")
        return
    
    for player in lobby['players']:
        if player['id'] == user_id:
            bot.send_message(message.chat.id, f"⚠️ Вы уже в этом лобби!")
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
    
    players_list = "\n".join([f"{'👑' if p['is_host'] else '👤'} {p['name']}" for p in lobby['players']])
    
    playing_count = len([p for p in lobby['players'] if p['is_playing']])
    status_text = "✅ Можно начинать!" if playing_count >= MIN_PLAYERS else f"⏳ Нужно еще {MIN_PLAYERS - playing_count} игрока"
    
    welcome_text = f"""
✅ Вы присоединились к лобби {lobby_code}!

<b>Статус:</b> {status_text}

Игроки в лобби ({len(lobby['players'])}/7):
{players_list}

Ведущий: {next(p['name'] for p in lobby['players'] if p['is_host'])}

Используйте кнопки ниже:
    """
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_lobby_keyboard())
    bot.send_message(message.chat.id, "🎮 Меню лобби:", reply_markup=create_lobby_menu(lobby_code))
    
    # Уведомление остальным игрокам
    playing_count = len([p for p in lobby['players'] if p['is_playing']])
    from game_logic import broadcast_to_lobby
    broadcast_to_lobby(lobby_code, 
        f"👤 {user_name} присоединился к лобби!\n"
        f"Теперь игроков: {len(lobby['players'])}/7\n"
        f"<b>Статус:</b> {'✅ Можно начинать игру!' if playing_count >= MIN_PLAYERS else f'⏳ Нужно еще {MIN_PLAYERS - playing_count} игрока'}",
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
        for player in lobby['players']:
            if player['id'] != user_id:
                try:
                    bot.send_message(player['id'], f"⚠️ Лобби {lobby_code} закрыто, потому что ведущий покинул игру.")
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
        
        bot.send_message(message.chat.id, "✅ Вы закрыли лобби и вышли из игры.\n\nЧто вы хотите сделать дальше?", reply_markup=create_host_options_keyboard())
        
    else:
        lobby['players'] = [p for p in lobby['players'] if p['id'] != user_id]
        del user_to_lobby[user_id]
        
        bot.send_message(message.chat.id, f"✅ Вы покинули лобби {lobby_code}.")
        bot.send_message(message.chat.id, "Главное меню:", reply_markup=get_main_keyboard())
        
        # Уведомление остальным игрокам
        from game_logic import broadcast_to_lobby
        broadcast_to_lobby(lobby_code, f"👤 {user_name} покинул лобби.\nОсталось игроков: {len(lobby['players'])}/7", exclude_user=user_id)
        
        if lobby['game_started'] and len([p for p in lobby['players'] if p['is_playing']]) < MIN_PLAYERS:
            lobby['game_started'] = False
            broadcast_to_lobby(lobby_code, f"⚠️ Игра завершена, потому что осталось меньше {MIN_PLAYERS} игроков!")
    
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
📖 Правила игры "Шпион":

1. Цель игры:
   • Один из игроков (шпион) НЕ знает слово
   • Шпион должен скрывать это
   • Остальные должны вычислить шпиона

2. Ход игры:
   • Каждый раунд - новое слово и шпион
   • Игроки по очереди описывают слово
   • После обсуждения - голосование
   • Если шпиона вычислили - побеждают игроки
   • Если шпион остался незамеченным - побеждает шпион

Удачи в игре! 🎮
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
        bot.send_message(message.chat.id, "⚠️ Укажите текст сообщения!\nПример: <code>/chat Привет всем!</code>")
        return
    
    chat_message = parts[1]
    lobby_code = user_to_lobby[user_id]
    user_name = message.from_user.first_name
    
    add_chat_message(lobby_code, user_name, chat_message)
    bot.send_message(message.chat.id, "✅ Сообщение отправлено в чат лобби!")
    
    from game_logic import broadcast_to_lobby
    broadcast_to_lobby(lobby_code, f"💬 {user_name}: {chat_message}", exclude_user=user_id)

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
    
    bot.send_message(message.chat.id, "🕵️ Голосование за шпиона:\nВыберите игрока:", reply_markup=create_voting_keyboard(lobby_code, user_id))

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text
    
    if text == "🎮 Создать лобби":
        handle_new(message)
    
    elif text == "🔗 Войти в лобби":
        bot.send_message(message.chat.id, "Введите код лобби:\nПример: <code>ABC123</code>\n(можно просто отправить код без /join)")
        bot.register_next_step_handler(message, process_join_code)
    
    elif text == "📖 Правила":
        handle_rules(message)
    
    elif text == "ℹ️ Помощь":
        handle_start(message)
    
    elif text == "👑 Админ-панель":
        if is_admin(user_id):
            bot.send_message(message.chat.id, "🔧 Админ-панель:", reply_markup=types.InlineKeyboardMarkup().add(
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
            bot.send_message(message.chat.id, f"👥 Игроки в лобби {lobby_code} ({len(lobby['players'])}/7):\n\n" + "\n".join(players_list) + f"\n\nСтатус: {status}")
    
    elif text == "🎨 Сменить тему":
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            lobby = lobbies[lobby_code]
            
            is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
            if not is_host:
                bot.send_message(message.chat.id, f"⚠️ Только ведущий может менять тему!")
                return
            
            current_theme = get_theme_name(lobby['theme'])
            if lobby['theme'] == 'custom' and lobby['custom_word']:
                current_word = f"\nТекущее слово: <code>{lobby['custom_word']}</code>"
            else:
                current_word = ""
            
            theme_text = f"""
🎨 Смена темы:

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
                    history += f"{msg['user']} ({time_str}): {msg['message']}\n"
                
                bot.send_message(message.chat.id, f"💬 История чата:\n\n{history}")
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
            
            bot.send_message(message.chat.id, "🕵️ Голосование за шпиона:\nВыберите игрока:", reply_markup=create_voting_keyboard(lobby_code, user_id))
    
    elif text == "👁️ Посмотреть голоса":
        if user_id in user_to_lobby:
            lobby_code = user_to_lobby[user_id]
            lobby = lobbies[lobby_code]
            
            if not lobby['game_started']:
                bot.send_message(message.chat.id, "⚠️ Игра еще не начата!")
                return
            
            votes_text = "👁️ Текущие голоса:\n\n"
            
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
                    votes_text += f"{voted_player}: {len(voters)} голосов\n"
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
            
            callback_text = text[:100]
            
            bot.send_message(message.chat.id, f"Отправить в чат лобби?\n\n<code>{truncated_text}</code>", reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("✅ Да", callback_data=f"send_{lobby_code}_{callback_text}"),
                types.InlineKeyboardButton("❌ Нет", callback_data="cancel")
            ))
        else:
            bot.send_message(message.chat.id, "Используйте кнопки ниже:", reply_markup=get_main_keyboard())

def process_join_code(message):
    user_id = message.from_user.id
    lobby_code = message.text.upper().strip()
    
    if len(lobby_code) != 6 or not lobby_code[:3].isalpha() or not lobby_code[3:].isdigit():
        bot.send_message(message.chat.id, "⚠️ Неверный формат кода! Пример: <code>ABC123</code>")
        return
    
    if lobby_code in lobbies:
        process_join_user(user_id, message.from_user.first_name, lobby_code, message)
    else:
        bot.send_message(message.chat.id, f"⚠️ Лобби <code>{lobby_code}</code> не найдено!")