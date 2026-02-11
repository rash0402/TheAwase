"""エサモデル (可変質量系)"""

import numpy as np
from theawase import config
from theawase.physics.integrator import verlet_integrate, verlet_integrate_symplectic


class BaitModel:
    """
    エサの物理モデル

    - 時間経過で質量が減少（バラケ）
    - 匂いパーティクルを放出
    - ハリスでウキに接続（重力+張力で追従）

    2段階更新（シンプレクティック積分）に対応:
        1. update_position(): 旧加速度で位置を更新
        2. update_velocity(): 新加速度で速度を更新
    """

    def __init__(
        self,
        initial_mass: float = 0.0006,  # kg (0.6g) ウキ浮力との最適バランス点
        dissolution_rate: float = 0.000004,  # kg/s (約150秒で完全溶解)
        diffusion_rate: float = 2.0,
        tippet_length: float = config.TIPPET_LENGTH,
        tippet_stiffness: float = config.TIPPET_STIFFNESS,
    ):
        self.initial_mass = initial_mass
        self.mass = initial_mass
        self.dissolution_rate = dissolution_rate
        self.diffusion_rate = diffusion_rate
        self.tippet_length = tippet_length
        self.tippet_stiffness = tippet_stiffness

        # 状態
        self.position = np.array([0.0, 0.0])
        self.velocity = np.array([0.0, 0.0])

        # 水中抵抗（小型で軽いエサは抵抗少）
        self.drag_coefficient = 0.1

        # 匂いパーティクル（位置リスト）
        self.particles: list[np.ndarray] = []

        # シンプレクティック積分用の内部変数
        self._acceleration_old = np.array([0.0, 0.0])
        self._use_symplectic = False  # 後方互換性のためのフラグ

    def _calculate_acceleration(self) -> np.ndarray:
        """
        加速度を計算（内部ヘルパーメソッド）

        可変質量系の運動方程式: M * a = F_gravity
        """
        # 重力加速度
        return np.array([0.0, -config.GRAVITY])

    def _apply_mass_loss(self, dt: float):
        """質量減少とパーティクル放出を適用"""
        # 最小質量（ゼロ除算防止: バラケ切っても針の重さが残る）
        MIN_MASS = 0.0001  # 0.1g

        if self.mass <= MIN_MASS:
            self.mass = MIN_MASS
            self.velocity *= 0.0  # 停止
            return

        # 質量減少
        velocity_factor = np.linalg.norm(self.velocity) ** 2
        mass_loss = (self.dissolution_rate + 0.002 * velocity_factor) * dt
        self.mass = max(0.0, self.mass - mass_loss)

        # パーティクル生成（確率的）
        if np.random.random() < self.diffusion_rate * dt:
            self._emit_particle()

        # パーティクル更新（ブラウン運動）
        self._update_particles(dt)

    def _apply_tippet_constraint(self, float_position: np.ndarray) -> np.ndarray:
        """
        ハリス拘束を適用し、張力を返す

        Args:
            float_position: ウキの現在位置

        Returns:
            ハリス張力ベクトル（エサがウキ方向に引かれる力）
        """
        tippet_tension = np.array([0.0, 0.0])

        if float_position is None:
            return tippet_tension

        # ハリス拘束: ウキから離れすぎたら紐長に射影
        diff = self.position - float_position
        dist = np.linalg.norm(diff)

        if dist > self.tippet_length and dist > 1e-6:
            # 紐がピンと張った → 位置を紐長に制約
            direction = diff / dist
            self.position = float_position + direction * self.tippet_length

            # 離れる方向の速度を除去（紐がこれ以上伸びない）
            v_along = np.dot(self.velocity, direction)
            if v_along > 0:
                self.velocity -= v_along * direction

        # ハリス張力（紐がピンと張っているときのみ）
        # T = m*g のハリス方向成分
        tippet_tension = np.array([0.0, self.mass * config.GRAVITY])

        # ハリス張力を返す（ウキ方向=上向き。main.pyで符号反転して下向きに適用）
        return tippet_tension

    def update_position(self, dt: float):
        """
        Phase 1: 位置を旧加速度で更新（シンプレクティック積分の第1段階）

        Args:
            dt: 時間刻み
        """
        self._use_symplectic = True

        # 質量減少とパーティクル放出
        self._apply_mass_loss(dt)

        # 旧加速度を計算して保存
        self._acceleration_old = self._calculate_acceleration()

        # 位置を更新（旧加速度を使用）
        self.position = self.position + self.velocity * dt + 0.5 * self._acceleration_old * dt**2

    def update_velocity(self, dt: float, float_position: np.ndarray = None) -> np.ndarray:
        """
        Phase 2: 速度を平均加速度で更新（シンプレクティック積分の第2段階）

        Args:
            dt: 時間刻み
            float_position: ウキの現在位置（ハリス結合用）

        Returns:
            ハリス張力ベクトル（エサがウキ方向に引かれる力）
        """
        if not self._use_symplectic:
            raise RuntimeError("update_position() must be called before update_velocity()")

        # 新位置での加速度を計算
        acceleration_new = self._calculate_acceleration()

        # 速度を更新（平均加速度を使用: シンプレクティック性の鍵）
        _, self.velocity = verlet_integrate_symplectic(
            self.position,
            self.velocity,
            self._acceleration_old,
            acceleration_new,
            dt
        )

        # 水中抵抗の後処理（暗黙的減衰）
        damping_factor = 1.0 / (1.0 + self.drag_coefficient * dt / self.mass)
        self.velocity *= damping_factor

        # ハリス拘束を適用し、張力を取得
        tippet_tension = self._apply_tippet_constraint(float_position)

        self._use_symplectic = False

        return tippet_tension

    def update(self, dt: float, float_position: np.ndarray = None) -> np.ndarray:
        """
        エサの状態を更新（後方互換性のための単一ステップ版）

        注意: この実装は実質的にオイラー法と同等。
        エネルギー保存性を高めるには、代わりに以下の2段階更新を使用すること:
            1. update_position(dt)
            2. update_velocity(dt, float_position)

        Args:
            dt: 時間刻み
            float_position: ウキの現在位置（ハリス結合用）

        Returns:
            ハリス張力ベクトル（エサがウキ方向に引かれる力）
        """
        # 質量減少とパーティクル放出
        self._apply_mass_loss(dt)

        # 簡易版Verlet積分（実質オイラー法）
        acceleration = self._calculate_acceleration()
        self.position, self.velocity = verlet_integrate(
            self.position,
            self.velocity,
            acceleration,
            dt
        )

        # 水中抵抗の後処理（暗黙的減衰）
        damping_factor = 1.0 / (1.0 + self.drag_coefficient * dt / self.mass)
        self.velocity *= damping_factor

        # ハリス拘束を適用し、張力を取得
        return self._apply_tippet_constraint(float_position)

    def _emit_particle(self):
        """匂いパーティクルを放出"""
        particle = self.position.copy()
        self.particles.append(particle)

    def _update_particles(self, dt: float):
        """パーティクルをブラウン運動で拡散（水中のみ）"""
        diffusion_strength = 0.01
        for particle in self.particles:
            particle += np.random.randn(2) * diffusion_strength * np.sqrt(dt)

            # 水面制約：パーティクルを水中に制限（y < 0）
            if particle[1] > 0.0:
                particle[1] = 0.0  # 水面でクランプ

            # 重力による沈降（匂い粒子はゆっくり沈む）
            particle[1] -= 0.005 * dt  # 0.5cm/s の沈降速度

        # 古いパーティクルを削除（最大100個）
        if len(self.particles) > 100:
            self.particles = self.particles[-100:]

    def get_mass_ratio(self) -> float:
        """残り質量の割合"""
        return self.mass / self.initial_mass
