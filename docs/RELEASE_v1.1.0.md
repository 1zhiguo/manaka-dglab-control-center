# Manaka × DG-LAB Control Center v1.1.0

## 中文更新说明

### 新增与改进

- **DG-LAB V4 双设备支持**：新增 DG-LAB 4 App 扫码连接，支持郊狼 Pulse（COYOTE_030）和负鼠振动（OVC_1）分别选择、启用和停止。V3 保留原单设备布局与连接教程；负鼠需要切换 V4。
- **A/B 通道自由分配**：每个郊狼通道可独立选择心率或游戏动作，支持双心率、双动作以及互换。强度、波形和仪表盘标签随来源切换；相同来源共用波形分配。心率设置显示低、中、高档的实际 BPM 范围，分界为开始/满幅区间的 30% 和 70%。保存新的来源分配后需重新手动启用郊狼。
- **负鼠工作台**：直接同步游戏振动器档位，随机档跟随游戏自身的实际变化；也可对 A/B 独立配置动作映射、随机波形池、固定波形或关闭。内置四种振动包络，提供悬停/下拉波形预览与独立自定义编辑器，可共用自定义曲线形状。
- **可配置原生 HUD**：按游戏风格重做透明 HUD，可选择显示郊狼/负鼠、A/B、数字、状态与波形，并调整大小、不透明度及位置。窗口化、全屏与分辨率变化由游戏内 Unity Canvas 适配，图形约 30 FPS。
- **界面与设置**：紫灰/玫紫配色、新侧栏分组和设置页；语言、日夜主题及 HUD 设置集中管理。原 A/B 监视页由负鼠工作台替代，实时波形预览仍保留。
- **连接反馈**：设备发现后自动选择但不自动启用输出；分别显示手机连接、蓝牙、配件、静音、App 上限与等待归零确认等原因。游戏进程检测及连接/启用卡片边框高光展示各阶段状态。

### 修复

- 修复 9527 整合包来源与游戏目录重叠时的 SameFile 错误；在备份、清理或复制前拒绝重叠路径，并提示在游戏目录外解压。
- 修复 V4 发现设备后未自动选择的问题，区分“已添加设备”和“手机已蓝牙连接硬件”。
- 游戏遥测或输出刷新短暂中断时立即归零，保留用户启用状态进入待机；只有中断后新收到的有效游戏数据才能恢复。蓝牙断开、输出错误及 App 应答超时仍需手动重新启用；手动停止不会被后续游戏数据撤销。
- 修复负鼠保存成功提示持续不消失的问题，增加保存时间及未保存草稿提示。
- 改进遥测实际收包时间、UI 排队延迟及 V4 错误分类日志。
- 整合已修正的 NPC 反应插件 v0.6.1 与安装资料；NPC 运行仍完全离线，字幕仍可编辑。

### 从旧版升级

1. 关闭游戏与旧控制中心，将完整 ZIP 解压到新文件夹，运行 `ManakaQmlControlCenter.exe`。无需安装 Python；保留整个 `_internal` 文件夹。
2. 选择原来的游戏目录，在「设备与游戏」执行「安装 / 修复运行环境」以更新遥测插件，再重新启动游戏。旧游戏进程无法热替换已加载的 DLL。
3. 郊狼用户可继续使用 V3；负鼠用户选择 V4，在手机连接好硬件及配件后扫码，分别手动启用设备。启用时没有游戏数据会保持零输出待机。
4. 已有设置和自定义波形保留在 `%APPDATA%\ManakaDGLab`。首次没有通道来源配置时使用 A 心率、B 动作。更改来源或负鼠配置后需重新启用对应设备。

继续支持 Secret Flasher Manaka v1.1.1 / v1.1.2 / v1.1.3。公开包不含游戏本体或第三方 Mod/任务。V4 的 COYOTE_020 仅可发现，不启用未验证的输出格式。HUD 数字表示软件请求强度，并非硬件实测值。

## English release notes

- Added DG-LAB 4 App / V4 support for independently selected and enabled Coyote Pulse (COYOTE_030) and Opossum vibration (OVC_1). The existing V3 connection layout remains available; Opossum requires V4.
- Each physical Pulse A/B channel can use heart rate or game actions. Both channels can use the same source, or swap roles. Output strength, waveform selection and dashboard labels follow the saved source. Channels using the same source share its waveform rules. Heart-rate settings show the actual BPM bands.
- Added an Opossum workbench with direct game-vibrator synchronization and independent A/B action, random, fixed and off policies. Random game mode follows the game's actual selected level. Includes four vibration envelopes, visual previews and a custom curve editor.
- Redesigned the native Unity HUD with selectable device/channel content, waveforms, size, opacity and placement. Adapts to window/fullscreen resolution changes and renders at approximately 30 FPS.
- Refreshed the visual theme and sidebar. Language, day/night appearance and HUD preferences now live in Settings. The standalone A/B monitor page is replaced by the Opossum workbench.
- Added game-process detection, connection/enable highlights, device auto-selection and clearer Bluetooth/accessory/mute/limit feedback. Selection does not enable output.
- Fixed overlapping user9527 import paths before any cleanup or copy operation.
- Brief telemetry/producer interruptions now zero output and enter enabled standby; only newly received, fresh game data may resume. Bluetooth disconnects, output failures and App response timeouts still require manual re-enabling. Manual stops remain stopped.
- Fixed persistent Opossum save feedback and improved timestamp-based diagnostics. Bundles the corrected NPC reactions v0.6.1 installation payload; NPC runtime remains offline and subtitles remain editable.

### Upgrade

Close the game and old control center. Extract the full ZIP into a new directory, keep `_internal`, and run the EXE. Select the game folder and use **Install / Repair Runtime** before restarting the game so that the updated telemetry/HUD plugin is loaded. Existing settings and curves remain in `%APPDATA%\ManakaDGLab`. Devices must be enabled manually; source/profile changes pause the affected device.

Supported game versions remain v1.1.1, v1.1.2 and v1.1.3. The game and third-party Mods/missions are not included. V4 COYOTE_020 output is not enabled. HUD values are requested software output, not hardware measurements.

### Validation

238 automated Python tests passed, including fake-App loopback protocol tests. Chinese/English QML previews were checked. These checks do not replace testing with the actual phone, hardware and game.
