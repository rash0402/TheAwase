# Game Development Todo List

## 実装状況

### 1. ゲームサイクル: 制限時間やスコア集計、リトライ機能 (Game Cycle)
- [✓ 完了] タイマー機能: 60秒カウントダウン実装済み（main.py）
- [✓ 完了] スコア表示UI: 画面左上に表示実装済み
- [✓ 完了] スコア計算ロジック: check_awase()で実装済み
- [✓ 完了] ゲームオーバー判定: TIME UP時にRESULT画面遷移
- [✓ 完了] リトライ機能: Rキーでタイトル画面へ戻る

## 新数学的ダイナミクス理論アルゴリズム実装 (2026-02)

**目標:** 実釣の物理パターン（なじみ→サワリ→モゾ→ツン）を正確に再現

### Phase 1: 数値積分の改善【Week 1】
- [ ] Day 1-2: physics/integrator.py にシンプレクティックVerlet実装
    - [ ] `verlet_integrate_symplectic()` 関数追加
    - [ ] 2回の加速度計算を実装
    - [ ] 単体テスト作成（エネルギー保存）
- [ ] Day 3: physics/rod.py の2段階更新
    - [ ] `update()` メソッドを2段階構造に変更
    - [ ] 位置更新→外力再計算→速度更新
- [ ] Day 4: physics/float_model.py の2段階更新
- [ ] Day 5: physics/bait.py の2段階更新、main.py の統合
- [ ] Day 6-7: テスト・調整（エネルギー保存、発散防止）

### Phase 2: FishAI高度化【Week 2】
- [ ] Day 8-9: Ornstein-Uhlenbeck過程（サワリの時間相関150ms）
    - [ ] entities/fish.py に OU過程実装
    - [ ] config.py に定数追加（SAWARI_OU_THETA, SIGMA）
- [ ] Day 10: 双極子吸込力場（1.5cm制限）
    - [ ] `get_suck_force()` を双極子型に変更
    - [ ] 範囲制限（5cm超で0）
- [ ] Day 11: ツン3段階モデル（準備→爆発→減衰）
    - [ ] `_calculate_suck_strength()` 実装
    - [ ] 50ms立ち上がり
- [ ] Day 12-14: テスト・調整

### Phase 3: ハリス拘束とウキ姿勢【Week 3】
- [ ] Day 15-17: physics/tippet_constraint.py 新規作成
    - [ ] ラグランジュ乗数法による拘束ソルバー実装
    - [ ] 魚のATTACK時のハリス張力伝達
    - [ ] 食い上げ/消し込みの力学実装
- [ ] Day 18-19: トルクベース姿勢制御
    - [ ] physics/float_model.py にトルク計算追加
    - [ ] 角運動方程式実装
    - [ ] メタセントリック復元モーメント
- [ ] Day 20-21: テスト・調整

### Phase 4: 水切り連続遷移とアタリ定量化【Week 4】
- [ ] Day 22: physics/line.py の水切り連続遷移
    - [ ] 時定数0.5sの指数関数遷移
    - [ ] config.py に WATER_CUT_TAU_S 追加
- [ ] Day 23-24: main.py に AtariDetector 実装
    - [ ] 目盛り数カウント（1目盛り=3mm）
    - [ ] スコアリングの定量化
- [ ] Day 25-28: 総合テスト・パラメータチューニング

## 将来のタスク（Phase 5以降）

### 2. パラメータ調整UI: ウキやエサの種類をゲーム内で変更できるメニュー
- [ ] ゲーム内メニューのUI/UX設計
- [ ] ウキとエサの種類選択UI実装
- [ ] 物理パラメータへの連携

### 3. プロシージャル効果音: アワセ音の合成実装
- [ ] Pygameオーディオを用いたアワセ音合成
- [ ] 周波数、エンベロープ、ノイズ成分の設計
- [ ] アワセアクションとの連携
