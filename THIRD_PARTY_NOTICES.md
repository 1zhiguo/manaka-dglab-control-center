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

本便携包包含经 SecretFlasherManaka v1.1.3 验证的 BepInEx 6 IL2CPP 运行环境：

- 版本：6.0.0-be.735（commit `5fef357`）
- 上游项目：https://github.com/BepInEx/BepInEx
- 上游许可证：GNU Lesser General Public License v2.1 或更高版本
- 许可证全文：https://github.com/BepInEx/BepInEx/blob/master/LICENSE

BepInEx 及随附运行组件保持为独立文件，安装器只负责将它们复制到游戏目录。
