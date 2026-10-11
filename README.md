# Manaka × DG-LAB Control Center

[![Windows](https://img.shields.io/badge/Windows-10%2F11-58a6ff)](https://github.com/1zhiguo/manaka-dglab-control-center/releases/latest)
[![Latest release](https://img.shields.io/github/v/release/1zhiguo/manaka-dglab-control-center?display_name=tag)](https://github.com/1zhiguo/manaka-dglab-control-center/releases/latest)
[![Non-commercial](https://img.shields.io/badge/license-non--commercial-ff65ac)](LICENSE.md)

一个面向 **Secret Flasher Manaka × DG-LAB 3.0** 的 Windows 控制中心：读取游戏内心率与动作事件，在用户设置的安全上限内控制 A/B 通道，并提供实时波形、波形工作台、存档工具和安全的 Drop-in Mod 管理器。

> 本项目是社区制作的第三方工具，与 DG-LAB、游戏作者或第三方 Mod 作者不存在官方隶属关系。

## 下载

- [下载最新 Windows 便携版](https://github.com/1zhiguo/manaka-dglab-control-center/releases/latest)
- [访问项目网站](https://manaka-dglab.chenerdong0921.chatgpt.site)
- [提出问题](https://github.com/1zhiguo/manaka-dglab-control-center/issues)
- [留言与讨论](https://github.com/1zhiguo/manaka-dglab-control-center/discussions)

公开版**不包含游戏本体和第三方 Mod**。解压 Release ZIP 后运行 `ManakaQmlControlCenter.exe`，不需要安装 Python 或 Node.js。

## 核心功能

- A 通道根据游戏心率平滑映射强度；B 通道响应游戏动作。
- 用户可设置个性化心率范围、输出范围和最高安全上限。
- 峰值事件同时驱动 A/B 通道，并限制为最近 5 秒最高值 + 15。
- 一键暂停/继续输出；游戏暂停时自动停止输出。
- 官方波形预览、自定义波形编辑与本地波形库。
- DG-LAB 3.0 Socket 二维码连接向导。
- 自动安装/检测 BepInEx 与本项目遥测插件。
- Drop-in Mod 收件箱可识别 DLL、V1 JSON、V2 文件夹和 ZIP。

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

- 本仓库不发布游戏文件、游戏生成的 IL2CPP interop assemblies 或第三方 Mod。
- BepInEx 在构建阶段从其官方发布地址下载，并保留原许可证。
- DG-LAB 协议与相关资料受其原始条款约束，未经授权请勿用于商业用途。

更多信息见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 [MOD_CONTENT_NOTICE_CN.md](MOD_CONTENT_NOTICE_CN.md)。

## 许可证

本项目采用非商业源码许可，详见 [LICENSE.md](LICENSE.md)。第三方组件继续适用各自许可证。
