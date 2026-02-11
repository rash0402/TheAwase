"""竿モデル (バネ・マス・ダンパ系)"""

import numpy as np
from theawase import config
from theawase.physics.integrator import verlet_integrate, verlet_integrate_symplectic


class RodModel:
    """
    竿の物理モデル

    手元と竿先をバネ・ダンパで結合した2質点系

    2段階更新（シンプレクティック積分）に対応:
        1. update_position(): 旧加速度で位置を更新
        2. update_velocity(): 新加速度で速度を更新
    """

    def __init__(
        self,
        mass: float = config.ROD_MASS,
        stiffness: float = config.ROD_STIFFNESS,
        damping: float = config.ROD_DAMPING,
    ):
        self.mass = mass
        self.stiffness = stiffness
        self.damping = damping

        # 状態
        self.hand_position = np.array([0.0, 0.0])  # 手元位置（入力）
        self.tip_position = np.array([0.0, 0.0])   # 竿先位置
        self.tip_velocity = np.array([0.0, 0.0])   # 竿先速度

        # シンプレクティック積分用の内部変数
        self._acceleration_old = np.array([0.0, 0.0])
        self._use_symplectic = False  # 後方互換性のためのフラグ
    
    def set_hand_position(self, position: np.ndarray):
        """手元位置を設定（トラックパッド入力）"""
        self.hand_position = position.copy()

    def _calculate_acceleration(self, external_force: np.ndarray) -> np.ndarray:
        """
        加速度を計算（内部ヘルパーメソッド）

        運動方程式: M * a = -K * (x_tip - x_hand) - C * v + F_external
        """
        if external_force is None:
            external_force = np.array([0.0, 0.0])

        # 復元力（バネ）
        displacement = self.tip_position - self.hand_position
        spring_force = -self.stiffness * displacement

        # 減衰力（ダンパ）
        damping_force = -self.damping * self.tip_velocity

        # 合力
        total_force = spring_force + damping_force + external_force

        # 加速度
        acceleration = total_force / self.mass

        # 加速度制限（物理発散防止）
        max_acceleration = 1000.0  # m/s^2
        acc_magnitude = np.linalg.norm(acceleration)
        if acc_magnitude > max_acceleration:
            acceleration = (acceleration / acc_magnitude) * max_acceleration

        # NaN チェック
        if not np.all(np.isfinite(acceleration)):
            acceleration = np.array([0.0, 0.0])

        return acceleration

    def update_position(self, dt: float, external_force: np.ndarray = None):
        """
        Phase 1: 位置を旧加速度で更新（シンプレクティック積分の第1段階）

        Args:
            dt: 時間刻み
            external_force: 外力（道糸の張力など）
        """
        self._use_symplectic = True

        # 旧加速度を計算して保存
        self._acceleration_old = self._calculate_acceleration(external_force)

        # 位置を更新（旧加速度を使用）
        self.tip_position = self.tip_position + self.tip_velocity * dt + 0.5 * self._acceleration_old * dt**2

    def update_velocity(self, dt: float, external_force_new: np.ndarray = None):
        """
        Phase 2: 速度を平均加速度で更新（シンプレクティック積分の第2段階）

        Args:
            dt: 時間刻み
            external_force_new: 新位置での外力
        """
        if not self._use_symplectic:
            raise RuntimeError("update_position() must be called before update_velocity()")

        # 新位置での加速度を計算
        acceleration_new = self._calculate_acceleration(external_force_new)

        # 速度を更新（平均加速度を使用: シンプレクティック性の鍵）
        _, self.tip_velocity = verlet_integrate_symplectic(
            self.tip_position,
            self.tip_velocity,
            self._acceleration_old,
            acceleration_new,
            dt
        )

        self._use_symplectic = False

    def update(self, dt: float, external_force: np.ndarray = None):
        """
        竿先の位置と速度を更新（後方互換性のための単一ステップ版）

        注意: この実装は実質的にオイラー法と同等。
        エネルギー保存性を高めるには、代わりに以下の2段階更新を使用すること:
            1. update_position(dt, external_force)
            2. 外力を再計算
            3. update_velocity(dt, external_force_new)

        運動方程式: M * a + C * v + K * (x_tip - x_hand) = F_external
        """
        acceleration = self._calculate_acceleration(external_force)

        # 簡易版Verlet積分（実質オイラー法）
        self.tip_position, self.tip_velocity = verlet_integrate(
            self.tip_position,
            self.tip_velocity,
            acceleration,
            dt
        )
    
    def get_tip_position(self) -> np.ndarray:
        """竿先位置を取得"""
        return self.tip_position.copy()
    
    def get_tip_velocity(self) -> np.ndarray:
        """竿先速度を取得"""
        return self.tip_velocity.copy()
