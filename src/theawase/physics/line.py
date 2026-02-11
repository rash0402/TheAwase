"""道糸モデル (不感帯付きバネ)"""

import numpy as np
from theawase import config


class LineModel:
    """
    道糸の物理モデル

    - 不感帯（デッドゾーン）付きバネモデル
    - 水切り（表面張力）の状態管理
    """

    def __init__(
        self,
        stiffness: float = config.LINE_STIFFNESS,
        rest_length: float = config.LINE_REST_LENGTH,
    ):
        self.stiffness = stiffness
        self.rest_length = rest_length
        
        # 水切り状態
        self.is_water_cut = False
        self.tension_transmission = config.SURFACE_TENSION_FACTOR
    
    def water_cut(self):
        """水切りを実行（竿先を水面下に押し込む操作）"""
        self.is_water_cut = True
        self.tension_transmission = 1.0
    
    def reset(self):
        """状態リセット"""
        self.is_water_cut = False
        self.tension_transmission = config.SURFACE_TENSION_FACTOR
    
    def calculate_tension(
        self,
        tip_position: np.ndarray,
        float_position: np.ndarray,
    ) -> np.ndarray:
        """
        張力を計算
        
        Args:
            tip_position: 竿先位置
            float_position: ウキ位置
        
        Returns:
            張力ベクトル（ウキに作用）
        """
        # 糸ベクトル
        line_vector = float_position - tip_position
        line_length = np.linalg.norm(line_vector)
        
        if line_length < 1e-6:
            return np.array([0.0, 0.0])
        
        # 長さ制限（物理発散防止）
        max_line_length = 10.0
        if line_length > max_line_length:
            line_vector = (line_vector / line_length) * max_line_length
            line_length = max_line_length
        
        # 正規化
        line_direction = line_vector / line_length

        # 伸び量（基準長を超えた分、張力発生開始）
        extension = line_length - self.rest_length
        
        if extension <= 0:
            # 糸が緩んでいる（張力なし）
            return np.array([0.0, 0.0])
        
        # 張力の大きさ
        tension_magnitude = self.stiffness * extension * self.tension_transmission
        
        # 張力上限（物理発散防止）
        max_tension = 5.0  # N（ニュートン）
        tension_magnitude = min(tension_magnitude, max_tension)
        
        # 張力ベクトル（竿先方向へ引っ張る）
        tension = -tension_magnitude * line_direction
        
        # NaN チェック
        if not np.all(np.isfinite(tension)):
            return np.array([0.0, 0.0])
        
        return tension
