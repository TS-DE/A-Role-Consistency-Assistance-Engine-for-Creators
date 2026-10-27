"""演示界面层：Streamlit 单页，直接调用后端模块（无 HTTP 层）。

为什么要 `streamlit run` 而不是 `python -m`：Streamlit 会把脚本所在目录塞进 sys.path，
而我们要 import `src.*`，所以文件开头手动把项目根加进去。

为什么不做前后端分离：两天的交付里，多一层 HTTP 就多一个录像时可能挂掉的环节。
后端能力已经有三个入口（CLI / MCP / 评测脚本），这里只是第四个消费者。
"""
