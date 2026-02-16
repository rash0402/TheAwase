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
        # TIMING_GAUGE_DURATION_MS でクリップ
        t_clamped = min(t_ms, config.TIMING_GAUGE_DURATION_MS)

        # 線形マッピング: 0ms → -90度, TIMING_GAUGE_DURATION_MS → +90度
        angle = -90.0 + (t_clamped / config.TIMING_GAUGE_DURATION_MS) * 180.0

        return angle

    def _draw_gauge_background(self, screen, center_x: int, center_y: int):
        """
        半円ゲージの背景を描画

        Args:
            screen: pygame surface
            center_x: 中心X座標（px）
            center_y: 中心Y座標（px）
        """
        # 半透明黒の背景円
        bg_color = (20, 20, 20, 180)
        bg_surface = pygame.Surface((self.radius * 2, self.radius), pygame.SRCALPHA)
        pygame.draw.circle(bg_surface, bg_color, (self.radius, self.radius), self.radius)
        screen.blit(bg_surface, (center_x - self.radius, center_y - self.radius))

        # 白色の枠線（半円）
        rect = pygame.Rect(center_x - self.radius, center_y - self.radius,
                          self.radius * 2, self.radius * 2)
        pygame.draw.arc(screen, (255, 255, 255), rect, 0, np.pi, 2)

        # 左右の端線（垂直）
        pygame.draw.line(screen, (255, 255, 255),
                        (center_x - self.radius, center_y),
                        (center_x - self.radius, center_y - self.radius), 2)
        pygame.draw.line(screen, (255, 255, 255),
                        (center_x + self.radius, center_y),
                        (center_x + self.radius, center_y - self.radius), 2)

    def _draw_color_zones(self, screen, center_x: int, center_y: int):
        """
        色分けされたタイミングゾーンを描画

        Args:
            screen: pygame surface
            center_x: 中心X座標（px）
            center_y: 中心Y座標（px）
        """
        # 各ゾーンの角度範囲（度 → ラジアン変換）
        zones = [
            # (開始角度, 終了角度, 色, 時間範囲ms)
            (-90, -60, (255, 50, 50), "0-100ms"),      # TOO EARLY
            (-60, -45, (255, 200, 0), "100-150ms"),    # EARLY
            (-45, 45, (50, 255, 50), "150-450ms"),     # PERFECT
            (45, 60, (255, 200, 0), "450-550ms"),      # LATE
            (60, 90, (255, 50, 50), "550-600ms"),      # TOO LATE
        ]

        rect = pygame.Rect(center_x - self.radius + 5, center_y - self.radius + 5,
                          (self.radius - 5) * 2, (self.radius - 5) * 2)

        for start_deg, end_deg, color, _ in zones:
            # 度をラジアンに変換（pygameのarcは数学座標系）
            # 数学座標系: 0度=右, 90度=上, 180度=左, 270度=下
            # 半円ゲージ座標系: -90度=左, 0度=中央, +90度=右
            # 変換: pygame角度 = 180度 - ゲージ角度
            start_rad = np.radians(180 - start_deg)
            end_rad = np.radians(180 - end_deg)

            # arcは反時計回りなので、start > endの場合は入れ替え
            if start_rad > end_rad:
                start_rad, end_rad = end_rad, start_rad

            pygame.draw.arc(screen, color, rect, start_rad, end_rad, 3)

    def _draw_needle(self, screen, center_x: int, center_y: int,
                    angle_deg: float, color: tuple):
        """
        針を描画

        Args:
            screen: pygame surface
            center_x: 中心X座標（px）
            center_y: 中心Y座標（px）
            angle_deg: 針の角度（度、-90～+90）
            color: 針の色（RGB）
        """
        # 角度をラジアンに変換（ゲージ座標系 → 数学座標系）
        # ゲージ: -90度=左（9時方向）, 0度=上（12時方向）, +90度=右（3時方向）
        # 数学: 0度=右（3時方向）, 90度=上（12時方向）, 180度=左（9時方向）
        # 変換: 数学角度 = 90度 - ゲージ角度
        math_angle_rad = np.radians(90 - angle_deg)

        # 針の先端座標
        end_x = center_x + self.needle_length * np.cos(math_angle_rad)
        end_y = center_y - self.needle_length * np.sin(math_angle_rad)

        # 針の太さ（最適ゾーンで太く）
        current_color = self._get_color_for_timing(
            (angle_deg + 90) / 180 * config.TIMING_GAUGE_DURATION_MS  # 角度から時間を逆算
        )
        width = 4 if current_color == config.COLOR_TIMING_PERFECT else 2

        # 針を描画
        pygame.draw.line(screen, color, (center_x, center_y),
                        (int(end_x), int(end_y)), width)

        # 中心点（小さな円）
        pygame.draw.circle(screen, (255, 255, 255), (center_x, center_y), 4)

    def render(self, screen, view_rect, state_timer_ms: float, bite_type):
        """
        タイミングゲージを描画

        Args:
            screen: pygame surface
            view_rect: マクロビューの矩形
            state_timer_ms: ATTACK開始からの経過時間（ミリ秒）
            bite_type: BiteType enum（KESHIKOMI/KUIAGE/NORMAL）
        """
        # ゲージの中心座標（画面下部中央）
        center_x = view_rect.centerx
        center_y = view_rect.bottom - 100

        # 1. 背景を描画
        self._draw_gauge_background(screen, center_x, center_y)

        # 2. 色ゾーンを描画
        self._draw_color_zones(screen, center_x, center_y)

        # 3. 針を描画
        angle = self._calculate_needle_angle(state_timer_ms)
        needle_color = self._get_color_for_timing(state_timer_ms)
        self._draw_needle(screen, center_x, center_y, angle, needle_color)
