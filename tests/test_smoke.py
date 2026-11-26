"""冒烟测试：确认项目骨架和质量门都能跑起来。

Day 0 的占位文件 —— 后面写真正的测试时可以删掉它，
但【先留着】有个好处：`uv run pytest` 从第一天起就有输出，
你能亲眼看到覆盖率工具的 report 长什么样。
"""


def test_skeleton_imports() -> None:
    """包能被导入（说明 src 布局 + editable 安装是通的）"""
    import kb

    assert kb.__doc__ is not None
