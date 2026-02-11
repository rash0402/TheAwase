"""数値積分器 (Verlet法)"""

import numpy as np


def verlet_integrate(
    position: np.ndarray,
    velocity: np.ndarray,
    acceleration: np.ndarray,
    dt: float
) -> tuple[np.ndarray, np.ndarray]:
    """
    Velocity Verlet 積分（簡易版）

    注意: この実装は実質的にオイラー法と同等。
    真のVelocity Verletには次ステップの加速度が必要。
    シンプレクティック性を保つには verlet_integrate_symplectic() を使用すること。

    Args:
        position: 現在位置 [x, y]
        velocity: 現在速度 [vx, vy]
        acceleration: 現在加速度 [ax, ay]
        dt: 時間刻み

    Returns:
        (new_position, new_velocity)
    """
    # 位置更新
    new_position = position + velocity * dt + 0.5 * acceleration * dt**2

    # 速度更新（加速度は次ステップで再計算される前提）
    new_velocity = velocity + acceleration * dt

    return new_position, new_velocity


def verlet_integrate_symplectic(
    position: np.ndarray,
    velocity: np.ndarray,
    acceleration_old: np.ndarray,
    acceleration_new: np.ndarray,
    dt: float
) -> tuple[np.ndarray, np.ndarray]:
    """
    真のVelocity Verlet積分（シンプレクティック）

    この実装はエネルギー保存性が高く、長時間シミュレーションでも
    数値的発散が少ない。バネ・ダンパ系の振動周期を正確に保持する。

    アルゴリズム:
        1. 位置を現在の速度と加速度で更新
        2. 新位置で力を再計算し、新加速度を取得（呼び出し側で実行）
        3. 速度を旧加速度と新加速度の平均で更新

    使用例:
        # Step 1: 旧加速度で位置を更新
        acc_old = force_old / mass
        pos_new = position + velocity * dt + 0.5 * acc_old * dt**2

        # Step 2: 新位置で力を再計算
        force_new = calculate_force(pos_new)
        acc_new = force_new / mass

        # Step 3: 平均加速度で速度を更新
        pos_final, vel_final = verlet_integrate_symplectic(
            position, velocity, acc_old, acc_new, dt
        )

    Args:
        position: 現在位置 [x, y]
        velocity: 現在速度 [vx, vy]
        acceleration_old: 現在位置での加速度 [ax, ay]
        acceleration_new: 新位置での加速度 [ax, ay]
        dt: 時間刻み

    Returns:
        (new_position, new_velocity)

    参考文献:
        Verlet, L. (1967). "Computer Experiments on Classical Fluids"
        https://en.wikipedia.org/wiki/Verlet_integration#Velocity_Verlet
    """
    # 位置更新（旧加速度を使用）
    new_position = position + velocity * dt + 0.5 * acceleration_old * dt**2

    # 速度更新（平均加速度を使用: シンプレクティック性の鍵）
    new_velocity = velocity + 0.5 * (acceleration_old + acceleration_new) * dt

    return new_position, new_velocity
