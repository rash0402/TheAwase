"""TheAwase メインエントリーポイント"""

import os
import numpy as np
import pygame
from theawase import config
from enum import Enum, auto
from theawase.physics.rod import RodModel
from theawase.physics.line import LineModel
from theawase.physics.float_model import FloatModel
from theawase.physics.bait import BaitModel
from theawase.physics.utils import apply_water_entry_damping
from theawase.entities.fish import FishAI, FishState, BiteType
from theawase.input.trackpad import TrackpadInput
from theawase.rendering.macro_view import MacroViewRenderer
from theawase.rendering.debug_view import DebugViewRenderer

class GameState(Enum):
    TITLE = auto()
    PLAYING = auto()
    RESULT = auto()

# 日本語フォント探索
pygame.font.init()

def _find_jp_font_path():
    candidates = [
        "/System/Library/Fonts/Hiragino Sans W3.ttc",  # Modern macOS (English name)
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", # Japanese name
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/AppleGothic.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    
    # フォールバック: システムフォントマッチング
    try:
        path = pygame.font.match_font('hiraginosans')
        if path: return path
        path = pygame.font.match_font('takaoexgothic')
        if path: return path
    except Exception:
        pass
        
    return None

_JP_FONT_PATH = _find_jp_font_path()


def create_fish_school(count: int = config.FISH_COUNT) -> list[FishAI]:
    """
    魚群を生成（達人推奨: 実釣に近い配置と活性）
    
    - 深度: 40-60cm（実釣の底釣りに相当）
    - 匹数: 2匹（60秒で0-1枚が現実的）
    - 活性: hunger=0.3-0.5（待つ楽しみ）
    """
    base_positions = [
        np.array([0.15, -0.40]),  # 水面下40cm（浅く）
        np.array([-0.12, -0.45]),  # 水面下45cm
        np.array([0.05, -0.50]),   # 水面下50cm
        np.array([-0.2, -0.55]),   # 水面下55cm
    ]
    fishes: list[FishAI] = []
    for i in range(count):
        base = base_positions[i % len(base_positions)].copy()
        jitter = np.random.uniform(-0.03, 0.03, size=2)
        pos = base + jitter
        fishes.append(
            FishAI(
                position=pos,
                hunger=float(np.random.uniform(0.3, 0.5)),  # 活性低下
                caution=float(np.random.uniform(0.2, 0.6)),
            )
        )
    return fishes


# 座標変換: ワールド座標（メートル）→ スクリーン座標（ピクセル）
def _get_jp_font(size: int) -> pygame.font.Font:
    """日本語フォントを取得（キャッシュなし、毎回生成）"""
    if _JP_FONT_PATH:
        return pygame.font.Font(_JP_FONT_PATH, size)
    return pygame.font.Font(None, size)



def _calculate_line_constraint_force(
    float_position: np.ndarray,
    tip_position: np.ndarray,
    max_line_dist: float,
    gravity_on_float: float,
    buoyancy: float,
    tippet_reaction_y: float,
) -> np.ndarray:
    """
    道糸の最大伸長を超えた場合の拘束力を計算

    糸がピンと張ったとき、ウキが下方に引かれすぎないよう
    糸方向に沿った拘束力を返す。

    Args:
        float_position: ウキの現在位置
        tip_position: 竿先の現在位置
        max_line_dist: 道糸の最大長さ (m)
        gravity_on_float: ウキにかかる重力 (N)
        buoyancy: ウキの浮力 (N)
        tippet_reaction_y: ハリス反力のY成分 (N)

    Returns:
        拘束力ベクトル [Fx, Fy]
    """
    line_diff = float_position - tip_position
    line_dist = np.linalg.norm(line_diff)

    if line_dist <= max_line_dist - 0.001 or line_dist < 1e-6:
        return np.array([0.0, 0.0])

    line_dir = line_diff / line_dist
    net_down = gravity_on_float + tippet_reaction_y - buoyancy
    force_along = -net_down * line_dir[1]

    if force_along > 0:
        return line_dir * force_along

    return np.array([0.0, 0.0])


def check_awase(trackpad: TrackpadInput, fishes: list[FishAI], line: LineModel, game_state: dict, bait: BaitModel) -> tuple[int, str] | None:
    """
    アワセ判定 v3.0（実釣感覚版）
    
    達人の推奨に基づき、タイミングウィンドウを実釣の人間反応時間に調整:
    - 視覚判断: 100ms
    - 運動反応: 120ms
    - 合計: 220ms前後が理想
    
    Priority A: タイミングウィンドウの細分化（実釣感覚）
    Priority B: 重複判定防止（クールダウン）
    Priority C: 複数魚の明確な処理
    Phase 3: タイミング履歴記録
    
    Returns:
        (スコア, メッセージ) or None
    """
    # 1. 鋭い上方向の動きを検出
    if not trackpad.is_awase_gesture(threshold=config.AWASE_THRESHOLD):
        return None

    # 2. Priority C: ATTACKしている魚を列挙し、最初にATTACKした魚を特定
    attacking_fishes = [f for f in fishes if f.state == FishState.ATTACK]
    
    result = None
    timing_ms = 0.0
    bite_type_str = "NONE"
    
    if attacking_fishes:
        # state_timerが最も進んでいる魚（＝最初にATTACKした魚）を判定対象に
        target_fish = max(attacking_fishes, key=lambda f: f.state_timer)
        t_ms = target_fish.state_timer * 1000  # ミリ秒変換
        bite = target_fish.bite_type
        timing_ms = t_ms
        bite_type_str = bite.name
        
        # Priority A: BiteType別のタイミングウィンドウ判定（実釣感覚版）
        if bite == BiteType.KESHIKOMI:
            # 消し込み: 最も難しい（瞬間勝負、100ms幅）
            if 150 <= t_ms <= 250:
                result = (3000, "EXCELLENT! 難しい消し込みを捉えた")
            elif 100 <= t_ms < 150 or 250 < t_ms <= 300:
                result = (1500, "GOOD! 消し込み（ギリギリ）")
            else:
                result = (-200, "MISS: 消し込みに遅れた")
        
        elif bite == BiteType.KUIAGE:
            # 食い上げ: チャンスアタリ（荷重が抜けるため広い、250ms幅）
            if 150 <= t_ms <= 400:
                result = (2500, "PERFECT! 食い上げを捉えた")
            elif 100 <= t_ms < 150 or 400 < t_ms <= 500:
                result = (1200, "GOOD! 食い上げ（やや早い/遅い）")
            else:
                result = (-50, "BAD: タイミング外")
        
        else:  # BiteType.NORMAL
            # 通常アタリ: 標準ウィンドウ（150ms幅）
            if 150 <= t_ms <= 300:
                result = (2500, "PERFECT! 理想のアワセ")
            elif 100 <= t_ms < 150 or 300 < t_ms <= 350:
                result = (1000, "GOOD! やや早い/遅い")
            else:
                result = (-100, "BAD: タイミング外")
    
    # 4. APPROACH中: 早アワセ
    if not result and any(fish.state == FishState.APPROACH for fish in fishes):
        result = (-100, "EARLY: まだ吸い込んでいない")
        bite_type_str = "EARLY"
    
    # 5. その他: 空振り
    if not result:
        result = (-50, "MISS: 空振り")
        bite_type_str = "MISS"
    
    # Phase 3: タイミング履歴に記録
    if result:
        score, message = result
        
        # 魚の加速度とハリス張力を取得
        fish_accel_y = 0.0
        tippet_tension = 0.0
        if attacking_fishes:
            target_fish = max(attacking_fishes, key=lambda f: f.state_timer)
            fish_accel = target_fish.get_acceleration_from_suction(bait.position)
            fish_accel_y = fish_accel[1]
            # ハリス張力は bait に保存されていない場合があるのでデフォルト値
            tippet_tension = getattr(bait, '_last_tippet_tension', 0.0)
        
        record = {
            'timestamp': 60.0 - game_state['time_left'],  # 経過時間
            'bite_type': bite_type_str,
            'timing_ms': timing_ms,
            'score': score,
            'fish_accel_y': fish_accel_y,
            'tippet_tension': tippet_tension,
        }
        
        game_state['awase_history'].append(record)
        
        # 最大50件に制限
        if len(game_state['awase_history']) > 50:
            game_state['awase_history'].pop(0)
    
    return result


def main():
    """メインループ"""
    pygame.init()
    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption("TheAwase: Digital Herabuna Physics")
    clock = pygame.time.Clock()
    
    # 物理モデル
    rod = RodModel()
    line = LineModel()
    float_model = FloatModel()
    bait = BaitModel()
    
    # エンティティ
    fishes = create_fish_school()
    
    # 初期位置設定
    def reset_physics():
        # モデル再作成ではなく状態リセット

        # ウキの初期位置
        float_model.position = np.array([0.0, config.FLOAT_INITIAL_Y])
        float_model.velocity = np.array([0.0, config.FLOAT_INITIAL_VELOCITY_Y])
        float_model.angle = 0.0  # 初期状態: 直立
        float_model.angular_velocity = 0.0

        # 竿先をウキから道糸自然長分上に配置（張力ゼロ）
        initial_rod_tip_y = config.FLOAT_INITIAL_Y + config.LINE_REST_LENGTH
        rod.tip_position = np.array([0.0, initial_rod_tip_y])
        rod.tip_velocity = np.array([0.0, 0.0])

        # 手元は竿先と同じ位置（バネ力ゼロ）
        rod.hand_position = np.array([0.0, initial_rod_tip_y])

        # エサはウキからハリス長分下に配置（バネ力ゼロの自然長）
        bait.position = np.array([0.0, config.FLOAT_INITIAL_Y - config.TIPPET_LENGTH])
        bait.velocity = np.array([0.0, 0.0])
        bait.mass = bait.initial_mass # エサ復活
        
        # 魚リセット
        fishes[:] = create_fish_school()

    reset_physics()
    
    # 入力
    trackpad = TrackpadInput(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
    
    # ゲーム状態
    game_state = {
        'state': GameState.TITLE,
        'score': 0,
        'time_left': 60.0,
        'last_result': None,
        'result_timer': 0,
        'awase_cooldown': 0.0,  # Priority B: 重複判定防止
        'fish_caught': 0,  # 釣れた魚の数
        'awase_history': [],  # Phase 3: タイミング履歴（最大50試行分）
    }

    # デバッグ出力の時刻管理
    debug_last_output_time = 0.0
    
    # 画面領域
    half_width = config.SCREEN_WIDTH // 2
    macro_rect = pygame.Rect(0, 0, half_width, config.SCREEN_HEIGHT)
    debug_rect = pygame.Rect(half_width, 0, half_width, config.SCREEN_HEIGHT)

    # レンダラー
    macro_renderer = MacroViewRenderer(_get_jp_font)
    debug_renderer = DebugViewRenderer(_get_jp_font)

    font_ui = _get_jp_font(24)
    font_large = _get_jp_font(64)
    font_medium = _get_jp_font(48)

    running = True
    while running:
        dt = config.DT

        # --- イベント処理 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                
                if game_state['state'] == GameState.TITLE:
                    if event.key == pygame.K_SPACE:
                        game_state['state'] = GameState.PLAYING
                        game_state['score'] = 0
                        game_state['fish_caught'] = 0
                        game_state['time_left'] = 60.0
                        reset_physics()
                
                elif game_state['state'] == GameState.PLAYING:
                    if event.key == pygame.K_r:
                        reset_physics() # デバッグ用リセット

                elif game_state['state'] == GameState.RESULT:
                    if event.key == pygame.K_r:
                        game_state['state'] = GameState.TITLE

        # --- 更新 ---
        # 物理演算は常時実行（背景演出として）
        trackpad.update(dt)
        
        # 手元位置更新 (PLAYING以外では自動で中央保持とか？まあ手動でいい)
        hand_pos = trackpad.get_position()
        hand_pos[1] += config.HAND_Y_OFFSET 

        # 物理更新（2パス方式：シンプレクティック積分）
        # Pass 1: 位置を旧加速度で更新
        rod.set_hand_position(hand_pos)

        # Pass 1.1: 竿の位置更新
        # 道糸張力を計算
        tension_old = line.calculate_tension(rod.get_tip_position(), float_model.get_position())
        rod.update_position(dt, -tension_old)

        # Pass 1.2: エサの位置更新（魚の力を適用）
        # 魚の吸い込み力とサワリ力を集計
        fish_force_on_bait = np.array([0.0, 0.0])
        for fish in fishes:
            fish_force_on_bait += fish.get_suck_force(bait.position)
            fish_force_on_bait += fish.get_disturbance_force()

        # Fix 1: float_position引数を追加（バネ力をPhase 1でも適用）
        bait.update_position(dt, fish_force_on_bait, float_model.get_position())

        # ★新規追加: 魚の吸い込み力の一部を直接ウキに伝達（圧力伝達モデル）
        total_suck_force = np.array([0.0, 0.0])
        for fish in fishes:
            total_suck_force += fish.get_suck_force(bait.position)

        float_suck_force_old = total_suck_force * config.SUCK_TO_FLOAT_FACTOR

        # Pass 1.3: ウキの位置更新（旧外力を使用）
        # 魚の更新（位置のみ更新、外力計算は後）
        bait_mass_ratio = bait.get_mass_ratio()
        disturbance_force_total = np.array([0.0, 0.0])
        for fish in fishes:
            particle_density = 0.0
            for p in bait.particles:
                if np.linalg.norm(p - fish.position) < config.PARTICLE_DENSITY_RANGE:
                    particle_density += config.PARTICLE_DENSITY_INCREMENT
            fish.update(dt, bait.position, particle_density, bait_mass_ratio)
            disturbance_force_total += fish.get_disturbance_force()

        # 旧ハリス張力（エサの旧位置での簡易計算: 垂直方向のみ）
        tippet_reaction_old = np.array([0.0, bait.mass * config.GRAVITY])
        tippet_tension_vertical_old = abs(tippet_reaction_old[1])

        # 道糸・拘束の共通パラメータ
        tip_pos_old = rod.get_tip_position()
        max_line_dist = config.LINE_REST_LENGTH + config.LINE_MAX_STRETCH
        gravity_on_float = float_model.mass * config.GRAVITY

        # 旧拘束力
        constraint_force_old = _calculate_line_constraint_force(
            float_model.position, tip_pos_old, max_line_dist,
            gravity_on_float, float_model.calculate_buoyancy(), tippet_reaction_old[1],
        )

        # ウキ位置更新（ハリス張力 + 圧力伝達で魚の力が伝達）
        float_model.update_position(
            dt,
            tension_old - tippet_reaction_old + constraint_force_old + float_suck_force_old,  # ★追加
            tippet_tension_vertical_old
        )

        # Pass 2: 新位置で外力を再計算し、速度を平均加速度で更新
        # Pass 2.1: 竿の速度更新
        tip_pos_new = rod.get_tip_position()
        float_pos_new = float_model.get_position()
        # 道糸張力を計算
        tension_new = line.calculate_tension(tip_pos_new, float_pos_new)
        rod.update_velocity(dt, -tension_new)

        # Pass 2.2: エサの速度更新とハリス張力計算
        # Phase 3: 魚の加速度を取得してハリス張力に反映
        fish_accel = np.array([0.0, 0.0])
        for fish in fishes:
            if fish.state == FishState.ATTACK:
                fish_accel = fish.get_acceleration_from_suction(bait.position)
                break  # 最初のATTACK魚のみ考慮

        # 魚の力を再計算（Pass 2用）
        fish_force_on_bait_new = np.array([0.0, 0.0])
        for fish in fishes:
            fish_force_on_bait_new += fish.get_suck_force(bait.position)
            fish_force_on_bait_new += fish.get_disturbance_force()

        tippet_reaction_new = bait.update_velocity(dt, float_pos_new, fish_accel, fish_force_on_bait_new)

        # ★新規追加: 新位置での吸い込み力を計算（シンプレクティック積分）
        total_suck_force_new = np.array([0.0, 0.0])
        for fish in fishes:
            total_suck_force_new += fish.get_suck_force(bait.position)

        float_suck_force_new = total_suck_force_new * config.SUCK_TO_FLOAT_FACTOR

        # Pass 2.3: ウキの速度更新（新外力を使用）
        # 新拘束力
        constraint_force_new = _calculate_line_constraint_force(
            float_model.position, tip_pos_new, max_line_dist,
            gravity_on_float, float_model.calculate_buoyancy(), tippet_reaction_new[1],
        )

        # ハリス張力（鉛直成分）: エサの重さがウキを立たせる力
        tippet_tension_vertical = abs(tippet_reaction_new[1])

        # ウキ速度更新（ハリス張力 + 圧力伝達で魚の力が伝達）
        float_model.update_velocity(
            dt,
            tension_new - tippet_reaction_new + constraint_force_new + float_suck_force_new,  # ★追加
            tippet_tension_vertical
        )

        # 着水時の速度減衰（段階的減衰）
        float_model.velocity = apply_water_entry_damping(
            float_model.position,
            float_model.velocity,
            config.WATER_ENTRY_DAMPING,
            config.WATER_ENTRY_ZONE
        )

        bait.velocity = apply_water_entry_damping(
            bait.position,
            bait.velocity,
            config.WATER_ENTRY_DAMPING,
            config.WATER_ENTRY_ZONE
        )

        # 位置拘束（後処理）投入中はスキップ
        if float_model.position[1] <= float_model.top_length * 0.5:
            line_diff = float_model.position - tip_pos_new
            line_dist = np.linalg.norm(line_diff)
            if line_dist > max_line_dist and line_dist > 1e-6:
                line_dir = line_diff / line_dist
                float_model.position = tip_pos_new + line_dir * max_line_dist
                v_along = np.dot(float_model.velocity, line_dir)
                if v_along > 0:
                    float_model.velocity -= v_along * line_dir

        # ゲームロジック
        if game_state['state'] == GameState.PLAYING:
            game_state['time_left'] -= dt

            # デバッグ出力（100msサンプリング、ON/OFF切り替え可能）
            if config.DEBUG_MODE:
                current_time = 60 - game_state['time_left']
                if (current_time - debug_last_output_time) >= config.DEBUG_SAMPLING_INTERVAL:
                    angle_deg = np.degrees(float_model.angle)
                    omega_deg = np.degrees(float_model.angular_velocity)
                    print(f"[DEBUG] t={current_time:.3f}s: angle={angle_deg:.1f}° omega={omega_deg:.2f}°/s y={float_model.position[1]:.6f}")
                    debug_last_output_time = current_time

            if game_state['time_left'] <= 0:
                game_state['time_left'] = 0
                game_state['state'] = GameState.RESULT
            
            # Priority B: アワセクールダウン更新
            if game_state['awase_cooldown'] > 0:
                game_state['awase_cooldown'] -= dt
            else:
                # クールダウンが終わっている場合のみ判定
                result = check_awase(trackpad, fishes, line, game_state, bait)
                if result:
                    score, msg = result
                    game_state['last_result'] = msg
                    game_state['score'] += score
                    game_state['result_timer'] = 2.0
                    game_state['awase_cooldown'] = 0.5  # 0.5秒クールダウン設定
                    if score > 0:  # 成功時
                        game_state['fish_caught'] += 1  # 魚カウント増加
        
        if game_state['result_timer'] > 0:
            game_state['result_timer'] -= dt
            if game_state['result_timer'] <= 0:
                game_state['last_result'] = None

        # --- 描画 ---
        macro_renderer.render(screen, macro_rect, float_model, bait, game_state)
        debug_renderer.render(screen, debug_rect, rod, line, float_model, bait, fishes, hand_pos, game_state)
        
        pygame.draw.line(screen, (100, 100, 100), (half_width, 0), (half_width, config.SCREEN_HEIGHT), 2)
        
        # UI Overlay
        # 共通UI (Score, Time, Fish Count)
        score_text = font_ui.render(f"SCORE: {game_state['score']}", True, (255, 255, 255))
        time_text = font_ui.render(f"TIME: {game_state['time_left']:.1f}", True, (255, 255, 255) if game_state['time_left'] > 10 else (255, 50, 50))
        fish_text = font_ui.render(f"FISH: {game_state['fish_caught']}", True, (255, 255, 255))
        screen.blit(score_text, (20, 20))
        screen.blit(fish_text, (20, 50))  # スコアの下に表示
        screen.blit(time_text, (half_width - 140, 20))

        # ステート別オーバーレイ
        cx, cy = config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2
        
        if game_state['state'] == GameState.TITLE:
            overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            
            title = font_large.render("TheAwase", True, (255, 200, 50))
            sub = font_ui.render("Digital Herabuna Physics", True, (200, 200, 200))
            start = font_medium.render("SPACE キーで開始", True, (255, 255, 255))
            
            screen.blit(title, (cx - title.get_width()//2, cy - 100))
            screen.blit(sub, (cx - sub.get_width()//2, cy - 30))
            screen.blit(start, (cx - start.get_width()//2, cy + 100))
            
        elif game_state['state'] == GameState.RESULT:
            overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            
            res_title = font_large.render("TIME UP", True, (255, 100, 100))
            score_final = font_large.render(f"Final Score: {game_state['score']}", True, (255, 255, 255))
            retry = font_ui.render("[R] タイトルへ戻る", True, (200, 200, 200))
            
            screen.blit(res_title, (cx - res_title.get_width()//2, cy - 100))
            screen.blit(score_final, (cx - score_final.get_width()//2, cy))
            screen.blit(retry, (cx - retry.get_width()//2, cy + 120))
        
        pygame.display.flip()
        clock.tick(config.FPS)
    
    pygame.quit()


if __name__ == "__main__":
    main()

