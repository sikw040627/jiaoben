# AI_MEMORY — 项目交接记忆（供其他 AI 接手阅读）

> 面向下一位 AI 协作者的项目速览：这是什么、已经实现到哪、用什么技术、下一步该做什么。

## 1. 项目是什么

`autoauto` —— 一套 **PC 端通过 ADB 驱动安卓设备**的 UI 自动化框架，功能对标「自动精灵 / 按键精灵」，用于测试、RPA、日常任务自动化。定位：在**自己拥有或获授权的设备**上做自动化。

- 语言：Python 3.12
- 仓库：`github.com/sikw040627/jiaoben`（分支 `main`）
- 本地根目录：`D:\android-auto`
- 运行前置：`adb` 在 PATH；手机开 USB 调试；`pip install -r requirements.txt`
- 跑测试：`.venv\Scripts\python.exe -m pytest`（当前 **100 项全绿**，全部用假设备+假时钟，无需真机）

## 2. 架构（模块职责）

```
device.py        ADB 原语（shell/截图/tap/swipe/key/text），DeviceProtocol 可 mock
capture.py       PNG→numpy(BGR) 解码 + 帧缓存(ScreenCache)
vision.py        找图(模板匹配/多实例/多尺度/掩码/置信度自适应)、找色/HSV/多点比色/进度条读数
templateset.py   多分辨率模板集(跨机型)：scale_template + TemplateSet
ocr.py           OCR 可插拔(pytesseract/easyocr) + preprocess_for_digits 数字预处理
numbers.py       parse_int/parse_float(纯解析) + read_int/read_float(读屏数字)
input_controller 高层点击/长按/滑动/滚动：分辨率自适应 + 随机偏移
humanize.py      贝塞尔轨迹 + 时长抖动(让拖拽平滑，flick 更易触发)
ui.py            UiAutomator2 控件树 + 连续多点手势/曲线滑动
recorder.py      录制/回放(Recorder/Player)   getevent.py 真机触摸事件解析
script_engine.py Engine 门面：变量(Context)/找图等待/找图点击/条件等待/OCR/read_number
flow.py          声明式任务流(JSON/dict)：变量、子流程call、if/while/loop/repeat_until、重试、断言
report.py        运行报告(RunReport) + 失败自动截图存档
scheduler.py     定时/循环/停止条件(run_loop)
stability.py     帧差(卡死检测)/等待画面稳定/App 强停重启
devicemanager.py 多设备管理 + 瞬断重试(call_with_retries)
parallel.py      多设备并行跑任务流(run_flow_on_each)，聚合各机 RunReport
shscript.py      录制Action → 安卓可执行 .sh(input 命令)，保留时序
store.py         根目录 .sh 文件存储库 ScriptStore(save/list/load/delete/
                 info/list_detailed/rename；ScriptInfo=大小/mtime/动作数)
cloudstore.py    RemoteStore 接口 + Memory/File/Http 三实现
cloudserver.py   自托管云端服务(stdlib http.server，REST /scripts)
sync.py          StoreSync：本地 ScriptStore ↔ RemoteStore push/pull/双向
touch.py         TouchBackend 接口(adb input 默认 / minitouch 占位未实现)
ondevice/        手机端 Termux 运行时 autorun.sh(下载云端脚本并执行)
__main__.py      CLI：devices/screencap/tap/swipe/findimage/record/play
                 + export-sh/store/serve/push/pull/sync(均无需设备)
```

设计原则：**设备层可替换**（`DeviceProtocol`），所有上层逻辑（视觉/输入/任务流/调度）都用假设备+假时钟做了单元测试。**时钟与 sleep 全部可注入**，测试零等待。

## 3. 已实现功能（对标自动精灵）

- 录制回放（含 `getevent` 真机触摸解析）
- 找图：模板匹配、多实例、多尺度、掩码匹配、置信度自适应、多分辨率模板集
- 找色：单色/数色/HSV 范围/多点比色/取色/进度条百分比读数
- OCR：可插拔后端 + 数字预处理 + 读屏数字（金币/血量/倒计时）
- 控件操作：UiAutomator2 找控件/点击/输入/XPath/连续手势
- 输入：点击/长按/滑动/滚动/按键/文本，分辨率自适应 + 随机偏移 + 贝塞尔轨迹
- 脚本编排：变量、找图等待、找图点击、条件等待
- 声明式任务流：变量、子流程复用、if/while/loop/repeat_until、重试、断言、失败截图
- 稳定性：卡死检测（帧差）、等待稳定、App 重启恢复
- 调度：定时/循环/停止条件
- 多设备：管理、断线重试、并行跑任务流 + 报告聚合

