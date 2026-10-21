# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## プロジェクト概要

**TheAwase** は「アワセの瞬間」のみに特化した、微分方程式ベースの物理駆動型ヘラブナ釣りシミュレータ。Python/Pygame デスクトップアプリケーション（macOS Apple Silicon向け）。コアメカニクスは乱数ではなく物理法則で記述（パーティクルの拡散のみ確率的）。

設計資料: `docs/GDD.md`（ゲームデザイン）、`docs/project_spec_maseter.md`（物理仕様）。

## ビルド・実行

```bash
# 仮想環境（~/local/venv を使用）
source ~/local/venv/bin/activate.fish   # fish shell
# or: source ~/local/venv/bin/activate  # bash/zsh

# 初回: editableモードでインストール
pip install -e ".[dev]"

# シミュレータ実行
theawase                    # エントリーポイント経由
python -m theawase.main     # 直接実行

# テスト実行
pytest

# ヘルパースクリプト経由（fish shell専用）
./scripts/run.sh
```

依存: `pygame>=2.5.0`, `numpy>=1.24.0`。開発用: `pytest>=7.0.0`。Python `>=3.10`。

## アーキテクチャ

### 物理カップリングチェーン

`main.py` のメインループは、物理的因果関係に従った順序でモデルを更新する:

```
TrackpadInput → RodModel → LineModel → FloatModel ← FishAI ← BaitModel
  (手元位置)     (竿先位置)  (張力)      (ウキ位置)   (吸込力)   (パーティクル)
```

1. **TrackpadInput** (`input/trackpad.py`): 絶対座標マッピング。マウス/トラックパッド位置をワールド空間の手元位置に直結（30cm×30cm）。
2. **RodModel** (`physics/rod.py`): バネ・マス・ダンパ系（2質点）。手元が竿先を `K_rod`, `C_rod` で駆動。積分は `physics/integrator.py` の Verlet（`verlet_integrate` / `verlet_integrate_symplectic`）を rod・float・bait で共通使用。
3. **LineModel** (`physics/line.py`): 不感帯付きバネ。スラック長以下では張力ゼロ、張力上限 5 N。張力は常時 100% 伝達（水切り機能は削除済み）。
4. **FloatModel** (`physics/float_model.py`): 円柱近似の排水体積から浮力計算（`ρgV`）、二次抵抗。y=0が水面、y<0が水中。
5. **BaitModel** (`physics/bait.py`): 可変質量系。ブラウン運動する匂いパーティクル（最大100個）を放出。質量は時間経過と速度で減衰。
6. **FishAI** (`entities/fish.py`): 4状態FSM: `IDLE → APPROACH → ATTACK → COOLDOWN`。ATTACK中にガウス分布の吸い込み力場を生成。遷移はパーティクル密度と空腹度/警戒心に依存。

### 描画: デュアルビューシステム

- **左半分（マクロビュー）**: ウキのフォトリアル拡大表示。プレイヤー向け。
- **右半分（デバッグビュー）**: 物理状態の全体可視化 — 竿、糸、ウキ、エサ、魚、パーティクル、ステート情報。

座標系: ワールド座標（メートル）→ スクリーン座標は各ビューの `_world_to_screen()` で変換（マクロビュー 2000 px/m、デバッグビュー 500 px/m、Y軸反転。`config.MACRO_VIEW_SCALE` / `DEBUG_VIEW_SCALE`）。

### アワセ判定

`main.py` の `check_awase()`: 上方向速度の閾値超過（`config.AWASE_THRESHOLD`）→ 魚の状態判定（ATTACK=HIT、APPROACH=EARLY、それ以外=MISS）。

## GUI/Visualization Debugging

- When fixing GUI/visualization issues, NEVER claim the fix is working until the user has confirmed with a screenshot. Do not say '完璧です' or 'fixed!' prematurely. Always say 'Please verify this visually and send a screenshot if it looks wrong.'
- When asked to fix a visual or physical bug, always investigate BOTH the rendering layer AND the simulation/physics layer. Removing something from the GUI does not remove it from the simulation. Verify both sides before declaring done.
- When the user asks to fix a specific visual element (e.g., 'remove dark gray walls'), ask for clarification about what should REMAIN before making changes. Distinguish between: borders/walls, background masks, obstacles, and overlays.

## General Rules

- Always use the correct directory name. Check existing directory names with `ls` before referencing paths. Never assume directory names from memory — verify first.

## コーディング規約

- **設定の集中管理**: 物理定数・画面設定はすべて `config.py` に定義。`config.CONSTANT_NAME` で参照。
- **座標系**: y=0 が水面。正方向が上（空中）、負方向が下（水中）。
- **安全ガード**: 全物理モデルにNaNチェック、加速度上限、マグニチュード制限を実装（シミュレーション発散防止）。
- **単位系**: SI単位系（メートル、キログラム、秒、ニュートン）。
- **言語**: コード（変数名・関数名）は英語、コメント・ドキュメントは日本語。ユーザー向け文字列は日本語。

## タスク管理

- 計画は `tasks/todo.md` に記載。技術的教訓は `tasks/lessons.md` に蓄積。
- ロードマップは `tasks/todo.md` を正とする（ゲームサイクルは実装済み。現行は数学的ダイナミクス Phase 1〜4、プロシージャル効果音は Phase 5 以降）。

## ワークフロールール

- 自明でないタスク（3ステップ以上、アーキテクチャ決定）ではプランモードに入ること。
- 問題発生時は停止して直ちに再計画。無理に進めない。
- ユーザーからの修正時は `tasks/lessons.md` をパターンで更新すること。
- 動作を証明せずにタスクを完了にしない（テスト実行、ログ確認）。
- 自明でない変更は「もっとエレガントな方法はないか？」と問う。ただし単純な修正にはオーバーエンジニアリングしない。
- バグ報告は自律的に調査・修正。手取り足取りの指示を求めない。
