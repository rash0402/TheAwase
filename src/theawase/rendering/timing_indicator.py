"""アワセタイミングインジケータ レンダラー"""

import pygame
import numpy as np
from theawase import config


class TimingIndicatorRenderer:
    """
    アワセタイミング半円ゲージレンダラー

    魚のATTACK中、画面下部にリアルタイムタイミングインジケータを表示。
    """

    def __init__(self):
        self.radius = 50  # 半円の半径（px）
        self.needle_length = 45  # 針の長さ（px）

    def _get_color_for_timing(self, t_ms: float) -> tuple:
        """
        時間に応じた色を返す

        Args:
            t_ms: ATTACK開始からの経過時間（ミリ秒）

        Returns:
            RGB色タプル (R, G, B)
        """
        if t_ms < config.TIMING_TOO_EARLY_MAX:
            # TOO EARLY: 赤
            return config.COLOR_TIMING_TOO_EARLY
        elif t_ms < config.TIMING_EARLY_MAX:
            # EARLY: 黄
            return config.COLOR_TIMING_EARLY
        elif t_ms <= config.TIMING_PERFECT_MAX:
            # PERFECT: 緑
            return config.COLOR_TIMING_PERFECT
        elif t_ms < config.TIMING_LATE_MAX:
            # LATE: 黄
            return config.COLOR_TIMING_EARLY
        else:
            # TOO LATE: 赤
            return config.COLOR_TIMING_TOO_EARLY

    def _calculate_needle_angle(self, t_ms: float) -> float:
        """
        針の角度を計算（時間に基づく）

        Args:
            t_ms: ATTACK開始からの経過時間（ミリ秒）

        Returns:
            角度（度）: -90（左端）～ +90（右端）
        """
        # 600msでクリップ
        t_clamped = min(t_ms, 600.0)

        # 線形マッピング: 0ms → -90度, 600ms → +90度
        angle = -90.0 + (t_clamped / 600.0) * 180.0

        return angle

    def render(self, screen, view_rect, state_timer_ms: float, bite_type):
        """
        タイミングゲージを描画

        Args:
            screen: pygame surface
            view_rect: マクロビューの矩形
            state_timer_ms: ATTACK開始からの経過時間（ミリ秒）
            bite_type: BiteType enum（KESHIKOMI/KUIAGE/NORMAL）
        """
        # TODO: 次のタスクで実装
        pass
