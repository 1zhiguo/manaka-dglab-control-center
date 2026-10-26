# A/B 独立通道、检测绑定与性能重构

> 本文记录早期 P0–P4 阶段。当前版本以 [WAVE_WORKBENCH.md](WAVE_WORKBENCH.md) 为准：已取消可调全局硬上限、取消运行时波形叠加，原始旧版玩法独立保存；当前页面布局、玩法与验证结果见该文。

本分支基于 `cde3df69872ad0dafe4e8f37a6eeff658b188875`，用于分阶段评审，
不包含发布操作。游戏目录只作为本地编译依赖；不分发游戏文件或生成的 Interop。

## 五个阶段

| 阶段 | 内容 | 主要验证 |
| --- | --- | --- |
| P0 基线 | 确定性遥测样本、离线回放工具、原版行为与性能基线 | 原有 103 项测试、回放基准 |
| P1 独立强度 | A/B 日常范围、硬上限、变化速度、独立事件与峰值历史；保留旧模式 | 通道隔离、上限与倍率、配置迁移 |
| P2 遥测 | v2 协议、会话标识、随机档实际生效值与来源有效性 | v1/v2、缺字段、v1.1.3 本地编译 |
| P3 绑定 | 来源选择、强度合成、独立波形和离线映射预览 | 任意交换/共享来源、不发送设备命令的预览 |
| P4 集成与性能 | 后台映射、独立看门狗、接收时间、限量显示队列、波形合成缓存、后台文件任务、界面与打包修正 | 完整回归、循环网络集成、双语界面渲染、开发版打包 |

P4 同时整合 P1–P3 的界面修正和波形流处理。中间快照用于审阅演进；最终快照为集成后的可运行状态。

## 强度含义

在“个性化范围”直接编辑 A/B 独立配置，或继续使用同一页的旧版范围。
每个通道分别设置启用状态、日常最低/最高值、硬上限、上升/下降速度。
软件总上限保留为最后约束。所有数值仍使用本项目现有的 0–100 软件强度范围。

- 振动器、活塞档位：`日常最高 × 档位百分比`。例如日常最高 20，弱档 30%，目标是 6；改变硬上限不会重新缩放这个目标。
- 连续来源：在自定义触发区间内映射到日常范围；低于开始点时该来源输出为零。支持线性、缓慢上升和快速上升曲线。
- 无有效数据、关闭来源或关闭通道时不应用日常最低值，输出为零。
- “取最大值”使用最大贡献及其波形；“加权叠加”叠加强度，并按贡献合成各来源的波形。合成后的普通目标不超过日常最高值。
- 波形内幅值是 0–100 的包络，不再次套用档位百分比。独立模式不使用旧版内置波形的隐式 `feel_scale`；旧模式保留它以保持兼容。
- 最终命令受通道硬上限、软件总上限、设备反馈上限共同约束；手动测试也遵守这些限制。

高潮和失败事件可分别配置作用通道、强度百分比、持续时间和冷却时间。
百分比以对应通道日常最高值为基准，不把硬上限当作事件目标。
失败事件在独立模式默认关闭。高潮仍经过各通道独立的“前五秒已发送强度最高值 +15”限制。
暂停、急停和失效归零优先于普通缓降。

## 检测与波形

可选来源为心率、游戏动作、兴奋度、振动器、活塞和 NPC 警觉度。
A/B 可以共享、交换来源，也可以每通道组合最多六项。每项可设置权重、波形和以 25ms 为采样粒度的相位。
振动器使用弱/强档，活塞使用弱/中/强档。随机档必须读取实际生效档，不能用“Random”配置标签猜测强度。

旧遥测继续提供心率/动作数据。缺少 v2 字段时，振动器/活塞显示不可用并贡献零；“关闭”和“数据不可用”是两个状态。
检测来源状态在独立设置面板显示。被删除的自定义波形不会把其强度贡献转移给其他来源。

v2 仍保留所有 v1 字段，新增 `sessionId`、`hasVibratorData`、
`vibratorConfiguredMode`、`vibratorEffectiveMode`、`hasPistonData`、
`pistonEffectiveMode` 和 `pistonRandom`。新增可选游戏 API 放在独立方法中，
避免旧游戏缺成员导致其他遥测一起失效。实际档位读取与分层思路参考
SecretFlasherManaka2_X_DGLAB；MIT 许可全文已保留在 THIRD_PARTY_NOTICES.md。

独立设置面板中的离线预览使用单独引擎，不修改运行中的引擎，也不调用设备接口。
CLI 可以回放完整样本：

```powershell
.venv\Scripts\python.exe tools\replay_channels.py `
  --input python\fixtures\channel_sources_v2.jsonl `
  --settings python\fixtures\mapping_example.json
```

## 实时与性能架构

`TelemetryWorker → RealtimeProcessor → DGLabBridge` 在后台处理数据和提交输出。
GUI 读取 `OutputSnapshot`，不再负责实时映射或每包的波形编码。

