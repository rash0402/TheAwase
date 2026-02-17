from theawase.config import Difficulty, DIFFICULTY_PRESETS

def test_difficulty_presets_exist():
    for d in Difficulty:
        assert d in DIFFICULTY_PRESETS

def test_easy_is_more_active_than_hard():
    easy = DIFFICULTY_PRESETS[Difficulty.EASY]
    hard = DIFFICULTY_PRESETS[Difficulty.HARD]
    assert easy['attack_rate'] > hard['attack_rate']
    assert easy['hunger_range'][0] > hard['hunger_range'][1]  # easy min > hard max

def test_normal_is_current_defaults():
    normal = DIFFICULTY_PRESETS[Difficulty.NORMAL]
    assert normal['attack_rate'] == 2.0
    assert normal['hunger_range'] == (0.3, 0.5)
    assert normal['caution_range'] == (0.2, 0.6)
