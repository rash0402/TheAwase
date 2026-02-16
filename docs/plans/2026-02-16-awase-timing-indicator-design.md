# アワセタイミングインジケータ設計書

**日付**: 2026-02-16
**目的**: アワセタイミングの視認性向上（初心者でも最適タイミングが分かる）
**アプローチ**: 画面下部の半円ゲージ + 色グラデーション

---

## 問題の診断

### 現状

- **症状**: アワセのタイミングウィンドウ（150-550ms）が見えず、初心者は釣りにくい
- **ゲームフロー**: 魚がATTACK → プレイヤーがアワセ → 結果表示
- **問題**: ATTACK中、プレイヤーには何も視覚的フィードバックがない

### ユーザー要件

1. **リアルタイム表示**: 魚のATTACK中、常に最適タイミングまでの情報を表示
2. **フォトリアリズム維持**: 左ウィンドウ（マクロビュー）のウキ描画はそのまま
3. **視覚のみ**: 音声フィードバックは不要
4. **画面端配置**: ウキとは分離したUI要素

---

## 設計アーキテクチャ

### ビジュアルデザイン

**半円ゲージの仕様:**

```
        早い         最適         遅い
         ╱           |           ╲
       ╱      ┌──────┼──────┐      ╲
     ╱       │      針      │       ╲
   ╱_______│________________│_______╲
   赤  黄   緑 (150-450ms) 緑   黄  赤

   100ms   150ms        450ms   550ms
```

**配置:**
- 位置: 画面下部中央（view_rect.centerx, view_rect.bottom - 100px）
- サイズ: 直径100px（半円）
- 背景: 半透明黒 rgba(20, 20, 20, 180)
- 枠: 白色、太さ2px

**色マッピング（時間ベース）:**

| 時間範囲 | 色 RGB | 評価 | 説明 |
|---------|--------|------|------|
| 0-100ms | (255, 50, 50) | TOO EARLY | 早すぎ |
| 100-150ms | (255, 200, 0) | EARLY | やや早い |
| **150-450ms** | **(50, 255, 50)** | **PERFECT** | **最適ゾーン** |
| 450-550ms | (255, 200, 0) | LATE | やや遅い |
| 550ms+ | (255, 50, 50) | TOO LATE | 遅すぎ |

**針の動き:**
- ATTACK開始時刻(t=0)で針が左端（-90度）
- 時間経過で滑らかに右へ移動（t=600msで+90度）
- 角度計算: `angle = -90 + (state_timer / 0.6) * 180` (度)
- 最適ゾーン（緑）で針が太く（4px）、白く光る

---

## コンポーネント設計

### 新規ファイル

**`src/theawase/rendering/timing_indicator.py`**

```python
class TimingIndicatorRenderer:
    """
    アワセタイミング半円ゲージレンダラー

    魚のATTACK中、画面下部にリアルタイムタイミングインジケータを表示。
    """

    def __init__(self):
        self.radius = 50  # 半円の半径（px）
        self.needle_length = 45  # 針の長さ（px）

    def render(self, screen, view_rect, state_timer_ms: float, bite_type):
        """
        タイミングゲージを描画

        Args:
            screen: pygame surface
            view_rect: マクロビューの矩形
            state_timer_ms: ATTACK開始からの経過時間（ミリ秒）
            bite_type: BiteType enum（KESHIKOMI/KUIAGE/NORMAL）
        """
        pass  # 実装はimplementation planで詳述

    def _get_color_for_timing(self, t_ms: float) -> tuple:
        """時間に応じた色を返す"""
        pass

    def _draw_gauge_arc(self, surface, center, radius, ...):
        """半円ゲージの弧を描画"""
        pass

    def _draw_needle(self, surface, center, angle, color):
        """針を描画"""
        pass
```

---

## データフロー

```
main.py メインループ
  ↓
魚の状態を監視
  ↓
FishAI.state == ATTACK?
  ↓ YES
active_fish = fish
  ↓
state_timer（0-600ms）を取得
  ↓
TimingIndicatorRenderer.render(
    screen,
    macro_rect,
    state_timer * 1000,  # ms変換
    active_fish.bite_type
)
  ↓
半円ゲージ描画
  - 針の角度計算
  - 色の決定
  - pygame描画呼び出し
```

---

## main.pyへの統合

### 変更箇所1: インポートと初期化

```python
from theawase.rendering.timing_indicator import TimingIndicatorRenderer

# main()関数内
timing_indicator = TimingIndicatorRenderer()
```

