# アワセタイミングインジケータ実装プラン

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 魚のATTACK中、画面下部に半円ゲージで最適アワセタイミングを視覚表示する

**Architecture:** 新規`TimingIndicatorRenderer`クラスを作成し、main.pyのマクロビュー描画後に条件付きレンダリング。色マッピングと角度計算のロジックは純粋関数として実装し、pygame描画メソッドは統合テストで検証。

**Tech Stack:** Python 3.10+, Pygame 2.5+, Pytest (テスト), Numpy (数学計算)

---

## Task 1: TimingIndicatorRendererクラスの骨格作成

**Files:**
- Create: `src/theawase/rendering/timing_indicator.py`
- Test: `tests/rendering/test_timing_indicator.py`

**Step 1: テストファイルのディレクトリ確認と作成**

```bash
# tests/renderingディレクトリが存在するか確認
ls tests/rendering 2>/dev/null || mkdir -p tests/rendering
touch tests/rendering/__init__.py
```

Expected: ディレクトリが作成される（既存なら何もしない）

**Step 2: 色マッピングの失敗テストを書く**

Create: `tests/rendering/test_timing_indicator.py`

```python
"""TimingIndicatorRendererのテスト"""

import pytest
from theawase.rendering.timing_indicator import TimingIndicatorRenderer


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
```

**Step 3: テストを実行して失敗を確認**

Run:
```bash
pytest tests/rendering/test_timing_indicator.py -v
```

Expected: `ModuleNotFoundError: No module named 'theawase.rendering.timing_indicator'`

**Step 4: 最小限の実装（クラス骨格 + 色マッピング）**

Create: `src/theawase/rendering/timing_indicator.py`

```python
"""アワセタイミングインジケータ レンダラー"""

import pygame
import numpy as np


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
        if t_ms < 100.0:
            # TOO EARLY: 赤
            return (255, 50, 50)
        elif t_ms < 150.0:
            # EARLY: 黄
            return (255, 200, 0)
        elif t_ms <= 450.0:
            # PERFECT: 緑
            return (50, 255, 50)
        elif t_ms < 550.0:
            # LATE: 黄
            return (255, 200, 0)
        else:
            # TOO LATE: 赤
            return (255, 50, 50)

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
```

**Step 5: テストを実行してパスを確認**

Run:
```bash
pytest tests/rendering/test_timing_indicator.py -v
```

Expected: すべてのテストがPASS（7個）

**Step 6: コミット**

```bash
git add src/theawase/rendering/timing_indicator.py tests/rendering/test_timing_indicator.py tests/rendering/__init__.py
git commit -m "feat: add TimingIndicatorRenderer with color mapping logic

- 時間ベースの色マッピング実装（0-600ms）
- テストケース7個でカバレッジ確保
- 赤/黄/緑の3色でタイミングゾーンを視覚化"
```

---

## Task 2: 針の角度計算メソッド追加

**Files:**
- Modify: `src/theawase/rendering/timing_indicator.py`
- Modify: `tests/rendering/test_timing_indicator.py`

**Step 1: 角度計算の失敗テストを書く**

Append to `tests/rendering/test_timing_indicator.py`:

```python
    def test_calculate_needle_angle_at_start(self):
        """0ms: 針が左端（-90度）"""
        renderer = TimingIndicatorRenderer()
        angle = renderer._calculate_needle_angle(0.0)
        assert angle == -90.0, f"Expected -90, got {angle}"

    def test_calculate_needle_angle_at_perfect_start(self):
        """150ms: 針が-45度（左から1/4）"""
        renderer = TimingIndicatorRenderer()
        angle = renderer._calculate_needle_angle(150.0)
        expected = -90 + (150 / 600) * 180  # -45度
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
```

**Step 2: テストを実行して失敗を確認**

Run:
```bash
pytest tests/rendering/test_timing_indicator.py::TestTimingIndicatorRenderer::test_calculate_needle_angle_at_start -v
```

Expected: `AttributeError: 'TimingIndicatorRenderer' object has no attribute '_calculate_needle_angle'`

**Step 3: 角度計算メソッドを実装**

Add to `src/theawase/rendering/timing_indicator.py` (after `_get_color_for_timing`):

```python
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
```

**Step 4: テストを実行してパスを確認**

Run:
```bash
pytest tests/rendering/test_timing_indicator.py -v
```

Expected: すべてのテストがPASS（12個）

**Step 5: コミット**

```bash
git add src/theawase/rendering/timing_indicator.py tests/rendering/test_timing_indicator.py
git commit -m "feat: add needle angle calculation for timing indicator

- 時間を角度に線形マッピング（0-600ms → -90～+90度）
- 600ms超は右端でクリップ
- テストケース5個で境界値とクリッピングを検証"
```

---

## Task 3: Pygame描画メソッドの実装

**Files:**
- Modify: `src/theawase/rendering/timing_indicator.py`

**Step 1: 半円ゲージ描画メソッドを実装**

Add to `src/theawase/rendering/timing_indicator.py` (after `_calculate_needle_angle`):

```python
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
            (angle_deg + 90) / 180 * 600  # 角度から時間を逆算
        )
        width = 4 if current_color == (50, 255, 50) else 2

        # 針を描画
        pygame.draw.line(screen, color, (center_x, center_y),
                        (int(end_x), int(end_y)), width)

        # 中心点（小さな円）
        pygame.draw.circle(screen, (255, 255, 255), (center_x, center_y), 4)
```

**Step 2: renderメソッドを完成させる**

Replace the `render` method in `src/theawase/rendering/timing_indicator.py`:

```python
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
```

**Step 3: コミット**