- 显示邮箱只保留最新连续状态，离散事件单独进入有界日志队列；事件在后台引擎内已经处理，日志保留数量不决定实际输出。
- 每次 GUI 消费最多处理 64 项且受 4ms 预算约束。界面属性通知保持节流，同时保留待发标志，避免最后一次变化被漏掉。
- 接收时记录本机时间；旧时间戳、乱序序列及已退休会话不能刷新数据有效期。游戏重启或真正中断后重新建立事件基线。
- 设备线程独立检查一秒遥测超时，窗口不处理事件时也能归零。波形清空等待期间重新检查急停代次和数据有效期。
- 波形 V3 编码和混合结果有界缓存。混合波形按绝对相位生成下一段 0.8 秒数据，不用截短周期的方式反复播放长波形。
- 个性化编辑器保持一份草稿，跨页面切换不会丢失未保存内容；A/B 监视页保持两个稳定的卡片，避免每次输出变化销毁并重建卡片。
- 扫描、Drop-in 导入、Mod 切换、运行环境/插件安装、NPC 语音安装和 9527 安装使用后台文件任务，结果回到 GUI 线程应用。
- 演示模式不建立 Socket、遥测或 HUD 网络服务。

本机合成压力测试每批 5,000 包，共十批；使用相同样本和 Python 环境：

| 指标 | P0 | 集成版 |
| --- | --- | --- |
| GUI 消费中位耗时 | 约 77ms | 约 0.03ms |
| GUI 消费最高耗时 | 约 81ms | 约 0.06ms |
| 测试进程 CPU 时间 | 约 1.11s | 约 0.59s |
| 工作集，前/后 | 约 48.9/50.8 MiB | 约 49.3/49.4 MiB |

这是离线数据处理压力测试，不包括真实游戏、完整 QML 渲染或硬件延迟，不能换算成游戏帧率或真实场景整体加速倍数。

## 开发与验收

