# ウキ反応改善 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** ウキのアタリ反応を80-120mmに改善し、極めて明確に視認可能にする

**Architecture:** 魚の吸い込み力の18%を直接ウキに伝達（圧力伝達モデル）。シンプレクティック積分を保持しつつ、Pass 1とPass 2の両方で力を追加。

**Tech Stack:** Python 3.10+, NumPy, Pygame

---

## Task 1: config.pyの修正（物理パラメータとデバッグ設定）

**Files:**
- Modify: `src/theawase/config.py:48` (SUCK_TO_FLOAT_FACTOR)
- Modify: `src/theawase/config.py:89` (デバッグ設定追加)

**Step 1: SUCK_TO_FLOAT_FACTORを18%に変更**

修正前（line 48）:
```python
SUCK_TO_FLOAT_FACTOR = 0.015   # 魚の吸い込み力のウキへの伝達率（1.5%、感度を適度に抑える）
```

修正後:
```python
SUCK_TO_FLOAT_FACTOR = 0.18    # 魚の吸い込み力のウキへの伝達率（18%、極めて明確なアタリ、80-120mm目標）
```

**Step 2: デバッグ設定を追加**

`FISH_STATE_NAMES_JP`の直後（line 88-89の後）に追加:

```python
# デバッグ設定
DEBUG_MODE = False              # デバッグ出力のON/OFF（デフォルトOFF）
DEBUG_SAMPLING_INTERVAL = 0.1   # 秒（100ms、毎フレームではなく）
DEBUG_TIME_LIMIT = None         # Noneの場合は時間制限なし（デバッグモード時）
```

**Step 3: 変更を確認**

Run: `grep -A 1 "SUCK_TO_FLOAT_FACTOR\|DEBUG_MODE" src/theawase/config.py`

Expected output:
```
SUCK_TO_FLOAT_FACTOR = 0.18    # ...
DEBUG_MODE = False
DEBUG_SAMPLING_INTERVAL = 0.1
DEBUG_TIME_LIMIT = None
```

**Step 4: コミット**

```bash
git add src/theawase/config.py
git commit -m "feat: SUCK_TO_FLOAT_FACTORを18%に変更、デバッグ設定追加

- ウキへの直接伝達率を1.5%→18%に引き上げ（12倍）
- 目標：アタリを80-120mmに改善（現状13.7mmの6-9倍）
- デバッグ出力制御用の設定を追加

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: main.py Pass 1の修正（魚の吸い込み力の直接伝達）

**Files:**
- Modify: `src/theawase/main.py:355-385` (Pass 1セクション)

**Step 1: Pass 1のエサ更新後に魚の吸い込み力を集計**

`bait.update_position(...)`の直後（line 361の後）に追加:

```python
        # エサ位置更新
        bait.update_position(dt, fish_force_on_bait, float_model.get_position())

        # ★新規追加: 魚の吸い込み力の一部を直接ウキに伝達（圧力伝達モデル）
        total_suck_force = np.array([0.0, 0.0])
        for fish in fishes:
            total_suck_force += fish.get_suck_force(bait.position)

        float_suck_force_old = total_suck_force * config.SUCK_TO_FLOAT_FACTOR
```

**Step 2: ウキの位置更新時に力を追加**

`float_model.update_position(...)`の引数を修正（line 385付近）:

修正前:
```python
        float_model.update_position(dt, tension_old - tippet_reaction_old + constraint_force_old, tippet_tension_vertical_old)
```

修正後:
```python
        float_model.update_position(
            dt,
            tension_old - tippet_reaction_old + constraint_force_old + float_suck_force_old,  # ★追加
            tippet_tension_vertical_old
        )
```

**Step 3: 変更を確認**

Run: `grep -A 3 "float_suck_force_old\|魚の吸い込み力の一部" src/theawase/main.py`

Expected: 新しいコードが表示される

**Step 4: コミット**

```bash
git add src/theawase/main.py
git commit -m "feat(main): Pass 1で魚の吸い込み力をウキに直接伝達

