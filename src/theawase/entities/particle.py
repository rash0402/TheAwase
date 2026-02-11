"""匂いパーティクル"""

import numpy as np


class Particle:
    """匂いパーティクル（ブラウン運動）"""
    
    def __init__(self, position: np.ndarray, lifetime: float = 5.0):
        self.position = position.copy()
        self.lifetime = lifetime
        self.age = 0.0
    
    def update(self, dt: float, diffusion: float = 0.01):
        """パーティクルを拡散"""
        self.position += np.random.randn(2) * diffusion * np.sqrt(dt)
        self.age += dt
    
    def is_alive(self) -> bool:
        """生存判定"""
        return self.age < self.lifetime
