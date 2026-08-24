# autoauto — Android 自动化框架（对标自动精灵的功能）

PC 端通过 **ADB** 驱动安卓设备的 UI 自动化工具库。定位为**正常的自动化/测试用途**：录制回放、找图找色、OCR、控件操作、脚本逻辑、定时调度。**不含任何隐藏/反检测功能**。

> 用途提示：请仅在**你自己拥有或获授权的设备**上，用于测试、RPA、辅助操作等合规场景。对第三方 App / 联机游戏做自动化可能违反其服务条款，请自行评估与承担责任。

## 环境

- Python 3.10+（本项目用 3.12 开发）
- Android SDK Platform-Tools（`adb` 在 PATH）
- 手机开启「USB 调试」，`adb devices` 能看到设备

## 安装

```powershell
cd D:\android-auto
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

OCR 为可选功能，按需装其一：

```powershell
.\.venv\Scripts\python.exe -m pip install pytesseract   # 另需系统安装 Tesseract 并加入 PATH
# 或
.\.venv\Scripts\python.exe -m pip install easyocr        # 体积较大（含 torch），中文识别更好
```

## 快速开始

```python
from autoauto import Auto

auto = Auto().connect()                 # 连接第一台 adb 设备
eng = auto.engine

# 找图并点击（最多等 10 秒）
if eng.find_and_tap("assets/templates/start.png", timeout=10):
    eng.wait_image("assets/templates/home.png", timeout=15, required=True)

# 找色 / 取色
p = eng.find_color((255, 215, 0), tolerance=20)   # RGB
print("金色像素:", p, "该点颜色:", eng.pixel(100, 200))
```

命令行：

```powershell
.\.venv\Scripts\python.exe -m autoauto devices
.\.venv\Scripts\python.exe -m autoauto screencap shot.png
.\.venv\Scripts\python.exe -m autoauto tap 500 1000
.\.venv\Scripts\python.exe -m autoauto findimage assets\templates\start.png
.\.venv\Scripts\python.exe -m autoauto record rec.json 15     # 录制 15 秒真机触摸
.\.venv\Scripts\python.exe -m autoauto play rec.json 3        # 回放 3 遍
```

## 功能对标自动精灵

| 自动精灵功能 | 本项目 | 位置 |
|---|---|---|
| 录制 / 回放 | `Recorder` / `Player`，`getevent` 实时录制 | `recorder.py`, `getevent.py` |
| 找图（模板匹配，多实例，多尺度） | `find_template` / `find_all_templates` / `find_template_multiscale` | `vision.py` |
| 找色 / 数色 | `find_color` / `count_color` | `vision.py` |
| 多点比色 | `match_multi_color` | `vision.py` |
| 取色 | `get_pixel` | `vision.py` |
| OCR 文字识别 | `get_ocr_engine`（tesseract/easyocr 可插拔） | `ocr.py` |
| 控件操作（找控件/点击/输入/XPath） | `UiController`（UiAutomator2） | `ui.py` |
| 点击 / 长按 / 滑动 / 滚动 | `InputController` | `input_controller.py` |
| 连续多点手势 / 曲线滑动 | `UiController.gesture` / `curved_swipe` | `ui.py` |
| 找图点击 / 等待出现 / 条件等待 | `find_and_tap` / `wait_image` / `wait_until` | `script_engine.py` |
| 变量 / 计数 | `Context` | `script_engine.py` |
| 循环 / 定时 / 停止条件 | `run_loop` | `scheduler.py` |
| 分辨率自适应 | `ResolutionAdapter` | `geometry.py` |
| 人性化轨迹（贝塞尔+抖动） | `bezier_path` / 随机偏移与时长 | `humanize.py`, `input_controller.py` |
| 按键 / 文本输入 | `key` / `back` / `home` / `text` | `input_controller.py` |
| 日志 | `setup_logging` | `logging_conf.py` |

## 增强功能（第二批）

在基础功能之上补充的细化能力：

| 能力 | API | 位置 |
|---|---|---|
| 掩码找图（忽略透明/动态区域） | `vision.find_template_masked` | `vision.py` |
| 多模板任选（找到哪个算哪个） | `vision.find_any` | `vision.py` |
| HSV 颜色范围找色（抗亮度/抗锯齿） | `vision.find_color_hsv` / `in_range_mask` | `vision.py` |
| 进度条 / 血条百分比读数 | `vision.color_ratio` | `vision.py` |
| 声明式任务流（JSON/dict） | `Flow` | `flow.py` |
| 任务流：重试 / 断言 / 条件 / 循环 / 直到出现 | `Flow`（op: `find_and_tap`/`wait_image`/`assert_image`/`if_image`/`loop`/`repeat_until_image` 等） | `flow.py` |
| 运行报告（成败/耗时/逐步结果） | `RunReport` | `report.py` |
| 失败自动截图存档 | `archive_frame`（`Flow` 自动调用） | `report.py` |
| 多设备管理 | `DeviceManager` | `devicemanager.py` |
| 断线重连 / 瞬断重试 | `call_with_retries` | `devicemanager.py` |
| 多分辨率模板集（跨机型找图） | `TemplateSet` / `scale_template` | `templateset.py` |
| 任务流变量 / 子流程 / while | `Flow`（op: `set`/`incr`/`call`/`while_image`）+ `$var` 引用 | `flow.py` |
| 置信度自适应找图 | `vision.find_best` | `vision.py` |
| OCR 数字读数（金币/血量/倒计时） | `Engine.read_number` / `numbers.read_int` / `read_float` | `numbers.py` |
| 数字 OCR 预处理（灰度/二值/放大） | `preprocess_for_digits` | `ocr.py` |

声明式任务流示例：

```python
from autoauto import Auto, Flow

eng = Auto().connect().engine
steps = [
    {"op": "find_and_tap", "template": "assets/templates/start.png", "timeout": 10},
    {"op": "wait_image", "template": "assets/templates/home.png", "timeout": 15, "required": True},
    {"op": "loop", "times": 3, "steps": [
        {"op": "find_and_tap", "template": "assets/templates/collect.png",
         "timeout": 5, "on_fail": "continue"},
        {"op": "sleep", "seconds": 1},
    ]},
    {"op": "repeat_until_image", "template": "assets/templates/done.png",
     "timeout": 60, "interval": 1.0,
     "do": [{"op": "find_and_tap", "template": "assets/templates/next.png", "timeout": 3}]},
]
report = Flow(eng).run(steps)          # 失败步骤自动截图到 logs/failures/
report.save("logs/last_run.json")
print(report.to_dict())
```

## 架构分层

```
device.py        ADB 原语（shell/截图/tap/swipe/key/text）  ← 可 mock
capture.py       PNG→numpy 解码 + 帧缓存
vision.py        找图/找色/多点比色（纯函数）
ocr.py           OCR（可插拔后端）
input_controller 高层点击/滑动（分辨率自适应+人性化）
ui.py            UiAutomator2 控件树 + 连续手势
recorder.py      录制/回放     getevent.py  真机触摸解析
script_engine.py 编排：变量/找图等待/找图点击/条件等待
scheduler.py     定时/循环/停止条件
flow.py          声明式任务流（重试/断言/条件/循环）
report.py        运行报告 + 失败截图存档
devicemanager.py 多设备管理 + 断线重连重试
__main__.py      命令行入口
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

全部逻辑（视觉、输入、录制回放、getevent 解析、调度、脚本引擎）均用假设备与假时钟做了单元测试，无需真机、无需真实等待即可运行。
