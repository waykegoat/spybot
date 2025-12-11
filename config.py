import os

API_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME', '@dimbub')
CHANNEL_URL = os.getenv('CHANNEL_URL', 'https://t.me/dimbub')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '-1003369490880'))

THEMES = {
    'dota2': [
        "Pudge", "Invoker", "Juggernaut", "Lina", "Crystal Maiden", "Anti-Mage",
        "Axe", "Zeus", "Slark", "Phantom Assassin", "Terrorblade", "Sven",
    ],
    
    'clashroyale': [
        "Рыцарь", "Лучники", "Ведьма", "Принц", "Голем", "Пекка", "Гигант",
        "Лава-щенок", "Минер", "Баллон", "Волшебник", "Стрелок",
    ],
    
    'brawlstars': [
        "Шэлли", "Кольт", "Булл", "Брок", "Эль Примо", "Роза", "Леон", "Спайк",
        "Кроу", "Джесси", "Нита", "Динамик", "Тик", "8-Бит", "Эмз", "Стью",
    ],
    
    'locations': [
        "Больница", "Ресторан", "Школа", "Тюрьма", "Космическая станция",
        "Банк", "Супермаркет", "Аэропорт", "Отель", "Кинотеатр", "Театр",
        "Музей", "Библиотека", "Спортзал", "Бассейн", "Пляж",
    ]
}