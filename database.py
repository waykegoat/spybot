import json
import time
import os
from collections import defaultdict, deque

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

def save_global_stats():
    try:
        with open('global_stats.json', 'w', encoding='utf-8') as f:
            json.dump(global_stats, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_global_stats():
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

def get_lobby(lobby_code):
    return lobbies.get(lobby_code)

def get_user_lobby(user_id):
    return user_to_lobby.get(user_id)

def is_user_in_lobby(user_id):
    return user_id in user_to_lobby