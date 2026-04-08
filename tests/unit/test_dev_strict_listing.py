from backend.services.dev_strict_listing import dev_strict_listing_skip_reason


def test_dev_strict_parallel_all_words_required():
    v = {
        'parallel': 'Gold Refractor',
        'set_name': 'Topps Chrome',
    }
    assert dev_strict_listing_skip_reason('Player 2024 Topps Chrome #1 Gold', v) == 'dev_strict_parallel'
    assert dev_strict_listing_skip_reason('Player 2024 Topps Chrome #1 Gold Refractor', v) is None


def test_dev_strict_set_tokens_majority():
    v = {'parallel': 'Base', 'set_name': 'Bowman Chrome Sapphire'}
    assert dev_strict_listing_skip_reason('Player 2024 Bowman #12 base', v) == 'dev_strict_set_tokens'
    assert dev_strict_listing_skip_reason('Player 2024 Bowman Chrome Sapphire #12', v) is None
