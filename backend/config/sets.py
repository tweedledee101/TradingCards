"""
High-Value Card Sets by Sport

These sets have parallels/inserts worth $10-$100+ that get buried
in generic "{player} card" searches (eBay returns max 200 results).

Set-specific queries like "{player} Topps Chrome" surface these cards.
"""

HIGH_VALUE_SETS = {
    'Baseball': [
        'Topps Chrome',
        'Bowman Chrome',
        'Topps Heritage',
        'Stadium Club',
        'Topps Finest',
        'Topps Inception',
    ],
    'Basketball': [
        'Prizm',
        'Select',
        'Mosaic',
        'Optic',
        'National Treasures',
    ],
    'Football': [
        'Prizm',
        'Select',
        'Mosaic',
        'Optic',
        'National Treasures',
    ],
}


def get_set_queries(player_name: str, sport: str) -> list:
    """Return set-specific search queries for a player.
    
    Args:
        player_name: e.g. "Shohei Ohtani"
        sport: e.g. "Baseball"
    
    Returns:
        List of queries like ["Shohei Ohtani Topps Chrome", ...]
    """
    sets = HIGH_VALUE_SETS.get(sport, [])
    return [f"{player_name} {s}" for s in sets]
