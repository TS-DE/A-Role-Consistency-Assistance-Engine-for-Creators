"""黄金测试集的运维脚本：结构校验、多方一致率对比、泄漏审计。

跑法（必须用 -m，脚本里依赖 `from src.*` 的包导入）：
    python -m tests.scripts.validate_golden
    python -m tests.scripts.compare_rounds
    python -m tests.scripts.audit_leakage
"""
