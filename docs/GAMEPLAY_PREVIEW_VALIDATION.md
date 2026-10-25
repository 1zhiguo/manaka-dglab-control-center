# 动态预览与玩法设置验收（2026-10-25）

本轮在 `manaka-channel-rework` 本地工作区实现，没有提交、推送或改写游戏目录。

| 请求 | 当前实现 | 验证证据 |
| --- | --- | --- |
| 切换波形后图像刷新 | `WaveWorkbench.qml` 的 `asset` 改为只读派生属性，选中键或版本号变化都会重新读取；收藏和编辑不再破坏绑定 | `tools/verify_wave_preview.py` 用真实鼠标选择，检查名称、时长、全部采样；覆盖收藏通知后、编辑器关闭后、等长数据编辑后再次切换 |
| 循环播放动态预览 | `WavePreview.qml` 使用完整振幅的两份缓存曲线，按波形实际时长连续滚动；隐藏时停表，返回时恢复；不连接设备 | 比较两次渲染像素不同，检查计时推进、周期回绕、短周期循环和隐藏页面计时不变 |
| 独立玩法设置侧标签 | `ControlCenter.qml` 新增第 11 页，导航位置紧随波形工作台；波形工作台移除规则、绑定和旧版标签 | 中英文最小窗口尺寸下各 19 个视图；波形工作台不再存在旧 TabBar；新页包含 A/B 规则和检测绑定 |
| 先二选一确认，再显示对应设置 | `GameplaySettings.qml` 首次显示旧版心率／动作和 A/B 独立绑定，未选择时不能确认；确认后只显示对应配置；可重新选择 | 中英文实际界面操作覆盖确认前后、旧版与新版双向切换、未保存草稿保留、侧栏往返与保存生效 |
| 保留已有设置行为 | 强度页独立保存；已有 A/B 上限、旧版设置、波形引用与关窗保护继续生效 | 192 项源代码回归测试；中英文各 21 项交互场景；各 6 项预览场景包含波形编辑器关窗保护 |

## 本轮结果

- `build/gameplay-preview-tests.txt`：192 项通过。
- `build/gameplay-preview-interaction-{zh,en}/results.json`：各 21 项通过，无 QML 绑定错误。
- `build/gameplay-preview-animation/{zh-light,en-dark-150}/results.json`：各 6 项通过，包含渲染快照；全程使用临时配置和演示后端。
- `build/gameplay-preview-ui/{zh-light,en-dark-150}/layout.json`：各 19 个视图，1120×720，英文另含 150% 缩放；无加载／绑定错误或横向溢出候选。原有仪表盘等页面仍会输出 `SectionTitle` 重复布局警告。
- `build/gameplay-preview-packaged-smoke.json`：Windows 程序启动、本机 Socket 和二维码检查通过；新旧五个 QML 文件及遥测 DLL 与源码一致；在 Windows 样式环境变量下仍使用 Basic，无原生子控件叠加。

## 交付

便携包：`build/gameplay-preview-final/dist/ManakaQmlControlCenter-gameplay-preview.zip`。完整解压后运行目录内 EXE，保留 `_internal`。这是本地开发包，不是包含游戏的安装器。

修改前后快照位于 `<local-backups>/manaka-gameplay-preview-backups-20261025`。U0/U1 各有源码 ZIP、SHA-256 文件清单、增量和累计补丁；之前阶段的备份保留。

没有实际游戏／手机／设备联动测试，没有向真实设备输出。沿用已验证编译的 v1.1.3 遥测 DLL；旧游戏版本等待补充。
