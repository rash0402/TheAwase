"""汎用UIButtonクラス（Pygame用）"""
import pygame
from typing import Callable


class UIButton:
    """
    クリック可能なボタン（hover/pressed/selected状態対応）

    使い方:
        Pygameのイベントループ内でhandle_event()を呼ぶ。
        render()は毎フレーム呼ぶ必要がある。
    """

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        on_click: Callable,
        color: tuple = (64, 128, 255),
        text_color: tuple = (255, 255, 255),
        font: pygame.font.Font = None,
    ):
        self.rect = rect
        self.label = label
        self.on_click = on_click
        self.color = color
        self.text_color = text_color
        self.font = font or pygame.font.Font(None, 28)

        self.hovered = False
        self.pressed = False
        self.selected = False  # ラジオボタン的な選択状態（外部から設定）

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        イベントを処理する。

        Returns:
            クリックが確定した場合 True、そうでなければ False
        """
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.rect.collidepoint(event.pos):
                self.pressed = False
                self.on_click()
                return True
            self.pressed = False
        return False

    def render(self, screen: pygame.Surface):
        """ボタンを描画（hover/pressed/selectedで色変化）"""
        r, g, b = self.color

        # 押下・ホバー時の輝度変化
        if self.pressed:
            r, g, b = int(r * 0.7), int(g * 0.7), int(b * 0.7)
        elif self.hovered:
            r = min(255, int(r * 1.3))
            g = min(255, int(g * 1.3))
            b = min(255, int(b * 1.3))

        pygame.draw.rect(screen, (r, g, b), self.rect, border_radius=6)

        # 選択中は太い白枠、非選択は細いグレー枠
        border_width = 3 if self.selected else 1
        border_color = (255, 255, 255) if self.selected else (180, 180, 180)
        pygame.draw.rect(screen, border_color, self.rect, border_width, border_radius=6)

        # テキスト（中央揃え）
        text_surface = self.font.render(self.label, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
