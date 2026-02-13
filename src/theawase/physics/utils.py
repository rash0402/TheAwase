"""物理計算の共通ユーティリティ"""
import numpy as np


def apply_water_entry_damping(
    position: np.ndarray,
    velocity: np.ndarray,
    damping_factor: float,
    zone_size: float
) -> np.ndarray:
    """
    着水時の速度減衰を段階的に適用

    Args:
        position: [x, y] 位置（yが水面判定に使用）
        velocity: [vx, vy] 速度ベクトル
        damping_factor: 最大減衰係数（例: 0.3なら70%減速）
        zone_size: 減衰範囲（±zone_size内で段階適用）

    Returns:
        減衰後の速度ベクトル
    """
    # 減衰範囲外、または上向き速度の場合は何もしない
    if not (-zone_size < position[1] < zone_size and velocity[1] < 0):
        return velocity

    # 深さ係数を計算（0.0 = 減衰なし、1.0 = 最大減衰）
    if position[1] >= 0:
        # 空中→水面: 線形補間（y=zone_sizeで0.0、y=0で0.5、連続的に増加）
        depth_factor = (zone_size - position[1]) / zone_size
    else:
        # 水中: 常に最大減衰
        depth_factor = 1.0

    # 減衰係数を計算（depth_factorに応じて0.0→damping_factorに変化）
    damping = 1.0 - (1.0 - damping_factor) * depth_factor

    # 速度に減衰を適用
    velocity_damped = velocity.copy()
    velocity_damped[1] *= damping

    return velocity_damped
