# 一站式发布说明

这套流程只会在维护者手动触发时运行。普通的代码提交不会创建新版本，也不会覆盖下载文件。

## v1.1.0 当前发布方式

本次由维护者手动上传 COS 和百度网盘，不运行 `Publish prebuilt release`。普通推送 `main` 只触发 Firebase 网站部署。

1. 本地运行 `build_qml_windows_app.ps1`，生成 `release/build-1.1.0-qml/ManakaQmlControlCenter`。
2. 完整 ZIP 为 `release/ManakaQmlControlCenter-v1.1.0-win64.zip`，同时提供 `.sha256` 校验文件；不要仅上传 EXE。
3. 更新说明在 `docs/RELEASE_v1.1.0.md`，含哈希的 GitHub 文案副本在 `release/GITHUB_v1.1.0_NOTES.md`。
4. 网站先展示 v1.1.0 功能、截图和升级提示，下载清单保留原可用版本，并明确标注新镜像准备中。
5. 维护者确认新 COS 对象可公开下载、提供百度链接/提取码及 GitHub Release 状态后，再更新下载清单与 SHA-256。准备中提示会在下载清单切至 v1.1.0 时自动隐藏。

以下自动镜像流程保留为以后显式手动选择的方式，不属于本次上传步骤。

## 发布内容规则

- 公共 Git 仓库、GitHub Release 与腾讯 COS 均不包含第三方 Mod 或任务文件。
- Windows 便携包只携带已验证的 BepInEx 运行环境、本项目的 DG-LAB 遥测插件、界面资源和 Drop-in 空目录。
- 日常本地预览与公开发行版使用同一套轻量构建，便于准确验证最终用户体验。
- 发布前必须检查 ZIP 中不存在 `mod_repositories`，并确认包含 `ManakaQmlControlCenter.exe`、快速开始文档和第三方声明。

## 首次设置（只做一次）

仓库的 `Settings → Secrets and variables → Actions` 需要保存以下密钥：

- `TENCENT_COS_SECRET_ID`：腾讯云 CAM 子用户的 SecretId。
- `TENCENT_COS_SECRET_KEY`：同一 CAM 子用户的 SecretKey。
- `FIREBASE_SERVICE_ACCOUNT_MANAKA_DGLAB`：Firebase Hosting 服务账号 JSON（现有网站工作流已经使用）。

不要使用腾讯云主账号永久密钥。CAM 子用户只应获得上海桶
`manaka-dglab-downloads-1504229034` 中 `releases/*` 对象所需的上传、校验和对象 ACL 权限。

COS 桶本身保持私有。发布流程只把最终 ZIP 对象设为 `public-read`，从而允许网页直接下载；请在 COS 中配置防盗链和用量告警以控制流量风险。

## 每次发布

1. 在维护者电脑运行测试并构建轻量 Windows 便携包。
2. 检查 ZIP 不含第三方 Mod 或 `mod_repositories`，然后生成同名 `.sha256` 文件。
3. 把完整 ZIP 与 `.sha256` 上传到对应的 GitHub Release。
4. 确认公共源码已经推送到 `main` 后，打开 GitHub Actions。
5. 选择 `Publish prebuilt release`，输入相同版本号并运行。
6. 工作流会下载刚上传的便携包，复核哈希和必要文件，随后上传腾讯 COS、更新网页下载清单并部署 Firebase。

同一版本可以安全重跑镜像部署；工作流不会在 Linux runner 上重新构建 Windows 包。

## 自动生成的发布地址

- 大陆镜像：`https://manaka-dglab-downloads-1504229034.cos.ap-shanghai.myqcloud.com/releases/<版本>/<文件名>`
- 海外镜像：`https://github.com/1zhiguo/manaka-dglab-control-center/releases/download/<版本>/<文件名>`
- 项目网站：`https://manaka-dglab.web.app`

发布失败时查看出错步骤。修复配置后直接用相同版本重跑即可；不要手动改网页中的链接或哈希。
