"""双極子力場のピーク位置テスト - 最大吸引力が理論値の位置にあることを確認"""

import numpy as np
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
    distances = np.linspace(0.001, 0.05, 100)
    forces = []

    for d in distances:
        target = fish.position + np.array([d, 0.0])
        force = fish.get_suck_force(target)
        forces.append(np.linalg.norm(force))

    forces = np.array(forces)
    peak_idx = np.argmax(forces)
    peak_distance = distances[peak_idx]

    print(f"双極子力場のピーク位置テスト:")
    print(f"  実測ピーク位置: {peak_distance*100:.2f}cm")
    print(f"  理論値: 3.0cm (2 × r₀)")
    print(f"  r₀ = {config.SUCK_FORCE_RANGE*100:.1f}cm")
    print(f"  カットオフ: {config.SUCK_FORCE_CUTOFF*100:.1f}cm")

    # 検証: ピークが2.5-3.5cmの範囲にあればOK
    if 0.025 <= peak_distance <= 0.035:
        print("  ✅ 合格 - ピーク位置は理論値と一致")
        return True
    else:
        print("  ❌ 不合格 - ピーク位置がずれている")
        return False

if __name__ == "__main__":
    test_dipole_peak_position()
