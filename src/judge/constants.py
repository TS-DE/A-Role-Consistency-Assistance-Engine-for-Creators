"""全局常量：路径、评分档位、调用参数。

作用域规则：常量只放这里，业务文件里禁止出现裸数字与裸字符串路径。
"""

from pathlib import Path

# ── 项目路径 ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "characters"
JUDGE_YAML = DATA_DIR / "sherlock.judge.yaml"
GOLDEN_DIR = PROJECT_ROOT / "data" / "golden"
GOLDEN_JSON = GOLDEN_DIR / "golden_cases.json"
HOLDOUT_JSON = GOLDEN_DIR / "golden_holdout.json"
HOLDOUT_F_JSON = GOLDEN_DIR / "golden_holdout_f.json"
REPORTS_DIR = PROJECT_ROOT / "reports"

# ── 评分档位（与规格书 §一 一致）──────────────────────────────
SCORE_OOC = 0
SCORE_DRIFT = 1
SCORE_PASS = 2
SOFT_HITS_TO_OOC = 2          # soft 累计到这个数就判 0

# ── 调用参数 ────────────────────────────────────────────────
DEFAULT_TIMEOUT = 60          # 单次 HTTP 超时（秒）。千问 27B 单次常到 15–30s，20s 会误杀
DEFAULT_RETRIES = 2           # 首次之外的重试次数（超时 60s 时不宜再多，否则一次调用拖 3 分钟）
BACKOFF_BASE = 3.0            # 指数退避基数：3 → 6 → 12，给限流窗口足够时间合上
BACKOFF_CAP = 20.0
CALL_GAP = 0.6                # 每次调用之间的间隔，避免 8 连发触发服务端限流
MAX_JUDGE_WORKERS = 4         # 判定并发数：8 条 trait 互相独立，串行是纯浪费
MISSING_RETRIES = 2           # 某条 trait 失败后补跑几轮（补跑只针对失败的那几条）
MAX_CONSECUTIVE_FAILURES = 8  # 连续失败到这条数就判定网络瘫了，立即中止
PREFLIGHT_PROMPT = "reply with the single word OK"

# ── 文本处理 ────────────────────────────────────────────────
SENTENCE_ENDS = ".!?"
QUOTE_ELLIPSIS = r"\s*(?:\.\.\.+|…)\s*"

# ── 闭环 ────────────────────────────────────────────────────
MAX_REWRITE_ATTEMPTS = 3      # 最多生成几稿；超过仍 <2 分则转人工（见 graph/routing.py）
INCOMPLETE_SCORE = -1         # 校验未完成时的分数占位，绝不会被当成"通过"
