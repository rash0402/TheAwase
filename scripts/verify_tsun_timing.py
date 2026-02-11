"""ツン3段階モデルのタイミングテスト - 立ち上がり時間とピーク時間を確認"""

import numpy as np
from theawase.entities.fish import FishAI

def test_tsun_timing():
    """
    3段階ツンモデルの時間特性を確認

    期待値:
        - 立ち上がり時間: 50ms以内に強度0.5を超える
        - ピーク時間: 100ms付近で最大値
    """
    fish = FishAI()

    # 0-300msをスキャン（0.5ms刻み）
    times = np.linspace(0, 0.3, 600)
    strengths = [fish._calculate_suck_strength_3stage(t) for t in times]
    strengths = np.array(strengths)

    # 立ち上がり時間: 強度が0.5を超える最初の時刻
    rise_idx = np.where(strengths > 0.5)[0]
    if len(rise_idx) > 0:
        rise_time = times[rise_idx[0]]
    else:
        rise_time = np.nan

    # ピーク時間: 最大値の時刻
    peak_idx = np.argmax(strengths)
    peak_time = times[peak_idx]
    peak_strength = strengths[peak_idx]

    print(f"ツン3段階モデルのタイミングテスト:")
    print(f"  立ち上がり時間: {rise_time*1000:.1f}ms (期待値: 50ms以内)")
    print(f"  ピーク時間: {peak_time*1000:.1f}ms (期待値: 100ms)")
    print(f"  ピーク強度: {peak_strength:.2f}")

    # 検証
    success = True
    if rise_time <= 0.05:
        print("  ✅ 立ち上がり: 合格")
    else:
        print("  ❌ 立ち上がり: 遅すぎる")
        success = False

    if 0.09 <= peak_time <= 0.11:
        print("  ✅ ピーク時間: 合格")
    else:
        print("  ❌ ピーク時間: ずれている")
        success = False

    return success

if __name__ == "__main__":
    test_tsun_timing()
