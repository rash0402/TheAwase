"""マクロビュー レンダラー"""

import numpy as np
import pygame
from theawase import config
from theawase.physics.float_model import FloatModel
from theawase.physics.utils import rotate_point


def safe_rect(x, y, w, h):
    """安全な矩形作成（負のサイズ回避）"""
    return (max(0, int(x)), max(0, int(y)), max(1, int(w)), max(1, int(h)))


class MacroViewRenderer:
    """
    マクロビュー（ウキの超拡大映像）のレンダラー

    フォトリアルなウキの拡大表示、静謐な美しさ
    """

    def __init__(self, font_loader):
        """
        Args:
            font_loader: フォント取得関数 (size: int) -> pygame.font.Font
        """
        self.font_loader = font_loader
        self.scale = config.MACRO_VIEW_SCALE  # 2000 px/m (1mm = 2px)

    def render(self, screen: pygame.Surface, view_rect: pygame.Rect,
               float_model: FloatModel, bait, game_state: dict):
        """マクロビューを描画"""
        # クリップ領域設定
        screen.set_clip(view_rect)

        # 背景（空）
        screen.fill(config.COLOR_SKY, view_rect)

        # 水面線（固定Y座標 - 現実的：水面は動かず、ウキが動く）
        water_line_y = view_rect.centery + config.MACRO_WATER_OFFSET_PX
        self._draw_water(screen, view_rect, water_line_y)

        # デバッグ: クリッピングを一時的に無効化してウキの位置を確認
        # ウキ描画
        self._draw_float(screen, view_rect, float_model, water_line_y)

        # エサ残量インジケーター（実釣の核心：エサの溶け具合でウキが浮上）
        self._draw_bait_indicator(screen, view_rect, bait)

        # 結果表示
        if game_state.get('last_result'):
            self._draw_result(screen, view_rect, game_state)

        # クリップ解除
        screen.set_clip(None)

    def _draw_water(self, screen, view_rect, water_line_y):
        """水面と水中領域を描画"""
        # 水面線
        pygame.draw.line(screen, (100, 160, 220),
                         (view_rect.left, int(water_line_y)),
                         (view_rect.right, int(water_line_y)), 2)

        # 水中領域（水面線より下）
        water_height = view_rect.bottom - int(water_line_y)
        if water_height > 0:
            pygame.draw.rect(screen, config.COLOR_WATER,
                             safe_rect(view_rect.left, water_line_y,
                                       view_rect.width, water_height))

    def _draw_float(self, screen, view_rect, float_model, water_line_y):
        """ウキを描画（物理位置に基づく、角度対応）"""
        float_pos = float_model.get_position()

        # ピクセルサイズ変換
        top_len_px = int(float_model.top_length * self.scale)
        body_len_px = int(float_model.body_length * self.scale)
        top_width_px = max(2, int(float_model.top_radius * 2 * self.scale))
        body_width_px = max(4, int(float_model.body_radius * 2 * self.scale))

        # ウキ座標計算（先端位置: 水面線から物理位置分だけオフセット）
        uki_tip_y = water_line_y - float(float_pos[1]) * self.scale
        uki_x = view_rect.centerx

        total_width = max(top_width_px, body_width_px) + 4  # マージン
        total_height = top_len_px + body_len_px

        # 一時Surfaceにウキを描画（回転前）
        float_surf = pygame.Surface((total_width, total_height), pygame.SRCALPHA)

        # トップ描画
        top_x_offset = (total_width - top_width_px) // 2
        self._draw_top_to_surface(float_surf, top_x_offset, 0, top_width_px, top_len_px)

        # ボディ描画
        body_x_offset = (total_width - body_width_px) // 2
        body_rect = safe_rect(body_x_offset, top_len_px, body_width_px, body_len_px)
        pygame.draw.ellipse(float_surf, (60, 40, 60), body_rect)

        # 角度を取得して回転
        angle_deg = np.degrees(float_model.angle)
        rotated_surf = pygame.transform.rotate(float_surf, -angle_deg)

        # 先端を回転中心にして配置（rotate_point ユーティリティ使用）
        offset_y = -(total_height / 2)  # 先端は上端中央
        rot_x, rot_y = rotate_point(0, offset_y, np.radians(-angle_deg))

        rotated_rect = rotated_surf.get_rect()
        tip_x = rotated_rect.width // 2 + rot_x
        tip_y = rotated_rect.height // 2 + rot_y

        blit_x = int(uki_x - tip_x)
        blit_y = int(uki_tip_y - tip_y)
        screen.blit(rotated_surf, (blit_x, blit_y))

    def _draw_top_to_surface(self, surface, x_offset, y_offset, top_width_px, top_len_px):
        """トップを赤/白の節模様でSurfaceに描画"""
        segment_height = config.TOP_SEGMENT_HEIGHT_PX  # 細かい節模様でリアルさ向上
        top_segments = max(5, top_len_px // segment_height)
        segment_height = top_len_px / top_segments

        for i in range(top_segments):
            # 色: 赤/白 (先端から交互)
            color = (255, 50, 50) if i % 2 == 0 else (255, 240, 240)

            # 節の黒線
            line_rect = safe_rect(x_offset,
                                  y_offset + i * segment_height,
                                  top_width_px, 1)
            pygame.draw.rect(surface, (0, 0, 0), line_rect)

            # セグメント本体
            rect = safe_rect(x_offset,
                             y_offset + i * segment_height + 1,
                             top_width_px, segment_height - 1)
            pygame.draw.rect(surface, color, rect)

    def _draw_bait_indicator(self, screen, view_rect, bait):
        """エサ残量インジケーター（実釣の核心：エサが溶けるとウキが浮く）"""
        # エサの残量比率（0.0～1.0）
        mass_ratio = bait.get_mass_ratio()

        # バーの位置とサイズ
        bar_width = 200
        bar_height = 20
        bar_x = view_rect.left + 20
        bar_y = view_rect.top + 20

        # 背景（枠）
        pygame.draw.rect(screen, (80, 80, 80),
                        (bar_x, bar_y, bar_width, bar_height), 2)

        # 残量バー（色のグラデーション：緑→黄→赤）
        if mass_ratio > 0:
            filled_width = int(bar_width * mass_ratio)
            # 色決定：100-50%=緑、50-20%=黄、20-0%=赤
            if mass_ratio > 0.5:
                color = (50, 200, 50)  # 緑
            elif mass_ratio > 0.2:
                color = (220, 200, 50)  # 黄
            else:
                color = (220, 50, 50)  # 赤

            pygame.draw.rect(screen, color,
                           (bar_x + 2, bar_y + 2, filled_width - 4, bar_height - 4))

        # ラベル
        font = self.font_loader(16)
        label = f"エサ残量: {mass_ratio*100:.0f}%"
        text_surface = font.render(label, True, (255, 255, 255))
        screen.blit(text_surface, (bar_x + bar_width + 10, bar_y + 2))

        # ヒント（エサが減るとウキが浮く）
        if mass_ratio < 0.3:
            hint_font = self.font_loader(14)
            hint_text = "（エサが溶けてウキが浮上中）"
            hint_surface = hint_font.render(hint_text, True, (180, 180, 255))
            screen.blit(hint_surface, (bar_x, bar_y + bar_height + 5))

    def _draw_result(self, screen, view_rect, game_state):
        """アワセ結果を表示"""
        font = self.font_loader(48)
        result_text = game_state['last_result']
        # 成功系メッセージは緑、失敗系は赤
        is_success = any(keyword in result_text for keyword in ('EXCELLENT', 'PERFECT', 'GOOD'))
        result_color = (50, 200, 50) if is_success else (200, 50, 50)
        text_surface = font.render(result_text, True, result_color)
        screen.blit(text_surface, (int(view_rect.centerx - 50),
                                    int(view_rect.top + 50)))
