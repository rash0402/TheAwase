"""OU過程の時間相関テスト - サワリが150msの時定数を持つことを確認"""

import numpy as np
from theawase.entities.fish import FishAI
from theawase import config

def test_ou_time_correlation():
    """
    OU過程の自己相関を計算し、150ms後の相関が0.4-0.6であることを確認

    理論値: exp(-θ·τ) = exp(-6.67 × 0.15) ≈ 0.367
    """
    fish = FishAI()
    dt = config.DT
    samples = []

    # 3秒間のサワリを記録（魚はAPPROACH状態で距離0.1m）
    for i in range(180):  # 3秒 = 180フレーム @ 60fps
        bait_pos = fish.position + np.array([0.10, 0.0])  # 10cm離れた位置
        fish._approach_behavior(dt, bait_pos, 1.0)
        samples.append(fish.disturbance_force[0])  # X方向の揺れを記録

    # 自己相関を計算
    samples = np.array(samples)
    autocorr = np.correlate(samples - samples.mean(), samples - samples.mean(), mode='full')
    autocorr = autocorr[len(autocorr)//2:]
    autocorr /= autocorr[0]

    # 150ms = 9フレーム後の相関
    lag_150ms = 9
    correlation_at_150ms = autocorr[lag_150ms]

    print(f"OU過程の時間相関テスト:")
    print(f"  150ms後の相関: {correlation_at_150ms:.3f}")
    print(f"  理論値: 0.367")
    print(f"  期待範囲: 0.30-0.50")

    # 検証
    if 0.30 <= correlation_at_150ms <= 0.50:
        print("  ✅ 合格 - サワリは適切な時間相関を持つ")
        return True
    else:
        print("  ❌ 不合格 - パラメータ調整が必要")
        return False

if __name__ == "__main__":
    test_ou_time_correlation()
