#!/usr/bin/env python3
"""アタリ（魚の食い）の詳細解析 - へらぶな釣りの達人視点"""

import pandas as pd
import numpy as np
import sys

def analyze_atari_response(csv_path: str):
    """
    アタリ時のウキの沈み込みを達人視点で評価

    へらぶな釣りでは、魚がエサを吸い込むと：
    1. 消し込み: ウキが沈む（下方向への動き）
    2. 食い上げ: ウキが浮く（上方向への動き）
    3. サワリ: 微細な揺れ（横方向や小さな上下動）

    理想的なアタリは、明確に視認できるが大げさでない動き（5-20mm程度）
    """
    df = pd.read_csv(csv_path)

    print("=" * 80)
    print("へらぶな釣りの達人による【アタリ診断】")
    print("=" * 80)

    # === 1. ベースライン確認 ===
    print("\n【1. ウキの基本状態】")

    # 最初の安定期（0-2秒）のウキ位置
    early_mask = df['time'] < 2.0
    early_float_y = df.loc[early_mask, 'float_y']

    print(f"  初期ウキ位置（0-2秒）:")
    print(f"    平均: {early_float_y.mean()*1000:.1f} mm")
    print(f"    最小: {early_float_y.min()*1000:.1f} mm")
    print(f"    最大: {early_float_y.max()*1000:.1f} mm")
    print(f"    変動: {(early_float_y.max() - early_float_y.min())*1000:.1f} mm")

    initial_stability = (early_float_y.max() - early_float_y.min()) * 1000
    if initial_stability > 50:
        print(f"  ⚠️  初期から大きく振動しています（{initial_stability:.1f}mm）")
        print(f"      → 初期位置が平衡点から離れている可能性")

    # === 2. ATTACK状態の検出と解析 ===
    print("\n【2. アタリ（ATTACK）の詳細解析】")

    attack_mask = df['fish_state'] == 'ATTACK'
    if attack_mask.sum() == 0:
        print("  ⚠️  ATTACK検出なし（魚が食わなかった）")
        return

    # ATTACKセッションを検出
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

    # 各ATTACKセッションで「沈み込み」を計算
    atari_details = []

    for session_idx, session in enumerate(sessions):
        if len(session) < 2:
            continue

        start_idx = session[0]
        end_idx = session[-1]

        # ATTACK開始直前のウキ位置（ベースライン）
        if start_idx > 5:
            # 直前5フレームの平均
            baseline_indices = range(start_idx - 5, start_idx)
            baseline_y = df.loc[baseline_indices, 'float_y'].mean()
        else:
            baseline_y = df.loc[start_idx, 'float_y']

        # ATTACK中のウキ位置変化
        attack_y_values = df.loc[session, 'float_y'].values

        # 最も沈んだ位置（下方向 = y値が小さくなる）
        min_y = attack_y_values.min()
        max_y = attack_y_values.max()

        # 沈み込み量（負の値 = 沈んだ）
        sinking = (min_y - baseline_y) * 1000  # mm
        rising = (max_y - baseline_y) * 1000   # mm

        # 全体の変位
        total_displacement = (max_y - min_y) * 1000  # mm

        # 吸い込み力のピーク
        suck_strength = df.loc[session, 'fish_suck_strength'].max()

        # アタリのタイプ判定
        if abs(sinking) > abs(rising):
            atari_type = "消し込み"
            primary_movement = sinking
        else:
            atari_type = "食い上げ"
            primary_movement = rising

        atari_details.append({
            'session': session_idx,
            'start_time': df.loc[start_idx, 'time'],
            'baseline_y': baseline_y * 1000,  # mm
            'sinking': sinking,
            'rising': rising,
            'total_displacement': total_displacement,
            'atari_type': atari_type,
            'primary_movement': primary_movement,
            'suck_strength': suck_strength
        })

    if not atari_details:
        print("  ⚠️  解析可能なATTACKセッションなし")
        return

    # === 3. 統計サマリー ===
    print(f"\n  総ATTACK回数: {len(atari_details)}")

    sinkings = [a['sinking'] for a in atari_details]
    risings = [a['rising'] for a in atari_details]
    total_disps = [a['total_displacement'] for a in atari_details]

    print(f"\n  【沈み込み（消し込み）】")
    print(f"    平均: {np.mean(sinkings):.2f} mm")
    print(f"    最大: {np.min(sinkings):.2f} mm（最も沈んだ）")
    print(f"    最小: {np.max(sinkings):.2f} mm（最も浮いた側）")

    print(f"\n  【浮き上がり（食い上げ）】")
    print(f"    平均: {np.mean(risings):.2f} mm")
    print(f"    最大: {np.max(risings):.2f} mm")
    print(f"    最小: {np.min(risings):.2f} mm")

    print(f"\n  【総変位（振幅）】")
    print(f"    平均: {np.mean(total_disps):.2f} mm")
    print(f"    最大: {np.max(total_disps):.2f} mm")

    # === 4. アタリの種類分布 ===
    print(f"\n  【アタリの種類分布】")
    keshikomi_count = sum(1 for a in atari_details if a['atari_type'] == '消し込み')
    kuiage_count = sum(1 for a in atari_details if a['atari_type'] == '食い上げ')

    print(f"    消し込み: {keshikomi_count}回 ({keshikomi_count/len(atari_details)*100:.1f}%)")
    print(f"    食い上げ: {kuiage_count}回 ({kuiage_count/len(atari_details)*100:.1f}%)")

    # === 5. 詳細表示（代表的な5件） ===
    print(f"\n【3. 代表的なアタリ（上位5件）】")
    print("Session | 時刻   | ベース位置 | タイプ   | 主動作  | 総変位  | 吸込力 | 判定")
    print("-" * 85)

    sorted_atari = sorted(atari_details, key=lambda x: abs(x['primary_movement']), reverse=True)[:5]
    for a in sorted_atari:
        judgment = "適切" if 5 <= abs(a['primary_movement']) <= 20 else ("小さい" if abs(a['primary_movement']) < 5 else "大きい")
        print(f"   {a['session']:4d} | {a['start_time']:5.1f}s | {a['baseline_y']:7.1f}mm | {a['atari_type']:8s} | "
              f"{a['primary_movement']:+6.1f}mm | {a['total_displacement']:6.1f}mm | {a['suck_strength']:6.3f} | {judgment}")

    # === 6. 達人の診断 ===
    print("\n" + "=" * 80)
    print("【へらぶな釣りの達人の診断】")
    print("=" * 80)

    avg_movement = np.mean([abs(a['primary_movement']) for a in atari_details])
    avg_sinking = abs(np.mean(sinkings))

    print(f"\n平均的なアタリの大きさ: {avg_movement:.1f} mm")
    print(f"平均的な沈み込み: {avg_sinking:.1f} mm")

    if avg_movement < 3:
        print("\n❌ アタリが小さすぎます（視認困難）")
        print("   推奨: ウキを軽くする（mass を 2.0-2.2g に減らす）")
    elif avg_movement < 8:
        print("\n✓ 理想的なアタリです（微細だが確実に視認可能）")
        print("   これがへらぶな釣りの醍醐味！")
    elif avg_movement < 20:
        print("\n⚠️  アタリがやや大きめ（初心者向け）")
        print("   中級者以上なら、もう少し繊細な方が良い")
    else:
        print("\n❌ アタリが大きすぎます（不自然）")
        print("   推奨: ウキを重くする（mass を 2.5-3.0g に増やす）")

    if avg_sinking < 5:
        print(f"\n⚠️  沈み込みが浅い（{avg_sinking:.1f}mm）")
        print("   消し込みアタリが見えにくい可能性")
        print("   → 魚の吸い込み力を調整するか、ウキを軽くする")

    # === 7. 初期振動の影響チェック ===
    if initial_stability > 50:
        print(f"\n⚠️  重要: 初期振動が{initial_stability:.1f}mmあり、アタリ判定に悪影響")
        print("   → 初期位置を真の平衡点に調整する必要があります")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_atari.py <csv_file>")
        sys.exit(1)

    csv_path = sys.argv[1]
    analyze_atari_response(csv_path)
