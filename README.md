# Manaka × DG-LAB Control Center

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

公开版**不包含游戏本体**。Release 同时提供内含 Mod 仓库的 Windows 便携包，以及可单独下载的 Mod/Plugins 包；第三方内容的权利与许可仍由各自作者保留。解压便携包后运行 `ManakaQmlControlCenter.exe`，不需要安装 Python 或 Node.js。

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

需要 Python 3.11：

```powershell
python -m venv python/.venv
python/.venv/Scripts/python.exe -m pip install -r python/qml_dashboard_prototype/requirements.txt
python/.venv/Scripts/python.exe python/qml_dashboard_prototype/main.py
```

构建 Windows 便携版还需要 `PyInstaller`，以及由官方来源取得的 BepInEx 6 IL2CPP x64 文件放在 `installer_payload/bepinex_v113`。GitHub Actions 会自动取得指定版本并创建 Release。

## 安全与责任

电刺激设备可能造成疼痛、皮肤刺激、肌肉痉挛或其他意外伤害。请在清醒、自愿且能立即停止的情况下使用，不要放置在头部、颈部、胸部或跨胸位置，也不要将本软件用于医疗用途。完整条款见 [USER_AGREEMENT_CN.md](USER_AGREEMENT_CN.md)。

## 第三方内容

- 本仓库不发布游戏文件或游戏生成的 IL2CPP interop assemblies。Release 中的第三方 Mod 以独立资源或便携包内仓库形式提供，权利与许可仍由各自作者保留。
- BepInEx 在构建阶段从其官方发布地址下载，并保留原许可证。
- DG-LAB 协议与相关资料受其原始条款约束，未经授权请勿用于商业用途。

更多信息见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 [MOD_CONTENT_NOTICE_CN.md](MOD_CONTENT_NOTICE_CN.md)。

## 许可证

本项目采用非商业源码许可，详见 [LICENSE.md](LICENSE.md)。第三方组件继续适用各自许可证。
