"""ツン3段階モデルのタイミングテスト - 詳細なプロット付き"""

import numpy as np
import matplotlib.pyplot as plt
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

    # 10%値と90%値（立ち上がり速度の評価）
    rise_10_idx = np.where(strengths > peak_strength * 0.1)[0]
    rise_90_idx = np.where(strengths > peak_strength * 0.9)[0]
    rise_10_time = times[rise_10_idx[0]] if len(rise_10_idx) > 0 else np.nan
    rise_90_time = times[rise_90_idx[0]] if len(rise_90_idx) > 0 else np.nan
    rise_slope = (rise_90_time - rise_10_time) * 1000  # 10-90%時間 [ms]

    # プロット
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # 上段: 全体波形
    axes[0].plot(times * 1000, strengths, linewidth=2, label='Tsun strength')
    axes[0].axvline(x=rise_time * 1000, color='r', linestyle=':', alpha=0.5, label=f'Rise (>0.5): {rise_time*1000:.1f}ms')
    axes[0].axvline(x=peak_time * 1000, color='g', linestyle=':', alpha=0.5, label=f'Peak: {peak_time*1000:.1f}ms')
    axes[0].axvline(x=50, color='k', linestyle='--', alpha=0.3, label='Target rise: 50ms')
    axes[0].axvline(x=100, color='k', linestyle='--', alpha=0.3, label='Target peak: 100ms')
    axes[0].axhline(y=0.5, color='orange', linestyle=':', alpha=0.3)
    axes[0].set_xlabel('Time [ms]')
    axes[0].set_ylabel('Suck strength')
    axes[0].set_title('Tsun 3-Stage Model (Full waveform)')
    axes[0].legend()
    axes[0].grid(alpha=0.3)
    axes[0].set_xlim(0, 300)

    # 下段: 立ち上がり拡大
    early_mask = times <= 0.15
    axes[1].plot(times[early_mask] * 1000, strengths[early_mask], linewidth=2, label='Tsun strength')
    axes[1].axvline(x=rise_time * 1000, color='r', linestyle=':', alpha=0.5, label=f'Rise: {rise_time*1000:.1f}ms')
    axes[1].axvline(x=peak_time * 1000, color='g', linestyle=':', alpha=0.5, label=f'Peak: {peak_time*1000:.1f}ms')
    axes[1].axhline(y=0.5, color='orange', linestyle=':', alpha=0.3, label='Threshold: 0.5')
    axes[1].axhline(y=peak_strength * 0.1, color='gray', linestyle=':', alpha=0.2, label='10% level')
    axes[1].axhline(y=peak_strength * 0.9, color='gray', linestyle=':', alpha=0.2, label='90% level')
    axes[1].fill_between([0, 50], 0, strengths.max(), color='green', alpha=0.1, label='Target rise zone')
    axes[1].fill_between([90, 110], 0, strengths.max(), color='blue', alpha=0.1, label='Target peak zone')
    axes[1].set_xlabel('Time [ms]')
    axes[1].set_ylabel('Suck strength')
    axes[1].set_title(f'Rise Phase (Zoomed, 10-90% rise time: {rise_slope:.1f}ms)')
    axes[1].legend()
    axes[1].grid(alpha=0.3)
    axes[1].set_xlim(0, 150)

    plt.tight_layout()
    plt.savefig('tsun_timing_verification.png', dpi=150)
    print(f"Plot saved to tsun_timing_verification.png")

    # 結果表示
    print(f"\nツン3段階モデルのタイミングテスト:")
    print(f"  立ち上がり時間 (>0.5): {rise_time*1000:.1f}ms (期待値: 50ms以内)")
    print(f"  10-90%立ち上がり時間: {rise_slope:.1f}ms")
    print(f"  ピーク時間: {peak_time*1000:.1f}ms (期待値: 100ms)")
    print(f"  ピーク強度: {peak_strength:.2f}")

    # 検証
    success = True
    if rise_time <= 0.05:
        print("  ✅ 立ち上がり: 合格")
    else:
        print("  ❌ 立ち上がり: 遅すぎる")
        print(f"     → {(rise_time - 0.05)*1000:.1f}ms 遅延")
        success = False

    if 0.09 <= peak_time <= 0.11:
        print("  ✅ ピーク時間: 合格")
    else:
        print("  ❌ ピーク時間: ずれている")
        print(f"     → {(peak_time - 0.10)*1000:.1f}ms ずれ")
        success = False

    # 立ち上がり速度評価
    if rise_slope < 30:
        print(f"  ✅ 立ち上がり速度: 急峻 ({rise_slope:.1f}ms)")
    else:
        print(f"  ⚠️  立ち上がり速度: やや緩慢 ({rise_slope:.1f}ms)")

    return success

if __name__ == "__main__":
    test_tsun_timing()
    plt.show()
