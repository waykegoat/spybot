from telebot import types
from database import lobbies

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
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🎮 Создать новое лобби", callback_data="create_new_lobby"),
        types.InlineKeyboardButton("📊 Глобальная статистика", callback_data="global_stats"),
        types.InlineKeyboardButton("📖 Правила игры", callback_data="show_rules"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_to_main")
    )
    return keyboard