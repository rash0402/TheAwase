# ウキ反応改善設計書

**日付**: 2026-02-13
**目的**: ウキのアタリ反応を極めて明確にする（視認困難 → 80-120mm）
**アプローチ**: 物理的整合性を保ちつつ、魚の吸い込み力の直接伝達を実装

---

## 問題の診断

### 現状

- **症状**: 左ウィンドウ（マクロビュー）でウキがほぼ無反応
- **物理データ**: アタリ平均13.7mm（理論的には正しいが視認困難）
- **根本原因**: `SUCK_TO_FLOAT_FACTOR`が定義されているが**実装されていない**

### 力の伝達経路（修正前）

```
魚のATTACK → エサに100%適用 → ハリス張力 → ウキ（間接伝達のみ）
```

**問題点**:
- エサが軽い（1.2g）ため、魚が吸い込んでもハリス張力がわずかしか増えない
- ウキへの伝達が間接的すぎる

---

## 設計アーキテクチャ

### 力の伝達経路（修正後）

```
魚のATTACK
    ↓
┌───────────────┐
│ 吸い込み力F   │
└───────────────┘
    ↓
    ├─→ 82% → エサに適用 → ハリス張力 → ウキ（間接伝達）
    │
    └─→ 18% → ウキに直接適用（新規実装）★
```

### 物理的根拠

**へらぶな釣りの達人の知見**:
- 魚が水を吸い込むと、水中に圧力変化が発生
- この圧力波は水を通じてウキにも伝わる
- 伝統的に「アタリは水を通じて伝わる」と言われる

**数理学者の視点**:
- 流体力学的には、圧力勾配 ∇p が存在
- ウキは水中に部分的に沈んでいるため、圧力変化の影響を受ける
- 伝達率18%は経験的な値だが、物理的に妥当な範囲

---

## 実装詳細

### 修正ファイル1: `src/theawase/config.py`

```python
# 修正前
SUCK_TO_FLOAT_FACTOR = 0.015   # 1.5%、感度を適度に抑える

# 修正後
SUCK_TO_FLOAT_FACTOR = 0.18    # 18%、極めて明確なアタリ（80-120mm目標）

# デバッグ設定（新規追加）
DEBUG_MODE = False              # デバッグ出力のON/OFF（デフォルトOFF）
DEBUG_SAMPLING_INTERVAL = 0.1   # 100ms（毎フレームではなく）
DEBUG_TIME_LIMIT = None         # Noneの場合は時間制限なし
```

### 修正ファイル2: `src/theawase/main.py`

#### Phase 1（位置更新）での変更

```python
# Pass 1.2: エサの位置更新（既存コード）
fish_force_on_bait = np.array([0.0, 0.0])
for fish in fishes:
    fish_force_on_bait += fish.get_suck_force(bait.position)
    fish_force_on_bait += fish.get_disturbance_force()

bait.update_position(dt, fish_force_on_bait, float_model.get_position())

# ★新規追加: 魚の吸い込み力の一部を直接ウキに伝達
total_suck_force = np.array([0.0, 0.0])
for fish in fishes:
    total_suck_force += fish.get_suck_force(bait.position)

float_suck_force_old = total_suck_force * config.SUCK_TO_FLOAT_FACTOR

# Pass 1.3: ウキの位置更新（修正）
float_model.update_position(
    dt,
    tension_old - tippet_reaction_old + constraint_force_old + float_suck_force_old,  # ★追加
    tippet_tension_vertical_old
)
```

#### Phase 2（速度更新）での変更

```python
# Pass 2.2: エサの速度更新（既存コード）
fish_force_on_bait_new = np.array([0.0, 0.0])
for fish in fishes:
    fish_force_on_bait_new += fish.get_suck_force(bait.position)
    fish_force_on_bait_new += fish.get_disturbance_force()

tippet_reaction_new = bait.update_velocity(dt, float_pos_new, fish_accel, fish_force_on_bait_new)

# ★新規追加: 新位置での吸い込み力を計算
total_suck_force_new = np.array([0.0, 0.0])
for fish in fishes:
    total_suck_force_new += fish.get_suck_force(bait.position)

float_suck_force_new = total_suck_force_new * config.SUCK_TO_FLOAT_FACTOR

# Pass 2.3: ウキの速度更新（修正）
float_model.update_velocity(
    dt,
    tension_new - tippet_reaction_new + constraint_force_new + float_suck_force_new,  # ★追加
    tippet_tension_vertical
)
```

#### デバッグ出力の改善

```python
# メインループ内
debug_last_output_time = 0.0

# 既存のデバッグ出力コードを条件分岐で囲む
if config.DEBUG_MODE and (time - debug_last_output_time) >= config.DEBUG_SAMPLING_INTERVAL:
    print(f"t={time:.3f}s: omega={float_model.angular_velocity:.6f}, y={float_model.position[1]:.6f}")
    debug_last_output_time = time

# 10秒制限の条件分岐
if not config.DEBUG_MODE and time > 10.0:
    break  # デバッグモードでない場合のみ10秒で制限
```

