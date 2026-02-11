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
    except:
        pass
        
    return None

_JP_FONT_PATH = _find_jp_font_path()

# 魚の状態名（日本語）
_FISH_STATE_NAMES = {
    FishState.IDLE: "待機",
    FishState.APPROACH: "接近",
    FishState.ATTACK: "吸込み",
    FishState.COOLDOWN: "離脱",
}


def create_fish_school(count: int = config.FISH_COUNT) -> list[FishAI]:
    """魚群を生成（エサ深度付近に配置）"""
    base_positions = [
        np.array([0.15, -0.80]),  # 水面下80cm（タナを深く）
        np.array([-0.12, -0.85]),  # 水面下85cm
        np.array([0.05, -0.90]),   # 水面下90cm
        np.array([-0.2, -0.75]),   # 水面下75cm
    ]
    fishes: list[FishAI] = []
    for i in range(count):
        base = base_positions[i % len(base_positions)].copy()
        jitter = np.random.uniform(-0.03, 0.03, size=2)
        pos = base + jitter
        fishes.append(
            FishAI(
                position=pos,
                hunger=float(np.random.uniform(0.45, 0.85)),
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


def check_awase(trackpad: TrackpadInput, fishes: list[FishAI], line: LineModel) -> tuple[int, str] | None:
    """
    アワセ判定 v2.0（完全版）
    
    Priority A: タイミングウィンドウの細分化（BiteType別）
    Priority B: 重複判定防止（後述のクールダウンで実装）
    Priority C: 複数魚の明確な処理（最初にATTACKした魚を優先）
    
    Returns:
        (スコア, メッセージ) or None
    """
    # 1. 鋭い上方向の動きを検出
    if not trackpad.is_awase_gesture(threshold=config.AWASE_THRESHOLD):
        return None
    
    # 2. 水切りチェック（必須）
    if not line.is_water_cut:
        return (-50, "MISS: 水切り未実行")
    
    # 3. Priority C: ATTACKしている魚を列挙し、最初にATTACKした魚を特定
    attacking_fishes = [f for f in fishes if f.state == FishState.ATTACK]
    
    if attacking_fishes:
        # state_timerが最も進んでいる魚（＝最初にATTACKした魚）を判定対象に
        target_fish = max(attacking_fishes, key=lambda f: f.state_timer)
        t_ms = target_fish.state_timer * 1000  # ミリ秒変換
        bite = target_fish.bite_type
        
        # Priority A: BiteType別のタイミングウィンドウ判定
        if bite == BiteType.KESHIKOMI:
            # 消し込み: 最も難しい（狭いウィンドウ: 50-100ms）
            if 50 <= t_ms <= 100:
                return (3000, "EXCELLENT! 難しい消し込みを捉えた")
            elif 30 <= t_ms < 50 or 100 < t_ms <= 120:
                return (1500, "GOOD! 消し込み（ギリギリ）")
            else:
                return (-200, "MISS: 消し込みに遅れた")
        
        elif bite == BiteType.KUIAGE:
            # 食い上げ: チャンスアタリ（広いウィンドウ: 40-160ms）
            if 50 <= t_ms <= 120:
                return (2200, "PERFECT! 食い上げを捉えた")
            elif 40 <= t_ms < 50 or 120 < t_ms <= 160:
                return (1200, "GOOD! 食い上げ（やや早い/遅い）")
            else:
                return (-50, "BAD: タイミング外")
        
        else:  # BiteType.NORMAL
            # 通常アタリ: 標準ウィンドウ（50-140ms）
            if 50 <= t_ms <= 110:
                return (2500, "PERFECT! 理想のアワセ")
            elif 30 <= t_ms < 50 or 110 < t_ms <= 140:
                return (1000, "GOOD! やや早い/遅い")
            else:
                return (-100, "BAD: タイミング外")
    
    # 4. APPROACH中: 早アワセ
    if any(fish.state == FishState.APPROACH for fish in fishes):
        return (-100, "EARLY: まだ吸い込んでいない")
    
    # 5. その他: 空振り
    return (-50, "MISS: 空振り")


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
        rod.hand_position = np.array([0.0, 0.50])
        rod.tip_position = np.array([0.0, 0.50])
        rod.tip_velocity = np.array([0.0, 0.0])
        
        line.reset()

        float_model.position = np.array([0.0, config.FLOAT_INITIAL_Y])
        float_model.velocity = np.array([0.0, config.FLOAT_INITIAL_VELOCITY_Y])
        float_model.angle = np.pi / 2  # 初期状態: 横倒し
        float_model.angular_velocity = 0.0

        # エサも空中に配置（ウキより10cm下、ハリスはたるんだ状態）
        bait.position = np.array([0.0, config.FLOAT_INITIAL_Y - 0.10])
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
    }
    
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
                    if event.key == pygame.K_SPACE:
                        line.water_cut()
                    elif event.key == pygame.K_r:
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
        # 投入中判定（ウキのトップ半分が水中に入るまでは道糸を弛める）
        if float_model.position[1] > float_model.top_length * 0.5:
            tension_old = np.array([0.0, 0.0])  # 投入中は張力ゼロ
        else:
            tension_old = line.calculate_tension(rod.get_tip_position(), float_model.get_position())
        rod.update_position(dt, -tension_old)

        # Pass 1.2: エサの位置更新
        bait.update_position(dt)

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

        suck_force = np.array([0.0, 0.0])
        for fish in fishes:
            suck_force += fish.get_suck_force(bait.position)
        suck_on_float_old = suck_force * config.SUCK_TO_FLOAT_FACTOR
        sawari_on_float_old = disturbance_force_total * config.SAWARI_TRANSMISSION_FACTOR

        # 旧ハリス張力（エサの旧位置で計算済み）
        tippet_reaction_old = np.array([0.0, bait.mass * config.GRAVITY])
        tippet_tension_vertical_old = abs(tippet_reaction_old[1])

        # 旧拘束力
        tip_pos_old = rod.get_tip_position()
        line_diff_old = float_model.position - tip_pos_old
        line_dist_old = np.linalg.norm(line_diff_old)
        max_line_dist = config.LINE_REST_LENGTH + config.LINE_MAX_STRETCH
        constraint_force_old = np.array([0.0, 0.0])
        if line_dist_old > max_line_dist - 0.001 and line_dist_old > 1e-6:
            line_dir_old = line_diff_old / line_dist_old
            gravity_on_float = float_model.mass * config.GRAVITY
            buoyancy_old = float_model.calculate_buoyancy()
            net_down_old = gravity_on_float + tippet_reaction_old[1] - buoyancy_old
            force_along_old = -net_down_old * line_dir_old[1]
            if force_along_old > 0:
                constraint_force_old = line_dir_old * force_along_old

        float_model.update_position(dt, tension_old + suck_on_float_old + sawari_on_float_old - tippet_reaction_old + constraint_force_old, tippet_tension_vertical_old)

        # Pass 2: 新位置で外力を再計算し、速度を平均加速度で更新
        # Pass 2.1: 竿の速度更新
        tip_pos_new = rod.get_tip_position()
        float_pos_new = float_model.get_position()
        # 投入中判定（ウキのトップ半分が水中に入るまでは道糸を弛める）
        if float_model.position[1] > float_model.top_length * 0.5:
            tension_new = np.array([0.0, 0.0])  # 投入中は張力ゼロ
        else:
            tension_new = line.calculate_tension(tip_pos_new, float_pos_new)
        rod.update_velocity(dt, -tension_new)

        # Pass 2.2: エサの速度更新とハリス張力計算
        tippet_reaction_new = bait.update_velocity(dt, float_pos_new)

        # Pass 2.3: ウキの速度更新（新外力を使用）
        # 魚の外力は既に計算済み（魚自体はオイラー法なので再計算不要）
        # 注意: Phase 2で魚もシンプレクティック化する予定

        # 新拘束力
        line_diff_new = float_model.position - tip_pos_new
        line_dist_new = np.linalg.norm(line_diff_new)
        constraint_force_new = np.array([0.0, 0.0])
        if line_dist_new > max_line_dist - 0.001 and line_dist_new > 1e-6:
            line_dir_new = line_diff_new / line_dist_new
            buoyancy_new = float_model.calculate_buoyancy()
            net_down_new = gravity_on_float + tippet_reaction_new[1] - buoyancy_new
            force_along_new = -net_down_new * line_dir_new[1]
            if force_along_new > 0:
                constraint_force_new = line_dir_new * force_along_new

        # ハリス張力（鉛直成分）を計算（エサの重さがウキを立たせる力）
        # tippet_reaction_new は [Fx, Fy] で、Fy > 0 は上向き（エサがウキから受ける力）
        tippet_tension_vertical = abs(tippet_reaction_new[1])

        float_model.update_velocity(dt, tension_new + suck_on_float_old + sawari_on_float_old - tippet_reaction_new + constraint_force_new, tippet_tension_vertical)

        # 着水判定と速度減衰（ウキ）
        # 水面付近（±1cm）で下向き速度がある場合、着水として速度を減衰
        if abs(float_model.position[1]) < 0.01 and float_model.velocity[1] < 0:
            float_model.velocity[1] *= config.WATER_ENTRY_DAMPING

        # 着水判定と速度減衰（エサ）
        if abs(bait.position[1]) < 0.01 and bait.velocity[1] < 0:
            bait.velocity[1] *= config.WATER_ENTRY_DAMPING

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

            # デバッグ出力（数値実験用、最初の10秒間）
            if game_state['time_left'] > 50.0:
                angle_deg = np.degrees(float_model.angle)
                omega_deg = np.degrees(float_model.angular_velocity)
                print(f"t={60-game_state['time_left']:.2f} angle={angle_deg:.1f}° omega={omega_deg:.2f}°/s y={float_model.position[1]:.3f}")

            if game_state['time_left'] <= 0:
                game_state['time_left'] = 0
                game_state['state'] = GameState.RESULT
            
            # Priority B: アワセクールダウン更新
            if game_state['awase_cooldown'] > 0:
                game_state['awase_cooldown'] -= dt
            else:
                # クールダウンが終わっている場合のみ判定
                result = check_awase(trackpad, fishes, line)
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
        fish_text = font_ui.render(f"🐟 × {game_state['fish_caught']}", True, (255, 200, 100))
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