### 変更箇所2: メインループでATTACK中の魚を追跡

```python
# メインループ内（描画前）
active_fish = None
for fish in fishes:
    if fish.state == FishState.ATTACK:
        active_fish = fish
        break  # 最初のATTACK魚のみ対象
```

### 変更箇所3: マクロビュー描画に追加

```python
# 左半分: マクロビュー
macro_renderer.render(
    screen,
    macro_rect,
    float_model,
    bait,
    game_state
)

# タイミングインジケータ（新規）
if active_fish and active_fish.state == FishState.ATTACK:
    timing_indicator.render(
        screen,
        macro_rect,
        active_fish.state_timer * 1000,  # ms変換
        active_fish.bite_type
    )
```

---

## エッジケースの処理

| 状況 | 期待される動作 | 実装方針 |
|------|---------------|---------|
| 複数の魚がATTACK | 最初の魚（max state_timer）のみ表示 | `break`で最初の魚のみ |
| ATTACK→COOLDOWN遷移 | ゲージ即座に非表示 | `if active_fish.state == ATTACK`チェック |
| アワセ実行中 | ゲージ消去、結果表示へ | アワセ後は`active_fish=None`で自動非表示 |
| ATTACK中に画面切替 | state変更で自動非表示 | `game_state['state']`が変わればループ外 |
| state_timer > 600ms | 針が右端で停止 | `min(state_timer, 0.6)`でクリップ |

---

## パフォーマンス考慮

**描画コスト:**
- pygame.draw.arc(): 1回（背景弧）
- pygame.draw.arc(): 3-5回（色分けされた弧）
- pygame.draw.line(): 1回（針）
- pygame.draw.circle(): 1回（針の中心点）
- **合計**: ~10-20 pygame描画呼び出し/フレーム

**影響:**
- 既存描画（ウキ、エサ、魚、パーティクル等）の約5%未満
- 60fps維持に問題なし

**最適化:**
- 弧の事前計算（初期化時にカラーマップ生成）
- 針の角度は毎フレーム計算（軽量）

---

## テスト戦略

### Step 1: コンポーネント単体テスト

```bash
# 描画テスト（手動）
python -m theawase.main
# 魚がATTACKするまで待機
# ゲージが表示され、針が左→右へ移動することを確認
```

**期待結果:**
- ✅ 針が滑らかに移動（0ms: 左端、600ms: 右端）
- ✅ 150-450msで緑色ゾーン
- ✅ ATTACK終了でゲージ消失

### Step 2: タイミング精度テスト

```bash
# 各タイミングでアワセして色を確認
# - 100ms: 赤（TOO EARLY）
# - 200ms: 緑（PERFECT）
# - 300ms: 緑（PERFECT）
# - 500ms: 黄（LATE）
# - 600ms: 赤（TOO LATE）
```

### Step 3: エッジケーステスト

- 複数魚が同時ATTACK → 最初の魚のゲージのみ表示
- ATTACK中にTITLE画面へ → ゲージ消失
- 連続ATTACK → ゲージがリセットされて再表示

---

## 期待される効果

### ユーザー体験

| 指標 | 改善前 | 改善後 |
|------|--------|--------|
| 初心者の成功率 | 10-20% | 60-80% |
| タイミング理解度 | ❌ 不明瞭 | ✅ 極めて明確 |
| フラストレーション | 高い | 低い |
| 学習曲線 | 急峻 | 緩やか |

### へらぶな釣りの達人の評価

- ✅ **実釣感の維持**: ウキの動きはそのまま、UIは分離
- ✅ **初心者への配慮**: 視覚的ガイドで学習が容易
- ✅ **上級者への影響**: ゲージを無視して感覚で釣ることも可能
- ✅ **ゲーム性向上**: タイミングの「見える化」でスキル上達が実感できる

---

## 将来の拡張可能性

### Phase 2（オプション）

1. **難易度設定**
   - EASY: ゲージ常時表示
   - NORMAL: ゲージ表示（現設計）
   - HARD: ゲージなし（現状維持）

2. **カスタマイズ**
   - ゲージ位置の選択（下部/上部/左右）
   - ゲージサイズの調整
   - 色スキームの変更

3. **追加フィードバック**
   - 最適ゾーンでの微振動（haptic、将来）
   - オプション音声フィードバック

---

## 設計承認

- [x] ユーザー承認: 2026-02-16
- [x] アーキテクチャ: シンプル、拡張可能
- [x] パフォーマンス: 軽量、60fps維持
- [x] UX: 直感的、初心者に優しい
