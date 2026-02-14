#!/usr/bin/env python3
"""物理ログデータ解析スクリプト（エサの挙動を定量化）"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path


def analyze_attack_behavior(csv_path: str):
    """
    ATTACK時のエサの挙動を解析

    Args:
        csv_path: ログCSVファイルのパス
    """
    print(f"ログファイル読込: {csv_path}")
    df = pd.read_csv(csv_path)

    print(f"\n=== データサマリー ===")
    print(f"総レコード数: {len(df)}")
    print(f"シミュレーション時間: {df['time'].iloc[-1]:.1f}秒")

    # 各状態の時間
    for state in ['IDLE', 'APPROACH', 'ATTACK', 'COOLDOWN']:
        count = (df['fish_state'] == state).sum()
        duration = count * 0.1  # 10フレームごとなので0.1秒
        print(f"  {state:10s}: {count:4d}レコード ({duration:5.1f}秒)")

    # ATTACK状態のデータを抽出
    attack_df = df[df['fish_state'] == 'ATTACK'].copy()

    if len(attack_df) == 0:
        print("\n⚠️ ATTACK状態が記録されていません")
        print("  → シミュレーション時間を延長するか、魚の初期配置を調整してください")
        return

    print(f"\n=== ATTACK状態の解析 ===")
    print(f"ATTACK期間の総レコード数: {len(attack_df)}")

    # ATTACKセッションを分割（連続するATTACKをグループ化）
    attack_df['session'] = (attack_df['time'].diff() > 0.5).cumsum()
    n_sessions = attack_df['session'].nunique()

    print(f"ATTACK発生回数: {n_sessions}回")

    # 各ATTACKセッションを解析
    print(f"\n=== 各ATTACK時のエサ移動量 ===")
    print(f"{'Session':>7s} | {'開始時刻':>8s} | {'持続時間':>8s} | {'最大吸込力':>10s} | {'エサ移動距離':>12s} | {'最大速度':>10s} | 判定")
    print("-" * 90)

    for session_id in sorted(attack_df['session'].unique()):
        session_data = attack_df[attack_df['session'] == session_id]

        t_start = session_data['time'].iloc[0]
        t_end = session_data['time'].iloc[-1]
        duration = t_end - t_start

        # エサの移動量
        bait_x_start = session_data['bait_x'].iloc[0]
        bait_y_start = session_data['bait_y'].iloc[0]
        bait_x_end = session_data['bait_x'].iloc[-1]
        bait_y_end = session_data['bait_y'].iloc[-1]

        displacement = np.sqrt((bait_x_end - bait_x_start)**2 + (bait_y_end - bait_y_start)**2)
        displacement_mm = displacement * 1000  # メートル→ミリメートル

        # 吸込力と速度
        max_suck = session_data['fish_suck_strength'].max()
        max_speed = session_data['bait_speed'].max()

        # 判定基準
        # B: わずかに動く（数mm～1cm = 1-10mm）
        if displacement_mm < 1.0:
            judgment = "ほぼ動かず（問題？）"
        elif 1.0 <= displacement_mm <= 10.0:
            judgment = "適切（わずか）✓"
        elif 10.0 < displacement_mm <= 50.0:
            judgment = "やや飛びすぎ"
        else:
            judgment = "飛びすぎ❌"

        print(f"{session_id:7d} | {t_start:7.2f}s | {duration:7.3f}s | {max_suck:10.3f} | {displacement_mm:10.2f} mm | {max_speed:9.4f} m/s | {judgment}")

    # 統計サマリー
    print(f"\n=== 統計サマリー ===")
    all_displacements = []
    all_max_speeds = []

    for session_id in attack_df['session'].unique():
        session_data = attack_df[attack_df['session'] == session_id]
        bait_x_start = session_data['bait_x'].iloc[0]
        bait_y_start = session_data['bait_y'].iloc[0]
        bait_x_end = session_data['bait_x'].iloc[-1]
        bait_y_end = session_data['bait_y'].iloc[-1]
        displacement = np.sqrt((bait_x_end - bait_x_start)**2 + (bait_y_end - bait_y_start)**2) * 1000
        all_displacements.append(displacement)
        all_max_speeds.append(session_data['bait_speed'].max())

    print(f"エサ移動距離（全ATTACK平均）:")
    print(f"  平均: {np.mean(all_displacements):.2f} mm")
    print(f"  最小: {np.min(all_displacements):.2f} mm")
    print(f"  最大: {np.max(all_displacements):.2f} mm")
    print(f"  標準偏差: {np.std(all_displacements):.2f} mm")

    print(f"\nエサ最大速度（全ATTACK平均）:")
    print(f"  平均: {np.mean(all_max_speeds):.4f} m/s")
    print(f"  最大: {np.max(all_max_speeds):.4f} m/s")

    # 結論
    print(f"\n=== 結論 ===")
    avg_displacement = np.mean(all_displacements)

    if avg_displacement < 1.0:
        print("❌ エサがほとんど動いていません（drag_coefficient が強すぎる）")
        print("   → drag_coefficient を 5.0 から 1.0～2.0 程度に下げることを推奨")
    elif 1.0 <= avg_displacement <= 10.0:
        print("✅ エサの動きは適切です（わずかに動く）")
        print("   → 実釣感覚に合致しています")
    elif 10.0 < avg_displacement <= 50.0:
        print("⚠️ エサがやや飛びすぎています")
        print("   → drag_coefficient を現在値より 2-3倍に増やすことを推奨")
    else:
        print("❌ エサが飛びすぎています（drag_coefficient が弱すぎる）")
        print(f"   → drag_coefficient を現在値の 5-10倍に増やすことを推奨")
        print(f"   → 目標: エサ移動距離を {avg_displacement:.1f}mm から 1-10mm に抑える")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        csv_path = Path(__file__).parent.parent / "physics_log.csv"
    else:
        csv_path = Path(sys.argv[1])

    if not csv_path.exists():
        print(f"エラー: ファイルが見つかりません: {csv_path}")
        print(f"\n先にログを生成してください:")
        print(f"  python scripts/log_physics.py")
        sys.exit(1)

    analyze_attack_behavior(str(csv_path))
