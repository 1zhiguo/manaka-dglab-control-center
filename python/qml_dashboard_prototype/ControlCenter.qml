import QtQuick
import "components" as UI
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: root
    width: 1320
    height: 840
    minimumWidth: 1120
    minimumHeight: 720
    visible: true
    title: "Manaka / DG-LAB · " + backend.version

    property int pageIndex: initialPageIndex >= 0 ? initialPageIndex : 0
    onPageIndexChanged: backend.setActivePage(pageIndex)
    property bool darkMode: backend.theme !== "light"
    Binding { target:UI.Theme; property:"dark"; value:root.darkMode }
    Binding { target:UI.Theme; property:"language"; value:backend.language }
    property url guidePreviewSource: ""
    property bool pendingWindowClose: false
    onClosing: function(event) {
        if (personalEditor.dirty) {
            event.accepted = false
            pendingWindowClose = true
            personalEditor.requestClose()
        } else if (waveWorkbench.dirty) {
            event.accepted=false
            pendingWindowClose=true
            waveWorkbench.requestClose()
        } else if (gameplaySettings.dirty) {
            event.accepted=false
            pendingWindowClose=true
            gameplaySettings.requestClose()
        }
    }
    BusyIndicator {
        anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 20
        running: backend.fileJobBusy; visible: running; z: 100
    }
    Connections {
        target: backend
        function onFileJobChanged() {
            if (pack9527Wizard.visible && pack9527Wizard.step === 3 && !backend.fileJobBusy)
                pack9527Wizard.step = backend.pack9527Backup.length > 0 ? 4 : 2
        }
    }
    property string npcTextLanguage: backend.npcVoiceLanguage
    property string npcTextState: "ambient"
    property string npcTextProfile: "young_female"
    function reloadNpcTextEditor() {
        npcTextArea.text = backend.loadNpcVoiceText(npcTextLanguage, npcTextState, npcTextProfile)
    }
    function t(source) {
        const languageDependency = backend.language
        return backend.translate(source)
    }
    property var pageTitles: [t("实时仪表盘"), t("设备与游戏"), t("个性化范围"), t("波形工作台"), t("A/B 波形监视"), t("存档工具"), t("Mod 管理器"), t("创意工坊"), t("NPC 语音"), t("事件记录"), t("玩法设置")]
    property var pageSubtitles: [
        t("游戏状态、心率与设备输出总览"),
        t("安装游戏插件并使用 DG-LAB 3.0 扫码"),
        t("设置 A/B 强度与原版范围"),
        t("选择官方预设或创建自定义波形"),
        t("查看两个通道当前选择的波形和实际强度"),
        t("安全修改当前存档的经验值与游戏货币"),
        t("管理你已有的插件、V1 任务与 V2 功能包"),
        t("从原作者页面发现任务、插件与工具"),
        "",
        t("检查连接、安全归零和游戏事件"),
        t("选择玩法并配置通道规则与检测绑定")
    ]

    // DG-LAB inspired palette: ink-black surfaces, warm logo gold and ivory text.
    // Cyan remains the B-channel color so live output stays easy to distinguish.
    readonly property color bg: UI.Theme.background
    readonly property color panel: UI.Theme.surface
    readonly property color panel2: UI.Theme.surfaceRaised
    readonly property color border: UI.Theme.borderDecorative
    readonly property color fg: UI.Theme.textPrimary
    readonly property color muted: UI.Theme.textSecondary
    readonly property color track: UI.Theme.borderControl
    readonly property color accent: UI.Theme.primaryFill
    readonly property color violet: UI.Theme.primaryFill
    readonly property color cyan: UI.Theme.info
    readonly property color green: UI.Theme.success
    readonly property color amber: UI.Theme.warning
    readonly property color red: UI.Theme.danger

    font.family: UI.Theme.fontFamily
    font.pixelSize: UI.Theme.bodySize
    readonly property int controlRadius: UI.Theme.controlRadius
    readonly property int cardRadius: UI.Theme.cardRadius

    color: bg
    palette.window: bg
    palette.windowText: fg
    palette.base: panel
    palette.alternateBase: panel2
    palette.text: fg
    palette.button: panel2
    palette.buttonText: fg
    palette.highlight: accent
    palette.highlightedText:UI.Theme.onPrimary
    Behavior on color { ColorAnimation { duration: UI.Theme.motionDuration } }

    component AppCard: Rectangle {
        default property alias contents: cardContent.data
        radius: root.cardRadius
        color: panel
        border.color: root.border
        border.width: 1
        clip: true
        Behavior on color { ColorAnimation { duration: UI.Theme.motionDuration } }
        Behavior on border.color { ColorAnimation { duration: UI.Theme.motionDuration } }

        Item { id: cardContent; anchors.fill: parent }
    }

    component AppButton: UI.Button { }

    component AppTextField: UI.TextField { }

    component AppComboBox: UI.ComboBox { }

    component NavItem: Button {
        id: nav
        required property int targetPage
        property string iconName: "dashboard"
        property string label: ""
        text: label
        objectName: "navItem" + targetPage
        Layout.fillWidth: true
        Layout.preferredHeight: root.height < 780 ? 36 : 42
        leftPadding: 12; rightPadding: 10
        hoverEnabled: true
        onClicked: root.pageIndex = targetPage
        background: Rectangle {
            radius: root.controlRadius
            color: root.pageIndex === nav.targetPage ? Qt.rgba(accent.r, accent.g, accent.b, darkMode ? 0.14 : 0.11) : nav.hovered ? panel2 : "transparent"
            border.color: nav.visualFocus ? accent : root.pageIndex === nav.targetPage ? Qt.rgba(accent.r, accent.g, accent.b, 0.30) : "transparent"
        }
        contentItem: RowLayout {
            spacing: 10
            Image {
                Layout.preferredWidth:20; Layout.preferredHeight:20
                source:"icons/"+nav.iconName+(root.darkMode ? "-dark" : "-light")+".svg"
                sourceSize:Qt.size(20,20); fillMode:Image.PreserveAspectFit
            }
            Text {
                objectName: "navLabel" + nav.targetPage
                Layout.fillWidth: true; Layout.fillHeight: true
                text: nav.label; color: root.pageIndex === nav.targetPage ? root.fg : muted
                font.family: UI.Theme.fontFamily; font.pixelSize: UI.Theme.bodySize
                font.weight: root.pageIndex === nav.targetPage ? Font.DemiBold : Font.Normal
                verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
            }
        }
        ToolTip.visible: hovered
        ToolTip.text: label
        ToolTip.delay: 700
    }

    component MetricBar: Item {
        id: metric
        property string label: "指标"
        property string valueText: "0"
        property real value: 0
        property real maximum: 100
        property color barColor: accent
        implicitHeight: 60
        Text { anchors.left: parent.left; anchors.right: metricValue.left; anchors.rightMargin: 10; anchors.top: parent.top; text: metric.label; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; elide: Text.ElideRight; ToolTip.visible: metricHover.hovered && truncated; ToolTip.text: text; HoverHandler { id: metricHover } }
        Text { id: metricValue; anchors.right: parent.right; anchors.top: parent.top; text: metric.valueText; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold }
        Rectangle {
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            height: 8; radius: 4; color: track
            Rectangle {
                height: parent.height; radius: 4; color: metric.barColor
                width: Math.max(metric.value <= 0 ? 0 : 6, parent.width * Math.max(0, Math.min(metric.maximum, metric.value)) / metric.maximum)
            }
        }
    }

    component WaveView: Canvas {
        id: wave
        property var points: []
        property color waveColor: accent
        property bool animated: true
        function effectivelyVisible() {
            if (!root.visible || root.visibility === Window.Minimized)
                return false
            let item = wave
            while (item) {
                if (!item.visible || item.opacity <= 0)
                    return false
                item = item.parent
            }
            return width > 0 && height > 0
        }
        antialiasing: true
        clip: true
        onPointsChanged: requestPaint()
        onWaveColorChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections {
            target: root
            function onDarkModeChanged() { wave.requestPaint() }
        }
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const w = width, h = height
            ctx.strokeStyle = UI.Theme.borderDecorative
            ctx.lineWidth = 1
            for (let i = 1; i < 4; i++) { const y = h * i / 4; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke() }
            if (!points || points.length < 2) return
            ctx.strokeStyle = waveColor
            ctx.lineWidth = 3
            ctx.lineCap = "round"
            ctx.lineJoin = "round"
            ctx.beginPath()
            const cycles = Math.max(2, Math.ceil(48 / points.length))
            const total = points.length * cycles
            for (let i = 0; i < total; i++) {
                const sample = points[i % points.length] / 100
                const x = i / (total - 1) * w
                const y = h * 0.82 - sample * h * 0.64
                if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
            }
            ctx.stroke()
        }
        Rectangle {
            id: playhead
            property real phase: 0
            visible: wave.animated && wave.effectivelyVisible() && wave.points && wave.points.length >= 2
            width: 2
            height: wave.height
            color: Qt.rgba(wave.waveColor.r, wave.waveColor.g, wave.waveColor.b, 0.58)
            x: phase * Math.max(0, wave.width - width)
            Timer { interval: 33; repeat: true; running: playhead.visible; onTriggered: playhead.phase=(playhead.phase+0.006)%1 }
        }
    }

    component SectionTitle: Item {
        id:sectionTitle
        property string title:"标题"
        property string detail:""
        readonly property bool stacked:width<260 && detail.length>0
        Layout.fillWidth:true; Layout.minimumWidth:0
        implicitHeight:stacked ? 44 : 26
        Text { id:sectionDetail; anchors.right:parent.right; anchors.bottom:parent.bottom; height:sectionTitle.stacked ? 18 : parent.height; verticalAlignment:Text.AlignVCenter; width:Math.min(implicitWidth,parent.width*0.48); text:sectionTitle.detail; color:root.muted; font.family:UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize; elide:Text.ElideRight; ToolTip.visible:sectionHover.hovered && truncated; ToolTip.text:text; HoverHandler { id:sectionHover } }
        Text { anchors.left:parent.left; anchors.right:parent.right; anchors.rightMargin:sectionTitle.stacked ? 0 : sectionDetail.width+12; anchors.top:parent.top; height:26; verticalAlignment:Text.AlignVCenter; text:sectionTitle.title; color:root.fg; font.family:UI.Theme.fontFamily; font.pixelSize:UI.Theme.headingSize; font.weight:Font.DemiBold; elide:Text.ElideRight }
    }

    component TutorialLine: Rectangle {
        id: tutorialLine
        property string numberText: "1"
        property string title: ""
        property string detail: ""
        Layout.fillWidth: true
        Layout.preferredHeight: 72
        radius: root.controlRadius
        color: panel2
        border.color: root.border
        RowLayout {
            anchors.fill: parent; anchors.margins: 13; spacing: 13
            Rectangle {
                Layout.preferredWidth: 38; Layout.preferredHeight: 38; radius: root.controlRadius
                color: Qt.rgba(accent.r, accent.g, accent.b, darkMode ? 0.18 : 0.14)
                Text { anchors.centerIn: parent; text: tutorialLine.numberText; color: accent; font.family: "Segoe UI"; font.pixelSize: 15; font.weight: Font.Bold }
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                Text { Layout.fillWidth: true; text: tutorialLine.title; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: UI.Theme.bodySize; font.weight: Font.DemiBold; elide: Text.ElideRight }
                Text { Layout.fillWidth: true; text: tutorialLine.detail; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: UI.Theme.background
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: backend.language === "en" ? 236 : 224
            Layout.fillHeight: true
            color: UI.Theme.surfaceRaised
            border.color: root.border
            Behavior on color { ColorAnimation { duration: UI.Theme.motionDuration } }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 8
                Row {
                    Layout.fillWidth: true; Layout.bottomMargin: 22; spacing: 10
                    Rectangle {
                        width: 40; height: 40; radius: root.controlRadius; color: panel2; clip: true
                        Image { anchors.fill: parent; source: "assets/app_icon.png"; fillMode: Image.PreserveAspectCrop; smooth: true; mipmap: true }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        Text { text: "MANAKA"; color: root.fg; font.family: "Segoe UI"; font.pixelSize: 15; font.weight: Font.Bold; font.letterSpacing: 1.4 }
                        Text { text: "DG-LAB CONTROL"; color: muted; font.pixelSize: 10; font.letterSpacing: 1.1 }
                    }
                }
                Text { Layout.leftMargin: 7; Layout.bottomMargin: 4; text: root.t("控制中心"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.letterSpacing: 1.3 }
                NavItem { targetPage: 0; iconName: "dashboard"; label: root.t("实时仪表盘") }
                NavItem { targetPage: 1; iconName: "connection"; label: root.t("设备与游戏") }
                NavItem { targetPage: 2; iconName: "strength"; label: root.t("个性化范围") }
                NavItem { targetPage: 10; iconName: "gameplay"; label: root.t("玩法设置") }
                NavItem { targetPage: 3; iconName: "waveform"; label: root.t("波形工作台") }
                NavItem { targetPage: 4; iconName: "monitor"; label: root.t("A/B 波形监视") }
                NavItem { targetPage: 5; iconName: "save"; label: root.t("存档工具") }
                NavItem { targetPage: 6; iconName: "mods"; label: root.t("Mod 管理器") }
                NavItem { targetPage: 7; iconName: "workshop"; label: root.t("创意工坊") }
                NavItem { targetPage: 8; iconName: "voice"; label: root.t("NPC 语音") }
                NavItem { targetPage: 9; iconName: "events"; label: root.t("事件记录") }
                Item { Layout.fillHeight: true }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 98; radius: root.cardRadius
                    color: Qt.rgba((backend.telemetryOnline ? green : amber).r, (backend.telemetryOnline ? green : amber).g, (backend.telemetryOnline ? green : amber).b, darkMode ? 0.08 : 0.09)
                    border.color: Qt.rgba((backend.telemetryOnline ? green : amber).r, (backend.telemetryOnline ? green : amber).g, (backend.telemetryOnline ? green : amber).b, 0.24)
                    Column {
                        anchors.fill: parent; anchors.margins: 14; spacing: 6
                        Row { spacing: 7; Rectangle { width: 8; height: 8; radius: 4; color: backend.telemetryOnline ? green : amber; anchors.verticalCenter: parent.verticalCenter } Text { text: backend.telemetryStatus; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold } }
                        Text { width: parent.width; wrapMode: Text.Wrap; text: backend.demoMode ? root.t("演示数据 · 无设备输出") : "10 Hz · Local UDP"; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: backend.version; color: muted; font.pixelSize:UI.Theme.captionSize }
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true; Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent; anchors.leftMargin: 24; anchors.rightMargin: 24; anchors.topMargin: 20; anchors.bottomMargin: 22; spacing: 15
                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: 58
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 3
                        Text { Layout.fillWidth: true; text: pageTitles[pageIndex]; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: UI.Theme.titleSize; font.weight: Font.DemiBold; elide: Text.ElideRight }
                        Text { Layout.fillWidth: true; text: pageSubtitles[pageIndex]; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                    }
                    UI.Switch {
                        objectName:"hudToggle"; text:"HUD"; Layout.preferredWidth:94
                        checked:backend.gameHudEnabled
                        onClicked:backend.setGameHudEnabled(checked)
                    }
                    AppButton {
                        Layout.leftMargin: 5
                        Layout.preferredWidth: 106
                        label: root.t("新手教程")
                        onClicked: onboardingDialog.openFromStart()
                    }
                    Rectangle {
                        Layout.preferredWidth: 158; Layout.preferredHeight: 38; radius: root.controlRadius
                        color: Qt.rgba((backend.deviceConnected ? green : amber).r, (backend.deviceConnected ? green : amber).g, (backend.deviceConnected ? green : amber).b, darkMode ? 0.10 : 0.09)
                        border.color: Qt.rgba((backend.deviceConnected ? green : amber).r, (backend.deviceConnected ? green : amber).g, (backend.deviceConnected ? green : amber).b, 0.26)
                        Row { anchors.centerIn: parent; spacing: 7; Rectangle { width: 8; height: 8; radius: 4; color: backend.deviceConnected ? green : amber; anchors.verticalCenter: parent.verticalCenter } Text { text: backend.deviceConnected ? root.t("DG-LAB 已连接") : root.t("等待设备连接"); color: backend.deviceConnected ? green : amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold } }
                    }
                    AppButton { Layout.leftMargin: 8; Layout.preferredWidth: 76; label: backend.language === "zh" ? "EN" : "中文"; onClicked: backend.setLanguage(backend.language === "zh" ? "en" : "zh") }
                    AppButton { objectName:"themeToggle"; Layout.preferredWidth:108; label:root.darkMode ? UI.Theme.t("日间模式","Light mode") : UI.Theme.t("夜间模式","Dark mode"); onClicked:backend.setTheme(root.darkMode ? "light" : "dark") }
                }

                StackLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    currentIndex: root.pageIndex

                    // Dashboard -------------------------------------------------
                    GridLayout {
                        columns: 12; rows: 12; columnSpacing: 15; rowSpacing: 15
                        AppCard {
                            Layout.columnSpan: 4; Layout.rowSpan: 7; Layout.fillWidth: true; Layout.fillHeight: true
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 22; spacing: 8
                                SectionTitle { title: root.t("游戏心率"); detail: backend.telemetryOnline ? "LIVE" : "WAITING" }
                                Item {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    Canvas {
                                        id: gauge
                                        width: Math.min(parent.width, parent.height) * 0.80; height: width; anchors.centerIn: parent; antialiasing: true
                                        onPaint: {
                                            const ctx = getContext("2d"); ctx.reset(); const cx=width/2, cy=height/2, r=width*0.38, start=Math.PI*0.72, sweep=Math.PI*1.56
                                            ctx.lineCap="round"; ctx.lineWidth=width*0.055; ctx.strokeStyle=track; ctx.beginPath(); ctx.arc(cx,cy,r,start,start+sweep); ctx.stroke()
                                            const ratio=Math.max(0,Math.min(1,(backend.heartRate-60)/120)); const grad=ctx.createLinearGradient(0,height,width,0); grad.addColorStop(0,violet); grad.addColorStop(1,accent)
                                            ctx.strokeStyle=grad; ctx.beginPath(); ctx.arc(cx,cy,r,start,start+sweep*ratio); ctx.stroke()
                                        }
                                        Connections { target: backend; function onVitalsChanged(){ if(root.pageIndex===0) gauge.requestPaint() } }
                                        Connections { target: root; function onDarkModeChanged(){ gauge.requestPaint() } }
                                    }
                                    Column { anchors.centerIn: parent; spacing: -4; Text { anchors.horizontalCenter: parent.horizontalCenter; text: Math.round(backend.heartRate); color: root.fg; font.family: "Segoe UI Variable Display"; font.pixelSize: 56; font.weight: Font.Bold } Text { anchors.horizontalCenter: parent.horizontalCenter; text: "BPM"; color: accent; font.pixelSize: 12; font.weight: Font.Bold; font.letterSpacing: 2.2 } }
                                }
                                Text { text: backend.stage + "  ·  " + backend.actionDisplay; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; Layout.alignment: Qt.AlignHCenter }
                            }
                        }
                        AppCard {
                            Layout.columnSpan: 5; Layout.rowSpan: 7; Layout.fillWidth: true; Layout.fillHeight: true
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 22; spacing: 8
                                SectionTitle { title: root.t("输出通道"); detail: root.t("安全上限 ") + "A " + backend.channelCapA + " / B " + backend.channelCapB }
                                Text { text: backend.deviceStatus; color: backend.safetyIdle || backend.outputPaused ? amber : muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                                MetricBar { Layout.fillWidth: true; label: backend.channelALabel; valueText: backend.outputA.toFixed(1) + " / " + backend.channelCapA; value: backend.outputA; maximum: Math.max(1,backend.channelCapA); barColor: accent }
                                MetricBar { Layout.fillWidth: true; label: backend.channelBLabel; valueText: backend.outputB.toFixed(1) + " / " + backend.channelCapB; value: backend.outputB; maximum: Math.max(1,backend.channelCapB); barColor: violet }
                                Item { Layout.fillHeight: true }
                                Rectangle {
                                    Layout.fillWidth: true; Layout.preferredHeight: 68; radius: root.controlRadius; color: panel2
                                    RowLayout { anchors.fill: parent; anchors.margins: 13; ColumnLayout { Layout.fillWidth: true; Layout.minimumWidth: 0; Text { Layout.fillWidth: true; text: root.t("当前波形"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize } Text { Layout.fillWidth: true; elide: Text.ElideRight; text: backend.waveAName; color: cyan; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold } } Text { text: backend.waveMode === "smart" ? root.t("智能策略") : root.t("固定预设"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12 } }
                                }
                            }
                        }
                        AppCard {
                            Layout.columnSpan: 3; Layout.rowSpan: 7; Layout.fillWidth: true; Layout.fillHeight: true
                            color: backend.outputPaused ? Qt.rgba(amber.r,amber.g,amber.b,darkMode?0.08:0.10) : panel
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 21; spacing: 9
                                Text { text: root.t("会话控制"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 15; font.weight: Font.DemiBold }
                                Text { Layout.fillWidth: true; wrapMode: Text.Wrap; text: backend.outputPaused ? root.t("输出已经归零\n设备连接保持不变") : root.t("随时暂停 A/B 输出\n再次点击即可继续"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.45 }
                                Item { Layout.fillHeight: true }
                                UI.Button {
                                    id:pauseControl; objectName:"pauseOutput"
                                    Layout.alignment:Qt.AlignHCenter; Layout.preferredWidth:116; Layout.preferredHeight:116
                                    text:backend.outputPaused ? root.t("继续输出") : root.t("暂停输出")
                                    scale: hovered ? 1.04 : 1
                                    Behavior on scale { NumberAnimation { duration: UI.Theme.motionDuration; easing.type: Easing.OutCubic } }
                                    background:Rectangle { radius:58; color:backend.deviceConnected || backend.outputPaused ? UI.Theme.primaryFill : root.panel2; border.color:pauseControl.visualFocus ? UI.Theme.accent : UI.Theme.borderControl; border.width:pauseControl.visualFocus ? 3 : 1 }
                                    contentItem:Item {
                                        Column { anchors.centerIn:parent; spacing:4
                                            Text { anchors.horizontalCenter:parent.horizontalCenter; text:backend.outputPaused ? "▶" : "Ⅱ"; color:backend.deviceConnected || backend.outputPaused ? UI.Theme.onPrimary : root.muted; font.pixelSize:30; font.weight:Font.Bold }
                                            Text { anchors.horizontalCenter:parent.horizontalCenter; text:pauseControl.text; color:backend.deviceConnected || backend.outputPaused ? UI.Theme.onPrimary : root.muted; font.family:UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize; font.weight:Font.DemiBold }
                                        }
                                    }
                                    onClicked:backend.toggleOutput()
                                }
                                Item { Layout.fillHeight: true }
                                Text { Layout.alignment: Qt.AlignHCenter; text: backend.outputPaused ? "PAUSED" : backend.safetyIdle ? "SAFETY IDLE" : "OUTPUT ACTIVE"; color: backend.outputPaused || backend.safetyIdle ? amber : green; font.pixelSize: 12; font.weight: Font.Bold; font.letterSpacing: 1.4 }
                            }
                        }
                        AppCard {
                            Layout.columnSpan: 8; Layout.rowSpan: 5; Layout.fillWidth: true; Layout.fillHeight: true
                            ColumnLayout { anchors.fill: parent; anchors.margins: 20; spacing: 7; SectionTitle { title: root.t("实时波形"); detail: root.t("A 通道 · ") + backend.waveAName } WaveView { Layout.fillWidth: true; Layout.fillHeight: true; points: backend.waveAPoints; waveColor: accent; animated: !backend.outputPaused } }
                        }
                        AppCard {
                            Layout.columnSpan: 4; Layout.rowSpan: 5; Layout.fillWidth: true; Layout.fillHeight: true
                            ColumnLayout { anchors.fill: parent; anchors.margins: 20; spacing: 8; SectionTitle { title: root.t("场景状态"); detail: backend.stage } MetricBar { Layout.fillWidth: true; label: root.t("NPC 警觉度"); valueText: Math.round(backend.alertLevel)+"%"; value: backend.alertLevel; barColor: amber } MetricBar { Layout.fillWidth: true; label: root.t("兴奋度"); valueText: Math.round(backend.excitement)+"%"; value: backend.excitement; barColor: violet } Item { Layout.fillHeight: true } Text { text: root.t("当前动作    ") + backend.actionDisplay; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 } }
                        }
                    }

                    // Device and game ------------------------------------------
                    ScrollView {
                        clip: true
                        contentWidth: availableWidth
                        ColumnLayout {
                            width: parent.width; spacing: 15
                            RowLayout {
                                Layout.fillWidth: true; Layout.preferredHeight: 360; spacing: 15
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 22; spacing: 12
                                        SectionTitle { title: root.t("游戏插件"); detail: root.t("自动部署") }
                                        Text { text: root.t("请选择能直接看到 SecretFlasherManaka.exe 的文件夹。\n不要选择 BepInEx、plugins 或游戏 Data 文件夹。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        AppTextField { Layout.fillWidth: true; text: backend.gameFolder; color: root.fg; font.family: UI.Theme.fontFamily; selectByMouse: true; placeholderText: root.t("游戏根目录");  onEditingFinished: backend.setGameFolder(text) }
                                        Text { text: backend.gameStatus; color: backend.gameStatus.indexOf("就绪") >= 0 ? green : amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        RowLayout { Layout.fillWidth: true; AppButton { label: root.t("选择目录"); onClicked: folderDialog.open() } AppButton { label: root.t("安装 / 修复运行环境"); onClicked: backend.installPluginAsync(false) } }
                                        AppButton { Layout.fillWidth: true; Layout.preferredHeight: 48; label: root.t("一键安装并启动游戏"); fillColor: accent; labelColor: "#11151C"; onClicked: backend.installPluginAsync(true) }
                                        Item { Layout.fillHeight: true }
                                        Text { text: root.t("正式支持游戏 v1.1.1 / v1.1.2 / v1.1.3；纯原版无需预装 BepInEx，控制中心会自动配置对应运行库。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                    }
                                }
                                AppCard {
                                    Layout.preferredWidth: 400; Layout.fillHeight: true
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: 22; spacing: 18
                                        ColumnLayout { Layout.fillWidth: true; Text { text: "DG-LAB Socket"; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 16; font.weight: Font.DemiBold } Text { text: backend.deviceStatus; color: backend.deviceConnected ? green : amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true } Item { Layout.fillHeight: true } Text { text: backend.lanAddress; color: muted; font.pixelSize: 12 } AppButton { visible: !backend.deviceConnected; Layout.preferredWidth: 136; label: root.t("连接不上？"); fillColor: Qt.rgba(amber.r,amber.g,amber.b,darkMode?0.18:0.12); labelColor: amber; onClicked: networkHelpDialog.open() } }
                                        Rectangle { Layout.preferredWidth: 210; Layout.preferredHeight: 210; radius: root.controlRadius; color: "white"; Image { objectName: "connectionQr"; anchors.fill: parent; anchors.margins: 8; source: backend.qrSource; fillMode: Image.PreserveAspectFit; visible: source !== "" } Text { anchors.centerIn: parent; visible: backend.qrSource === ""; width: parent.width - 20; wrapMode: Text.Wrap; text: backend.connectionHint; horizontalAlignment: Text.AlignHCenter; color: "#4B5565"; font.family: UI.Theme.fontFamily; font.pixelSize: 12 } }
                                    }
                                }
                            }
                            AppCard {
                                Layout.fillWidth: true; Layout.preferredHeight: 300
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 20; spacing: 12
                                    SectionTitle { title: "DG-LAB 3.0 " + root.t("连接向导"); detail: root.t("依次完成四步") }
                                    RowLayout {
                                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                                        Repeater {
                                            model: backend.guideSources
                                             delegate: Rectangle {
                                                required property var modelData
                                                required property int index
                                                 id: guideThumb
                                                Layout.fillWidth: true; Layout.fillHeight: true; radius: root.controlRadius; color: panel2; border.color: root.border
                                                 clip: true
                                                 Image {
                                                     anchors.fill: parent; anchors.margins: 8; source: modelData
                                                     fillMode: Image.PreserveAspectFit; asynchronous: true; smooth: true; mipmap: true
                                                     scale: guideHit.containsMouse ? 1.025 : 1.0
                                                     Behavior on scale { NumberAnimation { duration: UI.Theme.motionDuration; easing.type: Easing.OutCubic } }
                                                 }
                                                Rectangle { anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 8; width: 26; height: 26; radius: root.controlRadius; color: accent; Text { anchors.centerIn: parent; text: index+1; color: "#11151C"; font.weight: Font.Bold } }
                                                 Rectangle {
                                                     anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 10
                                                     width: 30; height: 30; radius: root.controlRadius
                                                     color: Qt.rgba(0.03, 0.05, 0.09, guideHit.containsMouse ? 0.82 : 0.58)
                                                     Text { anchors.centerIn: parent; text: "↗"; color: "white"; font.pixelSize: 15; font.weight: Font.Bold }
                                                 }
                                                 MouseArea {
                                                     id: guideHit; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                                     onClicked: { root.guidePreviewSource = modelData; guidePreviewDialog.open() }
                                                 }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // One draft and one save action for both generations of settings.
                    AppCard {
                        ChannelSettingsEditor {
                            id: personalEditor
                            anchors.fill: parent; anchors.margins: 18
                            controller: backend
                            onCloseCancelled: root.pendingWindowClose = false
                            onCloseRequested: {
                                const closeWindow = root.pendingWindowClose
                                root.pendingWindowClose = false
                                if (closeWindow) root.close()
                                else root.pageIndex = 0
                            }
                        }
                    }

                    // Wave library and local animated preview.
                    AppCard {
                        WaveWorkbench {
                            id: waveWorkbench
                            anchors.fill: parent; anchors.margins:18
                            controller: backend
                            onCloseCancelled: root.pendingWindowClose=false
                            onCloseRequested: {
                                const closeWindow=root.pendingWindowClose
                                root.pendingWindowClose=false
                                if(closeWindow) root.close()
                                else root.pageIndex=0
                            }
                        }
                    }

                    // A/B monitor ----------------------------------------------
                    RowLayout {
                        spacing: 15
                        Repeater {
                            model: ["A", "B"]
                            delegate: AppCard {
                                required property string modelData
                                property var channelView: ({channel:modelData,name:modelData === "A" ? backend.waveAName : backend.waveBName,points:modelData === "A" ? backend.waveAPoints : backend.waveBPoints,strength:modelData === "A" ? backend.outputA : backend.outputB,color:modelData === "A" ? accent : violet,detail:(modelData === "A" ? backend.channelALabel : backend.channelBLabel)+" · "+backend.waveRuleReasons[modelData],cap:modelData === "A" ? backend.channelCapA : backend.channelCapB})
                                Layout.fillWidth: true; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 24; spacing: 12
                                    RowLayout { Layout.fillWidth: true; Rectangle { width: 44; height: 44; radius: root.controlRadius; color: Qt.rgba(channelView.color.r,channelView.color.g,channelView.color.b,0.14); Text { anchors.centerIn: parent; text: channelView.channel; color: channelView.color; font.pixelSize: 18; font.weight: Font.Bold } } ColumnLayout { Layout.fillWidth: true; Layout.minimumWidth: 0; Text { Layout.fillWidth: true; text: channelView.channel+root.t(" 通道"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 16; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; elide: Text.ElideRight; text: channelView.detail; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 } } Text { text: channelView.strength.toFixed(1)+" / "+channelView.cap; color: channelView.color; font.pixelSize: UI.Theme.bodySize; font.weight: Font.Bold } }
                                    WaveView { Layout.fillWidth: true; Layout.fillHeight: true; points: channelView.points; waveColor: channelView.color; animated: !backend.outputPaused }
                                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 76; radius: root.controlRadius; color: panel2; RowLayout { anchors.fill: parent; anchors.margins: 14; ColumnLayout { Layout.fillWidth: true; Layout.minimumWidth: 0; Text { Layout.fillWidth: true; text: root.t("当前选择"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize } Text { Layout.fillWidth: true; elide: Text.ElideRight; text: channelView.name; color: channelView.color; font.family: UI.Theme.fontFamily; font.pixelSize: UI.Theme.bodySize; font.weight: Font.DemiBold } } Text { text: backend.outputPaused ? root.t("已暂停") : backend.safetyIdle ? root.t("安全待机") : root.t("实时输出"); color: backend.outputPaused || backend.safetyIdle ? amber : green; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold } } }
                                }
                            }
                        }
                    }

                    // Progress / save editor ----------------------------------
                    Item {
                        id: progressPage
                        property string draftRp: Math.round(backend.currentRp).toString()
                        property string draftExp: backend.exposeExp.toString()
                        function readCurrent() {
                            draftRp = Math.round(backend.currentRp).toString()
                            draftExp = backend.exposeExp.toString()
                        }
                        RowLayout {
                            anchors.fill: parent; spacing: 15
                            AppCard {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 24; spacing: 14
                                    SectionTitle { title: root.t("当前存档数值"); detail: backend.currentSaveSlot >= 0 ? root.t("手动槽位 ") + (backend.currentSaveSlot + 1) : root.t("未载入槽位") }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.preferredHeight: 92; radius: root.controlRadius
                                        color: panel2; border.color: root.border
                                        RowLayout {
                                            anchors.fill: parent; anchors.margins: 18
                                            Column { Layout.fillWidth: true; spacing: 5; Text { text: root.t("游戏货币 / RP"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 } Text { text: Math.round(backend.currentRp).toLocaleString(Qt.locale(backend.language === "zh" ? "zh_CN" : "en_US"), "f", 0); color: amber; font.family: "Segoe UI"; font.pixelSize: 25; font.weight: Font.Bold } }
                                            Column { Layout.fillWidth: true; spacing: 5; Text { text: root.t("经验值 / EXP"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 } Text { text: backend.exposeExp.toLocaleString(Qt.locale(backend.language === "zh" ? "zh_CN" : "en_US"), "f", 0); color: cyan; font.family: "Segoe UI"; font.pixelSize: 25; font.weight: Font.Bold } }
                                        }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.preferredHeight: 64; radius: root.controlRadius
                                        color: Qt.rgba((backend.canEditProgress ? green : amber).r, (backend.canEditProgress ? green : amber).g, (backend.canEditProgress ? green : amber).b, darkMode ? 0.08 : 0.10)
                                        border.color: Qt.rgba((backend.canEditProgress ? green : amber).r, (backend.canEditProgress ? green : amber).g, (backend.canEditProgress ? green : amber).b, 0.28)
                                        RowLayout { anchors.fill: parent; anchors.margins: 14; Rectangle { width: 9; height: 9; radius: 5; color: backend.canEditProgress ? green : amber } Column { Layout.fillWidth: true; Text { text: backend.canEditProgress ? root.t("可以安全写入") : root.t("写入暂时锁定"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold } Text { text: backend.progressEditorStatus; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; elide: Text.ElideRight; width: parent.width } } }
                                    }
                                    Text { Layout.fillWidth: true; text: root.t("为了避免游戏同时写入造成冲突，请先载入目标存档，再按 Esc 打开游戏菜单。每次修改前都会自动复制原始 .sd 文件。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap; lineHeight: 1.35 }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: border }
                                    Text { text: root.t("备份位置"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                                    Text { Layout.fillWidth: true; text: backend.saveBackupFolder; color: root.fg; font.family: "Cascadia Mono"; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
                                    Item { Layout.fillHeight: true }
                                    RowLayout { Layout.fillWidth: true; AppButton { label: root.t("刷新当前数值"); onClicked: progressPage.readCurrent() } AppButton { label: root.t("立即备份"); onClicked: backend.createSaveBackup() } Item { Layout.fillWidth: true } }
                                }
                            }
                            AppCard {
                                Layout.preferredWidth: 420; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 24; spacing: 13
                                    SectionTitle { title: root.t("修改并保存"); detail: "0–999999999" }
                                    Text { text: root.t("游戏货币 / RP"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                                    AppTextField {
                                        Layout.fillWidth: true; Layout.preferredHeight: 50
                                        text: progressPage.draftRp; selectByMouse: true
                                        color: root.fg; font.family: "Segoe UI"; font.pixelSize: 16
                                        validator: DoubleValidator { bottom: 0; top: 999999999; decimals: 2 }

                                        onTextEdited: progressPage.draftRp = text
                                    }
                                    Text { text: root.t("经验值 / EXP"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                                    AppTextField {
                                        Layout.fillWidth: true; Layout.preferredHeight: 50
                                        text: progressPage.draftExp; selectByMouse: true
                                        color: root.fg; font.family: "Segoe UI"; font.pixelSize: 16
                                        validator: IntValidator { bottom: 0; top: 999999999 }

                                        onTextEdited: progressPage.draftExp = text
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.preferredHeight: 132; radius: root.controlRadius
                                        color: UI.Theme.surfaceRaised; border.color: Qt.rgba(amber.r, amber.g, amber.b, 0.35)
                                        Column { anchors.fill: parent; anchors.margins: 14; spacing: 6; Text { text: root.t("写入与升级条件"); color: amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold } Text { width: parent.width; text: root.t("① 角色位于室外（非室内）并已载入目标存档\n② 按 Esc 暂停游戏\n③ 使用最新版游戏插件\n经验写入后：完成任意任务，再回家触发结算才会升级。"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.35; wrapMode: Text.Wrap } }
                                    }
                                    Item { Layout.fillHeight: true }
                                    AppButton { Layout.fillWidth: true; Layout.preferredHeight: 52; label: root.t("备份、写入并保存"); primary:true; onClicked: progressConfirm.open() }
                                    Text { Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; text: root.t("不会修改技能等级、解锁项目或任务进度"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize }
                                }
                            }
                        }
                    }

                    // Mod manager ---------------------------------------------
                    Item {
                        id: modPage
                        property string section: "all"
                        property string filterCategory: "all"
                        property string searchText: ""
                        property string loadedFilterCategory: "all"
                        property string loadedSearchText: ""
                        property string sourceSearch: ""
                        property string sourceCategory: "all"
                        property var filteredSources: {
                            let result = []
                            let query = sourceSearch.trim().toLowerCase()
                            let source = backend.modSourceLinks
                            for (let i = 0; i < source.length; ++i) {
                                let item = source[i]
                                if (sourceCategory !== "all" && item.category !== sourceCategory) continue
                                if (query.length && item.searchText.indexOf(query) < 0) continue
                                result.push(item)
                            }
                            return result
                        }
                        property var filteredInventory: {
                            let result = []
                            let query = searchText.trim().toLowerCase()
                            let source = backend.modInventory
                            for (let i = 0; i < source.length; ++i) {
                                let item = source[i]
                                if (filterCategory !== "all" && item.category !== filterCategory) continue
                                let haystack = (item.name + " " + item.description + " " + item.warning + " " + item.categoryLabel + " " + item.locationArea + " " + item.location + " " + item.locationNote).toLowerCase()
                                if (query.length && haystack.indexOf(query) < 0) continue
                                result.push(item)
                            }
                            return result
                        }
                        property var filteredLoadedInventory: {
                            let result = []
                            let query = loadedSearchText.trim().toLowerCase()
                            let source = backend.loadedModInventory
                            for (let i = 0; i < source.length; ++i) {
                                let item = source[i]
                                if (loadedFilterCategory !== "all" && item.category !== loadedFilterCategory) continue
                                let haystack = (item.name + " " + item.description + " " + item.warning + " " + item.categoryLabel + " " + item.classificationKey).toLowerCase()
                                if (query.length && haystack.indexOf(query) < 0) continue
                                result.push(item)
                            }
                            return result
                        }
                        ColumnLayout {
                            anchors.fill: parent; spacing: 14
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: false
                                Layout.minimumHeight: 166
                                Layout.preferredHeight: 166
                                Layout.maximumHeight: 166
                                spacing: 14
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 17; spacing: 9
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Rectangle { width: 42; height: 42; radius: root.controlRadius; color: Qt.rgba(violet.r,violet.g,violet.b,0.14); Text { anchors.centerIn: parent; text: "⬡"; color: violet; font.pixelSize: 20; font.weight: Font.Bold } }
                                            Column { Layout.fillWidth: true; spacing: 3; Text { text: root.t("本地 Mod 扫描"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: backend.modSummary; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize } }
                                            Rectangle { width: 9; height: 9; radius: 5; color: backend.modStatus.indexOf("完成") >= 0 ? green : amber }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 44; radius: root.controlRadius; color: panel2; border.color: root.border
                                            RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; Text { text: root.t("游戏目录"); color: violet; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; text: backend.gameFolder || root.t("尚未选择游戏目录"); color: root.fg; font.family: "Cascadia Mono"; font.pixelSize: 12; elide: Text.ElideMiddle } }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 7
                                            Text { Layout.fillWidth: true; text: root.t("这里只显示并管理当前游戏目录中的内容"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                                            AppButton { Layout.preferredWidth: 150; label: root.t("重新扫描"); fillColor: violet; labelColor: "#11151C"; onClicked: backend.scanModsAsync() }
                                        }
                                        Text { Layout.fillWidth: true; text: root.t("⚠ 修改开关前必须完全退出游戏"); color: amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; horizontalAlignment: Text.AlignRight }
                                    }
                                }
                                AppCard {
                                    Layout.preferredWidth: 430; Layout.fillHeight: true
                                    color: UI.Theme.surfaceRaised
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 17; spacing: 8
                                        RowLayout { Layout.fillWidth: true; Rectangle { width: 42; height: 42; radius: root.controlRadius; color: Qt.rgba(cyan.r,cyan.g,cyan.b,0.13); Text { anchors.centerIn: parent; text: "＋"; color: cyan; font.pixelSize: 22; font.weight: Font.Bold } } Column { Layout.fillWidth: true; Text { text: root.t("Drop-in 收件箱"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: "DLL / V1 JSON / V2 folders / ZIP"; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize } } }
                                        Text { Layout.fillWidth: true; text: root.t("导入路径：incoming → dropin_mods\\repository → 开启后同步到游戏"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                                        Text { Layout.fillWidth: true; text: backend.dropInStatus + " · " + backend.dropInFolder; color: cyan; font.family: "Cascadia Mono"; font.pixelSize: 12; elide: Text.ElideMiddle }
                                        Item { Layout.fillHeight: true }
                                        RowLayout { Layout.fillWidth: true; spacing: 8; AppButton { Layout.fillWidth: true; label: root.t("打开收件箱"); onClicked: backend.openDropInFolder() } AppButton { Layout.fillWidth: true; label: root.t("导入历史"); onClicked: backend.openDropInArchive() } AppButton { Layout.fillWidth: true; label: root.t("导入并扫描"); primary:true; onClicked: backend.importDropInsAsync() } }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true; spacing: 8
                                AppButton { Layout.preferredWidth: 142; label: root.t("本地 Mod"); fillColor: modPage.section === "all" ? UI.Theme.primaryFill : panel2; labelColor: modPage.section === "all" ? "#11151C" : root.fg; onClicked: modPage.section = "all" }
                                AppButton { Layout.preferredWidth: 144; label: root.t("● 当前加载"); fillColor: modPage.section === "loaded" ? UI.Theme.primaryFill : panel2; labelColor: modPage.section === "loaded" ? "#11151C" : root.fg; onClicked: { modPage.section = "loaded"; backend.scanModsAsync() } }
                                AppButton { Layout.preferredWidth: 142; label: root.t("★ 前置组件"); fillColor: modPage.section === "recommended" ? UI.Theme.primaryFill : panel2; labelColor: modPage.section === "recommended" ? "#11151C" : root.fg; onClicked: modPage.section = "recommended" }
                                Text { Layout.fillWidth: true; text: modPage.section === "recommended" ? root.t("检查本地前置组件") : modPage.section === "loaded" ? root.t("查看游戏目录中理论上会加载的文件") : root.t("扫描、导入、启停和删除本地 Mod"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; horizontalAlignment: Text.AlignRight }
                            }
                            StackLayout {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                currentIndex: modPage.section === "sources" ? 0 : modPage.section === "recommended" ? 1 : modPage.section === "all" ? 2 : 3
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 14; spacing: 10
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 58; radius: root.controlRadius
                                            color: Qt.rgba(accent.r,accent.g,accent.b,darkMode ? 0.09 : 0.11); border.color: Qt.rgba(accent.r,accent.g,accent.b,0.28)
                                            RowLayout {
                                                anchors.fill: parent; anchors.margins: 12; spacing: 12
                                                Rectangle { width: 34; height: 34; radius: root.controlRadius; color: Qt.rgba(accent.r,accent.g,accent.b,0.16); Text { anchors.centerIn: parent; text: "↗"; color: accent; font.pixelSize: 17; font.weight: Font.Bold } }
                                                Column { Layout.fillWidth: true; spacing: 2; Text { text: root.t("只做管理器，不做 Mod 下载平台"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold } Text { width: parent.width; text: root.t("第三方 Mod、任务与汉化内容请从作者发布页获取，并遵守各自的授权、转载与更新规则。本工具不代替作者授权。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap } }
                                            }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 62; radius: root.controlRadius
                                            color: UI.Theme.surfaceRaised; border.color: root.border
                                            RowLayout {
                                                anchors.fill: parent; anchors.margins: 10; spacing: 8
                                                Column {
                                                    Layout.fillWidth: true; spacing: 2
                                                    Text { text: root.t("选择获取路线"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold }
                                                    Text { width: parent.width; text: root.t("自行挑选原作者内容，或前往 user9527 的中文汉化整合帖。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; elide: Text.ElideRight }
                                                }
                                                AppButton { Layout.preferredWidth: 176; Layout.preferredHeight: 36; label: root.t("F95Zone 原作者目录"); primary:true; onClicked: backend.openExternalUrl("https://f95zone.to/threads/secret-flasher-manaka-custom-missions-1-2-1-version-2-4-0.263276/") }
                                                AppButton { Layout.preferredWidth: 176; Layout.preferredHeight: 36; label: root.t("user9527 汉化帖"); fillColor: violet; labelColor: "#10151A"; onClicked: backend.openExternalUrl("https://f95zone.to/threads/secret-flasher-manaka-custom-missions-1-2-1-version-2-4-0.263276/post-20360819") }
                                                AppButton { Layout.preferredWidth: 132; Layout.preferredHeight: 36; label: root.t("Mega 目录"); onClicked: backend.openExternalUrl("https://mega.nz/folder/QAEiCThB#V3T3H3c60jmQ_Pqm2R2eRA") }
                                            }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 10
                                            Column { Layout.fillWidth: true; Text { text: root.t("Mod 与任务来源目录"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: UI.Theme.bodySize; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight; text: root.t("CustomMission 1/2 已置顶；其余条目按类型整理。只跳转作者页面，不托管文件。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize } }
                                            AppTextField {
                                                Layout.preferredWidth: 250; Layout.preferredHeight: 38
                                                placeholderText: root.t("搜索名称、作者、类型或楼层")
                                                text: modPage.sourceSearch; selectByMouse: true; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12
                                                onTextEdited: modPage.sourceSearch = text

                                            }
                                            Text { text: modPage.filteredSources.length + " / " + backend.modSourceLinks.length; color: accent; font.family: "Cascadia Mono"; font.pixelSize: 12; font.weight: Font.DemiBold }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 6
                                            Repeater {
                                                model: [
                                                    { key: "all", label: root.t("全部") },
                                                    { key: "core", label: root.t("基础前置") },
                                                    { key: "persistent", label: root.t("持续任务") },
                                                    { key: "story", label: root.t("剧情任务") },
                                                    { key: "modes", label: root.t("小游戏与模式") },
                                                    { key: "utilities", label: root.t("功能扩展") },
                                                    { key: "tools", label: root.t("开发工具与其他") }
                                                ]
                                                delegate: AppButton {
                                                    required property var modelData
                                                    Layout.fillWidth: true; Layout.preferredHeight: 31
                                                    label: modelData.label
                                                    fillColor: modPage.sourceCategory === modelData.key ? accent : panel2
                                                    labelColor: modPage.sourceCategory === modelData.key ? "#10151A" : root.fg
                                                    onClicked: modPage.sourceCategory = modelData.key
                                                }
                                            }
                                        }
                                        GridView {
                                            id: modSourceList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                                            model: modPage.filteredSources
                                            cellWidth: width / 2; cellHeight: 142
                                            delegate: Rectangle {
                                                required property var modelData
                                                width: modSourceList.cellWidth - 7; height: 134; radius: root.controlRadius
                                                color: modelData.pinned ? (UI.Theme.surfaceRaised) : (UI.Theme.surfaceRaised)
                                                border.color: modelData.pinned ? accent : border
                                                RowLayout {
                                                    anchors.fill: parent; anchors.margins: 12; spacing: 11
                                                    Rectangle { Layout.alignment: Qt.AlignTop; width: 40; height: 40; radius: root.controlRadius; color: Qt.rgba(accent.r,accent.g,accent.b,0.13); Text { anchors.centerIn: parent; text: modelData.pinned ? "★" : "↗"; color: accent; font.pixelSize: 15; font.weight: Font.Bold } }
                                                    ColumnLayout {
                                                        Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 3
                                                        RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: modelData.displayName; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold; wrapMode: Text.Wrap } Rectangle { width: sourceGroupText.width + 12; height: 19; radius: 6; color: panel2; Text { id: sourceGroupText; anchors.centerIn: parent; text: modelData.categoryLabel; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 7 } } }
                                                        Text { Layout.fillWidth: true; text: modelData.alternateName; color: muted; font.family: "Segoe UI"; font.pixelSize: 12; elide: Text.ElideRight }
                                                        Text { Layout.fillWidth: true; text: modelData.author + " · " + modelData.kind + " · " + modelData.reference; color: cyan; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                                                        Text { Layout.fillWidth: true; visible: modelData.note.length > 0; text: modelData.note; color: muted; font.family: "Segoe UI"; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                                                    }
                                                    AppButton { Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 86; Layout.preferredHeight: 32; label: root.t("打开原帖页"); onClicked: backend.openExternalUrl(modelData.url) }
                                                }
                                            }
                                            ScrollBar.vertical: UI.ScrollBar {}
                                        }
                                        Text { Layout.fillWidth: true; text: root.t("支持 Mod 作者以及整合汉化工作者的劳动，是所有人都该守护的。"); color: amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
                                    }
                                }
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 12; spacing: 9
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 54; radius: root.controlRadius
                                            color: Qt.rgba(cyan.r,cyan.g,cyan.b,darkMode ? 0.08 : 0.10); border.color: Qt.rgba(cyan.r,cyan.g,cyan.b,0.25)
                                            RowLayout { anchors.fill: parent; anchors.margins: 12; Text { text: root.t("依赖顺序"); color: cyan; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; text: root.t("V1 任务 → CustomMission 1　　V2 包 → CustomMission 2"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12 } }
                                        }
                                        GridView {
                                            id: recommendedModList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                                            model: backend.recommendedModInventory
                                            cellWidth: width / 2; cellHeight: 114
                                            delegate: Rectangle {
                                                required property var modelData
                                                width: recommendedModList.cellWidth - 7; height: 106; radius: root.controlRadius
                                                color: UI.Theme.surfaceRaised
                                                border.color: modelData.enabled ? Qt.rgba(green.r,green.g,green.b,0.42) : border
                                                RowLayout {
                                                    anchors.fill: parent; anchors.margins: 14; spacing: 13
                                                    Rectangle { width: 46; height: 46; radius: root.controlRadius; color: Qt.rgba((modelData.accent === "cyan" ? cyan : modelData.accent === "violet" ? violet : modelData.accent === "amber" ? amber : accent).r,(modelData.accent === "cyan" ? cyan : modelData.accent === "violet" ? violet : modelData.accent === "amber" ? amber : accent).g,(modelData.accent === "cyan" ? cyan : modelData.accent === "violet" ? violet : modelData.accent === "amber" ? amber : accent).b,0.14); Text { anchors.centerIn: parent; text: modelData.kind === "plugin" ? "DLL" : "V2"; color: modelData.accent === "cyan" ? cyan : modelData.accent === "violet" ? violet : modelData.accent === "amber" ? amber : accent; font.pixelSize: 12; font.weight: Font.Bold } }
                                                    ColumnLayout {
                                                        Layout.fillWidth: true; spacing: 3
                                                        RowLayout { Layout.fillWidth: true; Text { text: modelData.displayName; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: UI.Theme.bodySize; font.weight: Font.DemiBold } Rectangle { width: roleText.width + 14; height: 21; radius: 7; color: panel2; Text { id: roleText; anchors.centerIn: parent; text: modelData.role; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize } } Item { Layout.fillWidth: true } Text { text: modelData.status; color: modelData.enabled ? green : modelData.available ? muted : red; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold } }
                                                        Text { Layout.fillWidth: true; text: modelData.summary; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; elide: Text.ElideRight }
                                                        Text { Layout.fillWidth: true; visible: modelData.requiredPluginName && !modelData.dependencyReady; text: modelData.dependencyAvailable ? root.t("⚠ 需要先启用 ") + modelData.requiredPluginName : root.t("⚠ 当前来源库缺少 ") + modelData.requiredPluginName; color: amber; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize }
                                                    }
                                                    UI.Switch { checked: modelData.enabled; enabled: modelData.available; onClicked: backend.setModEnabledAsync(modelData.id, checked, false); palette.highlight: green }
                                                }
                                            }
                                            ScrollBar.vertical: UI.ScrollBar {}
                                        }
                                    }
                                }
                                Item {
                                    ColumnLayout {
                                        anchors.fill: parent; spacing: 10
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 8
                                            Repeater {
                                                model: [
                                                    {key:"all",text:root.t("全部")},
                                                    {key:"core",text:root.t("必备前置")},
                                                    {key:"v1",text:root.t("V1 任务")},
                                                    {key:"v2_story",text:root.t("V2 剧情")},
                                                    {key:"gameplay",text:root.t("玩法与限制")},
                                                    {key:"media",text:root.t("外观与音效")},
                                                    {key:"utility",text:root.t("工具与辅助")}
                                                ]
                                                delegate: AppButton { required property var modelData; Layout.preferredWidth: 94; label: modelData.text; fillColor: modPage.filterCategory === modelData.key ? accent : panel2; labelColor: modPage.filterCategory === modelData.key ? "#11151C" : root.fg; onClicked: modPage.filterCategory = modelData.key }
                                            }
                                            Item { Layout.fillWidth: true }
                                            AppTextField {
                                                Layout.preferredWidth: 245; Layout.preferredHeight: 42
                                                placeholderText: root.t("搜索名称、详情、地点…"); selectByMouse: true; color: root.fg; font.family: UI.Theme.fontFamily
                                                onTextEdited: modPage.searchText = text

                                            }
                                        }
                                        AppCard {
                                            Layout.fillWidth: true; Layout.fillHeight: true
                                            GridView {
                                                id: modList; anchors.fill: parent; anchors.margins: 10; clip: true
                                                model: modPage.filteredInventory
                                                cellWidth: width / 2; cellHeight: 230
                                                delegate: Rectangle {
                                                    required property var modelData
                                                    width: modList.cellWidth - 7; height: 222; radius: root.controlRadius
                                                    color: UI.Theme.surfaceRaised; border.color: modelData.enabled ? Qt.rgba(green.r,green.g,green.b,0.40) : border
                                                    RowLayout {
                                                        anchors.fill: parent; anchors.margins: 14; spacing: 12
                                                        Rectangle {
                                                            Layout.alignment: Qt.AlignTop; width: 46; height: 46; radius: root.controlRadius
                                                            color: Qt.rgba((modelData.kind === "plugin" ? violet : modelData.kind === "v1" ? cyan : accent).r,(modelData.kind === "plugin" ? violet : modelData.kind === "v1" ? cyan : accent).g,(modelData.kind === "plugin" ? violet : modelData.kind === "v1" ? cyan : accent).b,0.13)
                                                            Text { anchors.centerIn: parent; text: modelData.kind === "plugin" ? "DLL" : modelData.kind.toUpperCase(); color: modelData.kind === "plugin" ? violet : modelData.kind === "v1" ? cyan : accent; font.family: "Segoe UI"; font.pixelSize: 12; font.weight: Font.Bold }
                                                        }
                                                        ColumnLayout {
                                                            Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 5
                                                            RowLayout {
                                                                Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 7
                                                                Text { Layout.fillWidth: true; text: modelData.name; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: UI.Theme.bodySize; font.weight: Font.DemiBold; wrapMode: Text.Wrap }
                                                                Rectangle { width: kindText.width+14; height: 22; radius: 7; color: panel2; Text { id: kindText; anchors.centerIn: parent; text: root.t(modelData.categoryLabel); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize } }
                                                                Text { text: modelData.status; color: modelData.enabled ? green : muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold }
                                                            }
                                                            Text { Layout.fillWidth: true; text: modelData.description; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.2; wrapMode: Text.Wrap }
                                                            Text { Layout.fillWidth: true; visible: modelData.kind === "v1"; text: modelData.hasLocationGuide ? root.t("起始地点：") + modelData.location : root.t("起始地点：说明中暂无记录"); color: modelData.hasLocationGuide ? cyan : muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold; wrapMode: Text.Wrap }
                                                            Text { Layout.fillWidth: true; visible: modelData.locationNote.length > 0; text: "⚠ " + modelData.locationNote; color: amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                                                            Text { Layout.fillWidth: true; visible: modelData.requiredPluginName && !modelData.dependencyReady; text: modelData.dependencyAvailable ? root.t("⚠ 需要先启用 ") + modelData.requiredPluginName : root.t("⚠ 当前来源库缺少 ") + modelData.requiredPluginName; color: amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                                                            Text { Layout.fillWidth: true; visible: modelData.warning.length > 0; text: "⚠ " + modelData.warning; color: amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                                                        }
                                                        ColumnLayout {
                                                            Layout.alignment: Qt.AlignTop; spacing: 8
                                                            UI.Switch { checked: modelData.enabled; enabled: modelData.available; onClicked: backend.setModEnabledAsync(modelData.id, checked, false); palette.highlight: green }
                                                            AppButton {
                                                                visible: modelData.userImported
                                                                Layout.preferredWidth: 58; Layout.preferredHeight: 30
                                                                label: root.t("删除"); destructive:true; fillColor: Qt.rgba(red.r,red.g,red.b,darkMode ? 0.18 : 0.10); labelColor: red
                                                                onClicked: { modDeleteConfirm.entryId = modelData.id; modDeleteConfirm.modName = modelData.name; modDeleteConfirm.open() }
                                                            }
                                                        }
                                                    }
                                                }
                                                ScrollBar.vertical: UI.ScrollBar {}
                                                footer: Item { width: 1; height: 8 }
                                            }
                                            Text { anchors.centerIn: parent; visible: modPage.filteredInventory.length === 0; text: backend.modInventory.length ? root.t("没有符合筛选条件的项目") : root.t("当前游戏目录中还没有可管理的 Mod"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                                        }
                                    }
                                }
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 14; spacing: 10
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 12
                                            Rectangle { width: 46; height: 46; radius: root.controlRadius; color: Qt.rgba(green.r,green.g,green.b,0.14); Text { anchors.centerIn: parent; text: "ON"; color: green; font.family: "Segoe UI"; font.pixelSize: 12; font.weight: Font.Bold } }
                                            Column { Layout.fillWidth: true; spacing: 3; Text { text: root.t("当前已启用的 Mod"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: root.t("按游戏目录中的文件状态筛选；不读取运行日志"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize } }
                                            AppButton { Layout.preferredWidth: 110; label: root.t("重新扫描"); onClicked: backend.scanModsAsync() }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 8
                                            Repeater {
                                                model: [
                                                    {key:"all",text:root.t("全部")},
                                                    {key:"core",text:root.t("必备前置")},
                                                    {key:"v1",text:root.t("V1 任务")},
                                                    {key:"v2_story",text:root.t("V2 剧情")},
                                                    {key:"gameplay",text:root.t("玩法与限制")},
                                                    {key:"media",text:root.t("外观与音效")},
                                                    {key:"utility",text:root.t("工具与辅助")}
                                                ]
                                                delegate: AppButton { required property var modelData; Layout.preferredWidth: 94; label: modelData.text; fillColor: modPage.loadedFilterCategory === modelData.key ? UI.Theme.primaryFill : panel2; labelColor: modPage.loadedFilterCategory === modelData.key ? "#11151C" : root.fg; onClicked: modPage.loadedFilterCategory = modelData.key }
                                            }
                                            Item { Layout.fillWidth: true }
                                            AppTextField {
                                                Layout.preferredWidth: 245; Layout.preferredHeight: 42
                                                placeholderText: root.t("搜索名称或详情…"); selectByMouse: true; color: root.fg; font.family: UI.Theme.fontFamily
                                                onTextEdited: modPage.loadedSearchText = text

                                            }
                                        }
                                        GridView {
                                            id: loadedModList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                                            model: modPage.filteredLoadedInventory
                                            cellWidth: width / 2; cellHeight: 126
                                            delegate: Rectangle {
                                                required property var modelData
                                                width: loadedModList.cellWidth - 7; height: 118; radius: root.controlRadius
                                                color: modelData.enabled ? (UI.Theme.surfaceRaised) : (UI.Theme.surfaceRaised)
                                                border.color: modelData.enabled ? Qt.rgba(green.r,green.g,green.b,0.40) : Qt.rgba(muted.r,muted.g,muted.b,0.35)
                                                opacity: modelData.enabled ? 1.0 : 0.72
                                                RowLayout {
                                                    anchors.fill: parent; anchors.margins: 13; spacing: 12
                                                    Rectangle { width: 42; height: 42; radius: root.controlRadius; color: Qt.rgba((modelData.enabled ? green : muted).r,(modelData.enabled ? green : muted).g,(modelData.enabled ? green : muted).b,0.13); Text { anchors.centerIn: parent; text: modelData.kind === "plugin" ? "DLL" : modelData.kind.toUpperCase(); color: modelData.enabled ? green : muted; font.family: "Segoe UI"; font.pixelSize: 12; font.weight: Font.Bold } }
                                                    ColumnLayout {
                                                        Layout.fillWidth: true; spacing: 4
                                                        RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: modelData.name; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold; wrapMode: Text.Wrap } Text { text: modelData.kindLabel; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize } }
                                                        Text { Layout.fillWidth: true; text: modelData.enabled ? root.t("文件已启用 · 理论上会随游戏加载") : root.t("本次会话已关闭 · 重新扫描后隐藏"); color: modelData.enabled ? green : muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold }
                                                        Text { Layout.fillWidth: true; text: modelData.description; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                                                        Text { Layout.fillWidth: true; visible: modelData.requiredPluginName && !modelData.dependencyReady; text: root.t("⚠ 需要启用 ") + modelData.requiredPluginName + root.t(" 才能实际加载"); color: amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                                                    }
                                                    UI.Switch { checked: modelData.enabled; enabled: modelData.available; onClicked: backend.setModEnabledAsync(modelData.id, checked, true); palette.highlight: green }
                                                }
                                            }
                                            ScrollBar.vertical: UI.ScrollBar {}
                                        }
                                        Text { Layout.fillWidth: true; visible: modPage.filteredLoadedInventory.length === 0; text: backend.loadedModInventory.length ? root.t("没有符合筛选条件的项目") : root.t("游戏目录中暂时没有处于启用位置的 Mod。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                                    }
                                }
                            }
                            Text { Layout.fillWidth: true; text: root.t("同名 Drop-in 会替换仓库版本，并在游戏关闭时同步已启用副本。删除按钮只会出现在用户导入的 Mod 上。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                        }
                    }

                    // Creative workshop ---------------------------------------
                    Item {
                        id: workshopPage
                        property string route: "f95"
                        property string searchText: ""
                        property string category: "all"
                        property var filteredSources: {
                            let result = []
                            let query = searchText.trim().toLowerCase()
                            let source = backend.modSourceLinks
                            for (let i = 0; i < source.length; ++i) {
                                let item = source[i]
                                if (category !== "all" && item.category !== category) continue
                                if (query.length && item.searchText.indexOf(query) < 0) continue
                                result.push(item)
                            }
                            return result
                        }

                        AppCard {
                            anchors.fill: parent
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 16; spacing: 10
                                Rectangle {
                                    Layout.fillWidth: true; Layout.preferredHeight: 58; radius: root.controlRadius
                                    color: UI.Theme.surfaceRaised; border.color: root.border
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: 8; spacing: 8
                                        AppButton { Layout.fillWidth: true; Layout.preferredHeight: 42; label: root.t("路线 1 · F95Zone 原帖"); fillColor: workshopPage.route === "f95" ? UI.Theme.primaryFill : panel2; labelColor: workshopPage.route === "f95" ? "#10151A" : root.fg; onClicked: workshopPage.route = "f95" }
                                        AppButton { Layout.fillWidth: true; Layout.preferredHeight: 42; label: root.t("路线 2 · user9527 汉化整合"); fillColor: workshopPage.route === "user9527" ? UI.Theme.primaryFill : panel2; labelColor: workshopPage.route === "user9527" ? "#10151A" : root.fg; onClicked: workshopPage.route = "user9527" }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 10; visible: workshopPage.route === "f95"
                                    ColumnLayout { Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 3; Text { Layout.fillWidth: true; elide: Text.ElideRight; text: root.t("Mod 与任务来源目录"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 16; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight; text: root.t("CustomMission 1/2 已置顶；其余条目按类型整理。只跳转作者页面，不托管文件。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 } }
                                    AppTextField {
                                        Layout.preferredWidth: 270; Layout.preferredHeight: 38
                                        placeholderText: root.t("搜索名称、作者、类型或楼层")
                                        text: workshopPage.searchText; selectByMouse: true; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12
                                        onTextEdited: workshopPage.searchText = text

                                    }
                                    Text { text: workshopPage.filteredSources.length + " / " + backend.modSourceLinks.length; color: accent; font.family: "Cascadia Mono"; font.pixelSize: 12; font.weight: Font.DemiBold }
                                }
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 6; visible: workshopPage.route === "f95"
                                    Repeater {
                                        model: [
                                            { key: "all", label: root.t("全部") },
                                            { key: "core", label: root.t("基础前置") },
                                            { key: "persistent", label: root.t("持续任务") },
                                            { key: "story", label: root.t("剧情任务") },
                                            { key: "modes", label: root.t("小游戏与模式") },
                                            { key: "utilities", label: root.t("功能扩展") },
                                            { key: "tools", label: root.t("开发工具与其他") }
                                        ]
                                        delegate: AppButton {
                                            required property var modelData
                                            Layout.fillWidth: true; Layout.preferredHeight: 31
                                            label: modelData.label
                                            fillColor: workshopPage.category === modelData.key ? accent : panel2
                                            labelColor: workshopPage.category === modelData.key ? "#10151A" : root.fg
                                            onClicked: workshopPage.category = modelData.key
                                        }
                                    }
                                }
                                GridView {
                                    id: workshopSourceList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; visible: workshopPage.route === "f95"
                                    model: workshopPage.filteredSources
                                    cellWidth: width / 2; cellHeight: 158
                                    delegate: Rectangle {
                                        required property var modelData
                                        width: workshopSourceList.cellWidth - 7; height: 150; radius: root.controlRadius
                                        color: modelData.pinned ? (UI.Theme.surfaceRaised) : (UI.Theme.surfaceRaised)
                                        border.color: modelData.pinned ? accent : border
                                        RowLayout {
                                            anchors.fill: parent; anchors.margins: 12; spacing: 11
                                            Rectangle { Layout.alignment: Qt.AlignTop; width: 40; height: 40; radius: root.controlRadius; color: Qt.rgba(accent.r,accent.g,accent.b,0.13); Text { anchors.centerIn: parent; text: modelData.pinned ? "★" : "↗"; color: accent; font.pixelSize: 15; font.weight: Font.Bold } }
                                            ColumnLayout {
                                                Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 3
                                                RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: modelData.displayName; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: UI.Theme.bodySize; font.weight: Font.DemiBold; wrapMode: Text.Wrap } Rectangle { width: workshopGroupText.width + 14; height: 22; radius: 7; color: panel2; Text { id: workshopGroupText; anchors.centerIn: parent; text: modelData.categoryLabel; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize } } }
                                                Text { Layout.fillWidth: true; text: modelData.alternateName; color: muted; font.family: "Segoe UI"; font.pixelSize: 12; elide: Text.ElideRight }
                                                Text { Layout.fillWidth: true; text: modelData.author + " · " + modelData.kind + " · " + modelData.reference; color: cyan; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                                                Text { Layout.fillWidth: true; visible: modelData.note.length > 0; text: modelData.note; color: muted; font.family: "Segoe UI"; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                                            }
                                            AppButton { Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 98; Layout.preferredHeight: 36; label: root.t("打开原帖页"); onClicked: backend.openExternalUrl(modelData.url) }
                                        }
                                    }
                                    ScrollBar.vertical: UI.ScrollBar {}
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; Layout.fillHeight: true; visible: workshopPage.route === "user9527"; spacing: 11
                                    Text { Layout.fillWidth: true; text: root.t("user9527 中文汉化整合"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 21; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter }
                                    Text { Layout.fillWidth: true; text: root.t("选择原帖查看说明，或打开作者提供的文件目录。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                                    RowLayout {
                                        Layout.fillWidth: true; Layout.preferredHeight: 126; Layout.minimumHeight: 126; Layout.maximumHeight: 126; spacing: 12
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.fillHeight: true; radius: root.controlRadius
                                            color: UI.Theme.surfaceRaised; border.color: Qt.rgba(violet.r,violet.g,violet.b,0.38)
                                            RowLayout {
                                                anchors.fill: parent; anchors.margins: 14; spacing: 12
                                                Rectangle { width: 38; height: 38; radius: root.controlRadius; color: Qt.rgba(violet.r,violet.g,violet.b,0.16); Text { anchors.centerIn: parent; text: "↗"; color: violet; font.pixelSize: 16; font.weight: Font.Bold } }
                                                ColumnLayout { Layout.fillWidth: true; spacing: 4; Text { text: root.t("F95Zone 汉化整合原帖"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 14; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; text: root.t("查看使用说明、更新记录与作者声明"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap } }
                                                AppButton { Layout.preferredWidth: 112; Layout.preferredHeight: 38; label: root.t("打开原帖"); fillColor: violet; labelColor: "#10151A"; onClicked: backend.openExternalUrl("https://f95zone.to/threads/secret-flasher-manaka-custom-missions-1-2-1-version-2-4-0.263276/post-20360819") }
                                            }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.fillHeight: true; radius: root.controlRadius
                                            color: UI.Theme.surfaceRaised; border.color: root.border
                                            RowLayout {
                                                anchors.fill: parent; anchors.margins: 14; spacing: 12
                                                Rectangle { width: 38; height: 38; radius: root.controlRadius; color: Qt.rgba(cyan.r,cyan.g,cyan.b,0.14); Text { anchors.centerIn: parent; text: "⌁"; color: cyan; font.pixelSize: 16; font.weight: Font.Bold } }
                                                ColumnLayout { Layout.fillWidth: true; spacing: 4; Text { text: root.t("作者文件目录"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 14; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; text: root.t("打开作者在原帖中提供的 Mega 目录"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap } }
                                                AppButton { Layout.preferredWidth: 112; Layout.preferredHeight: 38; label: root.t("打开目录"); primary:true; onClicked: backend.openExternalUrl("https://mega.nz/folder/QAEiCThB#V3T3H3c60jmQ_Pqm2R2eRA") }
                                            }
                                        }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 230; radius: root.cardRadius
                                        color: UI.Theme.surfaceRaised; border.color: Qt.rgba(violet.r,violet.g,violet.b,0.55); border.width: 1
                                        ColumnLayout {
                                            anchors.fill: parent; anchors.margins: 20; spacing: 13
                                            Text { Layout.fillWidth: true; text: root.t("导入 9527 汉化整合"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 20; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter }
                                            Text { Layout.fillWidth: true; text: root.t("下载并解压整合包后，可使用专用向导安全备份、导入并应用精简启动预设。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
                                            RowLayout {
                                                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
                                                Repeater {
                                                    model: [
                                                        { number: "1", title: root.t("下载整合包"), detail: root.t("从原帖或作者目录获取最新文件") },
                                                        { number: "2", title: root.t("完整解压"), detail: root.t("保留文件夹结构，不要直接选择压缩包") },
                                                        { number: "3", title: root.t("启动导入向导"), detail: root.t("自动校验、备份并应用精简预设") }
                                                    ]
                                                    delegate: Rectangle {
                                                        required property var modelData
                                                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.maximumHeight: 108; radius: root.controlRadius
                                                        color: UI.Theme.surfaceRaised; border.color: root.border
                                                        RowLayout {
                                                            anchors.fill: parent; anchors.margins: 13; spacing: 10
                                                            Rectangle { width: 38; height: 38; radius: 19; color: modelData.number === "3" ? violet : panel2; Text { anchors.centerIn: parent; text: modelData.number; color: modelData.number === "3" ? "#10151A" : root.fg; font.pixelSize: 16; font.weight: Font.Bold } }
                                                            ColumnLayout { Layout.fillWidth: true; spacing: 3; Text { Layout.fillWidth: true; text: modelData.title; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: UI.Theme.bodySize; font.weight: Font.DemiBold; wrapMode: Text.Wrap } Text { Layout.fillWidth: true; text: modelData.detail; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap } }
                                                        }
                                                    }
                                                }
                                            }
                                            AppButton { Layout.alignment: Qt.AlignHCenter; Layout.preferredWidth: 330; Layout.preferredHeight: 52; label: root.t("开始导入 9527 汉化整合"); fillColor: violet; labelColor: "#10151A"; onClicked: { backend.reset9527Import(); pack9527Wizard.step = 0; pack9527Wizard.open() } }
                                        }
                                    }
                                }
                                Text { Layout.fillWidth: true; visible: workshopPage.route === "f95"; text: root.t("支持 Mod 作者以及整合汉化工作者的劳动，是所有人都该守护的。"); color: amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
                            }
                        }
                    }

                    // NPC voice installer -------------------------------------
                    Item {
                        id: npcVoicePage
                        AppCard {
                            anchors.fill: parent
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 24; spacing: 14
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 14
                                    Rectangle {
                                        width: 48; height: 48; radius: root.controlRadius
                                        color: Qt.rgba(cyan.r, cyan.g, cyan.b, 0.14)
                                        Text { anchors.centerIn: parent; text: "♫"; color: cyan; font.pixelSize: 23; font.weight: Font.Bold }
                                    }
                                    Text { Layout.fillWidth: true; text: root.t("NPC 语气与字幕"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 20; font.weight: Font.Bold }
                                    Rectangle {
                                        width: npcVoiceStatusText.width + 26; height: 34; radius: root.controlRadius
                                        color: Qt.rgba((backend.npcVoiceInstalled ? green : amber).r, (backend.npcVoiceInstalled ? green : amber).g, (backend.npcVoiceInstalled ? green : amber).b, 0.13)
                                        Text { id: npcVoiceStatusText; anchors.centerIn: parent; text: backend.npcVoiceInstalled ? root.t("已就绪") : root.t("等待安装"); color: backend.npcVoiceInstalled ? green : amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold }
                                    }
                                }

                                Rectangle {
                                    id: npcMasterCard
                                    property bool active: backend.npcVoiceInstalled && backend.npcVoiceEnabled
                                    Layout.fillWidth: true; Layout.preferredHeight: Math.max(112,npcMasterDescription.implicitHeight+36); radius: root.cardRadius
                                    color: Qt.rgba((active ? green : muted).r, (active ? green : muted).g, (active ? green : muted).b, darkMode ? 0.11 : 0.09)
                                    border.color: Qt.rgba((active ? green : muted).r, (active ? green : muted).g, (active ? green : muted).b, 0.35)
                                    Behavior on color { ColorAnimation { duration: UI.Theme.motionDuration } }
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: 18; spacing: 18
                                        Rectangle {
                                            Layout.preferredWidth: 54; Layout.preferredHeight: 54; radius: root.cardRadius
                                            color: Qt.rgba((npcMasterCard.active ? green : muted).r, (npcMasterCard.active ? green : muted).g, (npcMasterCard.active ? green : muted).b, 0.18)
                                            Text { anchors.centerIn: parent; text: npcMasterCard.active ? "♫" : "×"; color: npcMasterCard.active ? green : muted; font.pixelSize: 24; font.weight: Font.Bold }
                                        }
                                        ColumnLayout {
                                            id:npcMasterDescription; Layout.fillWidth: true; Layout.minimumWidth:0; spacing: 5
                                            Text { Layout.fillWidth:true; wrapMode:Text.Wrap; text: root.t("NPC 功能总开关"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 17; font.weight: Font.Bold }
                                            Text { Layout.fillWidth:true; wrapMode:Text.Wrap; text: !backend.npcVoiceInstalled ? root.t("尚未安装") : UI.Theme.t("已保存配置 · 重启游戏后生效","Configuration saved · Restart the game to apply"); color: npcMasterCard.active ? green : muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold }
                                            Text { Layout.fillWidth:true; wrapMode:Text.Wrap; text: backend.npcVoiceInstalled ? root.t("切换后重新启动游戏生效；语言、台词和细分设置会保留。") : root.t("请先安装 NPC 语音插件，再使用总开关。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                                        }
                                        UI.Switch {
                                            id:npcMasterSwitch; objectName:"npcMasterSwitch"
                                            large:true; Layout.preferredWidth:166; Layout.minimumWidth:166; Layout.maximumWidth:166
                                            checked:npcMasterCard.active; enabled:backend.npcVoiceInstalled
                                            onLabel:root.t("开启"); offLabel:root.t("关闭")
                                            Accessible.name:root.t("NPC 功能总开关")
                                            onClicked:backend.setNpcVoiceEnabled(checked)
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true; Layout.preferredHeight: 104; radius: root.controlRadius
                                    color: UI.Theme.surfaceRaised; border.color: root.border
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: 16; spacing: 18
                                        ColumnLayout {
                                            Layout.fillWidth: true; spacing: 5
                                            Text { text: root.t("当前状态"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                                            Text { Layout.fillWidth: true; text: backend.npcVoiceInstallStatus; color: backend.npcVoiceInstalled ? green : amber; font.family: UI.Theme.fontFamily; font.pixelSize: 14; font.weight: Font.DemiBold; wrapMode: Text.Wrap }
                                            Text { Layout.fillWidth: true; text: backend.gameFolder.length ? backend.gameFolder : root.t("尚未选择游戏目录"); color: muted; font.family: "Cascadia Mono"; font.pixelSize: 12; elide: Text.ElideMiddle }
                                        }
                                        AppButton { Layout.preferredWidth: 260; Layout.preferredHeight: 48; label: backend.npcVoiceInstalled ? root.t("更新 / 修复 NPC 语音") : root.t("一键安装 NPC 语音"); fillColor: accent; labelColor: "#10151A"; enabled: backend.gameFolder.length > 0; onClicked: backend.installNpcVoicesAsync() }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true; Layout.preferredHeight: npcOptions.implicitHeight+32; radius: root.cardRadius
                                    color: UI.Theme.surfaceRaised; border.color: root.border
                                    ColumnLayout {
                                        id:npcOptions; anchors.fill: parent; anchors.margins:16; spacing:12
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: root.t("字幕与语音设置"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 15; font.weight: Font.DemiBold }
                                            Item { Layout.fillWidth: true }
                                            AppButton {
                                                Layout.preferredWidth: 150; Layout.preferredHeight: 38
                                                label: root.t("编辑字幕台词")
                                                enabled: backend.gameFolder.length > 0
                                                onClicked: {
                                                    root.npcTextLanguage = backend.npcVoiceLanguage
                                                    root.npcTextState = "ambient"
                                                    root.reloadNpcTextEditor()
                                                    npcTextEditorDialog.open()
                                                }
                                            }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 8
                                            Text { text: root.t("字幕语言"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                                            Repeater {
                                                model: [{key:"zh",label:"中文"},{key:"ja",label:"日本語"},{key:"en",label:"English"}]
                                                delegate: AppButton {
                                                    required property var modelData
                                                    Layout.fillWidth:true; Layout.preferredHeight:UI.Theme.controlHeight
                                                    label: modelData.label
                                                    fillColor: backend.npcVoiceLanguage === modelData.key ? UI.Theme.primaryFill : panel
                                                    labelColor: backend.npcVoiceLanguage === modelData.key ? "#10151A" : root.fg
                                                    enabled:backend.npcVoiceInstalled; onClicked: backend.setNpcVoiceLanguage(modelData.key)
                                                }
                                            }
                                        }
                                        RowLayout {
                                            Layout.fillWidth:true; spacing:24
                                            UI.Switch { id:npcAudioSwitch; objectName:"npcAudioSwitch"; text:root.t("语气词"); checked:backend.npcVoiceAudioEnabled; enabled:backend.npcVoiceInstalled; onClicked:backend.setNpcVoicePlayback(checked,npcSubtitleSwitch.checked) }
                                            UI.Switch { id:npcSubtitleSwitch; objectName:"npcSubtitleSwitch"; text:root.t("字幕"); checked:backend.npcVoiceSubtitlesEnabled; enabled:backend.npcVoiceInstalled; onClicked:backend.setNpcVoicePlayback(npcAudioSwitch.checked,checked) }
                                            Item { Layout.fillWidth:true }
                                        }
                                    }
                                }

                                Item { Layout.fillHeight: true }
                                RowLayout {
                                    Layout.alignment: Qt.AlignHCenter; spacing: 10
                                    AppButton { Layout.preferredWidth: 170; Layout.preferredHeight: 44; label: root.t("打开安装目录"); enabled: backend.gameFolder.length > 0; onClicked: backend.openVoicePackFolder() }
                                }
                            }
                        }
                    }

                    // Logs ------------------------------------------------------
                    AppCard {
                        color: panel
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 20; spacing: 12
                            RowLayout { Layout.fillWidth: true; Text { text: root.t("最近 ") + backend.logs.length + root.t(" 条记录"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 } Item { Layout.fillWidth: true } AppButton { label: root.t("清空日志"); onClicked: backend.clearLogs() } }
                            Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true; radius: root.controlRadius
                                color: UI.Theme.surfaceRaised; border.color: root.border
                                ListView {
                                    id: logList; anchors.fill: parent; anchors.margins: 8; clip: true; model: backend.logs; spacing: 2
                                    delegate: Rectangle { required property var modelData; required property int index; width: logList.width; height: 34; radius: 8; color: index % 2 ? "transparent" : (UI.Theme.surfaceRaised); Text { anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 10; text: modelData; color: root.fg; font.family: "Cascadia Mono"; font.pixelSize: 12; elide: Text.ElideRight } }
                                    ScrollBar.vertical: UI.ScrollBar {}
                                    onCountChanged: positionViewAtEnd()
                                }
                            }
                        }
                    }

                    AppCard {
                        GameplaySettings {
                            id:gameplaySettings
                            anchors.fill:parent; anchors.margins:18
                            controller:backend
                            onCloseCancelled:root.pendingWindowClose=false
                            onCloseRequested: {
                                const closeWindow=root.pendingWindowClose
                                root.pendingWindowClose=false
                                if(closeWindow) root.close()
                                else root.pageIndex=0
                            }
                        }
                    }

                }
            }
        }
    }

    FolderDialog { id: folderDialog; title: root.t("选择游戏根目录"); onAccepted: backend.setGameFolder(selectedFolder.toString()) }
    FolderDialog {
        id: pack9527FolderDialog
        title: root.t("选择解压后的 9527 整合包")
        onAccepted: {
            backend.inspect9527PackAsync(selectedFolder.toString())
            pack9527Wizard.step = 1
        }
    }

    UI.Dialog {
        id: npcTextEditorDialog
        anchors.centerIn: parent
        width: Math.min(940, root.width - 70)
        height: Math.min(700, root.height - 54)
        modal: true
        closePolicy: Popup.CloseOnEscape
        padding: 0
        background: Rectangle { color: panel; border.color: root.border; border.width: 1; radius: root.cardRadius }
        contentItem: ColumnLayout {
            spacing: 0
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 82; radius: root.cardRadius
                color: UI.Theme.surfaceRaised
                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 20; color: parent.color }
                Column {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 24; spacing: 3
                    Text { text: root.t("NPC 字幕台词"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 20; font.weight: Font.Bold }
                    Text { text: root.t("声音固定为日文短语气词；这里仅编辑字幕文本。"); color: cyan; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                }
                AppButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: 20; width: 96; height: 40; label:UI.Theme.t("关闭","Close"); onClicked: npcTextEditorDialog.close() }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.margins: 22; spacing: 12
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Text { text: root.t("字幕语言"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; Layout.preferredWidth:backend.language === "en" ? 110 : 70 }
                    Repeater {
                        model: [{key:"zh",label:"中文"},{key:"ja",label:"日本語"},{key:"en",label:"English"}]
                        delegate: AppButton {
                            required property var modelData
                            Layout.preferredWidth: 120; Layout.preferredHeight: 38
                            label: modelData.label
                            fillColor: root.npcTextLanguage === modelData.key ? UI.Theme.primaryFill : panel2
                            labelColor: root.npcTextLanguage === modelData.key ? "#10151A" : root.fg
                            onClicked: { root.npcTextLanguage = modelData.key; root.reloadNpcTextEditor() }
                        }
                    }
                    Item { Layout.fillWidth: true }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Text { text: root.t("分类"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; Layout.preferredWidth:backend.language === "en" ? 110 : 70 }
                    Repeater {
                        model: [
                            {key:"ambient",label:root.t("碎碎念")},
                            {key:"phone",label:root.t("手机闲聊")},
                            {key:"watching",label:root.t("观察")},
                            {key:"alert",label:root.t("警觉")},
                            {key:"found",label:root.t("发现")},
                            {key:"failure",label:root.t("失败")},
                            {key:"aftermath",label:root.t("互动")}
                        ]
                        delegate: AppButton {
                            required property var modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 38
                            label: modelData.label
                            fillColor: root.npcTextState === modelData.key ? UI.Theme.primaryFill : panel2
                            labelColor: root.npcTextState === modelData.key ? "#10151A" : root.fg
                            onClicked: { root.npcTextState = modelData.key; root.reloadNpcTextEditor() }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Text { text: root.t("角色"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; Layout.preferredWidth:backend.language === "en" ? 110 : 70 }
                    Repeater {
                        model: [
                            {key:"young_female",label:root.t("年轻女性")},
                            {key:"young_male",label:root.t("年轻男性")},
                            {key:"older_female",label:root.t("年长女性")},
                            {key:"older_male",label:root.t("年长男性")}
                        ]
                        delegate: AppButton {
                            required property var modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 38
                            label: modelData.label
                            fillColor: root.npcTextProfile === modelData.key ? UI.Theme.primaryFill : panel2
                            labelColor: root.npcTextProfile === modelData.key ? "#10151A" : root.fg
                            onClicked: { root.npcTextProfile = modelData.key; root.reloadNpcTextEditor() }
                        }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: root.npcTextState === "aftermath"
                          ? root.t("互动分类：连续多行组成一个段落，空行分隔不同段落；每次触发会完整显示其中一段。")
                          : root.t("每行一条台词；空行会忽略。保存后游戏可读取本地覆盖。")
                    color: muted
                    font.family: UI.Theme.fontFamily
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                }
                ScrollView {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    clip: true
                    background: Rectangle { color: UI.Theme.surfaceRaised; border.color: root.border; radius: root.controlRadius }
                    TextArea {
                        id: npcTextArea
                        padding: 16
                        color: root.fg
                        selectionColor: accent
                        selectedTextColor: "#10151A"
                        font.family: UI.Theme.fontFamily
                        font.pixelSize: 15
                        wrapMode: TextEdit.Wrap
                        background: null
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    AppButton { Layout.preferredWidth: 150; label: root.t("恢复默认文案"); onClicked: { const restored = backend.resetNpcVoiceText(root.npcTextLanguage, root.npcTextState, root.npcTextProfile); if (restored.length) npcTextArea.text = restored } }
                    Item { Layout.fillWidth: true }
                    AppButton { Layout.preferredWidth: 180; label: root.t("保存文案"); fillColor: accent; labelColor: "#10151A"; onClicked: backend.saveNpcVoiceText(root.npcTextLanguage, root.npcTextState, root.npcTextProfile, npcTextArea.text) }
                }
            }
        }
    }

    UI.Dialog {
        id: guidePreviewDialog
        anchors.centerIn: parent
        width: Math.min(1120, root.width - 64)
        height: Math.min(720, root.height - 54)
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: 14
        background: Rectangle {
            color: UI.Theme.surfaceRaised
            border.color: accent; border.width: 1; radius: root.cardRadius
        }
        contentItem: Item {
            Image {
                anchors.fill: parent; anchors.margins: 8
                source: root.guidePreviewSource
                fillMode: Image.PreserveAspectFit
                asynchronous: true; smooth: true; mipmap: true
            }
            Rectangle {
                anchors.right: parent.right; anchors.top: parent.top
                width: 38; height: 38; radius: 19
                color: closeGuideHit.pressed ? Qt.darker(panel2, 1.12) : panel2
                border.color: root.border
                Text { anchors.centerIn: parent; text: "×"; color: root.fg; font.pixelSize: 23 }
                MouseArea {
                    id: closeGuideHit; anchors.fill: parent; hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor; onClicked: guidePreviewDialog.close()
                }
            }
        }
    }

    UI.Dialog {
        id: pack9527Wizard
        property int step: 0
        property bool confirmed: false
        anchors.centerIn: parent
        width: Math.min(790, root.width - 70)
        height: Math.min(650, root.height - 50)
        modal: true
        closePolicy: Popup.NoAutoClose
        padding: 0
        background: Rectangle { color: panel; border.color: root.border; border.width: 1; radius: root.cardRadius }
        Timer {
            id: pack9527InstallTimer
            interval: 80
            onTriggered: backend.install9527PackAsync()
        }
        contentItem: ColumnLayout {
            spacing: 0
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 86; radius: root.cardRadius
                color: UI.Theme.surfaceRaised
                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 20; color: parent.color }
                Column {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 24; spacing: 4
                    Text { text: root.t("导入 user9527 汉化整合"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 20; font.weight: Font.Bold }
                    Text { text: root.t("校验来源、备份现有文件，并应用安全的精简启动预设"); color: violet; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                }
                Row {
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: 24; spacing: 7
                    Repeater {
                        model: 4
                        Rectangle {
                            required property int index
                            width: 30; height: 30; radius: root.controlRadius
                            color: pack9527Wizard.step >= index || pack9527Wizard.step === 4 ? accent : panel2
                            Text { anchors.centerIn: parent; text: index + 1; color: parent.color === accent ? "#10151A" : muted; font.family: "Cascadia Mono"; font.pixelSize: 12; font.weight: Font.Bold }
                        }
                    }
                }
            }
            StackLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; currentIndex: pack9527Wizard.step
                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 28; spacing: 16
                        Text { Layout.fillWidth: true; text: root.t("开始之前"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 18; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("请先在“设备与游戏”选择原版游戏目录，并完成 BepInEx 运行环境安装。游戏必须完全退出，不能只停留在标题画面。"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.4; wrapMode: Text.Wrap }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 118; radius: root.controlRadius; color: panel2; border.color: root.border
                            Column { anchors.fill: parent; anchors.margins: 16; spacing: 7
                                Text { text: root.t("你需要选择解压后的目录，其中应直接包含："); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                                Text { text: "BepInEx  ·  CustomMissions  ·  CustomMissions2  ·  " + root.t("必读说明"); color: cyan; font.family: "Cascadia Mono"; font.pixelSize: 12; font.weight: Font.DemiBold }
                                Text { width: parent.width; text: root.t("软件不会执行整合包中的 EXE、BAT 或脚本，也不会上传这些文件。"); color: amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                            }
                        }
                        Item { Layout.fillHeight: true }
                        RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } AppButton { label: root.t("取消"); onClicked: pack9527Wizard.close() } AppButton { Layout.preferredWidth: 190; label: root.t("选择解压目录"); fillColor: accent; labelColor: "#10151A"; onClicked: pack9527FolderDialog.open() } }
                    }
                }
                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 28; spacing: 14
                        Text { text: root.t("目录校验"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 18; font.weight: Font.Bold }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: root.controlRadius; color: panel2; border.color: backend.pack9527Ready ? green : amber; Text { anchors.fill: parent; anchors.margins: 13; text: backend.pack9527Folder || root.t("尚未选择目录"); color: root.fg; font.family: "Cascadia Mono"; font.pixelSize: 12; elide: Text.ElideMiddle; verticalAlignment: Text.AlignVCenter } }
                        Text { Layout.fillWidth: true; text: backend.pack9527Status; color: backend.pack9527Ready ? green : amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                        GridLayout {
                            Layout.fillWidth: true; columns: 3; rowSpacing: 8; columnSpacing: 8
                            Repeater {
                                model: [
                                    { title: root.t("插件 DLL"), value: backend.pack9527Analysis.plugins || 0 },
                                    { title: root.t("V1 JSON 任务"), value: backend.pack9527Analysis.v1_missions || 0 },
                                    { title: root.t("V2 任务包"), value: backend.pack9527Analysis.v2_packages || 0 }
                                ]
                                Rectangle { required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 86; radius: root.controlRadius; color: panel2; border.color: root.border; Column { anchors.centerIn: parent; spacing: 4; Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.value; color: accent; font.family: "Cascadia Mono"; font.pixelSize: 22; font.weight: Font.Bold } Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.title; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize } } }
                            }
                        }
                        Text { Layout.fillWidth: true; text: root.t("识别到的说明文件：") + ((backend.pack9527Analysis.readmes || []).join(" · ") || root.t("无")); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                        Item { Layout.fillHeight: true }
                        RowLayout { Layout.fillWidth: true; AppButton { label: root.t("重新选择"); onClicked: pack9527FolderDialog.open() } Item { Layout.fillWidth: true } AppButton { label:UI.Theme.t("关闭","Close"); onClicked: pack9527Wizard.close() } AppButton { Layout.preferredWidth: 170; enabled: backend.pack9527Ready; label: root.t("查看安装计划"); fillColor: backend.pack9527Ready ? accent : panel2; labelColor: backend.pack9527Ready ? "#10151A" : muted; onClicked: pack9527Wizard.step = 2 } }
                    }
                }
                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 28; spacing: 13
                        Text { text: root.t("精简启动安装计划"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 18; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("软件会先备份将被替换的文件，然后导入配置与附属资源。首次启动只保留两个任务加载器，其余内容进入停用区，可随时在“本地 Mod”中开启。"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.4; wrapMode: Text.Wrap }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 150; radius: root.controlRadius; color: panel2; border.color: root.border
                            Column { anchors.fill: parent; anchors.margins: 16; spacing: 9
                                Text { text: root.t("安装后默认状态"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize }
                                Text { text: "● SFM_custom_mission.dll   " + root.t("启用"); color: green; font.family: "Cascadia Mono"; font.pixelSize: 12; font.weight: Font.DemiBold }
                                Text { text: "● SFM_custom_mission_v2.dll   " + root.t("启用"); color: green; font.family: "Cascadia Mono"; font.pixelSize: 12; font.weight: Font.DemiBold }
                                Text { text: root.t("○ 其他插件、全部 V1/V2 任务   默认停用"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                                Text { text: root.t("DG-LAB 遥测插件保持启用，不会被精简预设关闭。"); color: cyan; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize }
                            }
                        }
                        CheckBox { id: pack9527Confirm; text: root.t("我已阅读 9527 的必读说明，并确认游戏已经完全退出"); checked: pack9527Wizard.confirmed; onToggled: pack9527Wizard.confirmed = checked; palette.windowText: root.fg }
                        Text { Layout.fillWidth: true; text: root.t("提示：第一次导入可能需要一些时间，请勿在处理中关闭软件。"); color: amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                        Item { Layout.fillHeight: true }
                        RowLayout { Layout.fillWidth: true; AppButton { label: root.t("上一步"); onClicked: pack9527Wizard.step = 1 } Item { Layout.fillWidth: true } AppButton { label: root.t("取消"); onClicked: pack9527Wizard.close() } AppButton { Layout.preferredWidth: 190; enabled: pack9527Wizard.confirmed; label: root.t("备份并开始导入"); fillColor: pack9527Wizard.confirmed ? accent : panel2; labelColor: pack9527Wizard.confirmed ? "#10151A" : muted; onClicked: { pack9527Wizard.step = 3; pack9527InstallTimer.start() } } }
                    }
                }
                Item {
                    ColumnLayout { anchors.centerIn: parent; width: Math.min(500, parent.width - 60); spacing: 16; BusyIndicator { Layout.alignment: Qt.AlignHCenter; running: pack9527Wizard.step === 3 } Text { Layout.fillWidth: true; text: root.t("正在备份与导入…"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 18; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter } Text { Layout.fillWidth: true; text: root.t("正在复制配置、插件与任务，并应用精简启动预设。请勿关闭软件或启动游戏。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter } }
                }
                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 28; spacing: 15
                        Item { Layout.fillHeight: true }
                        Rectangle { Layout.alignment: Qt.AlignHCenter; width: 72; height: 72; radius: 36; color: Qt.rgba(green.r,green.g,green.b,0.15); Text { anchors.centerIn: parent; text: "✓"; color: green; font.pixelSize: 34; font.weight: Font.Bold } }
                        Text { Layout.fillWidth: true; text: root.t("9527 汉化整合已导入"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 21; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter }
                        Text { Layout.fillWidth: true; text: backend.pack9527Status; color: green; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter }
                        Text { Layout.fillWidth: true; text: root.t("接下来可关闭向导，在“本地 Mod”里只开启你真正需要的任务和插件。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter }
                        Item { Layout.fillHeight: true }
                        RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } AppButton { visible: backend.pack9527Backup.length > 0; label: root.t("打开备份目录"); onClicked: backend.open9527Backup() } AppButton { Layout.preferredWidth: 170; label: root.t("完成"); fillColor: accent; labelColor: "#10151A"; onClicked: { pack9527Wizard.close(); modPage.section = "all" } } }
                    }
                }
            }
        }
        onOpened: { confirmed = false; pack9527Confirm.checked = false }
    }

    UI.Dialog {
        id: onboardingDialog
        property int step: 0
        function openFromStart() { step = 0; open() }
        function finishGuide() { backend.completeOnboarding(); close() }
        anchors.centerIn: parent
        width: Math.min(900, root.width - 64)
        height: Math.min(680, root.height - 50)
        modal: true
        closePolicy: Popup.NoAutoClose
        padding: 0
        background: Rectangle { color: panel; border.color: root.border; border.width: 1; radius: root.cardRadius }
        contentItem: ColumnLayout {
            spacing: 0
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 92; radius: root.cardRadius
                color: UI.Theme.surfaceRaised
                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 22; color: parent.color }
                Column {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 26; spacing: 4
                    Text { text: root.t("第一次使用 Manaka × DG-LAB？"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 21; font.weight: Font.Bold }
                    Text { text: root.t("从游戏准备到安全连接，一步一步完成；所有步骤都可以跳过"); color: accent; font.family: UI.Theme.fontFamily; font.pixelSize: 12 }
                }
                Row {
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: 25; spacing: 6
                    Repeater {
                        model: 7
                        Rectangle {
                            required property int index
                            width: onboardingDialog.step === index ? 28 : 9; height: 9; radius: 5
                            color: onboardingDialog.step === index ? accent : border
                            Behavior on width { NumberAnimation { duration: UI.Theme.motionDuration; easing.type: Easing.OutCubic } }
                            Behavior on color { ColorAnimation { duration: 150 } }
                        }
                    }
                }
            }

            StackLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                currentIndex: onboardingDialog.step

                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 34; spacing: 18
                        Text { Layout.fillWidth: true; text: root.t("先告诉我你的情况"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 22; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter }
                        Text { Layout.fillWidth: true; text: root.t("向导不会替你下载游戏，也不会上传任何文件。你可以稍后从窗口顶部重新打开它。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 16
                            Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true; radius: root.cardRadius; color: panel2; border.color: root.border
                                ColumnLayout { anchors.fill: parent; anchors.margins: 22; spacing: 10
                                    Rectangle { width: 52; height: 52; radius: root.cardRadius; color: Qt.rgba(green.r,green.g,green.b,0.16); Text { anchors.centerIn: parent; text: "✓"; color: green; font.pixelSize: 25; font.weight: Font.Bold } }
                                    Text { text: root.t("我已经有游戏"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 17; font.weight: Font.Bold }
                                    Text { Layout.fillWidth: true; text: root.t("从选择 SecretFlasherManaka 游戏根目录开始，然后安装连接所需的运行环境与插件。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.35; wrapMode: Text.Wrap }
                                    Item { Layout.fillHeight: true }
                                    AppButton { Layout.fillWidth: true; Layout.preferredHeight: 48; label: root.t("从安装开始"); primary:true; onClicked: onboardingDialog.step = 2 }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true; radius: root.cardRadius; color: panel2; border.color: root.border
                                ColumnLayout { anchors.fill: parent; anchors.margins: 22; spacing: 10
                                    Rectangle { width: 52; height: 52; radius: root.cardRadius; color: Qt.rgba(accent.r,accent.g,accent.b,0.16); Text { anchors.centerIn: parent; text: "↗"; color: accent; font.pixelSize: 23; font.weight: Font.Bold } }
                                    Text { text: root.t("我还没有游戏"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 17; font.weight: Font.Bold }
                                    Text { Layout.fillWidth: true; text: root.t("先前往 DLsite 购买并下载正版游戏。准备完成后，再回来继续安装。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.35; wrapMode: Text.Wrap }
                                    Item { Layout.fillHeight: true }
                                    AppButton { Layout.fillWidth: true; Layout.preferredHeight: 48; label: root.t("查看购买步骤"); fillColor: accent; labelColor: "#10151A"; onClicked: onboardingDialog.step = 1 }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 34; spacing: 16
                        Text { text: root.t("1 · 获取正版游戏"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 22; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("在 DLsite 的作品页面购买并下载游戏。下载结束后完整解压，记住能直接看到 SecretFlasherManaka.exe 的文件夹位置。"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.45; wrapMode: Text.Wrap }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 120; radius: root.cardRadius; color: panel2; border.color: accent
                            RowLayout { anchors.fill: parent; anchors.margins: 18; spacing: 16
                                Rectangle { width: 52; height: 52; radius: root.controlRadius; color: Qt.rgba(accent.r,accent.g,accent.b,0.16); Text { anchors.centerIn: parent; text: "DL"; color: accent; font.pixelSize: 16; font.weight: Font.Bold } }
                                ColumnLayout { Layout.fillWidth: true; spacing: 4
                                    Text { text: "Secret Flasher Manaka · RJ01389782"; color: root.fg; font.family: "Segoe UI"; font.pixelSize: 14; font.weight: Font.DemiBold }
                                    Text { Layout.fillWidth: true; text: root.t("官方购买页将在浏览器中打开；购买、下载和账号登录均由 DLsite 处理。"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                                }
                                AppButton { Layout.preferredWidth: 150; label: root.t("打开 DLsite"); fillColor: accent; labelColor: "#10151A"; onClicked: backend.openExternalUrl("https://www.dlsite.com/maniax/work/=/product_id/RJ01389782.html") }
                            }
                        }
                        TutorialLine { numberText: "1"; title: root.t("购买并下载"); detail: root.t("从订单或下载页面取得游戏压缩包") }
                        TutorialLine { numberText: "2"; title: root.t("完整解压"); detail: root.t("不要直接在压缩包或网盘预览里运行游戏") }
                        TutorialLine { numberText: "3"; title: root.t("确认根目录"); detail: root.t("文件夹内应直接包含 SecretFlasherManaka.exe") }
                        Item { Layout.fillHeight: true }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 34; spacing: 15
                        Text { text: root.t("2 · 选择游戏目录"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 22; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("请选择能直接看到 SecretFlasherManaka.exe 的文件夹。不要选择 BepInEx、plugins 或游戏 Data 文件夹。"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.4; wrapMode: Text.Wrap }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 120; radius: root.cardRadius; color: panel2; border.color: backend.gameFolder.length > 0 ? green : border
                            ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 8
                                Text { text: root.t("当前游戏目录"); color: muted; font.family: UI.Theme.fontFamily; font.pixelSize:UI.Theme.captionSize }
                                Text { Layout.fillWidth: true; text: backend.gameFolder || root.t("尚未选择游戏目录"); color: root.fg; font.family: "Cascadia Mono"; font.pixelSize: 12; elide: Text.ElideMiddle }
                                Text { Layout.fillWidth: true; text: backend.gameStatus; color: backend.gameFolder.length > 0 ? green : amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap }
                            }
                        }
                        AppButton { Layout.preferredWidth: 210; Layout.preferredHeight: 48; label: root.t("选择游戏根目录"); fillColor: accent; labelColor: "#10151A"; onClicked: folderDialog.open() }
                        TutorialLine { numberText: "✓"; title: root.t("正确示例"); detail: "D:\\Games\\SecretFlasherManaka\\SecretFlasherManaka.exe" }
                        TutorialLine { numberText: "×"; title: root.t("不要选择"); detail: "...\\BepInEx  /  ...\\BepInEx\\plugins  /  ...\\SecretFlasherManaka_Data" }
                        Item { Layout.fillHeight: true }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 34; spacing: 16
                        Text { text: root.t("3 · 安装连接插件"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 22; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("关闭游戏后点击安装。软件会为纯原版配置 BepInEx 6，并安装 Manaka DG-LAB 遥测插件；已有环境则会检查并修复。"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.45; wrapMode: Text.Wrap }
                        TutorialLine { numberText: "1"; title: root.t("完全退出游戏"); detail: root.t("不要停留在标题画面，确认游戏进程已经关闭") }
                        TutorialLine { numberText: "2"; title: root.t("安装运行环境"); detail: root.t("自动配置 BepInEx 与本软件的遥测插件") }
                        TutorialLine { numberText: "3"; title: root.t("首次启动游戏"); detail: root.t("进入存档后，控制中心会开始收到游戏数据") }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 58; radius: root.controlRadius; color: panel2; border.color: root.border; Text { anchors.fill: parent; anchors.margins: 14; text: backend.gameStatus; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter; wrapMode: Text.Wrap } }
                        AppButton { Layout.preferredWidth: 230; Layout.preferredHeight: 48; label: root.t("安装 / 修复运行环境"); fillColor: accent; labelColor: "#10151A"; onClicked: backend.installPluginAsync(false) }
                        Item { Layout.fillHeight: true }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 34; spacing: 15
                        Text { text: root.t("4 · 连接 DG-LAB"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 22; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("让手机和电脑连接同一个 Wi‑Fi。先在 DG-LAB App 连接蓝牙主机，再进入 SOCKET 控制扫描下方二维码。"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.4; wrapMode: Text.Wrap }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 22
                            Rectangle { Layout.preferredWidth: 220; Layout.preferredHeight: 220; radius: root.cardRadius; color: "white"; Image { anchors.fill: parent; anchors.margins: 10; source: backend.qrSource; fillMode: Image.PreserveAspectFit; visible: source !== "" } Text { anchors.centerIn: parent; visible: backend.qrSource === ""; width: parent.width - 20; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter; text: backend.connectionHint; color: "#4B5565"; font.pixelSize: 12 } }
                            ColumnLayout { Layout.fillWidth: true; spacing: 10
                                TutorialLine { numberText: "1"; title: root.t("同一 Wi‑Fi"); detail: root.t("暂时关闭手机流量以及电脑 VPN 或代理") }
                                TutorialLine { numberText: "2"; title: root.t("连接蓝牙主机"); detail: root.t("在 DG-LAB App 中先确认主机已经在线") }
                                TutorialLine { numberText: "3"; title: root.t("扫描 SOCKET 二维码"); detail: root.t("连接成功后，顶部状态会变为“DG-LAB 已连接”") }
                                AppButton { Layout.preferredWidth: 190; label: root.t("连接不上？"); onClicked: networkHelpDialog.open() }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 30; spacing: 10
                        Text { text: root.t("5 · 常用页面"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 22; font.weight: Font.Bold }
                        TutorialLine { numberText: "◈"; title: root.t("实时仪表盘"); detail: root.t("查看游戏心率、场景、动作以及 A/B 通道实时输出") }
                        TutorialLine { numberText: "⌁"; title: root.t("设备与游戏"); detail: root.t("选择游戏、安装插件、启动游戏并扫描设备二维码") }
                        TutorialLine { numberText: "◫"; title: root.t("个性化范围"); detail: root.t("设置心率触发区间、日常强度范围和安全硬上限") }
                        TutorialLine { numberText: "〰"; title: root.t("波形工作台"); detail: root.t("选择官方波形、编辑自定义波形，并给不同动作分配反馈") }
                        TutorialLine { numberText: "◉"; title: root.t("A/B 波形监视"); detail: root.t("单独观察心率通道与动作通道当前正在播放的波形") }
                        Item { Layout.fillHeight: true }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 30; spacing: 12
                        Text { text: root.t("6 · 管理与排查页面"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 22; font.weight: Font.Bold }
                        TutorialLine { numberText: "✦"; title: root.t("存档工具"); detail: root.t("备份并修改当前存档的经验与游戏货币；按页面提示触发结算") }
                        TutorialLine { numberText: "⬡"; title: root.t("Mod 管理器"); detail: root.t("扫描本地插件和任务，查看说明，并在下次启动前启用或停用") }
                        TutorialLine { numberText: "✧"; title: root.t("创意工坊"); detail: root.t("前往原作者页面获取 Mod，或使用 user9527 汉化整合导入向导") }
                        TutorialLine { numberText: "◎"; title: root.t("事件记录"); detail: root.t("连接或输出异常时，查看最近的游戏事件与安全归零记录") }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 78; radius: root.controlRadius
                            color: Qt.rgba(green.r,green.g,green.b,darkMode?0.10:0.09); border.color: Qt.rgba(green.r,green.g,green.b,0.35)
                            Text { anchors.fill: parent; anchors.margins: 15; text: root.t("准备完成！建议第一次把强度保持在“低”，确认设备和动作反馈都符合预期后再逐步调整。教程以后可从顶部“新手教程”重新打开。"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.35; wrapMode: Text.Wrap; verticalAlignment: Text.AlignVCenter }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: border }
            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 78; Layout.leftMargin: 22; Layout.rightMargin: 22; spacing: 10
                AppButton { visible: onboardingDialog.step > 0; label: root.t("上一步"); onClicked: onboardingDialog.step = Math.max(0, onboardingDialog.step - 1) }
                AppButton { label: root.t("跳过教程"); labelColor: muted; onClicked: onboardingDialog.finishGuide() }
                Item { Layout.fillWidth: true }
                Text { visible: onboardingDialog.step > 0; text: (onboardingDialog.step + 1) + " / 7"; color: muted; font.family: "Cascadia Mono"; font.pixelSize: 12 }
                AppButton {
                    visible: onboardingDialog.step > 0
                    Layout.preferredWidth: 150
                    label: onboardingDialog.step === 6 ? root.t("完成教程") : root.t("下一步")
                    fillColor: accent; labelColor: "#10151A"
                    onClicked: {
                        if (onboardingDialog.step === 6) onboardingDialog.finishGuide()
                        else onboardingDialog.step += 1
                    }
                }
            }
        }
    }

    UI.Dialog {
        id: progressConfirm; width: Math.min(680,root.width-80); anchors.centerIn: parent; modal: true; title: root.t("确认修改当前存档"); standardButtons: Dialog.Yes | Dialog.No
        contentItem: Text { text: backend.language === "en" ? "Currency will be set to " + progressPage.draftRp + " and EXP to " + progressPage.draftExp + ".\nThe original save is backed up before the game save flow runs.\n\nConfirm that the character is outdoors. After editing EXP, complete any mission and return home to trigger settlement before the level updates." : "将把游戏货币修改为 " + progressPage.draftRp + "，经验值修改为 " + progressPage.draftExp + "。\n软件会先创建备份，再调用游戏自己的保存流程。\n\n请确认角色当前位于室外（非室内）。经验写入后，需要完成任意任务并回家触发结算，等级才会刷新。"; color: root.fg; font.family: UI.Theme.fontFamily; padding: 18; wrapMode: Text.Wrap }
        background: Rectangle { color: panel; border.color: root.border; radius: root.controlRadius }
        onAccepted: backend.applyProgressValues(progressPage.draftRp, progressPage.draftExp)
    }
    UI.Dialog {
        id: modDeleteConfirm
        width: Math.min(680,root.width-80)
        property string entryId: ""
        property string modName: ""
        anchors.centerIn: parent; modal: true; title: root.t("删除导入的 Mod"); confirmText:UI.Theme.t("删除","Delete"); standardButtons: Dialog.Yes | Dialog.No
        contentItem: Text { text: backend.language === "en" ? "This will delete the Mod from the Drop-in repository, game folder, and disabled quarantine:\n" + modDeleteConfirm.modName + "\n\nThe game must be fully closed. The original import remains in dropin_mods\\archive and can be returned to the inbox later." : "将从 Drop-in 仓库、游戏目录和停用隔离区删除：\n" + modDeleteConfirm.modName + "\n\n游戏必须完全退出。原始导入包仍保存在 dropin_mods\\archive，需要时可以重新放回收件箱。"; color: root.fg; font.family: UI.Theme.fontFamily; padding: 18; wrapMode: Text.Wrap }
        onAccepted: backend.deleteDropInModAsync(entryId)
    }

    UI.Dialog {
        id: networkHelpDialog
        objectName: "networkHelpDialog"
        property string selectedAddress: ""
        anchors.centerIn: parent
        width: Math.min(720, root.width - 60)
        height: Math.min(590, root.height - 60)
        modal: true
        padding: 20
        background: Rectangle { color: panel; border.color: root.border; radius: root.cardRadius }
        header: Text {
            objectName: "networkHelpTitle"
            text: root.t("DG-LAB 扫码连接排查"); color: root.fg
            font.pixelSize:UI.Theme.headingSize; font.weight:Font.DemiBold
            padding:20; bottomPadding: 0; wrapMode: Text.Wrap
        }
        function syncAddress() {
            const current = backend.lanAddress.split(":")[0]
            selectedAddress = backend.lanAddresses.indexOf(current) >= 0 ? current : (backend.lanAddresses[0] || "")
        }
        onOpened: { backend.refreshConnection(); syncAddress() }
        Connections { target: backend; function onConnectionChanged() { networkHelpDialog.syncAddress() } }
        contentItem: ScrollView {
            id: networkScroll
            clip: true; contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical: UI.ScrollBar {}
            ColumnLayout {
                width: networkScroll.availableWidth; spacing: 16
                Text { objectName: "networkHelpIntro"; Layout.fillWidth: true; text: root.t("先确认手机与电脑连接同一 Wi‑Fi，并暂时关闭手机流量、电脑 VPN/代理。DG-LAB App 中应先连接蓝牙主机，再进入 SOCKET 控制扫码。"); color: root.fg; font.pixelSize: UI.Theme.bodySize; wrapMode: Text.Wrap }
                Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: border }
                Text { text: root.t("1 选择二维码使用的电脑地址"); color: root.fg; font.pixelSize: 14; font.weight: Font.DemiBold }
                Text { Layout.fillWidth: true; text: backend.language === "en" ? "Choose the LAN adapter reachable from your phone. Refresh after changing networks." : "选择手机可访问的局域网网卡。切换网络后可重新检测地址。"; color: muted; font.pixelSize: UI.Theme.bodySize; wrapMode: Text.Wrap }
                RowLayout {
                    Layout.fillWidth: true; spacing: 10
                    AppComboBox { objectName: "lanAddressPicker"; Layout.fillWidth: true; model: backend.lanAddresses; currentIndex: backend.lanAddresses.indexOf(networkHelpDialog.selectedAddress); displayText: currentIndex >= 0 ? currentText : (backend.language === "en" ? "No LAN address" : "未检测到局域网地址"); onActivated: networkHelpDialog.selectedAddress = currentText }
                    AppButton { objectName: "refreshConnection"; label: backend.language === "en" ? "Refresh" : "重新检测"; onClicked: backend.refreshConnection() }
                }
                AppButton { objectName: "applyLanAddress"; label: root.t("应用并刷新二维码"); enabled: networkHelpDialog.selectedAddress !== "" && backend.serverReady; onClicked: backend.selectLanAddress(networkHelpDialog.selectedAddress) }
                Text { Layout.fillWidth: true; wrapMode: Text.Wrap; text: backend.serverReady ? (backend.language === "en" ? "Current address: " : "当前电脑地址：") + backend.lanAddress : backend.connectionHint; color: backend.serverReady ? muted : amber; font.pixelSize: 12 }
                Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: border }
                Text { text: root.t("2 修复 Windows 网络权限"); color: root.fg; font.pixelSize: 14; font.weight: Font.DemiBold }
                Text { Layout.fillWidth: true; text: backend.language === "en" ? "On a trusted home network, this requests administrator approval to set the adapter to Private and allow TCP port " + backend.socketPort + "." : "仅在可信任的家庭网络中使用。系统会弹出管理员确认，将当前网卡设为专用网络，并放行本软件实际使用的 TCP " + backend.socketPort + " 端口。"; color: muted; font.pixelSize: UI.Theme.bodySize; wrapMode: Text.Wrap }
                AppButton { label: root.t("管理员修复网络权限"); enabled: backend.serverReady; onClicked: backend.repairNetworkAccess() }
                Text { Layout.fillWidth: true; text: root.t("修复完成后无需重启电脑，直接回到 DG-LAB App 重新扫描当前二维码。"); color: muted; font.pixelSize: 12; wrapMode: Text.Wrap }
            }
        }
        footer: Item {
            implicitHeight: 64
            AppButton { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 16; label: backend.language === "en" ? "Close" : "关闭"; onClicked: networkHelpDialog.close() }
        }
    }

    Popup {
        id: toast; x: root.width-width-24; y: root.height-height-24; width: 360; height: 104; modal: false; closePolicy: Popup.NoAutoClose
        property string toastTitle: ""; property string toastMessage: ""
        background: Rectangle { color: panel; border.color: root.border; radius: root.cardRadius }
        contentItem: Column { spacing: 6; Text { text: toast.toastTitle; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: UI.Theme.bodySize; font.weight: Font.DemiBold } Text { width: 320; text: toast.toastMessage; color: muted; font.family: UI.Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.Wrap } }
        Timer { id: toastTimer; interval: 3200; onTriggered: toast.close() }
    }
    Connections { target: backend; function onToastRequested(title,message){toast.toastTitle=title;toast.toastMessage=message;toast.open();toastTimer.restart()} }

    UI.Dialog {
        id: agreementDialog
        anchors.centerIn: parent
        width: Math.min(760, root.width - 80)
        height: Math.min(650, root.height - 60)
        modal: true
        closePolicy: Popup.NoAutoClose
        padding: 0
        background: Rectangle { color: panel; border.color: root.border; border.width: 1; radius: root.cardRadius }
        contentItem: ColumnLayout {
            spacing: 0
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 82
                color: UI.Theme.surfaceRaised
                radius: root.cardRadius
                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 22; color: parent.color }
                Column { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 24; spacing: 4; Text { text: root.t("使用协议与风险知情确认"); color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 20; font.weight: Font.Bold } Text { text: root.t("请完整阅读；不同意不会启动任何设备连接服务"); color: amber; font.family: UI.Theme.fontFamily; font.pixelSize: 12 } }
                AppButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: 22; width: 78; label: backend.language === "zh" ? "English" : "中文"; onClicked: backend.setLanguage(backend.language === "zh" ? "en" : "zh") }
            }
            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.margins: 18
                clip: true; contentWidth: availableWidth
                Text { width: parent.width; text: backend.agreementText; color: root.fg; font.family: UI.Theme.fontFamily; font.pixelSize: 12; lineHeight: 1.45; wrapMode: Text.Wrap }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: border }
            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 76; Layout.leftMargin: 18; Layout.rightMargin: 18; spacing: 12
                AppButton { Layout.preferredWidth: 170; label: root.t("不同意并退出"); fillColor: UI.Theme.surfaceRaised; labelColor: red; onClicked: backend.declineAgreement() }
                Item { Layout.fillWidth: true }
                AppButton { Layout.preferredWidth: 210; label: root.t("我已阅读并同意"); fillColor: accent; labelColor: "#10151C"; onClicked: { backend.acceptAgreement(); agreementDialog.close(); if (!backend.onboardingCompleted) Qt.callLater(function() { onboardingDialog.openFromStart() }) } }
            }
        }
    }
    Component.onCompleted: {
        backend.setActivePage(pageIndex)
        if (!backend.agreementAccepted) agreementDialog.open()
        else if (!backend.onboardingCompleted) onboardingDialog.openFromStart()
    }

}
