# 第三方内容说明

## DG-LAB 官方波形

本项目的“官方精选”波形数据来自 DG-LAB 的开源项目 `dglab-kit`：

- 源文件：https://github.com/dungeonlab-open/dglab-kit/blob/main/src/waveform/coyote.ts
- 上游项目：https://github.com/dungeonlab-open/dglab-kit
- 上游许可证：GNU General Public License v3.0
- 许可证全文：https://github.com/dungeonlab-open/dglab-kit/blob/main/LICENSE

导入内容仅包含郊狼 V3 波形帧，并在界面中明确标记为“DG-LAB 官方”。
Manaka 控制中心额外提供的中文用途说明、保守体感系数和心率区间映射并非上游原始说明。

DG-LAB 主开源仓库另有“未经授权请勿用于商业用途”的提示。发布或商业使用前，
请自行核对上游最新许可证和 DG-LAB 的授权要求。

## BepInEx

本便携包包含支持 SecretFlasherManaka v1.1.1、v1.1.2、v1.1.3 的 BepInEx 6 IL2CPP 运行环境；控制中心会按游戏版本准备对应的 Interop：

- 版本：6.0.0-be.735（commit `5fef357`）
- 上游项目：https://github.com/BepInEx/BepInEx
- 上游许可证：GNU Lesser General Public License v2.1 或更高版本
- 许可证全文：https://github.com/BepInEx/BepInEx/blob/master/LICENSE

BepInEx 及随附运行组件保持为独立文件，安装器只负责将它们复制到游戏目录。

## Fish Audio 生成语气词

NPC 语气包中的日文短语音是在开发阶段通过 Fish Audio API 生成的 AI 音频；
游戏和控制中心运行时不会连接 Fish Audio，也不会收集或分发 API Key。所用公开参考模型：

- 青年女性：`0089dce5fefb4c6ba9b9f2f0debe1ddc`
- 青年男性：`8f99ad75c8184f1db0c21d3a906445a4`
- 老年女性：`0429f2b252464b88b2ab2128f084290c`
- 老年男性：`a365c3050dd04026a81291145e017d6f`

模型页面可按 `https://fish.audio/app/m/<模型 ID>` 访问。相关音频属于 AI 生成内容，
不应被描述为真人配音；使用与再分发仍须遵守 Fish Audio 条款及对应模型权利人的要求。
