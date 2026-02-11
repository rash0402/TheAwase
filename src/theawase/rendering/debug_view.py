"""デバッグビュー レンダラー"""

import numpy as np
import pygame
from theawase import config
from theawase.physics.rod import RodModel
from theawase.physics.line import LineModel
from theawase.physics.float_model import FloatModel
from theawase.physics.bait import BaitModel
from theawase.entities.fish import FishAI, FishState


# 魚の状態名（日本語）
_FISH_STATE_NAMES = {
    FishState.IDLE: "待機",
    FishState.APPROACH: "接近",
    FishState.ATTACK: "吸込み",
    FishState.COOLDOWN: "警戒",
}


class DebugViewRenderer:
    """
    デバッグビュー（水中断面図）のレンダラー

    物理状態の全体を可視化: 竿、糸、ウキ、エサ、魚、パーティクル
    """

    def __init__(self, font_loader):
        """
        Args:
            font_loader: フォント取得関数 (size: int) -> pygame.font.Font
        """
        self.font_loader = font_loader
        self.scale = config.DEBUG_VIEW_SCALE

    def render(self, screen: pygame.Surface, view_rect: pygame.Rect,
               rod: RodModel, line: LineModel, float_model: FloatModel,
               bait: BaitModel, fishes: list[FishAI], hand_pos: np.ndarray,
               game_state: dict):
        """デバッグビューを描画"""
        font = self.font_loader(14)
        font_title = self.font_loader(16)

        # クリップ領域設定（はみ出し防止）
        screen.set_clip(view_rect)

        # 背景
        screen.fill(config.COLOR_DEBUG_BG, view_rect)

        # タイトル
        title_surface = font_title.render("水中断面図（横から見た図）", True, (160, 180, 200))
        screen.blit(title_surface, (view_rect.left + 10, view_rect.top + 8))

        # 水面ライン
        water_y = view_rect.centery
        pygame.draw.line(screen, (100, 160, 220),
                         (view_rect.left, water_y), (view_rect.right, water_y), 3)
        # 水面ラベル
        wl = font.render("── 水面 ──", True, (100, 160, 220))
        screen.blit(wl, (view_rect.right - wl.get_width() - 10, water_y - wl.get_height() - 2))

        # 水中領域（半透明）
        water_surface = pygame.Surface((view_rect.width, view_rect.height // 2), pygame.SRCALPHA)
        water_surface.fill((64, 128, 192, 100))
        screen.blit(water_surface, (view_rect.left, water_y))

        # 匂いパーティクル
        for particle_pos in bait.particles:
            p_screen = self._world_to_screen(particle_pos, view_rect)
            pygame.draw.circle(screen, (255, 255, 100, 128), p_screen, 3)

        # エサ
        bait_screen = self._world_to_screen(bait.position, view_rect)
        bait_size = int(7 * bait.get_mass_ratio() + 3)
        pygame.draw.circle(screen, (200, 150, 100), bait_screen, bait_size)
        self._draw_label(screen, font, f"エサ {bait.get_mass_ratio()*100:.0f}%",
                         bait_screen, (200, 150, 100))

        # 魚群
        for i, fish in enumerate(fishes):
            fish_screen = self._world_to_screen(fish.position, view_rect)
            fish_color = {
                FishState.IDLE: (120, 120, 120),
                FishState.APPROACH: (180, 180, 60),
                FishState.ATTACK: (255, 80, 80),
                FishState.COOLDOWN: (100, 100, 150),
            }.get(fish.state, (120, 120, 120))
            pygame.draw.ellipse(screen, fish_color,
                                (fish_screen[0] - 25, fish_screen[1] - 10, 50, 20))
            if fish.state == FishState.ATTACK:
                pygame.draw.circle(screen, (255, 100, 100), fish_screen,
                                   int(fish.suck_strength * 10), 1)
            state_jp = _FISH_STATE_NAMES.get(fish.state, "?")
            self._draw_label(screen, font, f"魚{i+1} [{state_jp}]", fish_screen, fish_color, (30, -8))

        # 手元位置
        hand_screen = self._world_to_screen(hand_pos, view_rect)
        pygame.draw.circle(screen, (255, 200, 50), hand_screen, 10)
        self._draw_label(screen, font, "手元", hand_screen, (255, 200, 50))

        # 竿先位置
        tip_pos = rod.get_tip_position()
        tip_screen = self._world_to_screen(tip_pos, view_rect)
        pygame.draw.circle(screen, (200, 100, 50), tip_screen, 8)
        self._draw_label(screen, font, "竿先", tip_screen, (200, 100, 50), (14, -18))

        # 竿（手元→竿先）
        pygame.draw.line(screen, (139, 90, 43), hand_screen, tip_screen, 3)

        # ウキ位置
        float_pos = float_model.get_position()
        float_screen = self._world_to_screen(float_pos, view_rect)

        # 道糸（竿先→ウキ）
        line_color = (100, 200, 100) if line.is_water_cut else (200, 100, 100)
        pygame.draw.line(screen, line_color, tip_screen, float_screen, 2)
        # 道糸ラベル（中点付近）
        line_mid = ((tip_screen[0] + float_screen[0]) // 2,
                    (tip_screen[1] + float_screen[1]) // 2)
        line_label = "水切り済" if line.is_water_cut else "水切り前"
        self._draw_label(screen, font, line_label, line_mid, line_color, (-70, -4))

        # ハリス（ウキ→エサ）
        pygame.draw.line(screen, (150, 150, 150), float_screen, bait_screen, 1)

        # ウキ本体（角度付き描画）
        self._draw_float_with_angle(screen, float_model, float_screen, font)

        # クリップ解除 for UI overlay
        screen.set_clip(None)

        # 情報パネル（右下）
        self._draw_info_panel(screen, view_rect, font, fishes, bait, game_state)

    def _draw_float_with_angle(self, screen, float_model, float_screen, font):
        """ウキを角度付きで描画（トップ先端を回転中心として）"""
        float_width = 12
        float_height = 52
        float_surf = pygame.Surface((float_width, float_height), pygame.SRCALPHA)
        pygame.draw.ellipse(float_surf, (255, 50, 50), (0, 0, float_width, float_height))

        # 角度を度に変換（pygameは度を使用）
        angle_deg = np.degrees(float_model.angle)
        rotated_surf = pygame.transform.rotate(float_surf, -angle_deg)  # 負の角度で時計回り

        # 回転の中心をトップ先端（糸の接続点）に設定
        # 元のSurfaceでの先端位置（上端中央）
        orig_tip_x = float_width // 2
        orig_tip_y = 0
        orig_center_x = float_width // 2
        orig_center_y = float_height // 2

        # 先端の中心からのオフセット
        offset_x = orig_tip_x - orig_center_x  # = 0
        offset_y = orig_tip_y - orig_center_y  # = -float_height/2

        # 回転後のオフセット（回転行列適用）
        angle_rad = np.radians(-angle_deg)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        rotated_offset_x = offset_x * cos_a - offset_y * sin_a
        rotated_offset_y = offset_x * sin_a + offset_y * cos_a

        # 回転後のSurfaceの中心
        rotated_rect = rotated_surf.get_rect()
        rotated_center_x = rotated_rect.width // 2
        rotated_center_y = rotated_rect.height // 2

        # 回転後の先端位置（Surface座標）
        tip_in_rotated_x = rotated_center_x + rotated_offset_x
        tip_in_rotated_y = rotated_center_y + rotated_offset_y

        # スクリーン上での描画位置（先端がfloat_screenに来るように）
        blit_x = int(float_screen[0] - tip_in_rotated_x)
        blit_y = int(float_screen[1] - tip_in_rotated_y)

        screen.blit(rotated_surf, (blit_x, blit_y))

        self._draw_label(screen, font, f"ウキ({angle_deg:.0f}°)", float_screen, (255, 80, 80), (-36, 10))

    def _draw_info_panel(self, screen, view_rect, font, fishes, bait, game_state):
        """情報パネルを描画"""
        attack_count = sum(1 for fish in fishes if fish.state == FishState.ATTACK)
        approach_count = sum(1 for fish in fishes if fish.state == FishState.APPROACH)
        avg_hunger = sum(fish.hunger for fish in fishes) / len(fishes) if fishes else 0

        info_texts = [
            f"魚数: {len(fishes)}",
            f"吸込み中: {attack_count}匹 / 接近中: {approach_count}匹",
            f"平均空腹度: {avg_hunger*100:.0f}%",
            f"エサ残量: {bait.get_mass_ratio()*100:.0f}%",
            f"スコア: {game_state.get('score', 0)}",
        ]

        panel_x = view_rect.left + 10
        panel_y = view_rect.bottom - 10 - len(info_texts) * 18

        for i, text in enumerate(info_texts):
            text_surface = font.render(text, True, (180, 200, 220))
            screen.blit(text_surface, (panel_x, panel_y + i * 18))

    def _world_to_screen(self, pos: np.ndarray, view_rect: pygame.Rect) -> tuple[int, int]:
        """ワールド座標からスクリーン座標に変換"""
        cx, cy = view_rect.centerx, view_rect.centery
        try:
            sx = int(float(pos[0]) * self.scale + cx)
            sy = int(cy - float(pos[1]) * self.scale)  # Y軸反転
            # クランプ
            sx = max(-10000, min(10000, sx))
            sy = max(-10000, min(10000, sy))
            return (sx, sy)
        except (ValueError, OverflowError):
            return (int(cx), int(cy))

    def _draw_label(self, screen, font, text, pos, color, offset=(10, -20)):
        """ラベルを描画"""
        label_surface = font.render(text, True, color)
        screen.blit(label_surface, (pos[0] + offset[0], pos[1] + offset[1]))
