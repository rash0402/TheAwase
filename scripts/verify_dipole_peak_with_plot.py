"""双極子力場のピーク位置テスト - 詳細なプロット付き"""

import numpy as np
import matplotlib.pyplot as plt
from theawase.entities.fish import FishAI
from theawase import config

def test_dipole_peak_position():
    """
    双極子力場 (r/r₀)² · exp(-r/r₀) のピーク位置を確認

    理論値: ピークは r = 2·r₀ = 2 × 1.5cm = 3.0cm
    """
    fish = FishAI()
    fish.suck_strength = 1.0  # 一定強度で測定

    # 距離 0.1cm ~ 5cm をスキャン
    distances = np.linspace(0.001, 0.05, 200)
    forces = []

    for d in distances:
        target = fish.position + np.array([d, 0.0])
        force = fish.get_suck_force(target)
        forces.append(np.linalg.norm(force))

    forces = np.array(forces)
    peak_idx = np.argmax(forces)
    peak_distance = distances[peak_idx]
    peak_force = forces[peak_idx]

    # 理論曲線
    r0 = config.SUCK_FORCE_RANGE
    theory_distances = np.linspace(0.001, 0.05, 500)
    theory_forces = []
    for r in theory_distances:
        normalized_r = r / r0
        profile = (normalized_r ** 2) * np.exp(-normalized_r)
        theory_forces.append(profile)
    theory_forces = np.array(theory_forces)
    theory_peak_idx = np.argmax(theory_forces)
    theory_peak_distance = theory_distances[theory_peak_idx]

    # プロット
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # 上段: 力場プロファイル
    axes[0].plot(distances * 100, forces, 'o-', label='Measured', markersize=3, alpha=0.7)
    axes[0].plot(theory_distances * 100, theory_forces, '--', label='Theory: (r/r₀)²exp(-r/r₀)', linewidth=2)
    axes[0].axvline(x=peak_distance * 100, color='r', linestyle=':', alpha=0.5, label=f'Peak: {peak_distance*100:.2f}cm')
    axes[0].axvline(x=3.0, color='g', linestyle=':', alpha=0.5, label='Target: 3.0cm')
    axes[0].axvline(x=config.SUCK_FORCE_CUTOFF * 100, color='k', linestyle='--', alpha=0.3, label=f'Cutoff: {config.SUCK_FORCE_CUTOFF*100:.1f}cm')
    axes[0].set_xlabel('Distance [cm]')
    axes[0].set_ylabel('Force magnitude [normalized]')
    axes[0].set_title(f'Dipole Force Field Profile (r₀={r0*100:.1f}cm)')
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    # 下段: 近距離拡大
    close_mask = distances <= 0.02
    axes[1].plot(distances[close_mask] * 100, forces[close_mask], 'o-', markersize=4, alpha=0.7)
    axes[1].axvline(x=peak_distance * 100, color='r', linestyle=':', alpha=0.5, label=f'Peak: {peak_distance*100:.2f}cm')
    axes[1].axvline(x=3.0, color='g', linestyle=':', alpha=0.5, label='Target: 3.0cm')
    axes[1].fill_between([2.5, 3.5], 0, forces.max(), color='green', alpha=0.1, label='Acceptable range')
    axes[1].set_xlabel('Distance [cm]')
    axes[1].set_ylabel('Force magnitude [normalized]')
    axes[1].set_title('Force Field Near Peak (Zoomed)')
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig('dipole_peak_verification.png', dpi=150)
    print(f"Plot saved to dipole_peak_verification.png")

    # 結果表示
    print(f"\n双極子力場のピーク位置テスト:")
    print(f"  実測ピーク位置: {peak_distance*100:.2f}cm")
    print(f"  理論値: 3.0cm (2 × r₀)")
    print(f"  r₀ = {r0*100:.1f}cm")
    print(f"  カットオフ: {config.SUCK_FORCE_CUTOFF*100:.1f}cm")
    print(f"  ピーク強度: {peak_force:.4f}")

    # 検証: ピークが2.5-3.5cmの範囲にあればOK
    if 0.025 <= peak_distance <= 0.035:
        print("  ✅ 合格 - ピーク位置は理論値と一致")
        return True
    else:
        print("  ❌ 不合格 - ピーク位置がずれている")
        print(f"\n【診断】ピークが理論値からずれています")
        print(f"  誤差: {(peak_distance - 0.03)*100:.2f}cm")
        return False

if __name__ == "__main__":
    test_dipole_peak_position()
    plt.show()
