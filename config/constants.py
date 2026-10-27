# config/constants.py

SUITS = ['S', 'H', 'D', 'C']  # Spades, Hearts, Diamonds, Clubs
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']

PLAYERS = ['SOUTH', 'WEST', 'NORTH', 'EAST']
PLAYER_NEXT = {
    'SOUTH': 'WEST',
    'WEST': 'NORTH',
    'NORTH': 'EAST',
    'EAST': 'SOUTH'
}

SUIT_SYMBOLS = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
SUIT_COLORS = {'S': 'Black', 'H': 'Red', 'D': 'Red', 'C': 'Black'}
ROBOT_LABELS = ['RED', 'ORANGE', 'YELLOW', 'BLUE', 'PURPLE', 'GREEN']