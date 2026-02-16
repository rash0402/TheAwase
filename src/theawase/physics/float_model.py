"""ウキモデル (浮力計算)"""

import numpy as np
from theawase import config
from theawase.physics.integrator import verlet_integrate, verlet_integrate_symplectic
from theawase.physics.utils import clamp_acceleration


class FloatModel:
    """
    ウキの物理モデル

    幾何形状から浮力をリアルタイム計算

    2段階更新（シンプレクティック積分）に対応:
        1. update_position(): 旧加速度で位置を更新
        2. update_velocity(): 新加速度で速度を更新
    """

    def __init__(
        self,
        mass: float = 0.0027,  # kg (2.7g) エサ1.2gの2.25倍、アタリ抑制重視（名人調整v3）
        body_radius: float = 0.0050,   # m (5.0mm、正浮力0.06mN、ほぼ中性浮力）
        body_length: float = 0.05,     # m (5cm)
        top_radius: float = 0.0004,    # m (0.4mm、ヘラブナ釣り用ウキの現実的な極細トップ)
        top_length: float = 0.10,      # m (10cm)
        meniscus_damping: float = config.MENISCUS_DAMPING,
    ):
        self.mass = mass
        self.body_radius = body_radius
        self.body_length = body_length
        self.top_radius = top_radius
        self.top_length = top_length
        self.meniscus_damping = meniscus_damping

        # 状態
        # positionは「トップの先端（道糸接続部）」を指すとする
        # y=0が水面、y<0が水中
        self.position = np.array([0.0, 0.0])
        self.velocity = np.array([0.0, 0.0])

        # 姿勢（メタセントリック安定性）
        self.angle = 0.0  # rad (0=直立, π/2=水平/倒れた状態)
        self.angular_velocity = 0.0  # rad/s (将来の物理ベース版用に予約)

        # 抵抗係数（バランス調整: 0.5 → 1.5 → 1.0、適度な抵抗）
        self.drag_coefficient = 1.0

        # シンプレクティック積分用の内部変数
        self._acceleration_old = np.array([0.0, 0.0])
        self._use_symplectic = False  # 後方互換性のためのフラグ
    
    def calculate_buoyancy(self) -> float:
        """
        浮力を計算 (トップ + ボディ)
        
        positionはトップ先端(上端)の位置。
        y軸: 水面=0, 空中>0, 水中<0
        
        ウキの構造:
          トップ先端 (position.y)
               |
          [トップ: 長さ top_length]
               |
          ボディ上端 (position.y - top_length)
               |
          [ボディ: 長さ body_length]
               |
          ボディ下端 (position.y - top_length - body_length)
        """
        tip_y = self.position[1]
        
        # 各部位の境界y座標
        body_top_y = tip_y - self.top_length           # トップとボディの境界
        body_bottom_y = body_top_y - self.body_length  # ウキの最下端
        
        # 水面 y=0 より下にある長さを計算
        # ある区間 [y_bottom, y_top] が水面下にある長さ:
        # = max(0.0, min(0.0, y_top) - y_bottom) if y_bottom < 0 else 0
        
        def submerged_length(y_bottom: float, y_top: float) -> float:
            """区間 [y_bottom, y_top] のうち水面 (y=0) より下にある長さ"""
            if y_top <= 0:
                # 区間全体が水面下
                return y_top - y_bottom
            elif y_bottom >= 0:
                # 区間全体が水面上
                return 0.0
            else:
                # 区間が水面をまたいでいる (y_bottom < 0 < y_top)
                return 0.0 - y_bottom  # = -y_bottom
        
        # ボディ部分の水没長さ
        sub_body = submerged_length(body_bottom_y, body_top_y)
        vol_body = np.pi * self.body_radius**2 * sub_body
        
        # トップ部分の水没長さ
        sub_top = submerged_length(body_top_y, tip_y)
        vol_top = np.pi * self.top_radius**2 * sub_top
        
        total_volume = vol_top + vol_body
        
        # 浮力 = ρgV
        buoyancy = config.WATER_DENSITY * config.GRAVITY * total_volume
        
        return buoyancy
    
    def calculate_drag(self) -> np.ndarray:
        """流体抵抗を計算"""
        speed = np.linalg.norm(self.velocity)

        # 速度制限（発散防止）
        if speed > config.MAX_SPEED:
            self.velocity = (self.velocity / speed) * config.MAX_SPEED
            speed = config.MAX_SPEED

        if speed < 1e-6:
            return np.array([0.0, 0.0])

        # 抵抗力（速度の二乗に比例）
        drag_magnitude = self.drag_coefficient * speed**2
        drag_direction = -self.velocity / speed

        return drag_magnitude * drag_direction

    def _calculate_acceleration(self, external_force: np.ndarray) -> np.ndarray:
        """
        加速度を計算（内部ヘルパーメソッド）

        注意: 減衰項（抵抗、メニスカス）は後処理で適用されるため、
        ここでは重力、浮力、外力のみを考慮する。
        """
        if external_force is None:
            external_force = np.array([0.0, 0.0])

        # 重力
        gravity_force = np.array([0.0, -self.mass * config.GRAVITY])

        # 浮力（上向き）
        buoyancy = self.calculate_buoyancy()
        buoyancy_force = np.array([0.0, buoyancy])

        # 合力 → 加速度（抵抗・メニスカスは後処理で適用）
        total_force = gravity_force + buoyancy_force + external_force
        acceleration = total_force / self.mass

        return clamp_acceleration(acceleration, config.MAX_ACCELERATION)

    def _apply_damping(self, dt: float):
        """
        後処理：減衰項を速度に適用（暗黙的減衰）

        注意: シンプレクティック積分の観点からは理想的でないが、
        安定性と既存挙動の保持のために維持。
        Phase 3で統合流体抵抗モデルに移行予定。
        """
        # 流体抵抗: 暗黙的減衰（v²抵抗の安定版）
        speed = np.linalg.norm(self.velocity)
        if speed > 1e-6:
            if self.position[1] < 0:
                # 水中: 強い抵抗
                drag_damping = 1.0 / (1.0 + self.drag_coefficient * speed * dt / self.mass)
                self.velocity *= drag_damping
            else:
                # 空中: 軽い空気抵抗（水中の1/10程度）
                air_drag = self.drag_coefficient * 0.1
                drag_damping = 1.0 / (1.0 + air_drag * speed * dt / self.mass)
                self.velocity *= drag_damping

        # 線形抵抗（粘性抵抗）: 低速時の振動減衰に不可欠
        # ボディの下端位置を計算（ウキの最下端）
        body_bottom_y = self.position[1] - self.top_length - self.body_length

        if body_bottom_y < 0.0:  # ボディの一部が水中にあれば（通常は常に真）
            # 異方性減衰: ウキは縦長なので、横方向の抵抗は大きく、縦方向は圧倒的に小さい
            # 横ブレを抑えつつ、上下方向は極めて敏感に（流体力学的に正確）
            damping_x = 200.0    # 横方向: 極限ブレーキ（断面積大、2.2→8.0→20.0→50.0→200.0に増強）
            damping_y = 0.001    # 縦方向: 極小抵抗（流線型、200000倍の差）

            factor_x = 1.0 / (1.0 + damping_x * dt / self.mass)
            factor_y = 1.0 / (1.0 + damping_y * dt / self.mass)

            self.velocity[0] *= factor_x
            self.velocity[1] *= factor_y

        # メニスカス効果（表面張力による水面付近の追加減衰）
        meniscus_zone = 0.01  # m (±1cm の範囲)
        if abs(self.position[1]) < meniscus_zone:
            meniscus_strength = 1.0 - abs(self.position[1]) / meniscus_zone
            meniscus_factor = 1.0 / (1.0 + self.meniscus_damping * meniscus_strength * dt / self.mass)
            self.velocity[1] *= meniscus_factor

    def update_position(self, dt: float, external_force: np.ndarray = None, tippet_tension: float = 0.0):
        """
        Phase 1: 位置と角度を旧加速度・角速度で更新（シンプレクティック積分の第1段階）

        Args:
            dt: 時間刻み
            external_force: 外力（道糸の張力など）
            tippet_tension: ハリス張力（エサの重さ）[N]
        """
        self._use_symplectic = True

        # 旧加速度を計算して保存
        self._acceleration_old = self._calculate_acceleration(external_force)

        # 位置を更新（旧加速度を使用）
        self.position = self.position + self.velocity * dt + 0.5 * self._acceleration_old * dt**2

        # 姿勢Phase 1: 角度を旧角速度で更新
        self.angle += self.angular_velocity * dt

    def update_velocity(self, dt: float, external_force_new: np.ndarray = None, tippet_tension: float = 0.0):
        """
        Phase 2: 速度と角速度を更新（シンプレクティック積分の第2段階）

        Args:
            dt: 時間刻み
            external_force_new: 新位置での外力
            tippet_tension: ハリス張力（エサの重さ）[N]
        """
        if not self._use_symplectic:
            raise RuntimeError("update_position() must be called before update_velocity()")

        # 新位置での加速度を計算
        acceleration_new = self._calculate_acceleration(external_force_new)

        # 速度を更新（平均加速度を使用: シンプレクティック性の鍵）
        _, self.velocity = verlet_integrate_symplectic(
            self.position,
            self.velocity,
            self._acceleration_old,
            acceleration_new,
            dt
        )

        # 減衰を適用（後処理）
        self._apply_damping(dt)

        # 姿勢Phase 2: 新しい角度で角加速度を再計算し、角速度を更新
        alpha_new = self._calculate_angular_acceleration(tippet_tension)
        self.angular_velocity += alpha_new * dt

        # 角速度・角度の安全ガード
        self._clamp_angular_state()

        self._use_symplectic = False

    def _calculate_angular_acceleration(self, tippet_tension: float = 0.0) -> float:
        """
        角加速度を計算（内部ヘルパーメソッド）

        Args:
            tippet_tension: ハリス張力（エサの重さ）[N]

        Returns:
            角加速度 [rad/s²]
        """
        # 慣性モーメント（細長い棒近似: I = (1/12) * m * L^2）
        total_length = self.body_length + self.top_length
        I = (1.0 / 12.0) * self.mass * total_length ** 2

        # NaN/Inf チェック（安全ガード）
        if not np.isfinite(self.angle):
            self.angle = 0.0
        if not np.isfinite(self.angular_velocity):
            self.angular_velocity = 0.0

        # 復元トルク = メタセントリック復元力 + ハリス張力による復元力
        # (1) メタセントリック復元トルク: 浮力中心が重心より上→復元力
        # 傾いた方向と逆向きにトルクが働くため、マイナス符号が必要
        buoyancy = self.calculate_buoyancy()
        weight = self.mass * config.GRAVITY
        metacentric_torque = -(buoyancy - weight) * np.sin(self.angle) * config.FLOAT_METACENTRIC_HEIGHT

        # (2) ハリス張力による復元トルク: エサの重さがウキを立たせる（最重要！）
        # ハリスはウキのボディ下端に接続
        # トルクアーム: 回転中心（重心≒ボディ中央）からハリス接続点（ボディ下端）まで
        # ウキ全長の中心（重心）から、ボディ下端までの距離
        center_of_mass_to_bottom = (self.body_length / 2.0) + (self.top_length / 2.0)  # 重心からボディ下端まで
        # エサの重さ（下向き）がウキを直立方向に回転させる
        # τ = -F * sin(θ) * L （マイナス符号: 直立方向への回転）
        tippet_torque = -tippet_tension * np.sin(self.angle) * center_of_mass_to_bottom

        total_torque = metacentric_torque + tippet_torque

        # 回転減衰トルク（流体抵抗）
        # 形状抵抗 ∝ ω² + 粘性抵抗 ∝ ω
        omega = abs(self.angular_velocity)
        damping_torque = -(config.FLOAT_ROTATIONAL_DRAG * omega * self.angular_velocity +
                           config.FLOAT_ROTATIONAL_VISCOSITY * self.angular_velocity)

        # 角加速度: α = τ / I
        alpha = (total_torque + damping_torque) / I

        # 角加速度制限（発散防止）
        if abs(alpha) > config.MAX_ANGULAR_ACCELERATION:
            alpha = np.sign(alpha) * config.MAX_ANGULAR_ACCELERATION

        return alpha

    def update(self, dt: float, external_force: np.ndarray = None, tippet_tension: float = 0.0):
        """
        ウキの位置と速度を更新（後方互換性のための単一ステップ版）

        注意: この実装は実質的にオイラー法と同等。
        エネルギー保存性を高めるには、代わりに以下の2段階更新を使用すること:
            1. update_position(dt, external_force, tippet_tension)
            2. 外力を再計算
            3. update_velocity(dt, external_force_new, tippet_tension)

        Args:
            dt: 時間刻み
            external_force: 外力（道糸の張力など）
            tippet_tension: ハリス張力（エサの重さ）[N]
        """
        acceleration = self._calculate_acceleration(external_force)

        # 簡易版Verlet積分（実質オイラー法）
        self.position, self.velocity = verlet_integrate(
            self.position,
            self.velocity,
            acceleration,
            dt
        )

        # 減衰を適用（後処理）
        self._apply_damping(dt)

        # 姿勢制御（オイラー法）
        self.angle += self.angular_velocity * dt
        alpha = self._calculate_angular_acceleration(tippet_tension)
        self.angular_velocity += alpha * dt

        # 角速度・角度の安全ガード
        self._clamp_angular_state()

    def _clamp_angular_state(self):
        """角速度と角度の安全ガード（共通処理）"""
        if abs(self.angular_velocity) > config.MAX_ANGULAR_VELOCITY:
            self.angular_velocity = np.sign(self.angular_velocity) * config.MAX_ANGULAR_VELOCITY

        if np.isfinite(self.angle):
            self.angle = np.arctan2(np.sin(self.angle), np.cos(self.angle))
        else:
            self.angle = 0.0

    def get_position(self) -> np.ndarray:
        return self.position.copy()
