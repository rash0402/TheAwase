#!/usr/bin/env python3
"""物理状態ロギングスクリプト（魚のATTACK時のエサ挙動解析用）"""

import csv
import sys
import numpy as np
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from theawase import config
from theawase.physics.rod import RodModel
from theawase.physics.line import LineModel
from theawase.physics.float_model import FloatModel
from theawase.physics.bait import BaitModel
from theawase.physics.utils import apply_water_entry_damping
from theawase.entities.fish import FishAI, FishState


def run_simulation(duration_sec: float = 60.0, output_csv: str = "physics_log.csv"):
    """
    物理シミュレーションを実行してログを記録

    Args:
        duration_sec: シミュレーション時間（秒）
        output_csv: 出力CSVファイル名
    """
    # モデル初期化（main.pyと同じ）
    rod = RodModel()
    line = LineModel()
    float_model = FloatModel()
    bait = BaitModel()

    # 魚を1匹作成（デバッグ用: エサに近い位置に配置して確実にATTACK発生）
    fish = FishAI(
        position=np.array([0.1, -0.3]),  # エサ付近
        hunger=0.9,    # 高空腹度
        caution=0.1,   # 低警戒心
    )

    # 初期位置設定（main.pyと同じ）
    rod.hand_position = np.array([0.0, 0.50])
    rod.tip_position = np.array([0.0, 0.50])
    rod.tip_velocity = np.array([0.0, 0.0])

    float_model.position = np.array([0.0, config.FLOAT_INITIAL_Y])
    float_model.velocity = np.array([0.0, config.FLOAT_INITIAL_VELOCITY_Y])
    float_model.angle = np.pi / 2
    float_model.angular_velocity = 0.0

    bait.position = np.array([0.0, config.FLOAT_INITIAL_Y - 0.10])
    bait.velocity = np.array([0.0, 0.0])

    # CSVファイル準備
    csv_path = project_root / output_csv
    csv_file = open(csv_path, 'w', newline='')
    csv_writer = csv.writer(csv_file)

    # ヘッダー
    csv_writer.writerow([
        'time',
        'fish_state',
        'fish_x', 'fish_y',
        'fish_suck_strength',
        'fish_to_bait_dist',
        'bait_x', 'bait_y',
        'bait_vx', 'bait_vy',
        'bait_speed',
        'float_y', 'float_vy',
        'line_tension',
        'bait_mass_ratio',
    ])

    # シミュレーションループ
    dt = config.DT
    time = 0.0
    frame_count = 0
    attack_count = 0

    print(f"シミュレーション開始: {duration_sec}秒間")
    print(f"出力先: {csv_path}")

    while time < duration_sec:
        # Pass 1: 位置更新
        hand_pos = np.array([0.0, 0.50 + config.HAND_Y_OFFSET])
        rod.set_hand_position(hand_pos)

        tension_old = line.calculate_tension(rod.get_tip_position(), float_model.get_position())
        rod.update_position(dt, -tension_old)

        # 魚の力を計算
        fish_force_on_bait = np.array([0.0, 0.0])
        fish_accel = np.array([0.0, 0.0])

        particle_density = len([p for p in bait.particles if np.linalg.norm(p - fish.position) < 0.2]) / 100.0
        bait_mass_ratio = bait.get_mass_ratio()

        fish.update(dt, bait.position, particle_density, bait_mass_ratio)

        fish_force_on_bait += fish.get_suck_force(bait.position)
        fish_force_on_bait += fish.get_disturbance_force()
        fish_accel = fish.get_acceleration_from_suction(bait.position)

        # エサ位置更新
        bait.update_position(dt, fish_force_on_bait, float_model.position)

        # ウキ位置更新
        tippet_reaction_old = np.array([0.0, bait.mass * config.GRAVITY])
        tippet_tension_vertical_old = abs(tippet_reaction_old[1])

        tip_pos_old = rod.get_tip_position()
        max_line_dist = config.LINE_REST_LENGTH + config.LINE_MAX_STRETCH
        gravity_on_float = float_model.mass * config.GRAVITY

        line_diff_old = float_model.position - tip_pos_old
        line_dist_old = np.linalg.norm(line_diff_old)
        constraint_force_old = np.array([0.0, 0.0])

        if line_dist_old > max_line_dist - 0.001 and line_dist_old > 1e-6:
            line_dir_old = line_diff_old / line_dist_old
            buoyancy_old = float_model.calculate_buoyancy()
            net_down_old = gravity_on_float + tippet_reaction_old[1] - buoyancy_old
            force_along_old = -net_down_old * line_dir_old[1]
            if force_along_old > 0:
                constraint_force_old = line_dir_old * force_along_old

        float_model.update_position(dt, tension_old - tippet_reaction_old + constraint_force_old, tippet_tension_vertical_old)

        # Pass 2: 速度更新
        tip_pos_new = rod.get_tip_position()
        tension_new = line.calculate_tension(tip_pos_new, float_model.position)
        rod.update_velocity(dt, -tension_new)

        float_pos_new = float_model.position
        fish_force_on_bait_new = fish.get_suck_force(bait.position) + fish.get_disturbance_force()

        tippet_reaction_new = bait.update_velocity(dt, float_pos_new, fish_accel, fish_force_on_bait_new)

        line_diff_new = float_model.position - tip_pos_new
        line_dist_new = np.linalg.norm(line_diff_new)
        constraint_force_new = np.array([0.0, 0.0])

        if line_dist_new > max_line_dist - 0.001 and line_dist_new > 1e-6:
            line_dir_new = line_diff_new / line_dist_new
            buoyancy_new = float_model.calculate_buoyancy()
            net_down_new = gravity_on_float + tippet_reaction_new[1] - buoyancy_new
            force_along_new = -net_down_new * line_dir_new[1]
            if force_along_new > 0:
                constraint_force_new = line_dir_new * force_along_new

        tippet_tension_vertical = abs(tippet_reaction_new[1])
        float_model.update_velocity(dt, tension_new - tippet_reaction_new + constraint_force_new, tippet_tension_vertical)

        # 着水減衰
        float_model.velocity = apply_water_entry_damping(
            float_model.position,
            float_model.velocity,
            config.WATER_ENTRY_DAMPING,
            config.WATER_ENTRY_ZONE
        )

        # ログ出力（10フレームごと = 0.1秒ごと）
        if frame_count % 10 == 0:
            fish_to_bait = np.linalg.norm(fish.position - bait.position)
            bait_speed = np.linalg.norm(bait.velocity)

            csv_writer.writerow([
                f"{time:.3f}",
                fish.state.name,
                f"{fish.position[0]:.6f}", f"{fish.position[1]:.6f}",
                f"{fish.suck_strength:.6f}",
                f"{fish_to_bait:.6f}",
                f"{bait.position[0]:.6f}", f"{bait.position[1]:.6f}",
                f"{bait.velocity[0]:.6f}", f"{bait.velocity[1]:.6f}",
                f"{bait_speed:.6f}",
                f"{float_model.position[1]:.6f}", f"{float_model.velocity[1]:.6f}",
                f"{np.linalg.norm(tension_new):.6f}",
                f"{bait_mass_ratio:.6f}",
            ])

        # ATTACK状態のカウント
        if fish.state == FishState.ATTACK and frame_count % 100 == 0:
            attack_count += 1
            print(f"  t={time:.1f}s: ATTACK検出 (累計{attack_count}回)")

        time += dt
        frame_count += 1

    csv_file.close()
    print(f"\nシミュレーション完了")
    print(f"総フレーム数: {frame_count}")
    print(f"ATTACK検出回数: {attack_count}")
    print(f"ログファイル: {csv_path}")

    return csv_path


if __name__ == "__main__":
    csv_path = run_simulation(duration_sec=60.0)
    print(f"\n解析を開始するには:")
    print(f"  python scripts/analyze_physics.py {csv_path}")
