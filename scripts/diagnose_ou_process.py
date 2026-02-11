"""OU過程の詳細診断スクリプト - 実装を検証"""

import numpy as np
import matplotlib.pyplot as plt
from theawase import config

def theoretical_ou_process(theta, sigma, dt, num_steps):
    """理論通りのOU過程を生成"""
    states = np.zeros(num_steps)
    for i in range(1, num_steps):
        drift = -theta * states[i-1] * dt
        diffusion = sigma * np.sqrt(dt) * np.random.randn()
        states[i] = states[i-1] + drift + diffusion
    return states

def main():
    theta = config.SAWARI_OU_THETA
    sigma = config.SAWARI_OU_SIGMA
    dt = config.DT
    num_steps = 300

    # 100試行の平均を取る
    num_trials = 100
    all_autocorrs = []

    for trial in range(num_trials):
        samples = theoretical_ou_process(theta, sigma, dt, num_steps)

        # 自己相関計算
        autocorr = np.correlate(samples - samples.mean(), samples - samples.mean(), mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        autocorr /= autocorr[0]

        all_autocorrs.append(autocorr)

    # 平均自己相関
    avg_autocorr = np.mean(all_autocorrs, axis=0)
    std_autocorr = np.std(all_autocorrs, axis=0)

    # 理論値
    lags = np.arange(len(avg_autocorr)) * dt
    theory_autocorr = np.exp(-theta * lags)

    # 150ms後の値
    lag_150ms = 9
    measured_150ms = avg_autocorr[lag_150ms]
    theory_150ms = theory_autocorr[lag_150ms]

    # プロット
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    ax.plot(lags[:60] * 1000, avg_autocorr[:60], 'o-', label=f'Numerical (100 trials avg)', markersize=4)
    ax.fill_between(lags[:60] * 1000,
                     avg_autocorr[:60] - std_autocorr[:60],
                     avg_autocorr[:60] + std_autocorr[:60],
                     alpha=0.2)
    ax.plot(lags[:60] * 1000, theory_autocorr[:60], '--', label='Theory: exp(-θτ)', linewidth=2)
    ax.axhline(y=measured_150ms, color='r', linestyle=':', alpha=0.5, label=f'Measured at 150ms: {measured_150ms:.3f}')
    ax.axhline(y=theory_150ms, color='g', linestyle=':', alpha=0.5, label=f'Theory at 150ms: {theory_150ms:.3f}')
    ax.set_xlabel('Lag [ms]')
    ax.set_ylabel('Autocorrelation')
    ax.set_title(f'OU Process Verification (θ={theta:.2f}, σ={sigma:.4f}, dt={dt:.6f})')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_xlim(0, 1000)

    plt.tight_layout()
    plt.savefig('ou_process_diagnosis.png', dpi=150)
    print(f"Plot saved to ou_process_diagnosis.png")

    # 診断結果
    print(f"\nOU過程の理論実装診断:")
    print(f"  θ = {theta:.2f} (1/s)")
    print(f"  σ = {sigma:.4f}")
    print(f"  dt = {dt:.6f} s = {dt*1000:.2f} ms")
    print(f"  理論時定数 τ = {1/theta*1000:.0f} ms")
    print(f"\n  150ms後の相関:")
    print(f"    実測平均: {measured_150ms:.3f} ± {std_autocorr[lag_150ms]:.3f}")
    print(f"    理論値: {theory_150ms:.3f}")
    print(f"    誤差: {abs(measured_150ms - theory_150ms):.3f}")

    # 収束時定数を実測
    # 1/e (0.368) になる時刻を求める
    idx_1e = np.where(avg_autocorr < 1/np.e)[0]
    if len(idx_1e) > 0:
        measured_tau = lags[idx_1e[0]]
        print(f"\n  実測時定数（1/e到達時刻）:")
        print(f"    τ_measured = {measured_tau*1000:.0f} ms")
        print(f"    τ_theory = {1/theta*1000:.0f} ms")
        print(f"    誤差: {abs(measured_tau - 1/theta)*1000:.0f} ms")

    # FishAIの実装との比較のため、strength_factorの影響を確認
    print(f"\n  注意: FishAIでは距離依存の強度係数がかかります")
    print(f"    strength_factor = (SAWARI_DISTANCE_THRESHOLD - distance) × 2.0")
    print(f"    最大値（distance=0）: {config.SAWARI_DISTANCE_THRESHOLD * 2.0:.2f}")
    print(f"    典型値（distance=0.1m）: {(config.SAWARI_DISTANCE_THRESHOLD - 0.1) * 2.0:.2f}")

    # また、範囲外での減衰も確認
    print(f"\n  範囲外では0.9倍の減衰がかかり、時定数が変化する可能性があります")
    equivalent_theta_decay = -np.log(0.9) / dt
    print(f"    0.9倍減衰の等価θ: {equivalent_theta_decay:.2f} (1/s)")
    print(f"    等価τ: {1/equivalent_theta_decay*1000:.0f} ms")

if __name__ == "__main__":
    main()
    plt.show()
