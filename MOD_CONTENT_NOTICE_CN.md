# 第三方 Mod 支持说明

公开版不包含游戏本体，但支持通过 Mod 管理器一站式加入第三方内容，包括：

- CustomMission V1 JSON 任务；
- CustomMission V2 `.code` 任务与资源目录；
- BepInEx 插件 DLL 及其必要资源；
- ZIP、文件夹和 Drop-in 收件箱中的混合整合包。

软件会先把导入内容识别并保存到本地仓库，再由用户选择启用或停用；不会在导入时直接覆盖游戏目录。CustomMission V1、CustomMission V2、Moaning2、Aftermath & StageLock 等内容均可通过同一管理界面处理，并显示相应依赖提示。

第三方 Mod 并非控制中心开发者原创，也不会随控制中心 Release 再分发。控制中心仅提供原作者来源索引，以及本地导入、识别、启停和依赖提示。使用者应从原发布页面取得内容，并遵守原作者的许可条件与随附说明。
