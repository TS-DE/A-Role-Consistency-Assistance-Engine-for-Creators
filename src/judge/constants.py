"""全局常量：路径、评分档位、调用参数。

作用域规则：常量只放这里，业务文件里禁止出现裸数字与裸字符串路径。
"""

from pathlib import Path

# ── 项目路径 ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "characters"
JUDGE_YAML = DATA_DIR / "sherlock.judge.yaml"
GOLDEN_JSON = PROJECT_ROOT / "tests" / "golden_cases.json"
HOLDOUT_JSON = PROJECT_ROOT / "tests" / "golden_holdout.json"
REPORTS_DIR = PROJECT_ROOT / "reports"

# ── 评分档位（与规格书 §一 一致）──────────────────────────────
SCORE_OOC = 0
SCORE_DRIFT = 1
SCORE_PASS = 2
SOFT_HITS_TO_OOC = 2          # soft 累计到这个数就判 0

# ── 调用参数 ────────────────────────────────────────────────
DEFAULT_TIMEOUT = 20          # 单次 HTTP 超时（秒）
DEFAULT_RETRIES = 3           # 首次之外的重试次数
BACKOFF_BASE = 1.5            # 指数退避基数：1.5 → 3 → 6
BACKOFF_CAP = 8.0
MAX_CONSECUTIVE_FAILURES = 8  # 连续失败到这条数就判定网络瘫了，立即中止
PREFLIGHT_PROMPT = "reply with the single word OK"

# ── 文本处理 ────────────────────────────────────────────────
SENTENCE_ENDS = ".!?"
QUOTE_ELLIPSIS = r"\s*(?:\.\.\.+|…)\s*"
