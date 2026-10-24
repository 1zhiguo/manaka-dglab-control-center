(() => {
  const translations = {
    zh: {
      "nav.dashboard": "返回 Dashboard",
      "meta.home.description": "Manaka × DG-LAB 控制中心：V3/V4、郊狼与负鼠、A/B 心率或动作分配、自定义波形、游戏 HUD 与 NPC 反应。",
      "meta.home.title": "Manaka × DG-LAB 控制中心",
      "meta.guide.description": "Manaka × DG-LAB 控制中心使用说明和常见问题。内容直接读取项目 Markdown 文档。",
      "meta.guide.title": "使用说明与 Q&A · Manaka × DG-LAB",
      "nav.features": "功能", "nav.downloads": "下载", "nav.screens": "界面", "nav.support": "支持", "nav.credits": "致谢", "nav.guide": "使用说明", "nav.home": "首页",
      "hero.title": "Manaka × DG-LAB<br>控制中心",
      "hero.lead": "连接 Manaka 与郊狼、负鼠设备。A/B 可自由选择心率或动作，负鼠跟随游戏振动器或自定义波形。公开版不包含游戏本体或第三方 Mod。",
      "hero.compatibility": "支持游戏版本：v1.1.1 · v1.1.2 · v1.1.3",
      "hero.download": "下载 Windows 版", "hero.guide": "使用说明与 Q&A", "hero.meta": "Windows 便携版 · 解压即用 · ",
      "download.baidu.short": "百度网盘（推荐）", "download.cos.short": "国内高速直链", "download.github.short": "GitHub 下载",
      "features.title": "核心功能",
      "feature.heart.title": "A/B 自由分配", "feature.heart.desc": "每个郊狼通道独立选择心率或动作",
      "feature.action.title": "负鼠振动工作台", "feature.action.desc": "游戏档位同步、动作映射与自定义波形",
      "feature.climax.title": "Climax 同步", "feature.climax.desc": "峰值事件联动 A/B 通道",
      "feature.wave.title": "波形预览", "feature.wave.desc": "查看预设并管理自定义波形",
      "feature.connect.title": "V3 / V4 扫码连接", "feature.connect.desc": "V3 保持原布局，V4 支持双设备管理",
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
      "download.baidu.title": "百度网盘", "download.baidu.badge": "大陆推荐", "download.baidu.desc": "适合中国大陆用户。提取码：<strong data-baidu-code>firk</strong>，打开分享页后保存或下载完整压缩包。", "download.baidu.button": "打开百度网盘",
      "download.cos.title": "大陆高速直链", "download.backup": "备用", "download.cos.desc": "腾讯云 COS 中国大陆节点，点击后直接下载，无需进入网盘或 GitHub 页面。", "download.cos.button": "从腾讯 COS 下载",
      "download.github.title": "海外镜像", "download.github.desc": "GitHub Release 官方发布文件，适合海外网络或 COS 通道临时不可用时使用。", "download.github.button": "从 GitHub Release 下载",
      "download.version": "版本", "screens.title": "程序界面", "screens.lead": "v1.1.0 控制中心实际界面预览。",
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
      "release.kicker": "VERSION 1.1.0",
      "release.title": "双设备联动，更自由的通道配置",
      "release.lead": "这次更新加入 V4 与负鼠支持，同时重做游戏 HUD 和设备连接体验。",
      "release.pending": "v1.1.0 已完成打包，下载通道正在准备。下方暂时提供 v1.0.5 下载；新镜像就绪后将更新。",
      "release.device.title": "郊狼 + 负鼠",
      "release.device.desc": "V4 一次扫码，两台设备独立启停；负鼠随机档跟随游戏实际切换。",
      "release.channels.title": "A/B 不再固定分工",
      "release.channels.desc": "双心率、双动作或互换。心率配置显示实际 BPM 分段，动作波形支持预览。",
      "release.hud.title": "按你的习惯摆放 HUD",
      "release.hud.desc": "自选设备、通道和显示内容，可调大小、透明度与位置，适配窗口和全屏。",
      "release.fixes.title": "连接与导入修复",
      "release.fixes.desc": "更清晰的蓝牙/配件提示，短暂遥测中断归零待机，修复 9527 重叠目录导入。",
      "release.upgrade": "升级提示：关闭游戏，在新版“设备与游戏”执行“安装 / 修复运行环境”，再重启游戏以加载新版 HUD 与遥测。",
    },
    en: {
      "nav.dashboard": "Back to Dashboard",
      "meta.home.description": "Manaka × DG-LAB Control Center: V3/V4, Pulse and Opossum, independent A/B heart-rate or action sources, waveforms, in-game HUD and NPC reactions.",
      "meta.home.title": "Manaka × DG-LAB Control Center",
      "meta.guide.description": "Setup guide and FAQ for the Manaka × DG-LAB Control Center.",
      "meta.guide.title": "Guide & FAQ · Manaka × DG-LAB",
      "nav.features": "Features", "nav.downloads": "Downloads", "nav.screens": "Screens", "nav.support": "Support", "nav.credits": "Credits", "nav.guide": "Guide", "nav.home": "Home",
      "hero.title": "Manaka × DG-LAB<br>Control Center",
      "hero.lead": "Connect Manaka to Coyote Pulse and Opossum vibration. Route heart rate or actions to either Pulse channel; follow the game vibrator or custom curves with Opossum. The game and third-party Mods are not included.",
      "hero.compatibility": "Supported game versions: v1.1.1 · v1.1.2 · v1.1.3",
      "hero.download": "Download for Windows", "hero.guide": "Guide & FAQ", "hero.meta": "Portable Windows build · extract and run · ",
      "download.baidu.short": "Baidu Netdisk (China)", "download.cos.short": "China Direct Link", "download.github.short": "GitHub Download",
      "features.title": "Core Features",
      "feature.heart.title": "Independent A/B sources", "feature.heart.desc": "Choose heart rate or actions for either Pulse channel",
      "feature.action.title": "Opossum workbench", "feature.action.desc": "Game-level sync, action rules and custom curves",
      "feature.climax.title": "Climax Sync", "feature.climax.desc": "Trigger both A/B channels on peak events",
      "feature.wave.title": "Waveform Preview", "feature.wave.desc": "Preview presets and manage custom waveforms",
      "feature.connect.title": "V3 / V4 QR connection", "feature.connect.desc": "Classic V3 layout; two-device management in V4",
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
      "download.baidu.title": "Baidu Netdisk", "download.baidu.badge": "Mainland China", "download.baidu.desc": "Recommended for mainland China. Extraction code: <strong data-baidu-code>firk</strong>. Open the share page and download the complete archive.", "download.baidu.button": "Open Baidu Netdisk",
      "download.cos.title": "China Direct Link", "download.backup": "Backup", "download.cos.desc": "Direct download from a Tencent COS mainland China region without opening Baidu Netdisk or GitHub.", "download.cos.button": "Download from Tencent COS",
      "download.github.title": "Global Mirror", "download.github.desc": "Official GitHub Release asset, recommended for users outside mainland China.", "download.github.button": "Download from GitHub Release",
      "download.version": "Version", "screens.title": "Application Screens", "screens.lead": "Actual v1.1.0 control-center interface previews.",
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
      "release.kicker": "VERSION 1.1.0",
      "release.title": "Two devices. Your choice of channel sources.",
      "release.lead": "V4 and Opossum support, a redesigned game HUD, and clearer device connection feedback.",
      "release.pending": "v1.1.0 is packaged; download mirrors are being prepared. Downloads below currently provide v1.0.5 and will be updated when the new mirrors are ready.",
      "release.device.title": "Pulse + Opossum",
      "release.device.desc": "One V4 scan, separate enable controls. Opossum Random follows the game’s actual vibrator level.",
      "release.channels.title": "Choose either source for A/B",
      "release.channels.desc": "Both heart rate, both actions, or swap roles. See actual BPM bands and preview action waveforms.",
      "release.hud.title": "Make the HUD your own",
      "release.hud.desc": "Choose devices, channels and content. Adjust size, opacity and placement in windowed or fullscreen play.",
      "release.fixes.title": "Connection and import fixes",
      "release.fixes.desc": "Clearer Bluetooth/accessory feedback, zero standby during brief telemetry gaps, and overlapping user9527 path protection.",
      "release.upgrade": "Upgrading: close the game, use Install / Repair Runtime in the new Setup page, then restart the game to load the new HUD and telemetry.",
    },
    ja: {
      "nav.dashboard": "Dashboard に戻る",
      "meta.home.description": "Manaka × DG-LAB：V3/V4、Pulse と Opossum、A/B の心拍数・アクション割り当て、カスタム波形、ゲーム内 HUD と NPC リアクション。",
      "meta.home.title": "Manaka × DG-LAB コントロールセンター",
      "meta.guide.description": "Manaka × DG-LAB コントロールセンターの使い方とよくある質問。",
      "meta.guide.title": "使い方と FAQ · Manaka × DG-LAB",
      "nav.features": "機能", "nav.downloads": "ダウンロード", "nav.screens": "画面紹介", "nav.support": "サポート", "nav.credits": "謝辞", "nav.guide": "使い方", "nav.home": "ホーム",
      "hero.title": "Manaka × DG-LAB<br>コントロールセンター",
      "hero.lead": "Manaka を Coyote Pulse と Opossum 振動に接続。Pulse の各チャンネルに心拍数またはアクションを割り当て、Opossum はゲーム内バイブやカスタム波形に連動できます。ゲーム本体とサードパーティー Mod は含まれません。",
      "hero.compatibility": "対応ゲームバージョン：v1.1.1 · v1.1.2 · v1.1.3",
      "hero.download": "Windows 版をダウンロード", "hero.guide": "使い方と FAQ", "hero.meta": "Windows ポータブル版 · 解凍して起動 · ",
      "download.baidu.short": "百度網盤（中国向け）", "download.cos.short": "中国向け直接リンク", "download.github.short": "GitHub ダウンロード",
      "features.title": "主な機能",
      "feature.heart.title": "A/B の入力を自由に選択", "feature.heart.desc": "各 Pulse チャンネルを心拍数またはアクションに設定",
      "feature.action.title": "Opossum ワークベンチ", "feature.action.desc": "ゲームの強度連動、アクション設定、カスタム波形",
      "feature.climax.title": "Climax 同期", "feature.climax.desc": "ピークイベントで A/B チャンネルを同期",
      "feature.wave.title": "波形プレビュー", "feature.wave.desc": "プリセットの確認とカスタム波形の管理",
      "feature.connect.title": "V3 / V4 QR 接続", "feature.connect.desc": "V3 は従来の画面、V4 は 2 台の個別管理に対応",
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
      "download.baidu.title": "百度網盤", "download.baidu.badge": "中国本土向け", "download.baidu.desc": "中国本土向けのダウンロード先です。取得コード：<strong data-baidu-code>firk</strong>。共有ページを開き、アーカイブ全体をダウンロードしてください。", "download.baidu.button": "百度網盤を開く",
      "download.cos.title": "中国向け直接リンク", "download.backup": "代替", "download.cos.desc": "Tencent COS の中国本土ノードから直接ダウンロードできます。網盤アプリは不要です。", "download.cos.button": "Tencent COS からダウンロード",
      "download.github.title": "海外向けミラー", "download.github.desc": "GitHub Release の正式配布ファイルです。中国本土以外のネットワークにおすすめです。", "download.github.button": "GitHub Release からダウンロード",
      "download.version": "バージョン", "screens.title": "ソフトウェア画面", "screens.lead": "v1.1.0 コントロールセンターの実際の画面プレビューです。",
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
      "release.kicker": "VERSION 1.1.0",
      "release.title": "2 台の連動と、自由なチャンネル設定",
      "release.lead": "V4・Opossum 対応、新しいゲーム内 HUD、わかりやすい接続状況の表示を追加しました。",
      "release.pending": "v1.1.0 のパッケージ作成は完了し、配布先を準備中です。以下は現在 v1.0.5 のダウンロードです。新しい配布先の準備後に更新します。",
      "release.device.title": "Pulse + Opossum",
      "release.device.desc": "V4 は 1 回のスキャンで接続し、各機器を個別に有効化。ランダム段階はゲーム内の実際の強度に連動します。",
      "release.channels.title": "A/B の役割を自由に変更",
      "release.channels.desc": "両方を心拍数、両方をアクション、または役割を交換。BPM 範囲と波形プレビューも確認できます。",
      "release.hud.title": "HUD を好みに合わせて調整",
      "release.hud.desc": "機器・チャンネル・表示内容を選択。サイズ、不透明度、位置を調整でき、ウィンドウ・全画面に対応します。",
      "release.fixes.title": "接続とインポートの修正",
      "release.fixes.desc": "Bluetooth・アクセサリーの案内、短いデータ途絶時のゼロ待機、user9527 の重複パス保護を改善しました。",
      "release.upgrade": "更新時：ゲームを終了し、新版の接続画面でランタイムのインストール／修復を実行してから、ゲームを再起動してください。新しい HUD とテレメトリーが読み込まれます。",
    }
  };

  const params = new URLSearchParams(window.location.search);
  const languages = ["zh", "en", "ja"];
  const htmlLanguages = {zh:"zh-CN", en:"en", ja:"ja"};
  let savedLanguage;
  try { savedLanguage = localStorage.getItem("manaka-site-language"); } catch {}
  let language = languages.includes(params.get("lang")) ? params.get("lang") : languages.includes(savedLanguage) ? savedLanguage : "zh";
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
    const imageLabels = {"果果的 X 头像":["果果的 X 头像","Guoguo's X avatar","Guoguo の X アバター"],"DG-LAB 图标":["DG-LAB 图标","DG-LAB icon","DG-LAB アイコン"],"Manaka 图标":["Manaka 图标","Manaka icon","Manaka アイコン"],"QQ 群二维码":["QQ 群二维码","QQ community QR code","QQ グループの QR コード"],"Reward QR code":["赞赏二维码","Reward QR code","応援用 QR コード"],"Guoguo's X avatar":["果果的 X 头像","Guoguo's X avatar","Guoguo の X アバター"],"NPC Voice Mod gameplay preview":["NPC 语音实机预览","NPC Voice Mod gameplay preview","NPC 音声 Mod の実機プレビュー"],"Dashboard":["实时仪表盘","Dashboard","ダッシュボード"],"Device and game":["设备与游戏","Device and game","デバイスとゲーム"],"Intensity range":["个性化范围","Intensity range","強度範囲"],"Waveform studio":["波形工作台","Waveform studio","波形ワークベンチ"],"Opossum workbench":["负鼠工作台","Opossum workbench","Opossum ワークベンチ"],"Settings":["设置","Settings","設定"],"Save tools":["存档工具","Save tools","セーブツール"],"Mod manager":["Mod 管理器","Mod manager","Mod 管理"],"Workshop":["创意工坊","Workshop","ワークショップ"],"NPC voices":["NPC 语音","NPC voices","NPC 音声"],"Event log":["事件记录","Event log","イベントログ"]};
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
