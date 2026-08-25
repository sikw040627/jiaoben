# ondevice — 手机端运行时（Termux，无需 PC）

实现「手机下载云端脚本并直接复用」这一环,全程在手机上完成,不需要连电脑/ADB。

## 原理

录制产物是一份安卓可直接执行的 `.sh`(`input tap/swipe/...`),上传到 autoauto 云端服务后
(见根目录 `autoauto/cloudserver.py`),手机用 `autorun.sh` 拉下来并 `sh` 执行即可。

## 在手机上准备(Termux)

```sh
pkg install curl        # 或 wget
# 把 autorun.sh 拷到手机(或 curl 从云端服务自身下载)
```

## 使用

```sh
# 下载并立即运行名为 daily_task 的脚本
sh autorun.sh http://192.168.1.10:8000 daily_task

# 只下载不运行
sh autorun.sh http://192.168.1.10:8000 daily_task --download-only

# 服务端开了 token 鉴权时
sh autorun.sh http://192.168.1.10:8000 daily_task --run --token 你的令牌
```

脚本会缓存到 `$AUTOAUTO_STORE`(默认 `~/autoauto-store`),之后可离线重复 `sh ~/autoauto-store/daily_task.sh`。

## 说明与边界

- 只用 Termux + 系统 `input`,不需要 root。
- `input` 是**离散**单点事件,连招/摇杆等连续多指手势不跟手;高保真多指注入需 minitouch/MaaTouch,
  属未实现的占位部分,见根目录 `UNFINISHED.md`。
- 原生 Android App 版(替代 Termux)属可选的后续工作,同样记录在 `UNFINISHED.md`。
- 请仅在自己拥有或获授权的设备上使用;对联机游戏做自动化可能违反其服务条款,风险自负。
