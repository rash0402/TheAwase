"""OU過程の時間相関テスト - 詳細なプロット付き"""

import numpy as np
import matplotlib.pyplot as plt
from theawase.entities.fish import FishAI
from theawase import config

def test_ou_time_correlation():
    """
    OU過程の自己相関を計算し、150ms後の相関が0.3-0.5であることを確認

    理論値: exp(-θ·τ) = exp(-6.67 × 0.15) ≈ 0.367
    """
    fish = FishAI()
    dt = config.DT
    samples = []

    # 5秒間のサワリを記録（魚はAPPROACH状態で距離0.1m）
    for i in range(300):  # 5秒 = 300フレーム @ 60fps
        bait_pos = fish.position + np.array([0.10, 0.0])  # 10cm離れた位置
        fish._approach_behavior(dt, bait_pos, 1.0)
        samples.append(fish.disturbance_force[0])  # X方向の揺れを記録

    samples = np.array(samples)
    time_axis = np.arange(len(samples)) * dt

    # 自己相関を計算
    autocorr = np.correlate(samples - samples.mean(), samples - samples.mean(), mode='full')
    autocorr = autocorr[len(autocorr)//2:]
    autocorr /= autocorr[0]

    # 150ms = 9フレーム後の相関
    lag_150ms = 9
    correlation_at_150ms = autocorr[lag_150ms]

    # 理論曲線
    theta = config.SAWARI_OU_THETA
    lags = np.arange(len(autocorr)) * dt
    theory_autocorr = np.exp(-theta * lags)

    # プロット
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # 上段: 時系列
    axes[0].plot(time_axis, samples, label='Sawari force (X)', alpha=0.7)
    axes[0].axhline(y=0, color='k', linestyle='--', alpha=0.3)
    axes[0].set_xlabel('Time [s]')
    axes[0].set_ylabel('Force [N]')
    axes[0].set_title('OU Process Time Series (Sawari)')
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    # 下段: 自己相関
    axes[1].plot(lags[:60] * 1000, autocorr[:60], 'o-', label='Measured', markersize=4)
    axes[1].plot(lags[:60] * 1000, theory_autocorr[:60], '--', label='Theory: exp(-θτ)', linewidth=2)
    axes[1].axhline(y=correlation_at_150ms, color='r', linestyle=':', alpha=0.5, label=f'150ms: {correlation_at_150ms:.3f}')
    axes[1].axhline(y=0.367, color='g', linestyle=':', alpha=0.5, label='Target: 0.367')
    axes[1].fill_between([0, 1000], 0.30, 0.50, color='green', alpha=0.1, label='Acceptable range')
    axes[1].set_xlabel('Lag [ms]')
    axes[1].set_ylabel('Autocorrelation')
    axes[1].set_title(f'OU Process Autocorrelation (θ={theta:.2f}, τ={1/theta*1000:.0f}ms)')
    axes[1].set_xlim(0, 1000)
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig('ou_correlation_verification.png', dpi=150)
    print(f"Plot saved to ou_correlation_verification.png")

    # 結果表示
    print(f"\nOU過程の時間相関テスト:")
    print(f"  150ms後の相関: {correlation_at_150ms:.3f}")
    print(f"  理論値: 0.367")
    print(f"  期待範囲: 0.30-0.50")
    print(f"  θ = {theta:.2f} (1/s)")
    print(f"  τ = {1/theta*1000:.0f}ms")
    print(f"  σ = {config.SAWARI_OU_SIGMA:.4f}")

    # 検証
    if 0.30 <= correlation_at_150ms <= 0.50:
        print("  ✅ 合格 - サワリは適切な時間相関を持つ")
        return True
    else:
        print("  ❌ 不合格 - パラメータ調整が必要")

        # 診断
        if correlation_at_150ms < 0.30:
            print(f"\n【診断】相関が速く減衰しすぎています（θが大きすぎる）")
            suggested_theta = -np.log(0.367) / 0.15
            print(f"  推奨θ: {suggested_theta:.2f} (現在: {theta:.2f})")
            print(f"  推奨τ: {1/suggested_theta*1000:.0f}ms (現在: {1/theta*1000:.0f}ms)")
        else:
            print(f"\n【診断】相関が長く残りすぎています（θが小さすぎる）")
            suggested_theta = -np.log(0.367) / 0.15
            print(f"  推奨θ: {suggested_theta:.2f} (現在: {theta:.2f})")
            print(f"  推奨τ: {1/suggested_theta*1000:.0f}ms (現在: {1/theta*1000:.0f}ms)")

        return False

if __name__ == "__main__":
    test_ou_time_correlation()
    plt.show()
