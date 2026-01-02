from telebot import types
from datetime import datetime
from collections import defaultdict

from config import CHANNEL_ID, MIN_PLAYERS
from database import *
from utils import *
from keyboards import *
from bot_instance import bot  # Импортируем из главной папки

def extract_lobby_code(data):
    if data.startswith('send_'):
        parts = data.split('_', 2)
        if len(parts) >= 2:
            return parts[1]
        return None
    
    if data.startswith('vote_'):
        parts = data.split('_')
        if len(parts) >= 3:
            if parts[1].isdigit() or parts[1] == 'none':
                return parts[2]
        return None
    
    if data.startswith('settheme_'):
        parts = data.split('_')
        if len(parts) >= 3:
            return parts[2]
        return None
    
    prefixes = [
        'menu_', 'start_', 'theme_menu_', 'game_menu_', 'vote_menu_',
        'end_game_', 'end_round_', 'new_round_', 'leave_', 'toggle_host_',
        'toggle_auto_', 'view_votes_', 'surrender_', 'lobby_chat_',
        'game_chat_', 'stats_', 'round_stats_'
    ]
    
    for prefix in prefixes:
        if data.startswith(prefix):
            return data[len(prefix):]
    
    return None

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def handle_check_subscription(call):
    user_id = call.from_user.id
    
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        status = member.status
        is_subscribed = status in ['creator', 'administrator', 'member']
    except:
        is_subscribed = False
    
    if is_subscribed:
        bot.answer_callback_query(call.id, "✅ Спасибо за подписку!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        bot.send_message(
            call.message.chat.id,
            "🎮 Добро пожаловать! Теперь вы можете использовать бота.",
            reply_markup=get_main_keyboard()
        )
    else:
        bot.answer_callback_query(
            call.id,
            "❌ Вы ещё не подписались!",
            show_alert=True
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    
    try:
        if data == 'create_new_lobby':
            from handlers import handle_new
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
📊 Глобальная статистика:

🎮 Всего игр: {global_stats['total_games']}
👥 Уникальных игроков: {global_stats['total_players']}
🏠 Создано лобби: {global_stats['total_lobbies']}

🏆 Побед шпионов: {global_stats['spy_wins']}
🎯 Побед игроков: {global_stats['players_wins']}

⏱️ Время работы: {hours}ч {minutes}м
            """
            
            bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, reply_markup=create_host_options_keyboard())
            return
        
        elif data == 'show_rules':
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
            bot.edit_message_text(rules_text, call.message.chat.id, call.message.message_id, reply_markup=create_host_options_keyboard())
            return
        
        elif data == 'go_to_main':
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, "🏠 Главное меню\n\nВыберите действие:", reply_markup=get_main_keyboard())
            return
        
        elif data == 'cancel':
            bot.answer_callback_query(call.id, "❌ Отменено")
            bot.delete_message(call.message.chat.id, call.message.message_id)
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
📊 Глобальная статистика:

🎮 Всего игр: {global_stats['total_games']}
👥 Уникальных игроков: {global_stats['total_players']}
🏠 Создано лобби: {global_stats['total_lobbies']}

🏆 Побед шпионов: {global_stats['spy_wins']}
🎯 Побед игроков: {global_stats['players_wins']}

🔴 Активных лобби: {global_stats['active_lobbies']}
⏱️ Время работы: {hours}ч {minutes}м
                """
                
                bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🎮 Лобби", callback_data="admin_lobbies"),
                    types.InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")
                ))
            elif data == 'admin_lobbies':
                if not lobbies:
                    lobbies_text = "🔴 Активных лобби нет"
                else:
                    lobbies_text = "🎮 Активные лобби:\n\n"
                    for code, lobby in lobbies.items():
                        created_time = datetime.fromtimestamp(lobby['created_time']).strftime('%H:%M')
                        players_count = len(lobby['players'])
                        status = "🟢 Игра" if lobby['game_started'] else "🟡 Ожидание"
                        
                        lobbies_text += f"<code>{code}</code> - {players_count}/7 игроков\n"
                        lobbies_text += f"Ведущий: {lobby['players'][0]['name']}\n"
                        lobbies_text += f"Создано: {created_time} | Статус: {status}\n"
                        lobbies_text += f"Раунд: {lobby['round_number']}\n"
                        lobbies_text += "─" * 20 + "\n"
                
                bot.edit_message_text(lobbies_text, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
                    types.InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")
                ))
            elif data == 'admin_close':
                bot.delete_message(call.message.chat.id, call.message.message_id)
            return
        
        lobby_code = extract_lobby_code(data)
        
        if lobby_code and lobby_code not in lobbies:
            bot.answer_callback_query(call.id, "⚠️ Лобби больше не существует!")
            
            bot.edit_message_text(
                "❌ Лобби больше не существует!\n\nВы можете создать новое лобби или вернуться в главное меню.",
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
        
        if data.startswith('menu_'):
            if lobby_code in lobbies:
                bot.edit_message_text("🎮 Меню лобби:", call.message.chat.id, call.message.message_id, reply_markup=create_lobby_menu(lobby_code))
        
        elif data.startswith('theme_menu_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может менять тему!")
                    return
                
                current_theme = get_theme_name(lobby['theme'])
                theme_text = f"🎨 Выберите тему:\n\nТекущая: {current_theme}"
                bot.edit_message_text(theme_text, call.message.chat.id, call.message.message_id, reply_markup=create_theme_keyboard(lobby_code))
        
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
                                bot.send_message(message.chat.id, f"✅ Слово установлено: <code>{lobby['custom_word']}</code>")
                                bot.send_message(message.chat.id, "🎮 Меню лобби:", reply_markup=create_lobby_menu(lobby_code))
                        
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
        
        elif data.startswith('start_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может начать игру!")
                    return
                
                playing_players = [p for p in lobby['players'] if p['is_playing']]
                if len(playing_players) < MIN_PLAYERS:
                    bot.answer_callback_query(call.id, f"⚠️ Нужно минимум {MIN_PLAYERS} игрока!")
                    return
                
                lobby['game_started'] = True
                lobby['round_number'] = 1
                global_stats['total_games'] += 1
                lobby_stats[lobby_code]['games_played'] += 1
                
                from game_logic import start_round
                start_round(lobby_code)
                
                bot.answer_callback_query(call.id, "✅ Игра начата!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
        
        elif data.startswith('vote_') and data[5:].split('_')[0].isdigit():
            parts = data.split('_')
            if len(parts) >= 3:
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
                        from game_logic import check_voting_complete
                        check_voting_complete(lobby_code)
                except ValueError:
                    bot.answer_callback_query(call.id, "⚠️ Ошибка голосования!")
        
        elif data.startswith('vote_none_'):
            lobby_code = data[10:]
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
                from game_logic import check_voting_complete
                check_voting_complete(lobby_code)
        
        elif data.startswith('game_menu_'):
            if lobby_code in lobbies:
                bot.edit_message_text("🎮 Меню игры:", call.message.chat.id, call.message.message_id, reply_markup=create_game_menu_keyboard(lobby_code))
        
        elif data.startswith('vote_menu_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                if not lobby['game_started']:
                    bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
                    return
                
                bot.edit_message_text("🕵️ Голосование за шпиона:\nВыберите игрока:", call.message.chat.id, call.message.message_id, reply_markup=create_voting_keyboard(lobby_code, user_id))
        
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
                
                from game_logic import broadcast_to_lobby
                broadcast_to_lobby(lobby_code, "⚠️ Игра завершена ведущим!", keyboard=get_lobby_keyboard())
                
                bot.answer_callback_query(call.id, "✅ Игра завершена!")
                bot.edit_message_text("✅ Игра завершена!", call.message.chat.id, call.message.message_id, reply_markup=create_lobby_menu(lobby_code))
        
        elif data.startswith('end_round_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может завершить раунд!")
                    return
                
                from game_logic import end_round
                end_round(lobby_code)
                bot.answer_callback_query(call.id, "✅ Раунд завершен!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
        
        elif data.startswith('new_round_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может начать новый раунд!")
                    return
                
                from game_logic import start_round
                start_round(lobby_code)
                bot.answer_callback_query(call.id, "✅ Новый раунд начат!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
        
        elif data.startswith('leave_'):
            if lobby_code in lobbies:
                from handlers import handle_leave
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
        
        elif data.startswith('send_'):
            parts = data.split('_', 2)
            if len(parts) == 3:
                lobby_code = parts[1]
                chat_message = parts[2]
                
                if lobby_code in lobbies:
                    user_name = call.from_user.first_name
                    
                    add_chat_message(lobby_code, user_name, chat_message)
                    from game_logic import broadcast_to_lobby
                    broadcast_to_lobby(lobby_code, f"💬 {user_name}: {chat_message}", exclude_user=user_id)
                    
                    bot.answer_callback_query(call.id, "✅ Сообщение отправлено!")
                    bot.delete_message(call.message.chat.id, call.message.message_id)
        
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
                
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_lobby_menu(lobby_code))
                bot.answer_callback_query(call.id, f"✅ Ведущий теперь {'участвует' if lobby['host_is_player'] else 'не участвует'} в игре!")
        
        elif data.startswith('toggle_auto_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                is_host = any(p['id'] == user_id and p['is_host'] for p in lobby['players'])
                if not is_host:
                    bot.answer_callback_query(call.id, "⚠️ Только ведущий может менять эту настройку!")
                    return
                
                lobby['auto_close'] = not lobby['auto_close']
                bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_lobby_menu(lobby_code))
                bot.answer_callback_query(call.id, f"✅ Авто-закрытие {'включено' if lobby['auto_close'] else 'выключено'}!")
        
        elif data.startswith('view_votes_'):
            if lobby_code in lobbies:
                lobby = lobbies[lobby_code]
                
                if not lobby['game_started']:
                    bot.answer_callback_query(call.id, "⚠️ Игра еще не начата!")
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
                
                bot.edit_message_text(votes_text, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data=f"game_menu_{lobby_code}")
                ))
        
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
                from game_logic import broadcast_to_lobby
                broadcast_to_lobby(lobby_code, f"⚠️ {player['name']} сдался и выбывает из игры!")
                
                bot.answer_callback_query(call.id, "✅ Вы сдались!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
                
                playing_players = [p for p in lobby['players'] if p['is_playing']]
                if len(playing_players) < MIN_PLAYERS:
                    lobby['game_started'] = False
                    broadcast_to_lobby(lobby_code, f"⚠️ Игра завершена, осталось меньше {MIN_PLAYERS} игроков!")
        
        elif data.startswith('lobby_chat_'):
            if lobby_code in lobbies:
                
                if lobby_code in chat_messages and chat_messages[lobby_code]:
                    history = ""
                    for msg in list(chat_messages[lobby_code])[-10:]:
                        time_str = datetime.fromtimestamp(msg['time']).strftime('%H:%M')
                        history += f"{msg['user']} ({time_str}): {msg['message']}\n"
                    
                    bot.edit_message_text(f"💬 Чат лобби:\n\n{history}", call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🔙 Назад", callback_data=f"menu_{lobby_code}")
                    ))
                else:
                    bot.edit_message_text("💬 В чате пока нет сообщений.", call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🔙 Назад", callback_data=f"menu_{lobby_code}")
                    ))
        
        elif data.startswith('game_chat_'):
            if lobby_code in lobbies:
                
                if lobby_code in chat_messages and chat_messages[lobby_code]:
                    history = ""
                    for msg in list(chat_messages[lobby_code])[-10:]:
                        time_str = datetime.fromtimestamp(msg['time']).strftime('%H:%M')
                        history += f"{msg['user']} ({time_str}): {msg['message']}\n"
                    
                    bot.edit_message_text(f"💬 Чат лобби:\n\n{history}", call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🔙 Назад", callback_data=f"game_menu_{lobby_code}")
                    ))
                else:
                    bot.edit_message_text("💬 В чате пока нет сообщений.", call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🔙 Назад", callback_data=f"game_menu_{lobby_code}")
                    ))
        
        elif data.startswith('stats_'):
            if lobby_code in lobbies and lobby_code in lobby_stats:
                stats = lobby_stats[lobby_code]
                stats_text = f"""
📊 Статистика лобби:

🎮 Сыграно игр: {stats['games_played']}
🕵️ Побед шпионов: {stats['spy_wins']}
🎯 Побед игроков: {stats['players_wins']}
🔁 Сыграно раундов: {stats['rounds_played']}

Текущий раунд: {lobbies[lobby_code]['round_number']}
                """
                bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data=f"menu_{lobby_code}")
                ))
        
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
📊 Статистика раунда:

Раунд: {lobby['round_number']}
Тема: {get_theme_name(lobby['theme'])}
Слово: <code>{lobby['word']}</code>
Шпион: {spy_name}

Режим: {'🕵️ Все шпионы' if lobby['all_spies_mode'] else '🎮 Обычный'}

Проголосовало: {len(lobby['votes'])}/{len([p for p in lobby['players'] if p['is_playing']])}
                """
                bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data=f"game_menu_{lobby_code}")
                ))
    
    except Exception as e:
        print(f"Ошибка в callback: {type(e).__name__}: {e}")
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка!")