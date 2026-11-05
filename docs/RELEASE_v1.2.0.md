# Manaka × DG-LAB Control Center v1.2.0

## 中文

- 新增电脑原生 BLE 路线：支持郊狼 2.0 / 3.0 与负鼠，沿用现有游戏事件、A/B 独立来源、预设、自定义曲线及随机/循环策略。连接方式整体选择 V3、V4 或蓝牙。
- 检测设备时显示进度条和旋转沙漏；本轮扫描仅发现一个同类设备时自动尝试连接，多台时由用户选择。连接后仍需手动启用输出。
- 新增「腰带骑士工作台」（FN010-RX，实验性直连）：独立连接、活塞低/中/高档位映射、档位上限、伴随振动和动作覆盖。游戏随机模式跟随遥测上报的实际速度。
- 游戏活塞映射标题旁新增保存按钮。保存配置会停止该设备联动，重新点击「启用联动」后应用。
- HUD 新增腰带骑士伸缩、振动档位条与连接/待机/同步状态；可在 HUD 设置中独立开关。隐藏只影响显示。
- 波形工作台和负鼠动作分配新增当前筛选内的全选、反选及批量应用；负鼠批量修改只作用于当前 A/B 通道。
- Socket 端口可在连接面板修改；修复负鼠动作策略对自定义波形的选择与应用。

升级：退出旧控制中心和游戏，将完整 ZIP 解压到新目录运行。在「设备与游戏」确认游戏目录，执行「安装 / 修复运行环境」并重启游戏，加载随包遥测 0.5.2 / HUD V3。旧游戏 HUD 仍可显示原四项，腰带骑士 HUD 和随机实际速度需要新版 DLL。设置和自定义波形保留。

蓝牙：先在手机 App 中断开设备；郊狼切换至蓝色蓝牙模式，负鼠按说明进入蓝牙模式。腰带骑士在其独立工作台点击「检测并连接」，握手就绪后手动启用。不要同时使用厂商 App 和电脑直连。

验证边界：电脑直连由假 GATT、模拟扫描与回环 APP 验证；不能据此声称两代郊狼及负鼠的实体输出均已实测。维护者已反馈 FN010-RX 基础连接与联动可用，新增随机速度和 HUD 仍需实体复核。FN010-RX 采用社区记录的实验性协议，只提供离散档位，没有实际位置、行程或运动/停止确认。郊狼 2.0 的 100ms 原生采样不承诺与 3.0 体感一致。

COS 和百度网盘由维护者手动上传，本次不会运行自动 COS 发布工作流。公开包不含游戏本体或第三方 Mod/任务。


发布验证：360 项源码回归通过；最终 EXE 通过 76 项假蓝牙/FN010-RX/HUD 验证及 11 项 V4 回环场景，均未连接实体硬件。

## English

- Adds direct PC BLE for Coyote 2.0/3.0 and Opossum while preserving the existing game mappings, independent A/B sources, presets, custom curves and queues. Choose one transport mode for all devices: V3, V4 or BLE.
- Scan progress and animated hourglass; one matching device can connect after an explicit scan, while ambiguous results require manual selection. Output always requires manual enable.
- New experimental FN010-RX Belt Knight workbench: independent connection, low/mid/high piston mappings, protocol-index cap, optional vibration and action overrides. Game Random follows the effective speed reported by telemetry.
- Adds a Save button beside Game Piston Mapping. Saving stops sync until explicitly re-enabled.
- Adds optional Belt Knight move/vibration HUD cells with requested indices and connection/idle/sync status. Hiding them does not stop the device.
- Adds current-filter select all, invert and batch assignment to Pulse/Opossum action mappings. Opossum edits remain confined to the selected channel.
- Configurable Socket ports and fixes for custom action waveforms in the Opossum workbench.

Upgrade: close the game and old controller, extract the full ZIP into a new directory, select the game folder, run Install / Repair Runtime and restart the game. Telemetry 0.5.2 / HUD V3 is required for Belt Knight HUD and effective random piston speed. Existing settings and custom waves are retained.

Validation uses mock GATT/discovery and loopback APP scenarios; it is not a claim that physical Coyote/Opossum BLE output or sensation has been tested. A maintainer reported basic FN010-RX connection/sync working; the new random-speed/HUD behavior still needs hardware confirmation. Its experimental community protocol exposes discrete indices without physical position/stroke/motion-stop feedback.

COS and Baidu mirrors will be uploaded manually. No game or third-party Mods/missions are included.

Release validation: 360 source regressions passed. The frozen EXE passed 76 mock BLE/FN010-RX/HUD cases and 11 loopback V4 scenarios, without connecting physical hardware.
