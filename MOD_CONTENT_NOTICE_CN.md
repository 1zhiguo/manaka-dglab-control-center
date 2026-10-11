# 第三方 Mod 支持说明

公开版不包含游戏本体，但支持通过 Mod 管理器一站式加入第三方内容，包括：

- CustomMission V1 JSON 任务；
- CustomMission V2 `.code` 任务与资源目录；
- BepInEx 插件 DLL 及其必要资源；
- ZIP、文件夹和 Drop-in 收件箱中的混合整合包。

软件会先把导入内容识别并保存到本地仓库，再由用户选择启用或停用；不会在导入时直接覆盖游戏目录。CustomMission V1、CustomMission V2、Moaning2、Aftermath & StageLock 等内容均可通过同一管理界面处理，并显示相应依赖提示。

第三方 Mod 并非控制中心开发者原创。当前本地快照未发现覆盖全部内容的明确再分发许可，因此公开安装包不直接携带这些作者文件。用户可导入自己从获授权来源取得的副本；取得单个 Mod 的明确再分发许可后，可以将其连同许可证和署名加入公开包。
