#!/usr/bin/env python3
"""ウキ挙動の専門解析（ヘラ釣り名人視点）"""

import pandas as pd
import numpy as np
import sys

def analyze_float_behavior(csv_path: str):
    """ウキの物理挙動を名人視点で評価"""
    df = pd.read_csv(csv_path)

    print("=" * 70)
    print("ヘラ釣り名人による【ウキ診断】")
    print("=" * 70)

    # === 1. ウキの静止位置（平衡点）===
    idle_mask = df['fish_state'] == 'IDLE'
    if idle_mask.sum() > 0:
        idle_float_y = df.loc[idle_mask, 'float_y'].mean()
    else:
        # IDLEがない場合はATTACK以外の全体平均
        non_attack_mask = df['fish_state'] != 'ATTACK'
        idle_float_y = df.loc[non_attack_mask, 'float_y'].mean()

    print(f"\n【静止時のウキ位置】")
    print(f"  平均: {idle_float_y*1000:.1f} mm (水面上)")
    print(f"  判定: ", end="")
    if idle_float_y < 0.01:  # 10mm未満
        print("❌ ウキが沈みすぎ（エサ重すぎorウキ軽すぎ）")
        recommendation_1 = "ウキ質量を増やすか、body_radiusを小さくする"
    elif idle_float_y > 0.15:  # 150mm超
        print("❌ ウキが浮きすぎ（エサ軽すぎorウキ重すぎ）")
        recommendation_1 = "ウキ質量を減らすか、body_radiusを大きくする"
    elif idle_float_y > 0.10:  # 100mm超
        print("⚠️  やや高め（実釣では50mm程度が理想）")
        recommendation_1 = "ウキ質量を2.0-2.2gに微調整"
    else:
        print("✓ 適切（水面上10-100mm、実釣的）")
        recommendation_1 = None

    # === 2. ATTACK時のウキ応答 ===
    print(f"\n【魚のアタック時のウキ応答】")
    attack_mask = df['fish_state'] == 'ATTACK'
    attack_sessions = []

    if attack_mask.sum() == 0:
        print("  ⚠️ ATTACK検出なし（データ不足）")
        return

    # ATTACK区間を検出
    attack_indices = df[attack_mask].index.tolist()
    sessions = []
    current_session = [attack_indices[0]]

    for i in range(1, len(attack_indices)):
        if attack_indices[i] - attack_indices[i-1] == 1:
            current_session.append(attack_indices[i])
        else:
            sessions.append(current_session)
            current_session = [attack_indices[i]]
    sessions.append(current_session)

    # 各ATTACKセッションでウキ変位を計算
    float_responses = []
    for session_idx, session in enumerate(sessions):
        if len(session) < 2:
            continue

        start_idx = session[0]
        end_idx = session[-1]

        # 開始直前のウキ位置（ベースライン）
        if start_idx > 0:
            baseline_y = df.loc[start_idx - 1, 'float_y']
        else:
            baseline_y = df.loc[start_idx, 'float_y']

        # ATTACK中の最大変位
        attack_y_values = df.loc[session, 'float_y'].values
        max_displacement = np.max(np.abs(attack_y_values - baseline_y)) * 1000  # mm

        # 吸い込み力のピーク
        suck_strength = df.loc[session, 'fish_suck_strength'].max()

        float_responses.append({
            'session': session_idx,
            'start_time': df.loc[start_idx, 'time'],
            'displacement': max_displacement,
            'suck_strength': suck_strength
        })

    if not float_responses:
        print("  ⚠️ 解析可能なATTACKセッションなし")
        return

    # 統計
    displacements = [r['displacement'] for r in float_responses]
    avg_displacement = np.mean(displacements)
    max_displacement = np.max(displacements)
    min_displacement = np.min(displacements)

    print(f"  総ATTACK回数: {len(float_responses)}")
    print(f"  ウキ変位（平均）: {avg_displacement:.2f} mm")
    print(f"  ウキ変位（最大）: {max_displacement:.2f} mm")
    print(f"  ウキ変位（最小）: {min_displacement:.2f} mm")
    print(f"\n  判定: ", end="")

    if avg_displacement < 0.5:  # 0.5mm未満
        print("❌ ウキがほぼ動かない（感度不足、質量重すぎ）")
        recommendation_2 = "ウキ質量を1.5-1.6gに減らす"
    elif avg_displacement < 2.0:  # 2mm未満
        print("✓ 理想的（微細な動き、名人級の感度）")
        recommendation_2 = None
    elif avg_displacement < 5.0:  # 5mm未満
        print("✓ 良好（わずかな動き、実釣的）")
        recommendation_2 = None
    elif avg_displacement < 10.0:  # 10mm未満
        print("⚠️  やや大きめ（感度は高いが、初心者向け）")
        recommendation_2 = "ウキ質量を2.0-2.2gに微増"
    else:
        print("❌ 動きすぎ（ウキ軽すぎ、実釣では誤判定多発）")
        recommendation_2 = "ウキ質量を2.5-3.0gに増やす"

    # === 3. 詳細表示（上位5件） ===
    print(f"\n【ATTACK時のウキ応答詳細（上位5件）】")
    print("Session |   時刻   | 吸込力 | ウキ変位 | 判定")
    print("-" * 55)

    sorted_responses = sorted(float_responses, key=lambda x: x['displacement'], reverse=True)[:5]
    for r in sorted_responses:
        judgment = "適切" if 0.5 <= r['displacement'] <= 5.0 else ("小さい" if r['displacement'] < 0.5 else "大きい")
        print(f"   {r['session']:4d} | {r['start_time']:6.2f}s | {r['suck_strength']:6.3f} | {r['displacement']:7.2f}mm | {judgment}")

    # === 4. 名人の総合診断 ===
    print("\n" + "=" * 70)
    print("【ヘラ釣り名人の総合診断】")
    print("=" * 70)

    recommendations = []
    if recommendation_1:
        recommendations.append(f"1. 静止位置: {recommendation_1}")
    if recommendation_2:
        recommendations.append(f"2. アタリ感度: {recommendation_2}")

    if not recommendations:
        print("✓ 現在の設定は実釣的に良好です。")
        print("  - ウキの静止位置が適切")
        print("  - アタリの出方が理想的（微細な動き）")
        print("\n次のステップ: ゲームを起動して視覚確認してください。")
    else:
        print("⚠️  以下の調整を推奨します：")
        for rec in recommendations:
            print(f"  {rec}")

        # 具体的なパラメータ提案
        print("\n【推奨パラメータ変更】")
        if avg_displacement < 0.5:
            print(f"  float_model.py: mass = 0.0015  # 1.5g（現在1.8g）")
        elif avg_displacement > 10.0:
            print(f"  float_model.py: mass = 0.0025  # 2.5g（現在1.8g）")
        elif idle_float_y > 0.10:
            print(f"  float_model.py: mass = 0.0020  # 2.0g（現在1.8g）")

        if idle_float_y < 0.01:
            print(f"  float_model.py: body_radius = 0.0055  # 5.5mm（現在5.0mm）")
        elif idle_float_y > 0.15:
            print(f"  float_model.py: body_radius = 0.0045  # 4.5mm（現在5.0mm）")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_float.py <csv_file>")
        sys.exit(1)

    csv_path = sys.argv[1]
    analyze_float_behavior(csv_path)