圧力伝達モデルの実装（Phase 1）:
- 魚の吸い込み力の18%を直接ウキに適用
- シンプレクティック積分の第1段階（位置更新）

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: main.py Pass 2の修正（シンプレクティック積分の完成）

**Files:**
- Modify: `src/theawase/main.py:410-422` (Pass 2セクション)

**Step 1: Pass 2のエサ速度更新後に魚の吸い込み力を再計算**

`tippet_reaction_new = bait.update_velocity(...)`の直後（line 415の後）に追加:

```python
        tippet_reaction_new = bait.update_velocity(dt, float_pos_new, fish_accel, fish_force_on_bait_new)

        # ★新規追加: 新位置での吸い込み力を計算（シンプレクティック積分）
        total_suck_force_new = np.array([0.0, 0.0])
        for fish in fishes:
            total_suck_force_new += fish.get_suck_force(bait.position)

        float_suck_force_new = total_suck_force_new * config.SUCK_TO_FLOAT_FACTOR
```

**Step 2: ウキの速度更新時に力を追加**

`float_model.update_velocity(...)`の引数を修正（line 422付近）:

修正前:
```python
        float_model.update_velocity(dt, tension_new - tippet_reaction_new + constraint_force_new, tippet_tension_vertical)
```

修正後:
```python
        float_model.update_velocity(
            dt,
            tension_new - tippet_reaction_new + constraint_force_new + float_suck_force_new,  # ★追加
            tippet_tension_vertical
        )
```

**Step 3: 変更を確認**

Run: `grep -A 3 "float_suck_force_new\|新位置での吸い込み力" src/theawase/main.py`

Expected: 新しいコードが表示される

**Step 4: コミット**

```bash
git add src/theawase/main.py
git commit -m "feat(main): Pass 2で魚の吸い込み力をウキに直接伝達

圧力伝達モデルの完成（Phase 2）:
- 新位置での吸い込み力を計算
- シンプレクティック積分の第2段階（速度更新）
- Pass 1とPass 2で対称的に力を適用（エネルギー保存性向上）

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: デバッグ出力の改善

**Files:**
- Modify: `src/theawase/main.py` (メインループ内のデバッグ出力部分)

**Step 1: 既存のデバッグ出力コードを特定**

Run: `grep -n "print.*omega\|print.*debug" src/theawase/main.py`

Expected: デバッグ出力している行番号が表示される（おそらく複数箇所）

**Step 2: メインループの初期化部分に変数追加**

メインループ開始直後（`time = 0.0`の後）に追加:

```python
    time = 0.0
    frame_count = 0
    debug_last_output_time = 0.0  # ★追加: デバッグ出力の時刻管理
```

**Step 3: デバッグ出力を条件分岐で囲む**

既存のデバッグ出力コード（omega, yなど）を以下で置き換え:

```python
        # デバッグ出力（100msサンプリング、ON/OFF切り替え可能）
        if config.DEBUG_MODE and (time - debug_last_output_time) >= config.DEBUG_SAMPLING_INTERVAL:
            print(f"[DEBUG] t={time:.3f}s: omega={float_model.angular_velocity:.6f}, y={float_model.position[1]:.6f}")
            debug_last_output_time = time
```

**Step 4: 10秒制限の条件分岐**

既存の10秒制限コード（`if time > 10.0: break`など）を以下で置き換え:

```python
        # 時間制限（デバッグモードでは無制限）
        if not config.DEBUG_MODE and config.DEBUG_TIME_LIMIT is not None and time > config.DEBUG_TIME_LIMIT:
            break
```

注: config.DEBUG_TIME_LIMIT がNoneの場合は制限なし、数値の場合はその秒数で制限

**Step 5: 変更を確認**

Run: `python -m theawase.main`

Expected: デバッグ出力が表示されない（DEBUG_MODE=False）

Run: 一時的にconfig.DEBUG_MODE=Trueにして実行

Expected: 100msごとにデバッグ出力、10秒制限なし

**Step 6: コミット**

```bash
git add src/theawase/main.py
git commit -m "feat(main): デバッグ出力の改善（100msサンプリング、ON/OFF切り替え）

