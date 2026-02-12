"""
ハリス角度による横方向力のテスト

Phase 3改良版: 2次元ハリス張力ベクトルの検証
"""

import numpy as np
import pytest
from theawase.physics.bait import BaitModel
from theawase import config


def test_tippet_tension_vertical():
    """鉛直ハリスは旧挙動と一致すべき"""
    bait = BaitModel()
    bait.position = np.array([0.0, -0.45])  # 真下45cm
    float_pos = np.array([0.0, 0.0])
    fish_accel = np.array([0.0, 0.0])

    T = bait._calculate_tippet_tension_vector(float_pos, fish_accel)

    # 横方向力はゼロ
    assert abs(T[0]) < 1e-6, f"Expected T_x ≈ 0, got {T[0]}"

    # 上向き張力（正の値）
    assert T[1] > 0, f"Expected T_y > 0, got {T[1]}"

    # 大きさは m*g
    expected = bait.mass * abs(config.GRAVITY)
    assert abs(T[1] - expected) < 1e-6, f"Expected {expected}, got {T[1]}"


def test_tippet_tension_45deg():
    """45度ハリスはsin/cos分解を反映すべき"""
    bait = BaitModel()
    L = config.TIPPET_LENGTH
    # 45度の位置: (L/√2, -L/√2)
    bait.position = np.array([L/np.sqrt(2), -L/np.sqrt(2)])
    float_pos = np.array([0.0, 0.0])
    fish_accel = np.array([0.0, 0.0])

    T = bait._calculate_tippet_tension_vector(float_pos, fish_accel)

    # 45度: sin(45°) = cos(45°) → |T_x| ≈ |T_y|
    ratio = abs(T[0]) / abs(T[1])
    assert 0.95 < ratio < 1.05, f"Expected ratio ≈ 1.0, got {ratio}"

    # T_x は負（ウキ方向への引き）
    assert T[0] < 0, f"Expected T_x < 0 (pulls toward float), got {T[0]}"

    # T_y は正（上向き）
    assert T[1] > 0, f"Expected T_y > 0 (upward), got {T[1]}"


def test_tippet_tension_horizontal():
    """水平ハリスは横方向力のみ"""
    bait = BaitModel()
    L = config.TIPPET_LENGTH
    # 水平位置: (L, 0)
    bait.position = np.array([L, 0.0])
    float_pos = np.array([0.0, 0.0])
    fish_accel = np.array([0.0, 0.0])

    T = bait._calculate_tippet_tension_vector(float_pos, fish_accel)

    # 縦方向力はゼロ
    assert abs(T[1]) < 1e-6, f"Expected T_y ≈ 0, got {T[1]}"

    # 横方向力は負（ウキ方向への引き）
    assert T[0] < 0, f"Expected T_x < 0, got {T[0]}"

    # 大きさは m*g
    expected = bait.mass * abs(config.GRAVITY)
    assert abs(abs(T[0]) - expected) < 1e-6, f"Expected |T_x| = {expected}, got {abs(T[0])}"


def test_phase3_dynamics_preserved():
    """Phase 3の動的張力が保持されるべき"""
    bait = BaitModel()
    bait.position = np.array([0.0, -0.45])
    float_pos = np.array([0.0, 0.0])

    # 魚が上昇加速（食い上げ）
    fish_accel = np.array([0.0, 15.0])  # a_y > g → T < 0
    T = bait._calculate_tippet_tension_vector(float_pos, fish_accel)

    # 張力の大きさ
    expected_magnitude = bait.mass * (config.GRAVITY - 15.0)
    assert T[1] < 0, f"Expected T_y < 0 (negative tension), got {T[1]}"
    assert abs(T[1] - expected_magnitude) < 1e-6, f"Expected {expected_magnitude}, got {T[1]}"

    # 鉛直状態なので横成分はゼロ
    assert abs(T[0]) < 1e-6, f"Expected T_x ≈ 0, got {T[0]}"


def test_degenerate_case():
    """退化ケース（距離ゼロ）は鉛直方向にフォールバック"""
    bait = BaitModel()
    bait.position = np.array([0.0, 0.0])  # ウキと同じ位置
    float_pos = np.array([0.0, 0.0])
    fish_accel = np.array([0.0, 0.0])

    T = bait._calculate_tippet_tension_vector(float_pos, fish_accel)

    # 横方向力はゼロ
    assert abs(T[0]) < 1e-6, f"Expected T_x ≈ 0, got {T[0]}"

    # 上向き張力
    expected = bait.mass * abs(config.GRAVITY)
    assert T[1] > 0, f"Expected T_y > 0, got {T[1]}"
    assert abs(T[1] - expected) < 1e-6, f"Expected {expected}, got {T[1]}"


def test_newton_third_law():
    """Newton第3法則: ウキとエサの力は逆向き"""
    bait = BaitModel()
    bait.position = np.array([0.2, -0.3])  # 任意の斜め位置
    float_pos = np.array([0.0, 0.0])
    fish_accel = np.array([0.0, 0.0])

    # エサがウキから受ける力
    T_bait = bait._calculate_tippet_tension_vector(float_pos, fish_accel)

    # ウキがエサから受ける力は反対向き（main.pyで -tippet_reaction として適用）
    T_float = -T_bait

    # 大きさは同じ
    assert np.linalg.norm(T_bait) == pytest.approx(np.linalg.norm(T_float))

    # 方向は逆
    assert np.dot(T_bait, T_float) < 0, "Forces should point in opposite directions"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
