"""トラックパッド入力処理"""

import numpy as np
import pygame


class TrackpadInput:
    """
    トラックパッド絶対座標入力
    
    パッド上の指の位置を手元の位置にマッピング
    """
    
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # マッピング範囲（メートル）
        self.world_width = 0.3   # 30cm
        self.world_height = 0.3  # 30cm
        
        # 状態
        self.is_touching = False
        self.position = np.array([0.0, 0.0])
        self.velocity = np.array([0.0, 0.0])
        self._prev_position = np.array([0.0, 0.0])
    
    def update(self, dt: float):
        """入力状態を更新"""
        mouse_pressed = pygame.mouse.get_pressed()[0]
        
        if mouse_pressed:
            mouse_pos = pygame.mouse.get_pos()
            
            # スクリーン座標 → ワールド座標
            new_position = np.array([
                (mouse_pos[0] / self.screen_width - 0.5) * self.world_width,
                -(mouse_pos[1] / self.screen_height - 0.5) * self.world_height,
            ])
            
            if self.is_touching:
                # 速度計算
                self.velocity = (new_position - self._prev_position) / dt
            else:
                self.velocity = np.array([0.0, 0.0])
            
            self._prev_position = self.position.copy()
            self.position = new_position
            self.is_touching = True
        else:
            self.is_touching = False
            self.velocity *= 0.9  # 減衰
    
    def get_position(self) -> np.ndarray:
        """手元位置を取得"""
        return self.position.copy()
    
    def get_velocity(self) -> np.ndarray:
        """手元速度を取得"""
        return self.velocity.copy()
    
    def is_awase_gesture(self, threshold: float = 0.5) -> bool:
        """
        アワセ動作の検出
        
        上方向への鋭い動き
        """
        return self.velocity[1] > threshold