- デフォルトでデバッグ出力なし（DEBUG_MODE=False）
- サンプリング間隔を100msに変更（毎フレーム16.67msから）
- デバッグモードでは時間制限なし
- 煩雑なデバッグ出力を解消

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: log_physics.pyへの同期

**Files:**
- Modify: `scripts/log_physics.py` (main.pyと同じ修正を適用)

**Step 1: Pass 1に魚の吸い込み力の直接伝達を追加**

`bait.update_position(...)`の直後に、Task 2と同じコードを追加:

```python
        # エサ位置更新
        bait.update_position(dt, fish_force_on_bait, float_model.position)

        # ★新規追加: 魚の吸い込み力の一部を直接ウキに伝達（圧力伝達モデル）
        total_suck_force = np.array([0.0, 0.0])
        total_suck_force += fish.get_suck_force(bait.position)

        float_suck_force_old = total_suck_force * config.SUCK_TO_FLOAT_FACTOR
```

**Step 2: ウキ位置更新時に力を追加**

```python
        float_model.update_position(
            dt,
            tension_old - tippet_reaction_old + constraint_force_old + float_suck_force_old,  # ★追加
            tippet_tension_vertical_old
        )
```

**Step 3: Pass 2に魚の吸い込み力の再計算を追加**

Task 3と同じコードを追加:

```python
        tippet_reaction_new = bait.update_velocity(dt, float_pos_new, fish_accel, fish_force_on_bait_new)

        # ★新規追加: 新位置での吸い込み力を計算（シンプレクティック積分）
        total_suck_force_new = np.array([0.0, 0.0])
        total_suck_force_new += fish.get_suck_force(bait.position)

        float_suck_force_new = total_suck_force_new * config.SUCK_TO_FLOAT_FACTOR
```

**Step 4: ウキ速度更新時に力を追加**

```python
        float_model.update_velocity(
            dt,
            tension_new - tippet_reaction_new + constraint_force_new + float_suck_force_new,  # ★追加
            tippet_tension_vertical
        )
```

**Step 5: コミット**

```bash
git add scripts/log_physics.py
git commit -m "feat(log_physics): main.pyと同じ圧力伝達モデルを適用

物理検証スクリプトにも同じ修正を適用:
- Pass 1とPass 2で魚の吸い込み力をウキに直接伝達
- シミュレーション結果の一貫性を確保

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: 物理シミュレーションでの検証

**Files:**
- Read: `physics_log.csv` (シミュレーション結果)
- Read: `scripts/analyze_atari.py` (解析ツール)

**Step 1: 60秒シミュレーションを実行**

Run: `python3 scripts/log_physics.py`

Expected output:
```
シミュレーション開始: 60.0秒間
出力先: .../physics_log.csv
  t=X.Xs: ATTACK検出 (累計N回)
...
シミュレーション完了
```

**Step 2: アタリ解析を実行**

Run: `python3 scripts/analyze_atari.py physics_log.csv`

Expected output（目標値）:
```
【へらぶな釣りの達人による【アタリ診断】

【1. ウキの基本状態】
  初期ウキ位置（0-2秒）:
    平均: 100.X mm
    変動: <5.0 mm  ← 初期振動が小さい

【2. アタリ（ATTACK）の詳細解析】
  平均的なアタリの大きさ: 80-120 mm  ← 目標達成
  平均的な沈み込み: XX mm

✓ 理想的なアタリです（明確に視認可能）
  極めて明確なアタリ！
