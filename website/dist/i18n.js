(() => {
  const translations = {
    zh: {
      "release111.title": "v1.1.1 · 郊狼 2.0 / V4 支持",
      "release111.desc": "通过 DG-LAB 4 App 连接郊狼 2.0，保留原有 A/B 心率与动作策略。补齐当前上限检查、确认归零与重连保护；实体 2.0 输出尚未实测。",
      "release111.mirrors": "v1.1.1 已提供百度网盘、腾讯 COS 和 GitHub 三种下载方式。",

      "nav.dashboard": "返回 Dashboard",
      "meta.home.description": "Manaka × DG-LAB 控制中心 v1.2.0：V3/V4 与电脑蓝牙直连、郊狼与负鼠、腰带骑士活塞联动、可自定义 HUD 和批量动作波形。",
      "meta.home.title": "Manaka × DG-LAB 控制中心",
      "meta.guide.description": "Manaka × DG-LAB 控制中心使用说明和常见问题。内容直接读取项目 Markdown 文档。",
      "meta.guide.title": "使用说明与 Q&A · Manaka × DG-LAB",
      "nav.features": "功能", "nav.downloads": "下载", "nav.screens": "界面", "nav.support": "支持", "nav.credits": "致谢", "nav.guide": "使用说明", "nav.home": "首页",
      "hero.title": "Manaka × DG-LAB<br>控制中心",
      "hero.lead": "连接 Manaka 与郊狼、负鼠和腰带骑士设备。支持 V3 / V4 扫码与电脑蓝牙直连，按心率、动作或游戏档位联动。公开版不包含游戏本体或第三方 Mod。",
      "hero.compatibility": "支持游戏版本：v1.1.1 · v1.1.2 · v1.1.3",
      "hero.download": "下载 Windows 版", "hero.guide": "使用说明与 Q&A", "hero.meta": "Windows 便携版 · 解压即用 · ",
      "download.baidu.short": "百度网盘（推荐）", "download.cos.short": "国内高速直链", "download.github.short": "GitHub 下载",
      "features.title": "核心功能",
      "feature.heart.title": "A/B 自由分配", "feature.heart.desc": "每个郊狼通道独立选择心率或动作",
      "feature.action.title": "负鼠振动工作台", "feature.action.desc": "游戏档位同步、动作映射与自定义波形",
      "feature.climax.title": "Climax 同步", "feature.climax.desc": "峰值事件联动 A/B 通道",
      "feature.wave.title": "波形预览", "feature.wave.desc": "预览预设、管理自定义波形并批量分配",
      "feature.connect.title": "扫码或蓝牙直连", "feature.connect.desc": "V3 / V4 Socket 与电脑 BLE，整体切换连接方式",
      "feature.save.title": "经验 / RP 修改", "feature.save.desc": "备份后修改游戏进度数据",
      "feature.mod.title": "Mod 一站式加载", "feature.mod.desc": "导入、识别、启停和依赖提示",
      "feature.voice.title": "NPC 反应语音", "feature.voice.desc": "离线触发语气词与可编辑字幕",
      "voice.kicker": "MANAKA NPC VOICES · 新功能",
      "voice.title": "让附近的 NPC 真正做出反应",
      "voice.lead": "插件会结合距离与游戏状态，在警觉、发现、失败和互动阶段播放对应的日语语气词与字幕，不再只是随机播报。",
      "voice.trigger.title": "情境触发", "voice.trigger.desc": "距离、警戒、发现、失败与 Aftermath 互动阶段分别处理",
      "voice.profile.title": "角色差异", "voice.profile.desc": "青年 / 老人、男性 / 女性使用不同反应池",
      "voice.edit.title": "可编辑字幕", "voice.edit.desc": "在控制中心修改中、日、英文本，语音统一使用日语语气词",
      "voice.offline.title": "完全离线", "voice.offline.desc": "一键安装、总开关与播放设置，游戏中不会调用任何 API",
      "voice.meta": "NPC Voice Mod v0.6.1 · 可通过控制中心安装，也支持手动安装",
      "voice.preview": "实机预览：显示 NPC 类型、距离与当前反应字幕",
      "downloads.title": "选择下载通道", "downloads.lead": "大陆用户优先使用百度网盘；腾讯 COS 提供高速直链，海外用户可使用 GitHub Release。",
      "download.baidu.title": "百度网盘", "download.baidu.badge": "大陆推荐", "download.baidu.desc": "适合中国大陆用户。提取码：<strong data-baidu-code>sdu4</strong>，打开分享页后保存或下载完整压缩包。", "download.baidu.button": "打开百度网盘",
      "download.cos.title": "大陆高速直链", "download.backup": "备用", "download.cos.desc": "腾讯云 COS 中国大陆节点，点击后直接下载，无需进入网盘或 GitHub 页面。", "download.cos.button": "从腾讯 COS 下载",
      "download.github.title": "海外镜像", "download.github.desc": "GitHub Release 官方发布文件，适合海外网络或 COS 通道临时不可用时使用。", "download.github.button": "从 GitHub Release 下载",
      "download.version": "版本", "screens.title": "程序界面", "screens.lead": "v1.2.0 控制中心界面预览，含腰带骑士工作台与 HUD 设置。",
      "screen.dashboard": "实时仪表盘", "screen.connection": "设备与游戏", "screen.range": "个性化范围", "screen.waveforms": "波形工作台", "screen.channels": "负鼠工作台", "screen.save": "存档工具", "screen.mods": "Mod 管理器", "screen.workshop": "创意工坊", "screen.voice": "NPC 语音", "screen.log": "事件记录",
      "support.title": "支持与交流", "support.lead": "关注开发动态、加入技术交流群，或者请果果喝杯柠檬茶！",
      "support.dev.kicker": "开发者动态", "support.dev.title": "在 X 上关注果果", "support.dev.desc": "版本进度、更新公告，以及一点论文摸鱼现场。", "support.dev.button": "关注 @1zhiguo",
      "support.qq.title": "技术交流群", "support.qq.desc": "QQ群：1129729751", "support.reward.title": "赞赏项目", "support.reward.desc": "感谢你对后续开发的支持",
      "credits.title": "特别感谢", "credits.copy": "感谢 <strong>user9527 前辈</strong>的汉化与整合，以及 <strong>F95Zone Mod 作者们</strong>的创作。",
      "footer.notice": "社区第三方项目，与 DG-LAB、游戏作者及第三方 Mod 作者不存在官方隶属关系。", "footer.issues": "问题反馈", "footer.source": "源代码",
      "guide.kicker": "文档中心", "guide.title": "使用说明<br>与 Q&A", "guide.full": "完整使用说明", "guide.faq": "常见问题 Q&A", "guide.search.label": "搜索当前文档", "guide.search.placeholder": "例如：扫码、Mod、暂停", "guide.raw": "查看原始 Markdown", "guide.loading": "正在读取 Markdown 文档…", "guide.error": "文档读取失败。请刷新页面，或点击上方“查看原始 Markdown”。",
      "guide.source": "读取 {file}", "guide.search.found": "找到 {count} 处，已定位第一处", "guide.search.none": "没有找到匹配内容",
      "download.current": "当前版本", "download.pending": "发布时提供",
      "language.button": "English",
      "screen.settings": "设置",
      "release.kicker": "VERSION 1.2.0",
      "release.title": "蓝牙直连，腰带骑士加入联动",
      "release.lead": "保留现有游戏策略，新增设备、HUD 显示和更方便的批量配置。",
      "release.pending": "v1.2.0 下载通道正在准备，请以下载区显示的版本为准。",
      "release.device.title": "电脑蓝牙直连",
      "release.device.desc": "郊狼 2.0 / 3.0 与负鼠可直接连接电脑；扫描后连接，各设备手动启用。V3 / V4 扫码路线仍可选择。",
      "release.channels.title": "A/B 不再固定分工",
      "release.channels.desc": "双心率、双动作或互换。心率配置显示实际 BPM 分段，动作波形支持预览。",
      "release.hud.title": "腰带骑士也加入 HUD",
      "release.hud.desc": "显示伸缩、振动的请求档位与连接状态，可独立隐藏；大小、透明度和位置仍可调整。",
      "release.fixes.title": "连接与导入修复",
      "release.fixes.desc": "更清晰的蓝牙/配件提示，短暂遥测中断归零待机，修复 9527 重叠目录导入。",
      "release.upgrade": "升级提示：关闭游戏和旧控制中心，在新版「设备与游戏」执行「安装 / 修复运行环境」，再重启游戏。新版遥测 0.5.2 用于随机活塞速度与 HUD V3。",
      "download.github.pending": "GitHub 版待发布，请先使用百度网盘或 COS。",
      "release.belt.title": "腰带骑士工作台",
      "release.belt.desc": "FN010-RX 独立连接，设置伸缩档位上限、伴随振动和动作覆盖；随机模式跟随游戏实际速度。",
      "release.batch.title": "动作波形批量设置",
      "release.batch.desc": "支持当前筛选内全选、反选和批量应用；负鼠 A/B 保持独立，也可使用自定义波形。",
      "release.fixes": "另外支持修改 V3 / V4 Socket 端口，并改善负鼠自定义动作波形的应用。",
      "release.notes": "查看完整更新说明与适配验证范围",
      "release.boundary": "腰带骑士 FN010-RX 为实验性蓝牙适配。HUD 数字为请求档位；不同硬件与固件的实测范围请见更新说明。",
      "feature.belt.title": "腰带骑士活塞联动",
      "feature.belt.desc": "低 / 中 / 高及随机实际速度，独立配置档位",
      "feature.batch.title": "批量动作配置",
      "feature.batch.desc": "全选、反选、按当前筛选批量分配波形",
      "screen.belt": "腰带骑士工作台",
      "screen.hud": "HUD 显示设置 · 腰带骑士独立开关",
    },
    en: {
      "release111.title": "v1.1.1 · Coyote 2.0 via V4",
      "release111.desc": "Connect Coyote 2.0 through DG-LAB 4 App. Existing A/B heart/action policies remain, with current-App limits and confirmed zero/reconnection barriers. Physical Coyote 2.0 output has not been tested.",
      "release111.mirrors": "v1.1.1 is available from Baidu Netdisk, Tencent COS and GitHub.",

      "nav.dashboard": "Back to Dashboard",
      "meta.home.description": "Manaka × DG-LAB v1.2.0: V3/V4 and direct PC BLE, Coyote and Opossum, Belt Knight piston sync, custom HUD and batch action waveforms.",
      "meta.home.title": "Manaka × DG-LAB Control Center",
      "meta.guide.description": "Setup guide and FAQ for the Manaka × DG-LAB Control Center.",
      "meta.guide.title": "Guide & FAQ · Manaka × DG-LAB",
      "nav.features": "Features", "nav.downloads": "Downloads", "nav.screens": "Screens", "nav.support": "Support", "nav.credits": "Credits", "nav.guide": "Guide", "nav.home": "Home",
      "hero.title": "Manaka × DG-LAB<br>Control Center",
      "hero.lead": "Connect Manaka to Coyote, Opossum and Belt Knight. Choose V3/V4 QR connection or direct PC BLE, then sync with heart rate, actions or game levels. The game and third-party Mods are not included.",
      "hero.compatibility": "Supported game versions: v1.1.1 · v1.1.2 · v1.1.3",
      "hero.download": "Download for Windows", "hero.guide": "Guide & FAQ", "hero.meta": "Portable Windows build · extract and run · ",
      "download.baidu.short": "Baidu Netdisk (China)", "download.cos.short": "China Direct Link", "download.github.short": "GitHub Download",
      "features.title": "Core Features",
      "feature.heart.title": "Independent A/B sources", "feature.heart.desc": "Choose heart rate or actions for either Pulse channel",
      "feature.action.title": "Opossum workbench", "feature.action.desc": "Game-level sync, action rules and custom curves",
      "feature.climax.title": "Climax Sync", "feature.climax.desc": "Trigger both A/B channels on peak events",
      "feature.wave.title": "Waveform Preview", "feature.wave.desc": "Preview presets, manage custom curves and batch-assign actions",
      "feature.connect.title": "QR or direct Bluetooth", "feature.connect.desc": "Choose V3/V4 Socket or direct PC BLE",
      "feature.save.title": "EXP / RP Editor", "feature.save.desc": "Back up and edit game progression values",
      "feature.mod.title": "One-stop Mod Loader", "feature.mod.desc": "Import, detect, toggle, and check dependencies",
      "feature.voice.title": "NPC Reactions", "feature.voice.desc": "Offline interjections with editable subtitles",
      "voice.kicker": "MANAKA NPC VOICES · NEW",
      "voice.title": "Give nearby NPCs a voice",
      "voice.lead": "The plugin combines distance and game state to play matching Japanese interjections and subtitles during alert, discovery, failure, and interaction sequences—instead of firing random voice lines.",
      "voice.trigger.title": "Context-aware", "voice.trigger.desc": "Separate handling for proximity, alert, discovery, failure, and Aftermath interactions",
      "voice.profile.title": "Different characters", "voice.profile.desc": "Distinct reaction pools for young / older and male / female NPCs",
      "voice.edit.title": "Editable subtitles", "voice.edit.desc": "Edit Chinese, Japanese, and English text in Control Center; voice cues stay in Japanese",
      "voice.offline.title": "Fully offline", "voice.offline.desc": "One-click install, master toggle, and playback settings with no API calls during gameplay",
      "voice.meta": "NPC Voice Mod v0.6.1 · install through Control Center or use the manual package",
      "voice.preview": "Gameplay preview: NPC profile, distance, and reaction subtitle",
      "downloads.title": "Choose a Download Mirror", "downloads.lead": "Use GitHub Release outside mainland China. Baidu Netdisk and Tencent COS are provided for mainland China.",
      "download.baidu.title": "Baidu Netdisk", "download.baidu.badge": "Mainland China", "download.baidu.desc": "Recommended for mainland China. Extraction code: <strong data-baidu-code>sdu4</strong>. Save or download the complete archive from the share page.", "download.baidu.button": "Open Baidu Netdisk",
      "download.cos.title": "China Direct Link", "download.backup": "Backup", "download.cos.desc": "Direct download from a Tencent COS mainland China region without opening Baidu Netdisk or GitHub.", "download.cos.button": "Download from Tencent COS",
      "download.github.title": "Global Mirror", "download.github.desc": "Official GitHub Release asset, recommended for users outside mainland China.", "download.github.button": "Download from GitHub Release",
      "download.version": "Version", "screens.title": "Application Screens", "screens.lead": "v1.2.0 interface previews, including Belt Knight and HUD settings.",
      "screen.dashboard": "Dashboard", "screen.connection": "Device & Game", "screen.range": "Intensity Range", "screen.waveforms": "Waveform Studio", "screen.channels": "Opossum workbench", "screen.save": "Save Tools", "screen.mods": "Mod Manager", "screen.workshop": "Workshop", "screen.voice": "NPC Voices", "screen.log": "Event Log",
      "support.title": "Support & Community", "support.lead": "Follow development, join the technical community, or buy Guoguo a lemon tea!",
      "support.dev.kicker": "Developer Updates", "support.dev.title": "Follow Guoguo on X", "support.dev.desc": "Release progress, update notes, and occasional research procrastination.", "support.dev.button": "Follow @1zhiguo",
      "support.qq.title": "Technical Community", "support.qq.desc": "QQ Group: 1129729751", "support.reward.title": "Support the Project", "support.reward.desc": "Thank you for supporting future development",
      "credits.title": "Special Thanks", "credits.copy": "Thanks to <strong>user9527</strong> for the Chinese localization and compilation, and to the <strong>F95Zone Mod authors</strong> for their work.",
      "footer.notice": "An unofficial community project with no affiliation to DG-LAB, the game developer, or third-party Mod authors.", "footer.issues": "Report an Issue", "footer.source": "Source Code",
      "guide.kicker": "Documentation", "guide.title": "Guide<br>& FAQ", "guide.full": "Full Setup Guide", "guide.faq": "Frequently Asked Questions", "guide.search.label": "Search this document", "guide.search.placeholder": "Try: QR code, Mod, pause", "guide.raw": "View raw Markdown", "guide.loading": "Loading Markdown…", "guide.error": "Could not load the document. Refresh the page or use View raw Markdown above.",
      "guide.source": "Reading {file}", "guide.search.found": "Found {count} matches; moved to the first", "guide.search.none": "No matching content found",
      "download.current": "Current version", "download.pending": "Provided with release",
      "language.button": "中文",
      "screen.settings": "Settings",
      "release.kicker": "VERSION 1.2.0",
      "release.title": "Direct Bluetooth. Belt Knight joins the game.",
      "release.lead": "Keep your game mappings, with a new device workbench, HUD cells and simpler batch editing.",
      "release.pending": "v1.2.0 download channels are being prepared. Check the version shown in Downloads.",
      "release.device.title": "Direct PC Bluetooth",
      "release.device.desc": "Connect Coyote 2.0/3.0 and Opossum directly to the PC. Scan, connect and enable each device manually. V3/V4 QR routes remain available.",
      "release.channels.title": "Choose either source for A/B",
      "release.channels.desc": "Both heart rate, both actions, or swap roles. See actual BPM bands and preview action waveforms.",
      "release.hud.title": "Belt Knight in the HUD",
      "release.hud.desc": "Show requested move/vibration levels and connection state, with an independent visibility toggle. Adjust size, opacity and position.",
      "release.fixes.title": "Connection and import fixes",
      "release.fixes.desc": "Clearer Bluetooth/accessory feedback, zero standby during brief telemetry gaps, and overlapping user9527 path protection.",
      "release.upgrade": "Upgrade: close the game and old controller, run Install / Repair Runtime in Setup, then restart the game. Telemetry 0.5.2 enables effective random piston speed and HUD V3.",
      "download.github.pending": "The GitHub release is pending. Please use Baidu or COS for v1.1.0.",
      "release.belt.title": "Belt Knight workbench",
      "release.belt.desc": "Independent FN010-RX connection, capped move levels, optional vibration and action overrides. Random follows the game's effective speed.",
      "release.batch.title": "Batch action waveforms",
      "release.batch.desc": "Select all, invert and apply within the current filter. Opossum A/B stay independent and support custom curves.",
      "release.fixes": "Also adds editable V3/V4 Socket ports and improves custom action waveforms in the Opossum workbench.",
      "release.notes": "Full release notes and hardware verification scope",
      "release.boundary": "FN010-RX direct BLE is experimental. HUD values are requested indices; see the release notes for hardware and firmware verification limits.",
      "feature.belt.title": "Belt Knight piston sync",
      "feature.belt.desc": "Low/mid/high and effective random speed with independent levels",
      "feature.batch.title": "Batch action mappings",
      "feature.batch.desc": "Select all, invert and assign within the current filter",
      "screen.belt": "Belt Knight workbench",
      "screen.hud": "HUD settings · independent Belt Knight toggle",
    },
    ja: {
      "release111.title": "v1.1.1 · Coyote 2.0 / V4 対応",
      "release111.desc": "DG-LAB 4 App 経由で Coyote 2.0 に接続。既存の A/B 心拍・動作設定を維持し、現在の上限確認とゼロ出力・再接続保護を追加。2.0 実機出力は未検証です。",
      "release111.mirrors": "v1.1.1 は Baidu、Tencent COS、GitHub からダウンロードできます。",

      "nav.dashboard": "Dashboard に戻る",
      "meta.home.description": "Manaka × DG-LAB v1.2.0：V3/V4・PC Bluetooth 直結、Coyote・Opossum、腰帯騎士のピストン連動、HUD と動作波形の一括設定。",
      "meta.home.title": "Manaka × DG-LAB コントロールセンター",
      "meta.guide.description": "Manaka × DG-LAB コントロールセンターの使い方とよくある質問。",
      "meta.guide.title": "使い方と FAQ · Manaka × DG-LAB",
      "nav.features": "機能", "nav.downloads": "ダウンロード", "nav.screens": "画面紹介", "nav.support": "サポート", "nav.credits": "謝辞", "nav.guide": "使い方", "nav.home": "ホーム",
      "hero.title": "Manaka × DG-LAB<br>コントロールセンター",
      "hero.lead": "Manaka を Coyote、Opossum、腰帯騎士に接続。V3/V4 の QR 接続または PC Bluetooth 直結を選び、心拍・動作・ゲーム内段階に連動できます。ゲーム本体と第三者 Mod は含まれません。",
      "hero.compatibility": "対応ゲームバージョン：v1.1.1 · v1.1.2 · v1.1.3",
      "hero.download": "Windows 版をダウンロード", "hero.guide": "使い方と FAQ", "hero.meta": "Windows ポータブル版 · 解凍して起動 · ",
      "download.baidu.short": "百度網盤（中国向け）", "download.cos.short": "中国向け直接リンク", "download.github.short": "GitHub ダウンロード",
      "features.title": "主な機能",
      "feature.heart.title": "A/B の入力を自由に選択", "feature.heart.desc": "各 Pulse チャンネルを心拍数またはアクションに設定",
      "feature.action.title": "Opossum ワークベンチ", "feature.action.desc": "ゲームの強度連動、アクション設定、カスタム波形",
      "feature.climax.title": "Climax 同期", "feature.climax.desc": "ピークイベントで A/B チャンネルを同期",
      "feature.wave.title": "波形プレビュー", "feature.wave.desc": "プリセットの確認、カスタム波形の管理と一括割り当て",
      "feature.connect.title": "QR または Bluetooth 直結", "feature.connect.desc": "V3/V4 Socket または PC BLE を一括選択",
      "feature.save.title": "経験値／RP 編集", "feature.save.desc": "バックアップしてから進行データを編集",
      "feature.mod.title": "Mod 一括管理", "feature.mod.desc": "インポート、検出、有効化、依存関係の確認",
      "feature.voice.title": "NPC リアクション音声", "feature.voice.desc": "オフライン音声と編集可能な字幕",
      "voice.kicker": "MANAKA NPC VOICES · 新機能",
      "voice.title": "近くの NPC にリアクション音声を",
      "voice.lead": "距離とゲーム内の状態を組み合わせ、警戒、発見、失敗、インタラクションの各段階に合った日本語の短い音声と字幕を再生します。ランダムな再生ではありません。",
      "voice.trigger.title": "状況に応じた反応", "voice.trigger.desc": "距離、警戒、発見、失敗、Aftermath の各段階を個別に判定",
      "voice.profile.title": "キャラクター別の反応", "voice.profile.desc": "若者／高齢者、男性／女性で異なる音声候補を使用",
      "voice.edit.title": "字幕を編集", "voice.edit.desc": "コントロールセンターで中・日・英の字幕を編集。音声は日本語を使用",
      "voice.offline.title": "完全オフライン", "voice.offline.desc": "ワンクリック導入、全体スイッチ、再生設定に対応。プレイ中の API 呼び出しなし",
      "voice.meta": "NPC Voice Mod v0.6.1 · コントロールセンターから導入、または手動インストール",
      "voice.preview": "実機プレビュー：NPC の種類、距離、現在の字幕を表示",
      "downloads.title": "ダウンロード先を選択", "downloads.lead": "中国本土以外では GitHub Release をご利用ください。中国本土向けに百度網盤と Tencent COS も用意しています。",
      "download.baidu.title": "百度網盤", "download.baidu.badge": "中国本土向け", "download.baidu.desc": "中国本土向け。抽出コード：<strong data-baidu-code>sdu4</strong>。共有ページから ZIP 全体を保存またはダウンロードしてください。", "download.baidu.button": "百度網盤を開く",
      "download.cos.title": "中国向け直接リンク", "download.backup": "代替", "download.cos.desc": "Tencent COS の中国本土ノードから直接ダウンロードできます。網盤アプリは不要です。", "download.cos.button": "Tencent COS からダウンロード",
      "download.github.title": "海外向けミラー", "download.github.desc": "GitHub Release の正式配布ファイルです。中国本土以外のネットワークにおすすめです。", "download.github.button": "GitHub Release からダウンロード",
      "download.version": "バージョン", "screens.title": "ソフトウェア画面", "screens.lead": "v1.2.0 の画面プレビュー。腰帯騎士ワークベンチと HUD 設定も掲載。",
      "screen.dashboard": "ダッシュボード", "screen.connection": "デバイスとゲーム", "screen.range": "強度範囲", "screen.waveforms": "波形ワークベンチ", "screen.channels": "Opossum ワークベンチ", "screen.save": "セーブツール", "screen.mods": "Mod 管理", "screen.workshop": "ワークショップ", "screen.voice": "NPC 音声", "screen.log": "イベントログ",
      "support.title": "サポートと交流", "support.lead": "開発情報の確認、技術交流グループへの参加、または Guoguo へのレモンティーの差し入れはこちら。",
      "support.dev.kicker": "開発情報", "support.dev.title": "X で Guoguo をフォロー", "support.dev.desc": "開発状況、アップデートのお知らせ、ときどき研究の息抜き。", "support.dev.button": "@1zhiguo をフォロー",
      "support.qq.title": "技術交流グループ", "support.qq.desc": "QQ グループ：1129729751", "support.reward.title": "プロジェクトを応援", "support.reward.desc": "今後の開発へのご支援ありがとうございます",
      "credits.title": "謝辞", "credits.copy": "中国語化と統合を手がけた <strong>user9527 さん</strong>、および <strong>F95Zone の Mod 制作者の皆様</strong>に感謝します。",
      "footer.notice": "非公式のコミュニティプロジェクトです。DG-LAB、ゲーム開発者、サードパーティー Mod 制作者との公式な提携関係はありません。", "footer.issues": "問題を報告", "footer.source": "ソースコード",
      "guide.kicker": "ドキュメント", "guide.title": "使い方<br>と FAQ", "guide.full": "使い方ガイド", "guide.faq": "よくある質問", "guide.search.label": "この文書を検索", "guide.search.placeholder": "例：QR コード、Mod、一時停止", "guide.raw": "Markdown 原文を表示", "guide.loading": "Markdown 文書を読み込み中…", "guide.error": "文書を読み込めませんでした。ページを更新するか、上の「Markdown 原文を表示」を開いてください。",
      "guide.source": "{file} を表示中", "guide.search.found": "{count} 件見つかりました。最初の結果に移動しました", "guide.search.none": "一致する内容が見つかりません",
      "download.current": "現在のバージョン", "download.pending": "リリース時に公開",
      "language.button": "日本語",
      "screen.settings": "設定",
      "release.kicker": "VERSION 1.2.0",
      "release.title": "Bluetooth 直結と、腰帯騎士の連動",
      "release.lead": "既存のゲーム連動を維持し、新デバイス、HUD 表示、一括設定を追加しました。",
      "release.pending": "v1.2.0 の配布先を準備中です。ダウンロード欄のバージョンをご確認ください。",
      "release.device.title": "PC Bluetooth 直結",
      "release.device.desc": "Coyote 2.0/3.0 と Opossum を PC に直接接続。検出・接続後、各デバイスを手動で有効にします。V3/V4 の QR 接続も選べます。",
      "release.channels.title": "A/B の役割を自由に変更",
      "release.channels.desc": "両方を心拍数、両方をアクション、または役割を交換。BPM 範囲と波形プレビューも確認できます。",
      "release.hud.title": "腰帯騎士も HUD に表示",
      "release.hud.desc": "伸縮・振動の要求段階と接続状態を表示。個別に非表示にでき、サイズ・透明度・位置も調整できます。",
      "release.fixes.title": "接続とインポートの修正",
      "release.fixes.desc": "Bluetooth・アクセサリーの案内、短いデータ途絶時のゼロ待機、user9527 の重複パス保護を改善しました。",
      "release.upgrade": "更新時はゲームと旧コントローラーを終了し、「デバイスとゲーム」で実行環境をインストール／修復してからゲームを再起動してください。ランダム速度と HUD V3 にはテレメトリー 0.5.2 が必要です。",
      "download.github.pending": "GitHub 版は準備中です。v1.1.0 は百度網盤または COS からダウンロードしてください。",
      "release.belt.title": "腰帯騎士ワークベンチ",
      "release.belt.desc": "FN010-RX の独立接続、伸縮段階の上限、連動振動、動作別設定に対応。ランダム時はゲームの実際の速度に追従します。",
      "release.batch.title": "動作波形の一括設定",
      "release.batch.desc": "現在の絞り込み内で全選択・選択反転・一括適用。Opossum の A/B は独立し、カスタム波形も使えます。",
      "release.fixes": "V3/V4 Socket ポートの変更と、Opossum のカスタム動作波形の適用も改善しました。",
      "release.notes": "更新内容と実機検証範囲を見る",
      "release.boundary": "FN010-RX の Bluetooth 直結は実験的な対応です。HUD の数値は要求段階です。ハードウェア・ファームウェアの検証範囲は更新説明をご確認ください。",
      "feature.belt.title": "腰帯騎士のピストン連動",
      "feature.belt.desc": "低・中・高とランダムの実速度に連動し、段階を個別設定",
      "feature.batch.title": "動作の一括設定",
      "feature.batch.desc": "絞り込み内の全選択・選択反転・波形の一括適用",
      "screen.belt": "腰帯騎士ワークベンチ",
      "screen.hud": "HUD 設定 · 腰帯騎士の個別表示切替",
    }
  };

  const params = new URLSearchParams(window.location.search);
  const languages = ["zh", "en", "ja"];
  const htmlLanguages = {zh:"zh-CN", en:"en", ja:"ja"};
  let language = languages.includes(params.get("lang")) ? params.get("lang") : "zh";
  const template = (value, parameters = {}) => Object.entries(parameters).reduce((text, [key, item]) => text.replaceAll(`{${key}}`, item), value);
  const t = (key, parameters) => template(translations[language]?.[key] || translations.zh[key] || key, parameters);

  function updateLanguageLinks() {
    document.querySelectorAll("[data-language-link]").forEach((link) => {
      const target = new URL(link.getAttribute("href"), window.location.href);
      target.searchParams.set("lang", language);
      link.href = `${target.pathname}${target.search}${target.hash}`;
    });
  }

  function apply() {
    document.documentElement.lang = htmlLanguages[language];
    document.querySelectorAll("[data-language-select]").forEach(select => {select.value = language;});
    document.querySelectorAll("[data-i18n]").forEach((node) => { node.textContent = t(node.dataset.i18n); });
    document.querySelectorAll("[data-i18n-html]").forEach((node) => { node.innerHTML = t(node.dataset.i18nHtml); });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => { node.placeholder = t(node.dataset.i18nPlaceholder); });
    document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => { node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel)); });
    const page = document.body.classList.contains("docs-body") ? "guide" : "home";
    document.title = t(`meta.${page}.title`);
    document.querySelector('meta[name="description"]')?.setAttribute("content", t(`meta.${page}.description`));
    updateLanguageLinks();
    const labels = {zh:{nav:"主导航",toc:"文档目录",repository:"GitHub 仓库",profile:"在 X 上关注 @1zhiguo"},en:{nav:"Main navigation",toc:"Document contents",repository:"GitHub repository",profile:"Follow @1zhiguo on X"},ja:{nav:"メインナビゲーション",toc:"文書の目次",repository:"GitHub リポジトリ",profile:"X で @1zhiguo をフォロー"}}[language];
    document.querySelector("header nav")?.setAttribute("aria-label", labels.nav);
    document.querySelector("#docToc")?.setAttribute("aria-label", labels.toc);
    document.querySelector(".github-link")?.setAttribute("aria-label", labels.repository);
    document.querySelector(".social-follow-button")?.setAttribute("aria-label", labels.profile);
    const imageLabels = {"果果的 X 头像":["果果的 X 头像","Guoguo's X avatar","Guoguo の X アバター"],"DG-LAB 图标":["DG-LAB 图标","DG-LAB icon","DG-LAB アイコン"],"Manaka 图标":["Manaka 图标","Manaka icon","Manaka アイコン"],"QQ 群二维码":["QQ 群二维码","QQ community QR code","QQ グループの QR コード"],"Reward QR code":["赞赏二维码","Reward QR code","応援用 QR コード"],"Guoguo's X avatar":["果果的 X 头像","Guoguo's X avatar","Guoguo の X アバター"],"NPC Voice Mod gameplay preview":["NPC 语音实机预览","NPC Voice Mod gameplay preview","NPC 音声 Mod の実機プレビュー"],"Dashboard":["实时仪表盘","Dashboard","ダッシュボード"],"Device and game":["设备与游戏","Device and game","デバイスとゲーム"],"Intensity range":["个性化范围","Intensity range","強度範囲"],"Waveform studio":["波形工作台","Waveform studio","波形ワークベンチ"],"Opossum workbench":["负鼠工作台","Opossum workbench","Opossum ワークベンチ"],"Settings":["设置","Settings","設定"],"Save tools":["存档工具","Save tools","セーブツール"],"Mod manager":["Mod 管理器","Mod manager","Mod 管理"],"Workshop":["创意工坊","Workshop","ワークショップ"],"NPC voices":["NPC 语音","NPC voices","NPC 音声"],"Event log":["事件记录","Event log","イベントログ"],"Belt Knight workbench":["腰带骑士工作台","Belt Knight workbench","腰帯騎士ワークベンチ"],"HUD settings":["HUD 显示设置","HUD settings","HUD 設定"]};
    document.querySelectorAll("img[alt]").forEach(image => {image.dataset.originalAlt ??= image.alt; const values = imageLabels[image.dataset.originalAlt]; if(values)image.alt = values[languages.indexOf(language)];});
    try { localStorage.setItem("manaka-site-language", language); } catch {}
  }

  function setLanguage(next) {
    language = languages.includes(next) ? next : "zh";
    const url = new URL(window.location.href);
    url.searchParams.set("lang", language);
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
    apply();
    window.dispatchEvent(new CustomEvent("manaka:languagechange", { detail: { language } }));
  }

  document.querySelectorAll("[data-language-select]").forEach(select => select.addEventListener("change", () => setLanguage(select.value)));
  apply();
  window.ManakaI18n = Object.freeze({ t, apply, setLanguage, get language() { return language; } });
})();