```bash
git add src/theawase/rendering/timing_indicator.py
git commit -m "feat: implement pygame drawing methods for timing indicator

- 半円ゲージの背景描画（半透明黒+白枠）
- 5つの色ゾーン描画（赤/黄/緑/黄/赤）
- 針の描画（角度ベース、最適ゾーンで太く）
- renderメソッド完成（背景→ゾーン→針の順）"
```

---

## Task 4: main.pyへの統合

**Files:**
- Modify: `src/theawase/main.py`

**Step 1: インポート追加**

Find the import section in `src/theawase/main.py` and add:

```python
from theawase.rendering.timing_indicator import TimingIndicatorRenderer
```

After:
```python
from theawase.rendering.macro_view import MacroViewRenderer
```

**Step 2: 初期化追加**

In the `main()` function, find where `macro_renderer` is initialized and add after it:

```python
    # マクロビューレンダラー
    macro_renderer = MacroViewRenderer(font_loader)

    # タイミングインジケータレンダラー（新規）
    timing_indicator = TimingIndicatorRenderer()
```

**Step 3: メインループでATTACK中の魚を追跡**

In the main game loop, find the rendering section (after physics updates, before drawing) and add:

```python
        # ATTACK中の魚を追跡（タイミングインジケータ用）
        active_fish = None
        for fish in fishes:
            if fish.state == FishState.ATTACK:
                active_fish = fish
                break  # 最初のATTACK魚のみ
```

**Step 4: マクロビュー描画後にインジケータを描画**

Find the macro view rendering block and add the indicator rendering:

```python
        # 左半分: マクロビュー
        macro_renderer.render(
            screen,
            macro_rect,
            float_model,
            bait,
            game_state
        )

        # タイミングインジケータ（ATTACK中のみ表示）
        if active_fish and active_fish.state == FishState.ATTACK:
            timing_indicator.render(
                screen,
                macro_rect,
                active_fish.state_timer * 1000,  # 秒 → ミリ秒変換
                active_fish.bite_type
            )
```

**Step 5: コミット**

```bash
git add src/theawase/main.py
git commit -m "feat: integrate TimingIndicatorRenderer into main loop

- インポートと初期化を追加
- ATTACK中の魚を追跡（最初の1匹のみ）
- マクロビュー描画後に条件付きレンダリング
- state_timerを秒→ミリ秒変換して渡す"
```

---

## Task 5: 手動動作確認とエッジケーステスト

**Files:**
- N/A (手動テスト)

**Step 1: シミュレータを起動**

Run:
```bash
python -m theawase.main
```

Expected: ゲームが起動する

**Step 2: タイミングインジケータの表示確認**

1. 魚がATTACK状態になるまで待機（エサ投入後、数秒～数十秒）
2. 画面下部中央に半円ゲージが表示されることを確認
3. 針が左端（-90度）から右端（+90度）へ滑らかに移動することを確認
4. 色ゾーンが正しく表示されることを確認：
   - 左端: 赤（TOO EARLY）
   - やや左: 黄（EARLY）
   - 中央付近: 緑（PERFECT）
   - やや右: 黄（LATE）
   - 右端: 赤（TOO LATE）

**Step 3: タイミング精度テスト**

各タイミングでアワセ（SPACEキー → マウス上げ）を実行：

1. **100ms（赤ゾーン）**: 結果が"TOO EARLY"または"EARLY"
2. **200ms（緑ゾーン）**: 結果が"PERFECT"または"EXCELLENT"
3. **300ms（緑ゾーン中央）**: 結果が"PERFECT"または"EXCELLENT"
4. **500ms（黄ゾーン）**: 結果が"LATE"または"GOOD"
5. **600ms（赤ゾーン）**: 結果が"TOO LATE"または"MISS"

**Step 4: エッジケーステスト**

1. **複数魚が同時ATTACK**: 最初の魚のゲージのみ表示されることを確認
2. **ATTACK→COOLDOWN遷移**: ゲージが即座に非表示になることを確認
3. **連続ATTACK**: ゲージがリセットされて再表示されることを確認
4. **アワセ実行後**: ゲージが消え、結果が表示されることを確認

**Step 5: パフォーマンス確認**

ゲーム実行中にフレームレートを確認：
- 60fps を維持していることを確認
- 描画負荷が増えていないことを確認

Expected: すべてのテストケースでゲージが正しく動作し、60fps維持

**Step 6: 最終コミット**

```bash
git add -A
git commit -m "test: manual verification of timing indicator

- ゲージ表示の視覚的確認完了
- タイミング精度テスト完了（5パターン）
- エッジケーステスト完了（4パターン）
- パフォーマンステスト完了（60fps維持確認）

✅ アワセタイミングインジケータ機能の実装完了"
```

---

## 完了条件

以下がすべて満たされたら実装完了：

- ✅ TimingIndicatorRendererクラスが作成され、テストがパス（12個）
- ✅ main.pyに統合され、ATTACK中のみゲージ表示
- ✅ 針が0-600msで滑らかに左→右へ移動
- ✅ 色ゾーンが正しく表示（赤/黄/緑/黄/赤）
- ✅ エッジケース（複数魚、状態遷移、連続ATTACK）が正しく処理
- ✅ 60fps維持（パフォーマンス劣化なし）

## 期待される成果

実装完了後、プレイヤーは：
- 魚のATTACK中、リアルタイムで最適タイミングが視覚的に分かる
- 緑ゾーン（150-450ms）でアワセすれば高確率で成功
- 初心者でもタイミングを学習しやすくなる
- ウキの動きだけでなく、ゲージも見ながら釣りを楽しめる

へらぶな釣りの達人の評価：
- ✅ 実釣感を損なわない（ウキ描画はそのまま）
- ✅ 初心者への配慮が十分
- ✅ 上級者はゲージを無視して感覚で釣れる
- ✅ ゲーム性とリアリズムのバランスが良い