```

**Step 3: 結果を確認**

期待される結果:
- ✅ アタリ平均: 80-120mm（目標達成）
- ✅ 初期振動: <5mm（バランス維持）
- ✅ 消し込み/食い上げ: 明確に視認可能

もし目標未達の場合:
- アタリが小さい（<60mm）: SUCK_TO_FLOAT_FACTORを20-22%に上げる
- アタリが大きすぎる（>150mm）: SUCK_TO_FLOAT_FACTORを15%程度に下げる
- 初期振動が大きい（>10mm）: 別の物理バグを調査

**Step 4: 結果をコミットメッセージに記録**

```bash
# 結果が良好な場合
git commit --allow-empty -m "test: 物理シミュレーション検証完了

60秒シミュレーション結果:
- アタリ平均: XX.X mm（目標80-120mm）
- 初期振動: X.X mm（<5mm維持）
- 消し込み/食い上げ: 明確に視認可能

検証: ✅ PASS

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: 実ゲームでの検証と微調整

**Files:**
- Run: `src/theawase/main.py`

**Step 1: ゲームを起動して視覚確認**

Run: `python -m theawase.main`

Expected behavior:
- 左ウィンドウ（マクロビュー）でウキが明確に動く
- 魚がATTACK状態になると、ウキが大きく沈む/浮く
- 動きが160-240ピクセル（画面の22-33%）程度

**Step 2: 視認性を評価**

確認ポイント:
- [ ] ウキの動きが誰でも見逃さないレベルで明確
- [ ] 魚の大きさに応じて動きが変化する
- [ ] 物理的に不自然でない（暴れすぎない）
- [ ] 初期状態でウキが安定している（振動<5mm）

**Step 3: 必要に応じて微調整**

もし視認性が不十分な場合:

Option A: SUCK_TO_FLOAT_FACTORを調整
```python
# config.py
SUCK_TO_FLOAT_FACTOR = 0.22  # 18% → 22%に増加
```

Option B: マクロビューのスケールを調整
```python
# config.py
MACRO_VIEW_SCALE = 2500.0  # 2000 → 2500に増加（1mm = 2.5px）
```

**Step 4: 最終コミット**

```bash
git add -A
git commit -m "feat: ウキ反応改善完了（アタリ80-120mm達成）

実装内容:
- 魚の吸い込み力の18%をウキに直接伝達（圧力伝達モデル）
- Pass 1とPass 2でシンプレクティック積分を保持
- デバッグ出力改善（100msサンプリング、ON/OFF切り替え）

検証結果:
- 物理シミュレーション: アタリ平均 XX mm
- 実ゲーム: 左ウィンドウで極めて明確に視認可能
- 初期振動: <5mm（バランス維持確認）

物理的整合性を保ちつつ、視認性を大幅に向上。

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## 完了条件

全タスク完了時、以下を確認:

- [x] SUCK_TO_FLOAT_FACTORが18%（またはテスト結果に基づく最適値）
- [x] main.pyとlog_physics.pyで同じ実装
- [x] デバッグ出力が改善されている
- [x] 物理シミュレーションでアタリ80-120mm達成
- [x] 実ゲームで左ウィンドウのウキが極めて明確に動く
- [x] 初期振動<5mm（物理バランス維持）
- [x] すべての変更がコミット済み

---

## トラブルシューティング

### 問題1: アタリが目標値に達しない

**症状**: シミュレーション結果が50-70mm程度
**原因**: SUCK_TO_FLOAT_FACTORが不足
**解決策**: 22-25%に引き上げて再テスト

### 問題2: 初期振動が大きくなった

**症状**: 初期2秒で10mm以上振動
**原因**: float_suck_forceが初期状態で非ゼロの可能性
**解決策**: 魚が初期状態でエサから離れているか確認

### 問題3: ウキが暴れすぎる

**症状**: アタリが150mm超、不自然な動き
**原因**: SUCK_TO_FLOAT_FACTORが高すぎる
**解決策**: 15%程度に下げて再テスト

---

## 実装完了後のアクション

1. 設計書を更新（実測値を記録）
2. CLAUDE.mdに新機能を記載
3. ユーザーに報告（スクリーンショット推奨）
4. 次のフェーズ（Phase 4: ゲームサイクル）への準備
