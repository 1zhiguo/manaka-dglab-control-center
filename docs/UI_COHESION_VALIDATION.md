# UI 统一优化验收（2026-10-26）

> 后续调整：已移除外观弹窗与单独的动画选项，顶部按钮直接切换日间／夜间主题。以下保留此前阶段的设计与验证记录。

## 实现

保留黑金／暖白风格，在 `python/qml_dashboard_prototype/components` 集中维护主题、按钮、文本框、数字框、选择框、勾选框、开关、标签、分页、分组、弹窗及滚动条。Basic 样式仍由生产入口强制设置，避免 Windows 原生勾选框叠入自绘控件。

- 11 个侧栏页面共用颜色与字体；正文 14、说明 12、分组 18、页面标题 24，默认控件高度 40。交互边框与装饰边框分离；数据大字、品牌字样和特殊操作保留其语义尺寸。
- 侧栏使用项目内原创 SVG：统一 20px 画布与 1.5px 笔画，深浅主题各一套，不请求网络字体。
- 个性化范围移除重复标题，共用 A/B 分页与细滚动条；玩法、波形库和强度编辑器保留各自真实的保存方式。持久化配置键、强度校准和草稿逻辑不变。
- NPC 大开关、HUD 和暂停按钮使用 Controls 键盘语义；NPC 的语言选择与音频开关分行，未安装时选项不可用。状态明确为“已保存配置 · 重启游戏后生效”，不假装能确认游戏是否已经重启。
- NPC 字幕弹窗的英文标签列加宽；关闭按钮正确显示 Close，与开关 OFF 区分。窄卡片标题与辅助文字分行，不再形成循环布局依赖。
- 顶部“外观”入口统一管理主题与“减少动态效果”，设置自动保存。主题列表在打开和语言刷新时重新读取当前主题，避免初始化模型把深色误显示为浅色。
- 仍然只有自适应预览：短波形显示 3 周期，整屏 5 秒；长波形显示 5 秒源数据。减少动态效果时显示静态预览；隐藏页面、隐藏窗口或最小化时停表。源波形、真实发送速度和设备协议不变。

## 验证

测试均使用临时配置、离线演示或本机 Socket 诊断；没有安装游戏插件，也没有向设备输出。

| 范围 | 检查与证据 |
| --- | --- |
| 业务回归 | 192 项 Python 单元测试通过，覆盖强度、配置、路由、波形和传输；本次界面偏好另由真实 QML 交互验证 |
| 页面矩阵 | `tools/verify_ui_matrix.py`：中文／英文 × 浅色／深色 × 100/125/150/200% × 1120×720／1320×840，共 32 组、每组 20 个页面及状态；`build/ui-cohesion-matrix/results.json` 汇总 QML 错误、递归布局警告和横向溢出扫描 |
| 草稿和保存 | 中英文各 21 项真实 QML 交互通过，包含输入未失焦直接保存、绑定修改保留草稿、报错纠正、模式重选、关闭保护；`build/ui-cohesion-interaction-{zh,en}.json` |
| 组件状态 | `tools/verify_shared_components.py`：中英文深浅主题 4 组，捕获正常、悬停、按下、键盘焦点、禁用和错误状态；验证 Tab/Space、搜索清空、数字输入、选择框和标准弹窗只接受一次；`build/ui-cohesion-components-final/results.json` |
| 波形预览 | 中英文各 9 项场景通过，覆盖 0.1/0.4/1.2/8.2/600 秒波形，像素与采样一致性、循环、隐藏停表、外观偏好仅保存对应键；`build/ui-cohesion-preview-{zh,en}/results.json` |
| NPC 开关 | 中英文各 5 个状态，通过鼠标往返切换和 Space 操作；未安装时点击无效；不重叠文字与滑块；`build/ui-cohesion-npc-final-{zh,en}/results.json` |
| 弹窗与偏好 | 中英文各 16 个场景：网络、外观、NPC 台词、导入、存档确认、Mod 删除确认、协议、7 步引导、键盘暂停和实际主题切换；仅打开与检查，不执行安装／删除／写入游戏；`build/ui-cohesion-dialogs-{zh,en}/results.json` |
| 长文本 | 英文 1120×720 下长路径、长波形名、全部绑定来源压力检查，20 个视图无错误／溢出候选；`build/ui-cohesion-stress/layout.json` |

矩阵使用 Qt 缩放系数的实际离屏渲染，不代表在四台不同 DPI 显示器上逐一手测。自动扫描之外，人工查看了主页面、玩法绑定、NPC 页面与弹窗、网络帮助、外观及控件状态截图。

## 性能测量

本机没有 Qt Creator / qmlprofiler 可执行工具，因此使用 `tools/profile_ui_rendering.py` 连接真实 Qt Quick 的 `beforeRendering`、`afterRendering` 和 `frameSwapped` 信号，并读取预览时钟及进程 CPU；没有把后端合成基准当成界面渲染测量。此替代方案不能给出逐个 QML 绑定的 Profiler 火焰图。

从 U0 备份提取原 QML，与修改后的 QML 分别测量；演示模式、软件渲染、1320×840。旧版每场景 5 秒，新版每场景 10 秒，按时间归一化。结果位于 `build/ui-cohesion-profile-before.json` 和 `build/ui-cohesion-profile-after.json`。

| 指标 | 原 QML | 新 QML |
| --- | --- | --- |
| 递归布局警告 | 本轮记录 8 条 | 0 条 |
| 可见预览绘制阶段 P95 | 0.510 ms | 0.519 ms |
| 仪表盘绘制阶段 P95 | 0.530 ms | 0.406 ms |
| A/B 监视绘制阶段 P95 | 0.877 ms | 0.784 ms |
| 隐藏预览页时钟增量 | 0 | 0 |
| 隐藏窗口时钟增量 | 约 5024 ms / 5 秒 | 0 / 10 秒 |
| 减少动态效果 | 原 QML 不支持，仍持续动画 | 10 秒时钟增量 0、渲染帧数 0 |

可见预览的耗时接近原版；本次明确的改善是消除重复布局及不必要的后台动画。上述绘制阶段不包含全部 QML/Canvas 准备或 GPU 延迟，CPU 小数也受采样分辨率影响，不据此宣称整体固定倍数提速。未验证真实游戏／手机／硬件的端到端表现。

## 构建、恢复与使用

最终便携包：`build/ui-cohesion-final/dist/ManakaQmlControlCenter-ui-cohesion.zip`。完整解压，运行目录中的 `ManakaQmlControlCenter-AB-dev.exe`，保留 `_internal`。这是开发验收包，沿用已有插件，不含完整 BepInEx 运行环境或游戏文件。

`tools/smoke_development.py` 检查生产入口强制 Basic、勾选框只有一套 20×20 指示器、界面渲染以及本机 Socket/二维码；同时逐文件比较全部 QML、公共组件、SVG 图标和遥测 DLL 的源码／包内哈希。报告为 `build/ui-cohesion-packaged-smoke.json`。

ZIP 的 CRC、源码／文档一致性和 SHA-256 记录在 `build/ui-cohesion-package.json`。修改前后的源码、增量及累计补丁存放于 `<local-backups>/manaka-ui-cohesion-backups-20261025`；`verification.json` 校验 U0/U1 归档和补丁还原。保留此前交付包，无提交、推送或游戏目录写入。
