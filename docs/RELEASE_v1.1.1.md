# Manaka × DG-LAB Control Center v1.1.1

## 中文
- 新增郊狼 2.0（COYOTE_020）支持：通过 DG-LAB 4 App 的 V4 Socket 接入，无需直连蓝牙驱动，也无需切换 V3。
- 设备发现、自动选择、列表过滤、就绪判断、发送及重连覆盖两代郊狼；负鼠保持独立角色。沿用 V4 手动启用规则。
- 2.0 不要求 3.0 专有电路状态字段；3.0 原有故障检查保留。
- 四采样 V3 输入帧显式发送 ver:3，A/B 分别发送 100ms 波形和 300ms 强度租约。
- 每通道按策略目标、用户硬上限、APP 当前 intensityMax 和协议 0–100 限幅。缺失、无效上限禁止非零输出；实际发送前再次核对。
- 首次选择和重连等待 A/B 归零完成、清队列确认、再次归零完成。修复旧计划/启用命令跨会话生效及快速屏蔽/解除跳过归零的竞态。
- 保留原有心率/动作来源、预设、自定义曲线、A/B 循环、渐强和负鼠策略。暂停、急停及过期数据保护保留。

升级：退出旧控制中心，将完整 ZIP 解压到新目录运行 EXE。此次无需更新游戏插件，设置和自定义波形保留。2.0 请选择 V4，手机 App 先连设备蓝牙，等待归零确认后手动启用。

验证：274 项源码回归通过；源码及打包 EXE 各通过 11 个仅监听 127.0.0.1 的模拟场景。**实体郊狼 2.0 蓝牙输出和体感尚未实测。**

## English
- Adds Coyote 2.0 (COYOTE_020) through DG-LAB 4 App / V4 Socket. Hardware generation is independent of Socket version.
- Discovery, selection, readiness, output and recovery cover both Coyote generations; Opossum remains an independent role. V4 output still requires explicit manual enabling.
- Coyote 2.0 does not require Coyote 3.0 circuit-status fields. Existing 3.0 fault checks remain.
- Four-sample V3 frames explicitly use ver:3; A/B retain independent 100ms waveform tasks and 300ms intensity leases.
- Enforces policy target, user cap, current App intensityMax and the 0–100 protocol range. Missing/invalid limits block nonzero output; limits are checked again at send time.
- Selection/reconnection waits for completed zero → clear → zero transactions. Fixes stale cross-session producer/enable callbacks and fast mute/unmute races.
- Preserves existing Manaka heart/action mappings, presets, custom curves, independent queues, ramping and Opossum policies.

Upgrade: close the old controller, extract the entire ZIP into a new folder and run the EXE. No game-plugin update is needed for this change. Select V4 for Coyote 2.0, connect hardware Bluetooth in the App, wait for confirmed zeroing, then manually enable output.

Validation: 274 source regressions passed; 11 loopback scenarios passed in both source and the frozen EXE. **Physical Coyote 2.0 Bluetooth output and sensation have NOT been tested.**
