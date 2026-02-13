"""TheAwase 設定・定数"""

# 画面設定
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# 物理パラメータ
DT = 1.0 / FPS  # 時間刻み (秒)

# 竿パラメータ (バネ・ダンパ)
ROD_MASS = 0.1       # kg
ROD_STIFFNESS = 200.0  # N/m (硬調子の竿に近い剛性)
ROD_DAMPING = 3.0     # Ns/m (Verlet統合後の最適値)

# 道糸パラメータ
LINE_STIFFNESS = 100.0   # N/m
LINE_REST_LENGTH = 0.6   # m (張力ゼロの基準長: 竿先〜ウキ間、実釣に即した値、1.5m→0.6mに変更)
LINE_MAX_STRETCH = 0.3   # m (道糸の最大伸長許容値)

# ウキパラメータ
WATER_DENSITY = 1000.0  # kg/m³
GRAVITY = 9.81          # m/s²
MENISCUS_DAMPING = 1.0  # N·s/m (水面付近の線形減衰: メニスカス効果)

# ウキの姿勢制御（トルクベース）
FLOAT_METACENTRIC_HEIGHT = 0.008  # m (メタセントリック高さ: 浮力中心から重心までの距離、8mm)
FLOAT_ROTATIONAL_DRAG = 0.0001    # N·m·s² 回転減衰係数（形状抵抗、慣性モーメント比例）
FLOAT_ROTATIONAL_VISCOSITY = 0.0005  # N·m·s 回転粘性減衰係数（5倍に増加、振動を早期に停止）

# ハリスパラメータ
TIPPET_LENGTH = 0.45      # m (45cm: ウキ→エサ間距離、魚の深度に合わせて調整)
TIPPET_STIFFNESS = 20.0   # N/m (Fix 2: 50.0→20.0、ナイロン0.4号の実測値に合わせて実釣感覚を改善)

# カラー定義
COLOR_WATER = (64, 128, 192)
COLOR_SKY = (200, 220, 240)
COLOR_DEBUG_BG = (20, 30, 40)

# レンダリング定数
MACRO_VIEW_SCALE = 2000.0      # px/m (1mm = 2px、超拡大)
DEBUG_VIEW_SCALE = 500.0       # px/m (全体俯瞰)
MACRO_WATER_OFFSET_PX = 80     # マクロビュー水面線オフセット（画面中心+80px、水面を中央やや下に配置）
TOP_SEGMENT_HEIGHT_PX = 10     # px (トップの節模様セグメント高さ、細かい節でリアルさ向上）

# ゲームロジック定数
FISH_COUNT = 4                 # 魚の数
SUCK_TO_FLOAT_FACTOR = 0.015   # 魚の吸い込み力のウキへの伝達率（1.5%、感度を適度に抑える）
SAWARI_DISTANCE_THRESHOLD = 0.15  # m (魚がこの距離以内でサワリを発生)
SAWARI_TRANSMISSION_FACTOR = 0.05  # サワリ力のウキへの伝達率（5%、微細な振動として伝達）
AWASE_THRESHOLD = 0.3          # m/s (アワセ判定の速度閾値、急速な上方向動作を検出)
HAND_Y_OFFSET = 0.50           # m (手元位置のY軸オフセット、竿の持ち位置調整)
PARTICLE_DENSITY_RANGE = 0.1   # m (パーティクル密度判定の距離閾値)
PARTICLE_DENSITY_INCREMENT = 0.1  # パーティクル密度の増分値

# Phase 2: FishAI高度化パラメータ
# Ornstein-Uhlenbeck過程（サワリの時間相関）
SAWARI_OU_THETA = 1.0      # 1/τ, τ=1000ms（達人推奨: 実釣の「じわじわ感」）
SAWARI_OU_SIGMA = 0.01     # 強度（標準偏差、ウキへの影響の大きさ）

# 魚の吸い込み力場（双極子型）
SUCK_FORCE_RANGE = 0.015    # m (1.5cm: 最大力の位置、ヘラブナの口径の2-3倍)
SUCK_FORCE_CUTOFF = 0.05    # m (5cm: この距離を超えると完全にゼロ)

# Phase 3: ハリス拘束動的化パラメータ
FISH_MASS = 0.2             # kg (200g: ヘラブナの標準的な質量)
MAX_FISH_ACCEL = 50.0       # m/s² (魚の加速度上限、安全ガード)

# 初期位置設定（仕掛け投入: 空中から落下）
FLOAT_INITIAL_Y = 0.30           # m (ウキ初期位置: 水面から30cm上、空中から落下)
FLOAT_INITIAL_VELOCITY_Y = 0.0   # m/s (初期速度: ゼロ、頂点から落下開始)
WATER_ENTRY_DAMPING = 0.3        # 着水時の速度減衰係数（水面衝突で速度が70%減衰）
WATER_ENTRY_ZONE = 0.10          # m (±10cm range for gradual damping)

# 安全ガード（物理発散防止）
MAX_ACCELERATION = 1000.0        # m/s² (加速度上限、全物理モデル共通)
MAX_ANGULAR_VELOCITY = 10.0      # rad/s (角速度上限)
MAX_ANGULAR_ACCELERATION = 50.0  # rad/s² (角加速度上限)
MAX_SPEED = 100.0                # m/s (速度上限)

# 魚の状態名（日本語、UIとデバッグ表示共通）
# ※ FishState enumへの依存を避けるため、文字列キーで定義
FISH_STATE_NAMES_JP = {
    "IDLE": "待機",
    "APPROACH": "接近",
    "ATTACK": "吸込み",
    "COOLDOWN": "離脱",
}