本次使用 Windows、Python 3.12 和仓库锁定的 PySide6 6.12.0。

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r python\qml_dashboard_prototype\requirements.txt
.venv\Scripts\python.exe -m unittest discover -s python -p "test_*.py"
.venv\Scripts\python.exe python\qml_dashboard_prototype\main.py --demo
```

增强遥测插件构建：

```powershell
.\manaka_telemetry\build_plugin.ps1 -GameDir "<已运行 BepInEx 的游戏目录>" -Compiler "<Roslyn csc.exe>"
```

不加 `-Deploy` 只生成本仓库 DLL。本次已用本机 v1.1.3 的程序集编译成功；没有替换游戏目录中的插件。
用户已确认暂不提供旧游戏目录，因此 v1.1.1/v1.1.2 实机验证留待补充。实机游戏与真实设备联调也不属于本次自动测试的已验证结果。

回归包含独立范围与事件、迁移、有效性、随机实际档位、相位与幅值、波形丢失、会话/乱序、数据中断、手动暂停、后台任务与界面通知。
完整回归当前为 143 项，全部通过。
循环网络测试用本机临时端口和手机模拟器，验证 UDP 到 WebSocket 链路；故意阻塞 GUI 所在线程，仍能发出输出和失效归零命令。

界面渲染检查：

```powershell
.venv\Scripts\python.exe tools\verify_channel_ui.py --output "<截图路径>.png"
.venv\Scripts\python.exe tools\verify_channel_ui.py --language en --output "<英文截图路径>.png"
```

渲染工具采用隔离的演示配置，并检查两通道的来源编辑行实际创建，避免仅凭 QML 加载成功判定界面可用。

开发版打包：

```powershell
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\python.exe tools\build_development.py
.venv\Scripts\python.exe tools\smoke_development.py --output "<启动检查记录>.json"
```

产物在 `build/development/dist/ManakaQmlControlCenter-AB-dev`。
这是审阅用开发版，包含增强遥测 DLL，不包含完整 BepInEx 安装载荷；
可更新已校验有效的现有 BepInEx 安装，首次安装/修复运行环境仍需完整发行构建的合法载荷。
正式构建脚本已加入新的 QML 编辑器，但本分支没有发布新的 Release。

开发构建只给打包子进程提供 Python 与 Windows 的依赖搜索路径，避免误打包其他软件的同名 ICU；
同时统一使用 PySide6 附带的 VC++ 运行库。`--build-dir build/development-validated` 可将构建及启动检查放入新目录，
保留前一份产物。启动检查使用临时配置、离线演示模式，并核对打包的 QML 与遥测 DLL 和源码一致。

## 后续分步提交

阶段快照放在工作目录外的备份目录。每阶段含：

- `source.zip`：该阶段源码与仓库资源，不含 `.git`、虚拟环境、游戏文件和构建临时目录。
- `incremental.patch`：相对前阶段的可应用补丁；P0 相对原始基线。
- `cumulative.patch`：相对原始基线的累计补丁。
- `manifest.json`：基线、阶段树标识与各文件 SHA-256。
- 对应测试、性能或渲染记录。

可以在基线的独立 checkout 按 P0→P1→P2→P3→P4 顺序检查并应用增量补丁，
或直接恢复最终 source.zip。保存快照使用临时索引和 Git 树对象，不创建提交，不改动实际索引。
P4 保留初次集成快照及 `P4-realtime-performance-final` 打包修正快照；最终快照的增量补丁接在初次 P4 后，
累计补丁可直接应用于原始基线。各快照的 `previous` 字段记录准确的增量顺序。
后续提交前再按上游反馈整理 PR 边界；本次不创建 commit、PR 或远程推送。

## 界面与设置交互优化

控制中心使用固定宽度图标列对齐侧栏文字；按钮使用原生键盘交互，宽度按文案计算，
长标签受可用空间约束并提供提示。正文主要使用 12px，按钮和输入控件使用 13px，
辅助标签保留 11px；数值重点和页面标题保持更大的字号。卡片圆角从 22px 缩小到 10px，
普通控件统一为 6px，编辑器分组为 8px。圆形仪表、状态点和滑动开关保留其原有形状。

较窄窗口中的页头、工坊说明、通道来源和长波形名使用换行或省略，避免侵入相邻控件。
旧版强度表单可滚动，路径输入框保持横向编辑能力。A/B 设置按通道分标签展示，
字段按三列排列，固定保留底部保存区。兼容模式明确提示独立设置暂不生效。

设置草稿与已保存状态分离；键盘输入后首次点击保存即可生效。恢复设置会重建编辑行，
避免下拉框和数值残留。范围关系、档位顺序和事件冷却时间在保存前显示具体错误，
不合法草稿不会改变输出或配置。振动器不再显示中档设置，离散档位隐藏不适用的映射曲线。
提高硬上限仍需原有确认；关闭编辑器或主窗口时可选择保留编辑或放弃草稿。

验收包含 143 项回归测试，以及单独运行的 QML 键盘/保存/恢复/确认/关闭交互检查。
中英文、深浅主题、1320×840 和 1120×720 窗口共四组常规渲染，另有长路径、长波形名称、
六来源组合的压力文案渲染；每组覆盖十个页面和三个通道设置视图。

```powershell
.venv\Scripts\python.exe tools\verify_settings_interaction.py --output build\settings-interaction.json
.venv\Scripts\python.exe tools\verify_ui_layout.py --language en --width 1120 --height 720 --theme light --independent --output build\ui-review
.venv\Scripts\python.exe tools\verify_ui_layout.py --language en --width 1120 --height 720 --stress-text --output build\ui-long-text
.venv\Scripts\python.exe tools\build_development.py --build-dir build\ui-validated
.venv\Scripts\python.exe tools\smoke_development.py --build-dir build\ui-validated --output build\ui-packaged-smoke.json
```

本轮源码备份独立保存在 `manaka-ui-backups-20261023`，`U0-before` 对应修改前，
`U1-ui-settings` 对应最终状态。U1 的增量补丁只包含本轮 UI 与设置交互修改；
此前 P0–P4 的备份保留。开发程序位于 `build/ui-validated/dist/ManakaQmlControlCenter-AB-dev`。


## 个性化配置与扫码连接修复（2026-10-23）

个性化范围现在只有一套编辑和保存流程，不再以灰色旧表单加独立弹窗的方式分开。
新用户采用 SecretFlasherManaka2_X_DGLAB 风格的档位配置：A 默认振动器、B 默认活塞，
弱/中/强比例为 30/50/70%，日常最高 20；仍使用本项目的独立通道和总硬上限。
已有旧版或独立配置原样读取。振动器/活塞模板仅替换草稿中的来源，保留已校准的范围与上限；
“沿用旧版范围到 A/B”复制旧心率阈值、日常最低/最高值，保留硬上限。
旧版参数和独立参数统一验证并原子写入，模式切换不会删除另一套参数。
滚动条为 6px、无常驻轨道、仅在需要滚动时显示；底部保存区保持固定。

本机已复现默认 TCP 9999 被 Windows 拒绝绑定（WinError 10013）。程序会回退到系统分配的空闲端口，
二维码、电脑地址和网络修复说明使用实际端口。内部回环连接显式禁用代理。
地址发现独立于 Socket 启动结果；支持重新检测网卡及失败重试，二维码生成失败不再阻断界面通知。
扫码弹窗使用独立标题、滚动内容和固定关闭区，跟随日间/夜间主题。

`tools/smoke_development.py` 现在同时验证打包 UI 和真实 Socket/QR 流程；
`--connection-check=<report.json>` 使用临时配置，不启动游戏遥测，不启用设备输出。
`tools/verify_ui_layout.py --live-connection --output <dir>` 验证实际二维码图片加载及弹窗标题边界。
自动端口回退不修改系统预留端口或防火墙；手机跨设备连通仍需要实际网络与 DG-LAB App 验证。


## 波形工作台后续调整（2026-10-24）

最新入口与播放行为见 [波形工作台说明](WAVE_WORKBENCH.md)。此前文档中关于个性化页编辑来源、波形、相位或运行时混合的描述已由该工作台取代；本文件其余部分保留为阶段记录。