## 4. 技术选型（为什么这么选，最满足需求）

| 需求 | 选用技术 | 理由 |
|---|---|---|
| 驱动设备、免侵入 | **ADB**（`adbutils`） | 免装 APK、跨机型、命令稳定；`input`/`am`/`getevent`/`screencap` 覆盖点击、生命周期、录制、截图 |
| 图像识别（找图找色） | **OpenCV**（`opencv-python-headless`） | 模板匹配/HSV/掩码/多尺度成熟高效；headless 免 GUI 依赖 |
| 跨机型稳定性 | **多分辨率模板集 + 分辨率自适应** | 同一目标存多分辨率截图取最优，坐标按屏幕比例缩放，一套脚本跑多机型 |
| 控件级操作 | **UiAutomator2** | 直接拿控件树，比纯图色更精准；`swipe_points` 支持连续手势 |
| 文字/数字读数 | **可插拔 OCR**（pytesseract / easyocr）+ 数字预处理 | 核心功能不强依赖 OCR；数字字段灰度二值放大后识别更准 |
| 复杂任务编排 | **声明式任务流(JSON/dict)** | 非程序员也能配任务；重试/断言/条件/循环内建，失败自动留证 |
| 规模化 | **多设备并行 + 报告聚合** | 线程池并发跑同一任务流，聚合各机结果 |

> 若要进一步提升执行流畅度/兼容新版本 Android，可评估把执行层从 `adb input` 换成 **MaaTouch / minitouch**（`/dev/input` 注入，事件更连续、带真实设备号）——见第 5 节。

## 4.5 录制→云端→手机复用（已打通）

「像自动精灵手机版那样：对局中录制 → 上传云端 → 手机下载复用」这条链路已实现：
录制产物编译成安卓可直接执行的 `.sh`（`shscript.py`）→ 存根目录 `store/`（`store.py`）→
自托管云端服务（`cloudserver.py`）+ 可插拔 `RemoteStore`（`cloudstore.py`）+ 同步（`sync.py`）→
手机 Termux 用 `ondevice/autorun.sh` 下载并 `sh` 执行，回放不需要 PC/ADB。
无新增依赖（全部标准库）。仍缺：对象存储后端、原生 App、游戏多指连续注入（见 `UNFINISHED.md`）。

## 5. 待办 / 当前缺口（下一位 AI 可接手）

- **真机端到端验证**：现有测试全是 mock；需接真机跑一遍找图/找色/OCR/任务流，校准阈值与坐标。
- **OCR 后端未内置**：`read_number` 需要用户自行装 pytesseract（+Tesseract 二进制）或 easyocr；可加安装脚本或打包。
- **执行层升级（可选）**：当前用 `adb input`（滑动分段、非连续）。可集成 **MaaTouch**（`MaaAssistantArknights/MaaTouch`）或 **minitouch**（`DeviceFarmer/minitouch`）走 `/dev/input`，实现连续拖拽、多指同时、真实 deviceId；需要 root 或 `app_process` 启动。
- **on-device 运行方式**：目前是 PC 驱动。若要脱机跑，可评估 **Termux + Python** 在手机本地跑，或将任务流编译给设备端执行器。
- **连续手势录制回放**：`getevent` 已能解析触摸；可扩展为多指连续手势的完整录制→连续注入（配合 MaaTouch）。
- **模板资源管理**：可加模板库目录约定、命名规范、批量截取工具、可视化选区。
- **CI**：加 GitHub Actions 跑 `pytest`（纯逻辑无需真机，适合 CI）。
- **打包/一键启动**：可加 `run.sh`/`run.bat` 一键装依赖 + 跑指定任务流。

## 6. 项目边界

本项目范围是**正常自动化**（测试/RPA/日常任务），只操作使用者自己拥有或获授权的设备。不含隐藏/反检测相关内容；这类不在本仓库范围内。使用第三方 App / 联机游戏的自动化可能违反其服务条款，接手者与使用者需自行评估合规与法律风险。

## 7. 关键约定（改代码时注意）

- 新增设备交互一律走 `DeviceProtocol`，方便 mock 测试。
- 任何轮询/等待逻辑的 `clock`/`sleep` 都要可注入，保证测试零等待。
- 颜色对外用 **RGB**（人读色卡习惯），内部转 BGR。
- 模板匹配用有纹理的截图；纯色块会让 `TM_CCOEFF_NORMED` 退化。
- 数字 OCR 的字母→数字混淆修正**默认关闭**，仅 `read_number` 等已知数字字段显式开启（避免把 "none" 读成 0）。
- 提交遵循现有风格；`.venv`/`logs`/缓存已在 `.gitignore` 排除。
