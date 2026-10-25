# 侧栏、自适应预览、原版命名与 NPC 开关验收

日期：2026-10-25。使用当前本地工作区与临时测试配置，没有提交／推送、没有安装或改写游戏目录，也没有真实设备输出。

## 需求与证据

| 需求 | 实现及直接验证 |
| --- | --- |
| 玩法设置排在波形工作台上方 | 交换 NavItem 的视觉顺序，保留内部页号；`verify_ui_layout.py` 在每个截图中检查两项的实际纵坐标 |
| 预览无起点圆点，避免过密／过快 | 按用户后续选择改为仅自适应预览：窗口 `min(5000 ms, 3 × 实际时长)`，整屏始终 5 秒滚完，短波形慢放；横轴显示真实源时间，字幕显示倍率。没有模式切换器，没有起点圆点 |
| 旧版改称原版 | 页面、监视状态、提示与错误文案统一“原版 / Original”；`legacy_v1` 等存储键保持兼容。界面测试检查玩法选项名称，既有配置测试继续通过 |
| NPC 大开关关闭文字异常 | 修改前在模拟未安装、已安装关闭、已安装开启及来回切换中复现：未限定的 `active` 误取窗口状态，文字落入滑块区域。修改后文字显式读取 `npcMasterSwitch.active`，与滑块使用独立空间；禁止未安装时交互 |
| 为整体 UI 调整做调研 | `UI_DESIGN_RESEARCH.md` 包含当前源码与截图观察、Qt／Windows／W3C 官方资料、计算后的配色示例、公共控件与排版规格以及分阶段建议；整体主题重构尚未实施 |

原“固定显示 5 秒”要求已由用户确认的“只用自适应预览，界面更简洁”补充调整。0.1 秒波形显示 0.3 秒源数据、慢放约 16.7 倍；长波形保留 5 秒真实窗口。只是预览慢放，数据文件与设备节奏不变。

## 验证结果

- `build/ui-polish-tests.txt`：192 项自动测试通过，覆盖强度范围、配置保存、波形策略及传输。
- `build/ui-polish-interaction/{zh-light,en-dark}/results.json`：各 21 项实际 QML 交互通过，包含“原版”名称、配置保存、模式重新选择与草稿保护。
- `build/ui-polish-adaptive/{zh-light,en-dark-150}/results.json`：各 7 项预览场景通过。测试 0.1、0.4、1.2、8.2 秒和 10 分钟波形，比较实际渲染像素与源时间采样；验证最多 3 个短波周期、整屏 5 秒、慢放倍率、无圆点、循环与隐藏停表。
- `build/ui-polish-npc/{zh-light,en-dark-150}/results.json`：各 5 种状态布局检查通过，并验证未安装时点击无效、安装后真实鼠标往返切换调用正确。只模拟安装状态和持久化，没有安装插件。
- `build/ui-polish-baseline-npc/results.json` 与截图保留修复前的文字／滑块重叠证据。
- `build/ui-polish-layout/{zh-light,en-dark-150}/layout.json`：各 19 个页面视图检查，最小窗口 1120×720；无 QML 加载／绑定错误和自动扫描发现的横向溢出候选。人工检查另外发现原有英文 NPC 小开关行裁切，已列入整体 UI 调整待办；原有 SectionTitle 重复布局警告也仍存在。

## 交付与边界

便携 ZIP：`build/ui-polish-final/dist/ManakaQmlControlCenter-adaptive-ui-fix.zip`。完整解压后运行 EXE，保留 `_internal`。

打包检查记录为 `build/ui-polish-packaged-smoke.json`，ZIP 校验记录为 `build/ui-polish-package.json`。修改前后源码备份位于 `<local-backups>/manaka-ui-polish-backups-20261025`，包括 U0/U1 文件哈希和可验证的增量／累计补丁。

预览检查使用离屏实际 QML 渲染；NPC 检查使用模拟安装状态。这些不代替游戏／手机／设备实机联动验证。沿用此前已编译的遥测插件，本轮不更改设备输出协议。