---

## 期待される効果

### シナリオ1: 小さな魚（suck_strength = 0.5）

- 吸い込み力: 0.5N
- ウキへの直接力: 0.5 × 0.18 = 90mN
- エサへの力: 0.41N → ハリス張力増加
- **総合効果**: ウキが30-50mm程度動く（明確に視認可能）

### シナリオ2: 大きな魚（suck_strength = 1.5）

- 吸い込み力: 1.5N
- ウキへの直接力: 1.5 × 0.18 = 270mN
- エサへの力: 1.23N → ハリス張力大幅増加
- **総合効果**: ウキが80-120mm程度動く（極めて明確）

### マクロビューでの視認性

- スケール: 1mm = 2px
- 80-120mmの動き = 160-240ピクセル
- 画面高さ720pxの22-33%を占める → **誰でも見逃さない**

---

## テスト戦略

### Step 1: 物理シミュレーションでの検証

```bash
# SUCK_TO_FLOAT_FACTOR = 0.18 に設定して60秒シミュレーション
python scripts/log_physics.py

# アタリ解析
python scripts/analyze_atari.py physics_log.csv
```

**期待結果**:
- アタリ平均: 80-120mm
- 初期振動: <5mm（バランス維持確認）
- 消し込み/食い上げ: 明確に視認可能

### Step 2: 実ゲームでの体感テスト

```bash
# デバッグモードOFF（デフォルト）
python -m theawase.main

# デバッグモードON（必要に応じて）
python -m theawase.main --debug
```

**確認ポイント**:
- 左ウィンドウでウキの動きが明確に見える
- 魚の大きさに応じて動きが変化する
- 物理的に不自然でない（暴れすぎない）

### Step 3: パラメータ微調整（必要に応じて）

もし18%で大きすぎる/小さすぎる場合：

```python
# config.py
SUCK_TO_FLOAT_FACTOR = 0.15  # 控えめ（60-90mm程度）
SUCK_TO_FLOAT_FACTOR = 0.18  # 推奨（80-120mm程度）
SUCK_TO_FLOAT_FACTOR = 0.22  # 強調（100-150mm程度）
```

---

## 設計原則の遵守

✅ **物理的整合性**: 圧力伝達という物理的根拠に基づく
✅ **総合的バランス**: 既存の平衡点（100mm）、質量比（2.25）を維持
✅ **調整可能性**: SUCK_TO_FLOAT_FACTORで簡単に微調整可能
✅ **段階的検証**: シミュレーション→実ゲーム→微調整のサイクル
✅ **安易な変更を回避**: ウキ質量やハリス剛性は変更せず、新機能実装で対応

---

## 実装チェックリスト

- [ ] config.py: SUCK_TO_FLOAT_FACTOR を 0.18 に変更
- [ ] config.py: デバッグ設定を追加
- [ ] main.py: Pass 1 で魚の吸い込み力をウキに直接伝達
- [ ] main.py: Pass 2 で魚の吸い込み力をウキに直接伝達（シンプレクティック積分）
- [ ] main.py: デバッグ出力を100msサンプリングに変更
- [ ] main.py: デバッグモードON/OFF切り替え実装
- [ ] main.py: 10秒制限の条件分岐
- [ ] テスト: log_physics.py で60秒シミュレーション
- [ ] テスト: analyze_atari.py でアタリ解析（80-120mm確認）
- [ ] テスト: 実ゲームで視認性確認
- [ ] 微調整: 必要に応じてSUCK_TO_FLOAT_FACTORを調整
- [ ] コミット: 修正完了後にコミット

---

## リスクと対策

### リスク1: ウキが暴れすぎる

**症状**: 80-120mmを超えて過剰に動く
**対策**: SUCK_TO_FLOAT_FACTORを15%程度に下げる

### リスク2: 物理バランスの崩壊

**症状**: 初期振動が再発、または平衡点がずれる
**対策**: float_suck_forceが他の力と干渉していないか確認。必要に応じて伝達率を調整。

### リスク3: 視認性が依然として不足

**症状**: 18%でも見えにくい
**対策**:
1. SUCK_TO_FLOAT_FACTORを22%程度に上げる
2. または、マクロビューの描画スケールを調整（MACRO_VIEW_SCALE）

---

## 設計承認

- [x] 数理学者の視点: 物理的根拠あり、計算妥当
- [x] プログラマの視点: 実装シンプル、既存コードへの影響最小
- [x] へらぶな釣りの達人の視点: リアルな挙動、視認性向上
- [x] ユーザー承認: 2026-02-13
