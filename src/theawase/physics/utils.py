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


def clamp_acceleration(acceleration: np.ndarray, max_magnitude: float) -> np.ndarray:
    """
    加速度をクランプし、NaN/Infをゼロに置換

    全物理モデル共通の安全ガード。

    Args:
        acceleration: 加速度ベクトル [ax, ay]
        max_magnitude: 加速度の最大マグニチュード (m/s²)

    Returns:
        安全な加速度ベクトル
    """
    if not np.all(np.isfinite(acceleration)):
        return np.array([0.0, 0.0])

    magnitude = np.linalg.norm(acceleration)
    if magnitude > max_magnitude:
        return (acceleration / magnitude) * max_magnitude

    return acceleration


def rotate_point(offset_x: float, offset_y: float, angle_rad: float) -> tuple[float, float]:
    """
    2D回転行列を適用

    ウキの回転描画で、先端を回転中心にするためのオフセット計算に使用。

    Args:
        offset_x: 回転中心からのX方向オフセット
        offset_y: 回転中心からのY方向オフセット
        angle_rad: 回転角度 (ラジアン)

    Returns:
        (rotated_x, rotated_y)
    """
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)
    return (
        offset_x * cos_a - offset_y * sin_a,
        offset_x * sin_a + offset_y * cos_a,
    )
