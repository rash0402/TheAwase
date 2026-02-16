"""TimingIndicatorRendererのテスト"""

import pytest
from theawase.rendering.timing_indicator import TimingIndicatorRenderer
from theawase import config


class TestTimingIndicatorRenderer:
    """TimingIndicatorRendererクラスのテスト"""

    def test_get_color_for_timing_too_early(self):
        """0-100ms: 赤色 (TOO EARLY)"""
        renderer = TimingIndicatorRenderer()
        color = renderer._get_color_for_timing(50.0)
        assert color == (255, 50, 50), f"Expected red, got {color}"

    def test_get_color_for_timing_early(self):
        """100-150ms: 黄色 (EARLY)"""
        renderer = TimingIndicatorRenderer()
        color = renderer._get_color_for_timing(125.0)
        assert color == (255, 200, 0), f"Expected yellow, got {color}"

    def test_get_color_for_timing_perfect_start(self):
        """150ms: 緑色 (PERFECT開始)"""
        renderer = TimingIndicatorRenderer()
        color = renderer._get_color_for_timing(150.0)
        assert color == (50, 255, 50), f"Expected green, got {color}"

    def test_get_color_for_timing_perfect_mid(self):
        """300ms: 緑色 (PERFECT中央)"""
        renderer = TimingIndicatorRenderer()
        color = renderer._get_color_for_timing(300.0)
        assert color == (50, 255, 50), f"Expected green, got {color}"

    def test_get_color_for_timing_perfect_end(self):
        """450ms: 緑色 (PERFECT終了)"""
        renderer = TimingIndicatorRenderer()
        color = renderer._get_color_for_timing(450.0)
        assert color == (50, 255, 50), f"Expected green, got {color}"

    def test_get_color_for_timing_late(self):
        """450-550ms: 黄色 (LATE)"""
        renderer = TimingIndicatorRenderer()
        color = renderer._get_color_for_timing(500.0)
        assert color == (255, 200, 0), f"Expected yellow, got {color}"

    def test_get_color_for_timing_too_late(self):
        """550ms+: 赤色 (TOO LATE)"""
        renderer = TimingIndicatorRenderer()
        color = renderer._get_color_for_timing(600.0)
        assert color == (255, 50, 50), f"Expected red, got {color}"

    def test_calculate_needle_angle_at_start(self):
        """0ms: 針が左端（-90度）"""
        renderer = TimingIndicatorRenderer()
        angle = renderer._calculate_needle_angle(0.0)
        assert angle == -90.0, f"Expected -90, got {angle}"

    def test_calculate_needle_angle_at_perfect_start(self):
        """150ms: 針が-45度（左から1/4）"""
        renderer = TimingIndicatorRenderer()
        angle = renderer._calculate_needle_angle(150.0)
        expected = -90 + (150 / config.TIMING_GAUGE_DURATION_MS) * 180  # -45度
        assert abs(angle - expected) < 0.1, f"Expected {expected}, got {angle}"

    def test_calculate_needle_angle_at_center(self):
        """300ms: 針が中央（0度）"""
        renderer = TimingIndicatorRenderer()
        angle = renderer._calculate_needle_angle(300.0)
        expected = 0.0
        assert abs(angle - expected) < 0.1, f"Expected {expected}, got {angle}"

    def test_calculate_needle_angle_at_end(self):
        """600ms: 針が右端（+90度）"""
        renderer = TimingIndicatorRenderer()
        angle = renderer._calculate_needle_angle(600.0)
        assert angle == 90.0, f"Expected 90, got {angle}"

    def test_calculate_needle_angle_clamping(self):
        """600ms超: 針が右端で停止（クリッピング）"""
        renderer = TimingIndicatorRenderer()
        angle = renderer._calculate_needle_angle(800.0)
        assert angle == 90.0, f"Expected 90 (clamped), got {angle}"
