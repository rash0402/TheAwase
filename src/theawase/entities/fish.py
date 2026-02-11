"""魚AI (ステートマシン)"""

import numpy as np
from enum import Enum, auto
from theawase import config


class FishState(Enum):
    """魚の状態"""
    IDLE = auto()      # ランダム徘徊
    APPROACH = auto()  # エサへ接近
    ATTACK = auto()    # 吸い込み
    COOLDOWN = auto()  # 離脱


class BiteType(Enum):
    """アタリの種類"""
    NORMAL = auto()     # 通常（居食い・反転なし）
    KUIAGE = auto()     # 食い上げ（上昇）
    KESHIKOMI = auto()  # 消し込み（潜行）


class FishAI:
    """
    魚の自律エージェント
    
    - 楕円体コライダー
    - 吸い込みアクチュエータ
    - アタリ（食い上げ/消し込み/サワリ）生成
    """
    
    def __init__(
        self,
        position: np.ndarray = None,
        hunger: float = 0.5,
        caution: float = 0.5,
    ):
        self.position = position if position is not None else np.array([0.0, -0.5])
        self.velocity = np.array([0.0, 0.0])
        
        # 内部状態
        self.hunger = hunger    # 空腹度 (0-1)
        self.caution = caution  # 警戒心 (0-1)
        
        # ステートマシン
        self.state = FishState.IDLE
        self.state_timer = 0.0
        
        # アタリパラメータ
        self.bite_type = BiteType.NORMAL
        self.suck_strength = 0.0
        self.suck_direction = np.array([0.0, 1.0])
        self.disturbance_force = np.array([0.0, 0.0])  # サワリ・水流

        # Phase 2: Ornstein-Uhlenbeck過程の状態変数（サワリの時間相関）
        self.ou_state = np.array([0.0, 0.0])  # X方向, Y方向の相関状態
    
    def update(self, dt: float, bait_position: np.ndarray, particle_density: float, bait_mass_ratio: float = 1.0):
        """
        魚の状態を更新
        
        Args:
            dt: 時間刻み
            bait_position: エサの位置
            particle_density: 周囲の匂いパーティクル密度
            bait_mass_ratio: エサの残り質量割合 (0.0-1.0)
        """
        self.state_timer += dt
        self.disturbance_force = np.array([0.0, 0.0])  # Reset
        
        if self.state == FishState.IDLE:
            self._idle_behavior(dt, bait_position, particle_density)
        elif self.state == FishState.APPROACH:
            self._approach_behavior(dt, bait_position, bait_mass_ratio)
        elif self.state == FishState.ATTACK:
            self._attack_behavior(dt, bait_position)
        elif self.state == FishState.COOLDOWN:
            self._cooldown_behavior(dt)
        
        # 位置更新
        self.position += self.velocity * dt
        
        # 水面拘束 (空を飛ばないようにする)
        if self.position[1] > 0.0:
            self.position[1] = 0.0
            if self.velocity[1] > 0:
                self.velocity[1] *= -0.5  # 水面で跳ね返る
    
    def _idle_behavior(self, dt: float, bait_position: np.ndarray, particle_density: float):
        """ランダム徘徊"""
        # ランダムな方向へ泳ぐ
        self.velocity += np.random.randn(2) * 0.01
        self.velocity *= 0.95  # 減衰
        
        # 匂いを検知したら接近へ遷移
        if particle_density > 0.1 or self.hunger > 0.7:
            self.state = FishState.APPROACH
            self.state_timer = 0.0
    
    def _approach_behavior(self, dt: float, bait_position: np.ndarray, bait_mass_ratio: float):
        """エサへ接近 + サワリ生成"""
        direction = bait_position - self.position
        distance = np.linalg.norm(direction)
        
        if distance > 0.01:
            direction /= distance
            self.velocity = direction * 0.1 * self.hunger
        
        # --- サワリ (Sawari) with Ornstein-Uhlenbeck過程 ---
        # 近くにいる場合、時間相関のある擾乱力を発生させる
        if distance < config.SAWARI_DISTANCE_THRESHOLD:
            # Ornstein-Uhlenbeck過程による時間相関のある揺れ
            # dX = -θ·X·dt + σ·√dt·ε （εは標準正規分布）
            theta = config.SAWARI_OU_THETA  # 1/τ（時定数の逆数）
            sigma = config.SAWARI_OU_SIGMA  # 強度

            # OU過程の更新（2次元独立）
            drift = -theta * self.ou_state * dt
            diffusion = sigma * np.sqrt(dt) * np.random.randn(2)
            self.ou_state = self.ou_state + drift + diffusion

            # 距離に応じた強度調整（近いほど強い）
            strength_factor = (config.SAWARI_DISTANCE_THRESHOLD - distance) * 2.0
            self.disturbance_force = self.ou_state * strength_factor
        else:
            # 範囲外では状態を徐々に減衰（魚が離れても揺れは残る）
            self.ou_state *= 0.9
            self.disturbance_force = np.array([0.0, 0.0])

        # 十分近づいたら攻撃へ遷移
        if distance < 0.05:
            # 基本攻撃確率
            attack_probability = self.hunger * (1 - self.caution)
            
            # --- アタリ返し (Atari-gaeshi) ---
            # エサが小さくなると食い気が上がる（特に残り30%以下）
            if bait_mass_ratio < 0.3:
                attack_probability *= 2.0  # 確率倍増
            
            # フレーム毎の判定なのでDtでスケーリング
            # (簡易ポアソン過程: P = rate * dt)
            base_attack_rate = 5.0 # 回/秒 (試行回数ベース)
            if np.random.random() < attack_probability * base_attack_rate * dt:
                self.state = FishState.ATTACK
                self.state_timer = 0.0
                self.suck_direction = direction
                
                # --- BiteType 決定 ---
                rand_val = np.random.random()
                if rand_val < 0.6:    # 60%: 通常アタリ（最も一般的）
                    self.bite_type = BiteType.NORMAL
                elif rand_val < 0.8:  # 20%: 食い上げ（チャンスアタリ）
                    self.bite_type = BiteType.KUIAGE
                else:                 # 20%: 消し込み（難易度高）
                    self.bite_type = BiteType.KESHIKOMI

    def _attack_behavior(self, dt: float, bait_position: np.ndarray):
        """吸い込み攻撃 + 事後動作"""
        # 吸い込み力を発生
        attack_duration = 0.3  # 秒
        
        # 3段階モデルで吸い込み力を計算（50ms急峻立ち上がり）
        self.suck_strength = self._calculate_suck_strength_3stage(self.state_timer)
        
        # --- 事後動作 (Post-Attack Motion) ---
        # エサを咥えている間の魚の動きがウキにアタリとして出る
        move_speed = 0.2  # 移動速度
        
        if self.bite_type == BiteType.KUIAGE:
            # 上方向 (+y) へ移動
            self.velocity += np.array([0.0, move_speed]) * dt
        elif self.bite_type == BiteType.KESHIKOMI:
            # 下方向 (-y) または元いた方向の逆へ強く移動
            dive_dir = -self.suck_direction
            if dive_dir[1] > 0: # もし上が潜る方向なら強制的に下へ
                dive_dir[1] = -1.0
            self.velocity += dive_dir * move_speed * 1.5 * dt
        else:
            # NORMAL: その場で少しランダム
             self.velocity += np.random.randn(2) * 0.05 * dt

        if self.state_timer > attack_duration:
            self.state = FishState.COOLDOWN
            self.state_timer = 0.0
            self.suck_strength = 0.0
    
    def _cooldown_behavior(self, dt: float):
        """離脱"""
        # 後退
        self.velocity = -self.suck_direction * 0.05
        
        if self.state_timer > 1.0:
            self.state = FishState.IDLE
            self.state_timer = 0.0

    def _calculate_suck_strength_3stage(self, t: float) -> float:
        """
        ツンの3段階モデル（実釣に即した急峻な立ち上がり）
        
        Args:
            t: ATTACK開始からの経過時間 [s]
        
        Returns:
            吸い込み強度（無次元、0-5程度）
        
        時間区分:
            - 準備 (0-50ms): 口を開く、緩やかな立ち上がり
            - 爆発 (50-150ms): 鰓蓋を閉じて爆発的吸引、50msでピーク
            - 減衰 (150-300ms): 離脱開始、指数減衰
        """
        if t < 0.05:
            # 準備段階: 口を開く（線形）
            return 0.5 * (t / 0.05)
        elif t < 0.15:
            # 爆発段階: 爆発的吸引（ガウス型、σ=25ms）
            peak_time = 0.10  # 100ms = 50ms準備 + 50ms爆発
            width = 0.025     # 25ms（標準偏差）
            return 5.0 * np.exp(-((t - peak_time) ** 2) / (2 * width ** 2))
        else:
            # 減衰段階: 離脱開始（指数減衰、τ=100ms）
            decay_start = 0.15
            decay_rate = 0.10  # 時定数100ms
            return 5.0 * np.exp(-(t - decay_start) / decay_rate)
    
    def get_suck_force(self, target_position: np.ndarray) -> np.ndarray:
        """吸い込み力を計算（双極子型力場）"""
        if self.suck_strength < 0.01:
            return np.array([0.0, 0.0])
        
        r_vec = target_position - self.position
        distance = np.linalg.norm(r_vec)
        
        # 範囲外は完全にゼロ
        if distance > config.SUCK_FORCE_CUTOFF or distance < 0.001:
            return np.array([0.0, 0.0])
        
        # 双極子型: (r/r₀)² · exp(-r/r₀)
        # ピーク位置が r₀ = 1.5cm、5cm超で完全にゼロ
        r0 = config.SUCK_FORCE_RANGE
        normalized_distance = distance / r0
        dipole_profile = (normalized_distance ** 2) * np.exp(-normalized_distance)
        
        force_magnitude = self.suck_strength * dipole_profile
        force_direction = -r_vec / distance
        
        return force_magnitude * force_direction

    def get_disturbance_force(self) -> np.ndarray:
        """サワリによる擾乱力を返す"""
        return self.disturbance_force

