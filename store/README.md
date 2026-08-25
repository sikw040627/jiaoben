# store — 录制脚本仓库（本地文件后端）

项目根目录下的脚本存储库。每个录制会被编译成一份 **可在安卓手机上直接执行的 `.sh`**
（用系统自带的 `input tap/swipe/keyevent/text` 命令，回放时不需要 PC/ADB）。

```python
from autoauto import ScriptStore, Recorder

store = ScriptStore("store")            # 根目录下的 store/
store.save_actions("daily_task", rec.actions)   # 录制动作 -> 编译成 .sh 存入
print(store.list())                     # ['daily_task']
```

在手机上复用：把 `store/daily_task.sh` 推到手机后
`adb shell sh /sdcard/daily_task.sh`，或在 Termux 里 `sh daily_task.sh`。

> 这是本地文件后端；未来的云端/对象存储后端实现同样的 `save/list/load/delete` 接口即可平替。
> 云端上传下载、手机端独立运行时（App/Termux）尚未实现，见根目录 `UNFINISHED.md`。
