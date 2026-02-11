"""
リアルタイムタイミンググラフレンダラー

Phase 3: ゲームフィードバック強化
デバッグビュー右下に表示する小型グラフ:
- X軸: 試行番号（最新20件）
- Y軸: タイミング値（-500ms ~ +500ms）
- 色分け: PERFECT/GOOD=緑系、EARLY=黄、LATE=橙、MISS=赤
"""

import pygame
import numpy as np
from typing import List, Dict

class TimingGraphRenderer:
    """
    リアルタイムタイミンググラフ

    アワセのタイミング履歴を視覚化し、プレイヤーに学習効果を提供。
    """

    def __init__(self, position: tuple[int, int], size: tuple[int, int]):
        """
        Args:
            position: グラフ左上座標 (x, y)
            size: グラフサイズ (width, height)
        """
        self.pos = position
        self.size = size
        self.max_samples = 20  # 表示する最大試行数

        # 色定義（BiteType + 結果別）
        self.colors = {
            'EXCELLENT': (0, 255, 0),       # 鮮やかな緑
            'PERFECT': (0, 255, 0),         # 鮮やかな緑
            'GOOD': (0, 200, 100),          # やや暗い緑
            'EARLY': (255, 255, 0),         # 黄色
            'BAD': (255, 165, 0),           # オレンジ
            'MISS': (255, 0, 0),            # 赤
        }

        self.bg_color = (20, 20, 20, 200)  # 半透明背景
        self.grid_color = (60, 60, 60)
        self.axis_color = (150, 150, 150)
        self.zero_line_color = (200, 200, 200)

    def render(self, surface: pygame.Surface, awase_history: List[Dict]):
        """
        グラフを描画

        Args:
            surface: 描画先サーフェス
            awase_history: game_state['awase_history']
        """
        # 半透明背景サーフェス（履歴がなくても枠を表示）
        graph_surface = pygame.Surface(self.size, pygame.SRCALPHA)
        graph_surface.fill(self.bg_color)

        # 枠線を描画（目立つように）
        pygame.draw.rect(graph_surface, (100, 150, 200), (0, 0, self.size[0], self.size[1]), 2)

        # グリッド描画
        self._draw_grid(graph_surface)

        # 軸ラベル描画
        self._draw_labels(graph_surface)

        # データポイント描画（履歴がある場合のみ）
        if len(awase_history) > 0:
            recent = awase_history[-self.max_samples:]
            self._draw_data_points(graph_surface, recent)
        else:
            # 履歴がない場合はメッセージを表示
            try:
                font = pygame.font.Font(None, 24)
            except:
                font = pygame.font.SysFont('Hiragino Sans', 24)
            message = font.render("Awaiting Awase...", True, (150, 150, 150))
            text_rect = message.get_rect(center=(self.size[0] // 2, self.size[1] // 2))
            graph_surface.blit(message, text_rect)

        # メインサーフェスに転送
        surface.blit(graph_surface, self.pos)

    def _draw_grid(self, surface: pygame.Surface):
        """グリッド線を描画"""
        width, height = self.size

        # 水平グリッド（±500ms, ±250ms, 0ms）
        for ms in [-500, -250, 0, 250, 500]:
            y = self._timing_to_y(ms)
            if ms == 0:
                color = self.zero_line_color
                thickness = 2
            else:
                color = self.grid_color
                thickness = 1
            pygame.draw.line(surface, color, (0, y), (width, y), thickness)

        # 垂直グリッド（5試行ごと）
        if len(self._get_sample_indices()) > 1:
            for i in range(0, self.max_samples, 5):
                if i < len(self._get_sample_indices()):
                    x = self._index_to_x(i, len(self._get_sample_indices()))
                    pygame.draw.line(surface, self.grid_color, (x, 0), (x, height), 1)

    def _draw_data_points(self, surface: pygame.Surface, data: List[Dict]):
        """データポイントとライン描画"""
        if len(data) < 1:
            return

        points = []
        for i, record in enumerate(data):
            x = self._index_to_x(i, len(data))
            y = self._timing_to_y(record['timing_ms'])

            # 色を決定（メッセージから推測）
            color = self._get_color_from_record(record)

            # 点を描画（円）
            pygame.draw.circle(surface, color, (x, y), 5)

            # 外枠（強調）
            pygame.draw.circle(surface, (255, 255, 255), (x, y), 5, 1)

            points.append((x, y))

        # ライン描画（折れ線グラフ）
        if len(points) > 1:
            pygame.draw.lines(surface, (100, 100, 100), False, points, 2)

    def _get_color_from_record(self, record: Dict) -> tuple[int, int, int]:
        """
        レコードから色を決定

        スコアとBiteTypeから適切な色を選択
        """
        # スコアが正なら成功系、負なら失敗系
        score = record.get('score', 0)

        if score >= 2500:
            return self.colors['PERFECT']
        elif score >= 1000:
            return self.colors['GOOD']
        elif 'EARLY' in record.get('bite_type', ''):
            return self.colors['EARLY']
        elif score < 0:
            return self.colors['MISS']
        else:
            return self.colors['BAD']

    def _draw_labels(self, surface: pygame.Surface):
        """軸ラベル描画"""
        try:
            font = pygame.font.Font(None, 20)
        except:
            font = pygame.font.SysFont('Hiragino Sans', 20)

        # Y軸ラベル
        for ms in [-500, 0, 500]:
            y = self._timing_to_y(ms)
            label_text = f"{ms:+.0f}ms" if ms != 0 else "0ms"
            label = font.render(label_text, True, self.axis_color)
            surface.blit(label, (5, y - 10))

        # X軸ラベル（タイトル）
        try:
            title_font = pygame.font.Font(None, 24)
        except:
            title_font = pygame.font.SysFont('Hiragino Sans', 24)
        x_label = title_font.render("Awase Timing", True, (200, 200, 200))
        surface.blit(x_label, (self.size[0] // 2 - 50, self.size[1] - 25))

    def _timing_to_y(self, timing_ms: float) -> int:
        """
        タイミング値（ms）をY座標に変換

        -500ms → height（下端）, +500ms → 0（上端）
        """
        height = self.size[1]
        # タイミング値を-500~+500の範囲で正規化
        normalized = (timing_ms + 500) / 1000  # 0~1
        # Y座標は上が0なので反転
        return int(height * (1 - normalized))

    def _index_to_x(self, index: int, total_count: int) -> int:
        """
        試行インデックスをX座標に変換

        Args:
            index: データ配列内のインデックス
            total_count: データの総数
        """
        width = self.size[0]
        if total_count <= 1:
            return width // 2
        return int((index / (total_count - 1)) * width)

    def _get_sample_indices(self) -> range:
        """サンプルインデックスの範囲を返す"""
        return range(self.max_samples)
