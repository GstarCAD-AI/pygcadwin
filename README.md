# pygcadwin

`pygcadwin` 是一个用于 Windows 上浩辰 CAD / GstarCAD 的 Python COM
自动化库。它通过 GstarCAD 注册的 `GStarCAD.Application.*` ProgID 连接
到正在运行的 GstarCAD，或按需启动新的 GstarCAD 实例，并提供更接近
Python 使用习惯的绘图、选择、布局、表格和视图截图 API。

这个项目的接口风格参考了
[pyautocad](https://github.com/reclosedev/pyautocad)，但目标应用是
GstarCAD，并且底层依赖 `pywin32`。

## 安装

运行环境：

- Windows
- Python 3.10+
- 已安装并注册 COM 的 GstarCAD

从 GitHub 安装：

```powershell
pip install git+https://github.com/GstarCAD-AI/pygcadwin.git
```

本地开发安装：

```powershell
git clone https://github.com/GstarCAD-AI/pygcadwin.git
cd pygcadwin
pip install -e .
```

如果需要 Excel / xlsx 表格导入导出功能：

```powershell
pip install -e ".[tables]"
```

## 快速开始

```python
import pygcadwin as gcad

cad = gcad.Gcad(create_if_missing=True, visible=True)
ctx = cad.context

ctx.ensure_layer("Walls")
ctx.create_segment((0, 0), (100, 0), layer="Walls", color=1)
ctx.create_circle((50, 50), 25)
ctx.zoom_extents()

cad.document.save_as(r"C:\tmp\demo.dwg")
cad.close()
```

也可以用上下文管理器自动释放 COM 引用：

```python
from pygcadwin import Gcad

with Gcad(create_if_missing=True, visible=True) as cad:
    cad.context.create_rect((0, 0), (100, 50), layer="Frame", color=3)
    cad.context.zoom_extents()
```

## 主要功能

- 连接或启动 GstarCAD COM 应用。
- 访问 Application、ActiveDocument、ModelSpace、Layouts。
- 创建线段、圆、圆弧、椭圆、多段线、矩形、文字、填充、标注和表格。
- 选择集、对象遍历、对象查找和布局遍历。
- `Point2`、`Vector2`、距离计算和 COM VARIANT 数组辅助函数。
- CSV / JSON 表格导入导出，Excel 格式通过 `tables` 可选依赖启用。
- 简单的工具调用分发接口，可用于 LLM agent 调用 CAD 操作。
- 视图快照和缩放辅助。

## 指定 GstarCAD 版本

默认会优先尝试已注册的版本化 ProgID，例如：

- `GStarCAD.Application.27`
- `GStarCAD.Application.26`
- `GStarCAD.Application`

当同一台机器上安装了多个版本时，可以显式指定：

```python
from pygcadwin import Gcad

cad = Gcad(prog_id="GStarCAD.Application.27")
```

## Agent 工具调用

```python
from pygcadwin import execute_tool

result = execute_tool(
    "create_circle",
    {"center": [0, 0], "radius": 10, "layer": "A-CIRC"},
)
print(result)
```

使用 `tool_schemas()` 可以获取可暴露给工具调用 agent 的操作 schema，
`run_actions([...])` 可以顺序执行多步绘图动作。

## 当前状态

这是第一版公开发布，API 仍处于 alpha 阶段。建议先在测试图纸或临时
DWG 文件中验证脚本行为，再用于正式生产图纸。

## 许可证

MIT License。详见 [LICENSE](LICENSE)。
