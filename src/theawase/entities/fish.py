"""魚AI (ステートマシン)"""

import numpy as np
from enum import Enum, auto


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
        
        # --- サワリ (Sawari) ---
        # 近くにいる場合、ランダムな水流（擾乱力）を発生させる
        if distance < 0.15:
            # 距離が近いほど強い、ただし微弱
            strength = (0.15 - distance) * 2.0 * np.random.random()
            # ランダムベクトル
            sawari_vec = np.random.randn(2) * strength
            self.disturbance_force = sawari_vec

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
        t = self.state_timer / attack_duration
        
        # サージ関数（立ち上がり）
        self.suck_strength = np.exp(-((t - 0.5)**2) / 0.1) * 5.0
        
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
    
    def get_suck_force(self, target_position: np.ndarray) -> np.ndarray:
        """吸い込み力を計算"""
        if self.suck_strength < 0.01:
            return np.array([0.0, 0.0])
        
        r = target_position - self.position
        distance = np.linalg.norm(r)
        
        if distance < 0.01:
            return np.array([0.0, 0.0])
        
        force_magnitude = self.suck_strength * np.exp(-distance**2)
        force_direction = -r / distance
        
        return force_magnitude * force_direction

    def get_disturbance_force(self) -> np.ndarray:
        """サワリによる擾乱力を返す"""
        return self.disturbance_force

