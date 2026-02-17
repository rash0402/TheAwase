"""魚のattack_rateパラメータのテスト"""
from theawase.entities.fish import FishAI


def test_fish_accepts_attack_rate():
    fish = FishAI(attack_rate=3.0)
    assert fish.attack_rate == 3.0


def test_fish_default_attack_rate():
    fish = FishAI()
    assert fish.attack_rate == 2.0  # 現在のハードコード値と同じ


def test_fish_attack_rate_stored():
    fish = FishAI(attack_rate=1.0)
    assert fish.attack_rate == 1.0
