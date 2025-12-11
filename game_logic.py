import time
from collections import defaultdict
from database import *
from utils import *
from keyboards import *

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
        spy_text = "🕵️ СЕКРЕТНЫЙ РАУНД! ВСЕ игроки - шпионы!"
    else:
        available_players = [p for p in playing_players if p['id'] != lobby.get('previous_spy_id')]
        if not available_players:
            available_players = playing_players
        
        spy = random.choice(available_players)
        lobby['spy_id'] = spy['id']
        lobby['previous_spy_id'] = spy['id']
        spy_text = "Один из игроков - ШПИОН! 🕵️"
    
    for player in playing_players:
        player_name = player['name']
        
        if lobby['all_spies_mode']:
            message = f"""
🎮 Раунд {lobby['round_number']} начался!

{spy_text}

Тема: {get_theme_name(lobby['theme'])}

⚠️ Вы не знаете слово!
Все игроки в этом раунде - шпионы.
            """
        elif player['id'] == lobby['spy_id']:
            message = f"""
🎮 Раунд {lobby['round_number']} начался!

{spy_text}

Тема: {get_theme_name(lobby['theme'])}

⚠️ ВЫ - ШПИОН! 🕵️

Вы НЕ знаете слово.

Слово, которое знают другие: <code>?? ??? ??</code>
            """
        else:
            message = f"""
🎮 Раунд {lobby['round_number']} начался!

{spy_text}

Тема: {get_theme_name(lobby['theme'])}

✅ Вы знаете слово!

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
                winner_text = "🎯 ИГРОКИ ВЫИГРАЛИ!\nОни смогли выбрать 'шпиона'!"
                global_stats['players_wins'] += 1
                lobby_stats[lobby_code]['players_wins'] += 1
            else:
                winner = "spies"
                winner_text = "🕵️ ШПИОНЫ ВЫИГРАЛИ!\nНикто не был разоблачен!"
                global_stats['spy_wins'] += 1
                lobby_stats[lobby_code]['spy_wins'] += 1
        else:
            winner = "spies"
            winner_text = "🕵️ ШПИОНЫ ВЫИГРАЛИ!\nНикто не проголосовал!"
            global_stats['spy_wins'] += 1
            lobby_stats[lobby_code]['spy_wins'] += 1
    else:
        if lobby['spy_id'] in vote_counts and vote_counts[lobby['spy_id']] > 0:
            winner = "players"
            winner_text = "🎯 ИГРОКИ ВЫИГРАЛИ!\nОни нашли шпиона!"
            global_stats['players_wins'] += 1
            lobby_stats[lobby_code]['players_wins'] += 1
        else:
            winner = "spy"
            
            spy_name = "Неизвестный"
            spy = next((p for p in playing_players if p['id'] == lobby['spy_id']), None)
            if spy:
                spy_name = spy['name']
            
            winner_text = f"🕵️ ШПИОН ВЫИГРАЛ!\n{spy_name} остался незамеченным!"
            global_stats['spy_wins'] += 1
            lobby_stats[lobby_code]['spy_wins'] += 1
    
    results_text = f"""
🏁 Раунд {lobby['round_number']} завершен!

Тема: {get_theme_name(lobby['theme'])}
Слово: <code>{lobby['word']}</code>

Результаты голосования:
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
            results_text += f"\n\n🕵️ Шпион был: {spy['name']}"
    
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
🎮 Игра завершена!

Игра автоматически завершена после 20 раундов.

Спасибо за игру! 🎉
        """
        broadcast_to_lobby(lobby_code, final_text, keyboard=get_lobby_keyboard())
    
    save_global_stats()