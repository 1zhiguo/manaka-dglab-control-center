# 一站式发布说明

这套流程只会在维护者手动触发时运行。普通的代码提交不会创建新版本，也不会覆盖下载文件。

## 发布内容规则

- 公共 Git 仓库不提交 CustomMission V1、CustomMission V2 或 Plugins 的实际文件，只保留说明文件和加载代码。
- GitHub Release 与腾讯 COS 中提供给用户的 Windows 便携包必须包含上述 Mod/插件资源。
- 日常本地预览必须运行完整打包目录中的 `ManakaQmlControlCenter.exe`，不得用公共仓库的轻量构建冒充发行版。
- 发布前必须检查压缩包内存在 `mod_repositories/custommissions1`、`mod_repositories/custommissions2` 和 `mod_repositories/plugins` 的实际内容；缺少任意一项就终止发布。

## 首次设置（只做一次）

仓库的 `Settings → Secrets and variables → Actions` 需要保存以下密钥：

- `TENCENT_COS_SECRET_ID`：腾讯云 CAM 子用户的 SecretId。
- `TENCENT_COS_SECRET_KEY`：同一 CAM 子用户的 SecretKey。
- `FIREBASE_SERVICE_ACCOUNT_MANAKA_DGLAB`：Firebase Hosting 服务账号 JSON（现有网站工作流已经使用）。

不要使用腾讯云主账号永久密钥。CAM 子用户只应获得上海桶
`manaka-dglab-downloads-1504229034` 中 `releases/*` 对象所需的上传、校验和对象 ACL 权限。

COS 桶本身保持私有。发布流程只把最终 ZIP 对象设为 `public-read`，从而允许网页直接下载；请在 COS 中配置防盗链和用量告警以控制流量风险。

## 每次发布

1. 在维护者电脑的完整工程中运行测试并构建 Windows 便携包；此工程包含不进入公共 Git 仓库的 Mod/插件资源。
2. 检查 ZIP 内确实包含三个 `mod_repositories` 子目录，并生成同名 `.sha256` 文件。
3. 把完整 ZIP 与 `.sha256` 上传到对应的 GitHub Release。
4. 确认公共源码已经推送到 `main` 后，打开 GitHub Actions。
5. 选择 `Publish prebuilt release`，输入相同版本号并运行。
6. 工作流会下载刚上传的完整包，复核哈希和 Mod 目录，随后上传腾讯 COS、更新网页下载清单并部署 Firebase。

同一版本可以安全重跑镜像部署；工作流不会从不含 Mod 的公共源码重新构建发行包。

## 自动生成的发布地址

- 大陆镜像：`https://manaka-dglab-downloads-1504229034.cos.ap-shanghai.myqcloud.com/releases/<版本>/<文件名>`
- 海外镜像：`https://github.com/1zhiguo/manaka-dglab-control-center/releases/download/<版本>/<文件名>`
- 项目网站：`https://manaka-dglab.web.app`

发布失败时查看出错步骤。修复配置后直接用相同版本重跑即可；不要手动改网页中的链接或哈希。
