# Manaka × DG-LAB Control Center

## A/B 独立通道开发分支

本地开发版提供 A/B 独立强度、自由检测绑定和后台实时处理。
“个性化范围”只调整强度；“波形工作台”管理波形库和循环动态预览；“玩法设置”先确认原版心率／动作或 A/B 独立玩法，再配置对应的动作、检测绑定和通道规则，可重新选择。
每个通道同时只有一个波形，支持完整 V3 波形导入、循环或单次播放及优先级切换。
A/B 各有硬上限，可选择独立、A→B 或 B→A 强度同步。每通道可绑定振动器或活塞机，以设备档位或游戏遥测控制强度，并独立设置波形条件；高潮事件可选且优先级最高。
原版玩法保留原始强度与波形逻辑，单独保存配置，可与新版切换。参考波形按用户选定的「官方示例 - 呼吸」「默认 - 活塞机」「默认 - 高潮」移植完整帧。
使用与验收见 [波形工作台说明](docs/WAVE_WORKBENCH.md)；此前阶段见 [通道重构说明](docs/CHANNEL_REWORK.md)。

[![Windows](https://img.shields.io/badge/Windows-10%2F11-58a6ff)](https://github.com/1zhiguo/manaka-dglab-control-center/releases/latest)
[![Latest release](https://img.shields.io/github/v/release/1zhiguo/manaka-dglab-control-center?display_name=tag)](https://github.com/1zhiguo/manaka-dglab-control-center/releases/latest)
[![Non-commercial](https://img.shields.io/badge/license-non--commercial-ff65ac)](LICENSE.md)

一个面向 **Secret Flasher Manaka × DG-LAB 3.0** 的 Windows 控制中心：连接 Manaka 与郊狼设备，并把心跳、游戏动作和 Climax 事件同步到不同通道。软件同时提供波形预览、经验/RP 修改和第三方 Mod 一站式加载。

> 本项目是社区制作的第三方工具，与 DG-LAB、游戏作者或第三方 Mod 作者不存在官方隶属关系。

## 下载

- [下载最新 Windows 便携版](https://github.com/1zhiguo/manaka-dglab-control-center/releases/latest)
- [访问项目网站](https://manaka-dglab.web.app)
- [提出问题](https://github.com/1zhiguo/manaka-dglab-control-center/issues)
- [留言与讨论](https://github.com/1zhiguo/manaka-dglab-control-center/discussions)

公开版**不包含游戏本体或第三方 Mod**。Release 仅携带已验证的 BepInEx 运行环境和本项目的 DG-LAB 遥测插件；用户可从原作者页面取得 Mod 后，通过控制中心管理插件、CustomMission 1 和 CustomMission 2。解压便携包后运行 `ManakaQmlControlCenter.exe`，不需要安装 Python 或 Node.js。

## 核心功能

- **心跳通道**：根据游戏内心率平滑调整 A 通道强度。
- **动作同步通道**：把游戏动作事件同步到 B 通道。
- **Climax 同步**：峰值事件同时驱动 A/B 通道，并受安全上限保护。
- **波形预览**：查看内置波形效果，并管理自定义波形。
- **Manaka 连接郊狼**：通过 DG-LAB 3.0 Socket 扫码完成连接。
- **经验 / RP 修改**：在控制中心内调整游戏经验值和 RP。
- **Mod 一站式加载**：导入、识别、启用、停用并检查第三方 Mod 依赖。

## 快速开始

1. 从 Releases 下载并解压便携版。
2. 启动控制中心，选择包含 `SecretFlasherManaka.exe` 的游戏根目录。
3. 在 DG-LAB App 打开“SOCKET 控制”，先连接设备，再连接服务器并用摄像头扫描二维码。
4. 从较低强度开始，设置安全上限后再启用游戏输出。

完整说明见 [QUICKSTART_CN.md](QUICKSTART_CN.md)。

## English Quick Start

1. Download the latest portable Windows archive from the [English website](https://manaka-dglab.web.app/?lang=en) or [GitHub Releases](https://github.com/1zhiguo/manaka-dglab-control-center/releases/latest), then extract the complete ZIP.
2. Run `ManakaQmlControlCenter.exe` and switch to **English** from the top bar or the first-run agreement window.
3. Select the folder that directly contains `SecretFlasherManaka.exe`, then choose **Install and Launch Game**. A clean game copy does not need BepInEx preinstalled.
4. In the DG-LAB 3.0 app, connect the device, open **SOCKET Control**, choose **Connect server**, and scan the QR code shown by the control center.
5. Begin with **Low · 5–30**, keep the initial hard cap at 30, and use **Pause output** whenever you need to set A/B output to zero without disconnecting the device.

The public build does **not** include the game. Read the full [English setup guide](QUICKSTART_EN.md) and [English FAQ](FAQ_EN.md) before first use.

## Mod 导入模型

```text
dropin_mods/incoming
        ↓ 导入并分类
dropin_mods/repository
        ↓ 用户主动启用
当前游戏目录
```

导入不会立刻改动游戏。只有启用某项内容时，管理器才会把插件同步至 `BepInEx/plugins`，把 V1/V2 任务同步到对应任务目录。停用的受管内容会放进游戏目录的 `ManakaModManager/disabled`。

## 从源码运行

当前 A/B 改版的界面规范、验证矩阵及性能测量见 [UI 统一优化验收](docs/UI_COHESION_VALIDATION.md)。波形库仅提供自适应预览；顶部按钮直接切换日间／夜间主题，不打开设置窗口。预览自动运行，隐藏时暂停，不改变设备实际播放速度。

需要 Python 3.11：

```powershell
python -m venv python/.venv
python/.venv/Scripts/python.exe -m pip install -r python/qml_dashboard_prototype/requirements.txt
python/.venv/Scripts/python.exe python/qml_dashboard_prototype/main.py
```

构建 Windows 便携版还需要 `PyInstaller`，以及由官方来源取得的 BepInEx 6 IL2CPP x64 文件放在 `installer_payload/bepinex_v113`。

维护者发布新版本时无需手工上传多个平台：先在 Windows 本机生成便携包并上传 GitHub Release，再手动运行 `Publish prebuilt release`，即可同步腾讯 COS、SHA-256 下载清单和 Firebase 网站。详见 [RELEASING_CN.md](RELEASING_CN.md)。

## 安全与责任

电刺激设备可能造成疼痛、皮肤刺激、肌肉痉挛或其他意外伤害。请在清醒、自愿且能立即停止的情况下使用，不要放置在头部、颈部、胸部或跨胸位置，也不要将本软件用于医疗用途。完整条款见 [USER_AGREEMENT_CN.md](USER_AGREEMENT_CN.md)。

## 第三方内容

- 本仓库不发布游戏文件或游戏生成的 IL2CPP interop assemblies。Release 中的第三方 Mod 以独立资源或便携包内仓库形式提供，权利与许可仍由各自作者保留。
- BepInEx 在构建阶段从其官方发布地址下载，并保留原许可证。
- DG-LAB 协议与相关资料受其原始条款约束，未经授权请勿用于商业用途。

更多信息见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 [MOD_CONTENT_NOTICE_CN.md](MOD_CONTENT_NOTICE_CN.md)。

## 许可证

本项目采用非商业源码许可，详见 [LICENSE.md](LICENSE.md)。第三方组件继续适用各自许可证。
