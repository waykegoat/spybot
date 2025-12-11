import random
import time
from datetime import datetime
from config import THEMES

def generate_lobby_code():
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    numbers = '0123456789'
    while True:
        code = ''.join(random.choices(letters, k=3)) + ''.join(random.choices(numbers, k=3))
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

def is_admin(user_id):
    from config import ADMIN_ID
    return user_id == ADMIN_ID

def format_time(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%H:%M')