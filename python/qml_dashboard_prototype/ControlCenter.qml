import QtQuick
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

    property int pageIndex: 0
    property bool darkMode: backend.theme !== "light"
    property real wavePhase: 0
    property var pageTitles: ["实时仪表盘", "设备与游戏", "个性化范围", "波形工作台", "A/B 波形监视", "存档工具", "Mod 管理器", "事件记录"]
    property var pageSubtitles: [
        "游戏状态、心率与设备输出总览",
        "安装游戏插件并使用 DG-LAB 3.0 扫码",
        "设置心率映射范围与安全硬上限",
        "选择官方预设或创建自定义波形",
        "查看两个通道当前选择的波形和实际强度",
        "安全修改当前存档的经验值与游戏货币",
        "管理你已有的插件、V1 任务与 V2 功能包",
        "检查连接、安全归零和游戏事件"
    ]

    readonly property color bg: darkMode ? "#070A11" : "#EEF2F8"
    readonly property color panel: darkMode ? "#101725" : "#F8FAFD"
    readonly property color panel2: darkMode ? "#172134" : "#E8EEF7"
    readonly property color border: darkMode ? "#2A3850" : "#C8D3E3"
    readonly property color fg: darkMode ? "#F7F9FD" : "#182033"
    readonly property color muted: darkMode ? "#8E9AAF" : "#667389"
    readonly property color track: darkMode ? "#253146" : "#CBD6E5"
    readonly property color accent: darkMode ? "#FF6FAE" : "#DF4D86"
    readonly property color violet: darkMode ? "#A78BFA" : "#7659D9"
    readonly property color cyan: darkMode ? "#5DE0EA" : "#168F9B"
    readonly property color green: darkMode ? "#4ADDA5" : "#168F68"
    readonly property color amber: darkMode ? "#F7C55B" : "#C68114"
    readonly property color red: darkMode ? "#FF5D7A" : "#D94362"

    color: bg
    palette.window: bg
    palette.windowText: fg
    palette.base: panel
    palette.alternateBase: panel2
    palette.text: fg
    palette.button: panel2
    palette.buttonText: fg
    palette.highlight: accent
    palette.highlightedText: "#10151A"
    Behavior on color { ColorAnimation { duration: 240 } }

    component AppCard: Rectangle {
        default property alias contents: cardContent.data
        radius: 22
        color: panel
        border.color: border
        border.width: 1
        clip: true
        Behavior on color { ColorAnimation { duration: 240 } }
        Behavior on border.color { ColorAnimation { duration: 240 } }
        Rectangle {
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            anchors.leftMargin: 24; anchors.rightMargin: 24
            height: 1
            color: darkMode ? "#50617A" : "#FFFFFF"
            opacity: 0.65
        }
        Item { id: cardContent; anchors.fill: parent }
    }

    component AppButton: Rectangle {
        id: button
        property string label: "按钮"
        property color fillColor: panel2
        property color labelColor: root.fg
        property bool enabled: true
        signal clicked()
        implicitWidth: 118
        implicitHeight: 42
        radius: 13
        opacity: enabled ? 1 : 0.48
        color: hit.pressed ? Qt.darker(fillColor, 1.10) : hit.containsMouse ? Qt.lighter(fillColor, 1.06) : fillColor
        border.color: Qt.rgba(labelColor.r, labelColor.g, labelColor.b, 0.18)
        Behavior on color { ColorAnimation { duration: 120 } }
        Text {
            anchors.centerIn: parent
            text: button.label
            color: button.labelColor
            font.family: "Microsoft YaHei UI"
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }
        MouseArea {
            id: hit
            anchors.fill: parent
            enabled: button.enabled
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: button.clicked()
        }
    }

    component AppComboBox: ComboBox {
        id: combo
        implicitHeight: 42
        leftPadding: 14
        rightPadding: 40
        font.family: "Microsoft YaHei UI"
        font.pixelSize: 11
        background: Rectangle {
            radius: 12
            color: combo.pressed ? Qt.darker(panel2, 1.08) : panel2
            border.color: combo.activeFocus ? accent : border
            Behavior on border.color { ColorAnimation { duration: 120 } }
        }
        contentItem: Text {
            leftPadding: 2
            text: combo.displayText
            color: root.fg
            font: combo.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        indicator: Text {
            x: combo.width - width - 15
            anchors.verticalCenter: parent.verticalCenter
            text: combo.popup.visible ? "⌃" : "⌄"
            color: combo.popup.visible ? accent : muted
            font.pixelSize: 16
        }
        delegate: ItemDelegate {
            required property int index
            width: combo.width - 12
            height: 38
            leftPadding: 12
            contentItem: Text {
                text: combo.textAt(index)
                color: root.fg
                font: combo.font
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            background: Rectangle {
                radius: 9
                color: highlighted ? Qt.rgba(accent.r, accent.g, accent.b, darkMode ? 0.18 : 0.12) : "transparent"
            }
        }
        popup: Popup {
            y: combo.height + 5
            width: combo.width
            implicitHeight: Math.min(contentItem.implicitHeight + 12, 292)
            padding: 6
            background: Rectangle { radius: 13; color: panel; border.color: border }
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: combo.popup.visible ? combo.delegateModel : null
                currentIndex: combo.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator { }
            }
        }
    }

    component NavItem: Rectangle {
        id: nav
        required property int targetPage
        property string iconText: "•"
        property string label: "页面"
        Layout.fillWidth: true
        Layout.preferredHeight: 46
        radius: 14
        color: root.pageIndex === targetPage ? Qt.rgba(accent.r, accent.g, accent.b, darkMode ? 0.14 : 0.11) : "transparent"
        border.color: root.pageIndex === targetPage ? Qt.rgba(accent.r, accent.g, accent.b, 0.30) : "transparent"
        Row {
            anchors.fill: parent; anchors.leftMargin: 15; spacing: 12
            Text { anchors.verticalCenter: parent.verticalCenter; text: nav.iconText; color: root.pageIndex === targetPage ? accent : muted; font.pixelSize: 16 }
            Text { anchors.verticalCenter: parent.verticalCenter; text: nav.label; color: root.pageIndex === targetPage ? root.fg : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: root.pageIndex === targetPage ? Font.DemiBold : Font.Normal }
        }
        MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.pageIndex = nav.targetPage }
    }

    component MetricBar: Item {
        id: metric
        property string label: "指标"
        property string valueText: "0"
        property real value: 0
        property real maximum: 100
        property color barColor: accent
        implicitHeight: 60
        Text { anchors.left: parent.left; anchors.top: parent.top; text: metric.label; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
        Text { anchors.right: parent.right; anchors.top: parent.top; text: metric.valueText; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; font.weight: Font.DemiBold }
        Rectangle {
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            height: 8; radius: 4; color: track
            Rectangle {
                height: parent.height; radius: 4; color: metric.barColor
                width: Math.max(metric.value <= 0 ? 0 : 6, parent.width * Math.max(0, Math.min(metric.maximum, metric.value)) / metric.maximum)
                Behavior on width { NumberAnimation { duration: 360; easing.type: Easing.OutCubic } }
            }
        }
    }

    component WaveView: Canvas {
        id: wave
        property var points: []
        property color waveColor: accent
        property bool animated: true
        antialiasing: true
        onPointsChanged: requestPaint()
        onWaveColorChanged: requestPaint()
        Connections { target: root; function onWavePhaseChanged() { if (wave.animated) wave.requestPaint() } function onDarkModeChanged() { wave.requestPaint() } }
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const w = width, h = height
            ctx.strokeStyle = darkMode ? "#253249" : "#D7DFEA"
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
            if (animated) {
                const playX = (wavePhase % 1) * w
                ctx.strokeStyle = Qt.rgba(waveColor.r, waveColor.g, waveColor.b, 0.65)
                ctx.lineWidth = 2
                ctx.beginPath(); ctx.moveTo(playX, 5); ctx.lineTo(playX, h - 5); ctx.stroke()
            }
        }
    }

    component SectionTitle: RowLayout {
        property string title: "标题"
        property string detail: ""
        Layout.fillWidth: true
        Text { text: parent.title; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Item { Layout.fillWidth: true }
        Text { text: parent.detail; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: darkMode ? "#090D17" : "#EEF2F8" }
            GradientStop { position: 1; color: darkMode ? "#070A11" : "#F7F9FC" }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 224
            Layout.fillHeight: true
            color: darkMode ? "#0B101B" : "#F8FAFD"
            border.color: border
            Behavior on color { ColorAnimation { duration: 240 } }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 19; spacing: 6
                Row {
                    Layout.fillWidth: true; Layout.bottomMargin: 22; spacing: 10
                    Rectangle {
                        width: 40; height: 40; radius: 13; color: panel2; clip: true
                        Image { anchors.fill: parent; source: "assets/app_icon.png"; fillMode: Image.PreserveAspectCrop; smooth: true; mipmap: true }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        Text { text: "MANAKA"; color: root.fg; font.family: "Segoe UI"; font.pixelSize: 15; font.weight: Font.Bold; font.letterSpacing: 1.4 }
                        Text { text: "DG-LAB CONTROL"; color: muted; font.pixelSize: 8; font.letterSpacing: 1.1 }
                    }
                }
                Text { Layout.leftMargin: 7; Layout.bottomMargin: 4; text: "控制中心"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; font.letterSpacing: 1.3 }
                NavItem { targetPage: 0; iconText: "◈"; label: "实时仪表盘" }
                NavItem { targetPage: 1; iconText: "⌁"; label: "设备与游戏" }
                NavItem { targetPage: 2; iconText: "◫"; label: "个性化范围" }
                NavItem { targetPage: 3; iconText: "〰"; label: "波形工作台" }
                NavItem { targetPage: 4; iconText: "◉"; label: "A/B 波形监视" }
                NavItem { targetPage: 5; iconText: "✦"; label: "存档工具" }
                NavItem { targetPage: 6; iconText: "⬡"; label: "Mod 管理器" }
                NavItem { targetPage: 7; iconText: "◎"; label: "事件记录" }
                Item { Layout.fillHeight: true }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 98; radius: 17
                    color: Qt.rgba((backend.telemetryOnline ? green : amber).r, (backend.telemetryOnline ? green : amber).g, (backend.telemetryOnline ? green : amber).b, darkMode ? 0.08 : 0.09)
                    border.color: Qt.rgba((backend.telemetryOnline ? green : amber).r, (backend.telemetryOnline ? green : amber).g, (backend.telemetryOnline ? green : amber).b, 0.24)
                    Column {
                        anchors.fill: parent; anchors.margins: 14; spacing: 6
                        Row { spacing: 7; Rectangle { width: 8; height: 8; radius: 4; color: backend.telemetryOnline ? green : amber; anchors.verticalCenter: parent.verticalCenter } Text { text: backend.telemetryStatus; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold } }
                        Text { text: backend.demoMode ? "演示数据 · 无设备输出" : "10 Hz · 本地 UDP"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                        Text { text: backend.version; color: muted; font.pixelSize: 9 }
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true; Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent; anchors.leftMargin: 28; anchors.rightMargin: 28; anchors.topMargin: 20; anchors.bottomMargin: 22; spacing: 15
                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: 58
                    Column {
                        Layout.fillWidth: true; spacing: 1
                        Text { text: pageTitles[pageIndex]; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 22; font.weight: Font.Bold }
                        Text { text: pageSubtitles[pageIndex]; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                    }
                    Rectangle {
                        Layout.preferredWidth: 158; Layout.preferredHeight: 38; radius: 19
                        color: Qt.rgba((backend.deviceConnected ? green : amber).r, (backend.deviceConnected ? green : amber).g, (backend.deviceConnected ? green : amber).b, darkMode ? 0.10 : 0.09)
                        border.color: Qt.rgba((backend.deviceConnected ? green : amber).r, (backend.deviceConnected ? green : amber).g, (backend.deviceConnected ? green : amber).b, 0.26)
                        Row { anchors.centerIn: parent; spacing: 7; Rectangle { width: 8; height: 8; radius: 4; color: backend.deviceConnected ? green : amber; anchors.verticalCenter: parent.verticalCenter } Text { text: backend.deviceConnected ? "DG-LAB 已连接" : "等待设备连接"; color: backend.deviceConnected ? green : amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; font.weight: Font.DemiBold } }
                    }
                    AppButton { Layout.leftMargin: 8; Layout.preferredWidth: 94; label: darkMode ? "☀  日间" : "☾  夜间"; onClicked: { darkMode = !darkMode; backend.setTheme(darkMode ? "dark" : "light") } }
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
                                SectionTitle { title: "游戏心率"; detail: backend.telemetryOnline ? "LIVE" : "WAITING" }
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
                                        Connections { target: backend; function onStateChanged(){ gauge.requestPaint() } }
                                        Connections { target: root; function onDarkModeChanged(){ gauge.requestPaint() } }
                                    }
                                    Column { anchors.centerIn: parent; spacing: -4; Text { anchors.horizontalCenter: parent.horizontalCenter; text: Math.round(backend.heartRate); color: root.fg; font.family: "Segoe UI Variable Display"; font.pixelSize: 56; font.weight: Font.Bold } Text { anchors.horizontalCenter: parent.horizontalCenter; text: "BPM"; color: accent; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 2.2 } }
                                }
                                Text { text: backend.stage + "  ·  " + backend.action; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; Layout.alignment: Qt.AlignHCenter }
                            }
                        }
                        AppCard {
                            Layout.columnSpan: 5; Layout.rowSpan: 7; Layout.fillWidth: true; Layout.fillHeight: true
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 22; spacing: 8
                                SectionTitle { title: "输出通道"; detail: "安全上限 " + backend.hardCap }
                                Text { text: backend.deviceStatus; color: backend.safetyIdle || backend.outputPaused ? amber : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                MetricBar { Layout.fillWidth: true; label: "A · 心跳 Pulse"; valueText: backend.outputA.toFixed(1) + " / " + backend.hardCap; value: backend.outputA; maximum: backend.hardCap; barColor: accent }
                                MetricBar { Layout.fillWidth: true; label: "B · 动作反馈"; valueText: backend.outputB.toFixed(1) + " / " + backend.hardCap; value: backend.outputB; maximum: backend.hardCap; barColor: violet }
                                Item { Layout.fillHeight: true }
                                Rectangle {
                                    Layout.fillWidth: true; Layout.preferredHeight: 68; radius: 15; color: panel2
                                    RowLayout { anchors.fill: parent; anchors.margins: 13; Column { Layout.fillWidth: true; Text { text: "当前波形"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } Text { text: backend.waveAName; color: cyan; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; font.weight: Font.DemiBold } } Text { text: backend.waveMode === "smart" ? "智能策略" : "固定预设"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } }
                                }
                            }
                        }
                        AppCard {
                            Layout.columnSpan: 3; Layout.rowSpan: 7; Layout.fillWidth: true; Layout.fillHeight: true
                            color: backend.outputPaused ? Qt.rgba(amber.r,amber.g,amber.b,darkMode?0.08:0.10) : panel
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 21; spacing: 9
                                Text { text: "会话控制"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                Text { text: backend.outputPaused ? "输出已经归零\n设备连接保持不变" : "随时暂停 A/B 输出\n再次点击即可继续"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; lineHeight: 1.45 }
                                Item { Layout.fillHeight: true }
                                Rectangle {
                                    Layout.alignment: Qt.AlignHCenter; width: 116; height: 116; radius: 58
                                    color: backend.outputPaused ? green : backend.deviceConnected ? amber : panel2
                                    scale: pauseHit.containsMouse ? 1.04 : 1
                                    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                                    Column { anchors.centerIn: parent; spacing: 4; Text { anchors.horizontalCenter: parent.horizontalCenter; text: backend.outputPaused ? "▶" : "Ⅱ"; color: "#11151C"; font.pixelSize: 30; font.weight: Font.Bold } Text { anchors.horizontalCenter: parent.horizontalCenter; text: backend.outputPaused ? "继续输出" : "暂停输出"; color: backend.deviceConnected ? "#11151C" : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.Bold } }
                                    MouseArea { id: pauseHit; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: backend.toggleOutput() }
                                }
                                Item { Layout.fillHeight: true }
                                Text { Layout.alignment: Qt.AlignHCenter; text: backend.outputPaused ? "PAUSED" : backend.safetyIdle ? "SAFETY IDLE" : "OUTPUT ACTIVE"; color: backend.outputPaused || backend.safetyIdle ? amber : green; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1.4 }
                            }
                        }
                        AppCard {
                            Layout.columnSpan: 8; Layout.rowSpan: 5; Layout.fillWidth: true; Layout.fillHeight: true
                            ColumnLayout { anchors.fill: parent; anchors.margins: 20; spacing: 7; SectionTitle { title: "实时波形"; detail: "A 通道 · " + backend.waveAName } WaveView { Layout.fillWidth: true; Layout.fillHeight: true; points: backend.waveAPoints; waveColor: accent; animated: !backend.outputPaused } }
                        }
                        AppCard {
                            Layout.columnSpan: 4; Layout.rowSpan: 5; Layout.fillWidth: true; Layout.fillHeight: true
                            ColumnLayout { anchors.fill: parent; anchors.margins: 20; spacing: 8; SectionTitle { title: "场景状态"; detail: backend.stage } MetricBar { Layout.fillWidth: true; label: "NPC 警觉度"; valueText: Math.round(backend.alertLevel)+"%"; value: backend.alertLevel; barColor: amber } MetricBar { Layout.fillWidth: true; label: "兴奋度"; valueText: Math.round(backend.excitement)+"%"; value: backend.excitement; barColor: violet } Item { Layout.fillHeight: true } Text { text: "当前动作    " + backend.action; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } }
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
                                        SectionTitle { title: "游戏插件"; detail: "自动部署" }
                                        Text { text: "请选择能直接看到 SecretFlasherManaka.exe 的文件夹。\n不要选择 BepInEx、plugins 或游戏 Data 文件夹。"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        TextField { Layout.fillWidth: true; text: backend.gameFolder; color: root.fg; font.family: "Microsoft YaHei UI"; selectByMouse: true; placeholderText: "游戏根目录"; background: Rectangle { radius: 12; color: panel2; border.color: border } onEditingFinished: backend.setGameFolder(text) }
                                        Text { text: backend.gameStatus; color: backend.gameStatus.indexOf("就绪") >= 0 ? green : amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        RowLayout { Layout.fillWidth: true; AppButton { label: "选择目录"; onClicked: folderDialog.open() } AppButton { label: "安装 / 修复运行环境"; onClicked: backend.installPlugin() } }
                                        AppButton { Layout.fillWidth: true; Layout.preferredHeight: 48; label: "一键安装并启动游戏"; fillColor: accent; labelColor: "#11151C"; onClicked: backend.installAndLaunch() }
                                        Item { Layout.fillHeight: true }
                                        Text { text: "纯原版无需预装 BepInEx；安装器会配置已验证的 v1.1.3 运行环境与独立遥测插件。"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                    }
                                }
                                AppCard {
                                    Layout.preferredWidth: 400; Layout.fillHeight: true
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: 22; spacing: 18
                                        ColumnLayout { Layout.fillWidth: true; Text { text: "DG-LAB Socket"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 16; font.weight: Font.DemiBold } Text { text: backend.deviceStatus; color: backend.deviceConnected ? green : amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true } Item { Layout.fillHeight: true } Text { text: backend.lanAddress; color: muted; font.pixelSize: 10 } }
                                        Rectangle { Layout.preferredWidth: 210; Layout.preferredHeight: 210; radius: 14; color: "white"; Image { anchors.fill: parent; anchors.margins: 8; source: backend.qrSource; fillMode: Image.PreserveAspectFit; visible: source !== "" } Text { anchors.centerIn: parent; visible: backend.qrSource === ""; text: backend.demoMode ? "演示模式\n不生成二维码" : "正在生成二维码…"; horizontalAlignment: Text.AlignHCenter; color: "#4B5565"; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 } }
                                    }
                                }
                            }
                            AppCard {
                                Layout.fillWidth: true; Layout.preferredHeight: 300
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 20; spacing: 12
                                    SectionTitle { title: "DG-LAB 3.0 连接向导"; detail: "依次完成四步" }
                                    RowLayout {
                                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                                        Repeater {
                                            model: backend.guideSources
                                            delegate: Rectangle {
                                                required property var modelData
                                                required property int index
                                                Layout.fillWidth: true; Layout.fillHeight: true; radius: 14; color: panel2; border.color: border
                                                Image { anchors.fill: parent; anchors.margins: 8; source: modelData; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                                Rectangle { anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 8; width: 26; height: 26; radius: 13; color: accent; Text { anchors.centerIn: parent; text: index+1; color: "#11151C"; font.weight: Font.Bold } }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Personal settings ---------------------------------------
                    Item {
                        id: personalPage
                        property int draftTrigger: backend.triggerBpm
                        property int draftFull: backend.fullBpm
                        property int draftMin: backend.minStrength
                        property int draftMax: backend.outputMax
                        property int draftCap: backend.hardCap
                        ColumnLayout {
                            anchors.fill: parent; spacing: 15
                            AppCard {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 24; spacing: 16
                                    RowLayout {
                                        Layout.fillWidth: true; spacing: 10
                                        Text { text: "快速预设"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                        Item { Layout.fillWidth: true }
                                        AppButton { label: "低 · 5–30"; onClicked: { personalPage.draftTrigger=90; personalPage.draftFull=160; personalPage.draftMin=5; personalPage.draftMax=30 } }
                                        AppButton { label: "中 · 5–50"; fillColor: Qt.rgba(violet.r,violet.g,violet.b,darkMode?0.20:0.13); onClicked: { personalPage.draftTrigger=85; personalPage.draftFull=160; personalPage.draftMin=5; personalPage.draftMax=50 } }
                                        AppButton { label: "高 · 10–90"; fillColor: Qt.rgba(red.r,red.g,red.b,darkMode?0.20:0.13); onClicked: { personalPage.draftTrigger=80; personalPage.draftFull=160; personalPage.draftMin=10; personalPage.draftMax=90 } }
                                    }
                                    Text { text: "预设只填写心率和日常输出范围，不会改变安全硬上限；点击底部“应用并保存”后生效。"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                    SectionTitle { title: "心率触发范围"; detail: personalPage.draftTrigger + " – " + personalPage.draftFull + " BPM" }
                                    Text { text: "左端开始输出，右端达到设定的日常最高强度。"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                                    RangeSlider { Layout.fillWidth: true; from: 60; to: 160; stepSize: 1; first.value: personalPage.draftTrigger; second.value: personalPage.draftFull; first.onMoved: personalPage.draftTrigger = Math.round(first.value); second.onMoved: personalPage.draftFull = Math.round(second.value) }
                                    RowLayout { Layout.fillWidth: true; Text { text: "60 BPM"; color: muted; font.pixelSize: 10 } Item { Layout.fillWidth: true } Text { text: "160 BPM"; color: muted; font.pixelSize: 10 } }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: border }
                                    SectionTitle { title: "输出强度范围"; detail: personalPage.draftMin + " – " + personalPage.draftMax }
                                    Text { text: "心率在触发区间升高时，强度会在此范围内平滑变化。"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                                    RangeSlider { Layout.fillWidth: true; from: 0; to: 100; stepSize: 1; first.value: personalPage.draftMin; second.value: personalPage.draftMax; first.onMoved: personalPage.draftMin = Math.round(first.value); second.onMoved: personalPage.draftMax = Math.round(second.value) }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: border }
                                    SectionTitle { title: "安全硬上限"; detail: personalPage.draftCap + " / 100" }
                                    Text { text: "独立于上方预设；实际输出、Climax 和设备命令都不能突破此值。初始推荐 30。"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                                    Slider { Layout.fillWidth: true; from: 1; to: 100; stepSize: 1; value: personalPage.draftCap; onMoved: personalPage.draftCap = Math.round(value) }
                                    Item { Layout.fillHeight: true }
                                    RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } AppButton { label: "恢复当前设置"; onClicked: { personalPage.draftTrigger=backend.triggerBpm; personalPage.draftFull=backend.fullBpm; personalPage.draftMin=backend.minStrength; personalPage.draftMax=backend.outputMax; personalPage.draftCap=backend.hardCap } } AppButton { label: "应用并保存"; fillColor: green; labelColor: "#10151A"; onClicked: { if (personalPage.draftCap > 30 && personalPage.draftCap > backend.hardCap) capConfirm.open(); else backend.savePersonalSettings(personalPage.draftTrigger,personalPage.draftFull,personalPage.draftMin,personalPage.draftMax,personalPage.draftCap,false) } } }
                                }
                            }
                        }
                        Dialog {
                            id: capConfirm; anchors.centerIn: parent; modal: true; title: "提高安全硬上限"; standardButtons: Dialog.Yes | Dialog.No
                            contentItem: Text { text: "你正在把安全硬上限提高到 30 以上。\n请先确认个人可承受范围，并从低强度逐步测试。"; color: root.fg; font.family: "Microsoft YaHei UI"; padding: 18 }
                            background: Rectangle { color: panel; border.color: border; radius: 16 }
                            onAccepted: backend.savePersonalSettings(personalPage.draftTrigger,personalPage.draftFull,personalPage.draftMin,personalPage.draftMax,personalPage.draftCap,true)
                        }
                    }

                    // Waveform studio ------------------------------------------
                    Item {
                        id: wavePage
                        property string draftMode: backend.waveMode
                        property string draftFixed: backend.fixedWave
                        property var draftMap: Object.assign({}, backend.waveMap)
                        property string draftName: backend.customName
                        property var draftPoints: backend.customPoints.slice()
                        property int draftFrequency: backend.customFrequency
                        function presetIndex(key) { for (let i=0;i<backend.presets.length;i++) if (backend.presets[i].key===key) return i; return 0 }
                        function setPoint(index,value) { let copy=draftPoints.slice(); copy[index]=Math.max(0,Math.min(100,Math.round(value))); draftPoints=copy }
                        function restoreDefaults() {
                            draftMode="smart"; draftFixed="official_heartbeat"
                            draftMap={low:"official_breath",mid:"official_heartbeat",high:"official_pulsating",action:"official_tide",peak:"climax"}
                            draftName="我的波形"; draftPoints=[0,18,48,82,100,58,20,0,0,25,68,45,15,0,0,0]; draftFrequency=92
                            backend.resetWaveSettings()
                        }
                        ScrollView {
                            anchors.fill: parent; clip: true; contentWidth: availableWidth
                            ColumnLayout {
                            width: parent.width; spacing: 15
                            RowLayout {
                                Layout.fillWidth: true; Layout.preferredHeight: 46
                                AppButton { label: "智能分段"; fillColor: wavePage.draftMode === "smart" ? accent : panel2; labelColor: wavePage.draftMode === "smart" ? "#11151C" : root.fg; onClicked: wavePage.draftMode="smart" }
                                AppButton { label: "固定预设"; fillColor: wavePage.draftMode === "fixed" ? accent : panel2; labelColor: wavePage.draftMode === "fixed" ? "#11151C" : root.fg; onClicked: wavePage.draftMode="fixed" }
                                Item { Layout.fillWidth: true }
                                AppButton { label: "一键恢复默认"; onClicked: wavePage.restoreDefaults() }
                                AppButton { label: "保存波形策略"; fillColor: green; labelColor: "#11151C"; onClicked: backend.saveWaveSettings(wavePage.draftMode,wavePage.draftFixed,wavePage.draftMap.low,wavePage.draftMap.mid,wavePage.draftMap.high,wavePage.draftMap.action,wavePage.draftMap.peak,wavePage.draftName,wavePage.draftPoints,wavePage.draftFrequency) }
                            }
                            AppCard {
                                Layout.fillWidth: true; Layout.preferredHeight: 252
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 16; spacing: 8
                                    SectionTitle { title: "波形预设与我的波形库"; detail: "内置预设只读 · " + backend.waveformCatalog.length + " 个波形" }
                                    ListView {
                                        id: waveformCatalogList
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        orientation: ListView.Horizontal; spacing: 10; clip: true; interactive: true
                                        boundsBehavior: Flickable.StopAtBounds
                                        model: backend.waveformCatalog
                                        delegate: Rectangle {
                                            required property var modelData
                                            width: 250; height: waveformCatalogList.height; radius: 13
                                            color: panel2; border.color: modelData.source === "我的波形库" ? Qt.rgba(cyan.r,cyan.g,cyan.b,0.55) : border
                                            ColumnLayout {
                                                anchors.fill: parent; anchors.margins: 10; spacing: 4
                                                RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: modelData.name; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold; elide: Text.ElideRight } Text { text: modelData.source === "我的波形库" ? "自定义" : modelData.source; color: modelData.source === "我的波形库" ? cyan : muted; font.pixelSize: 8 } }
                                                WaveView { Layout.fillWidth: true; Layout.fillHeight: true; points: modelData.points; waveColor: modelData.color; animated: false }
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    Text { Layout.fillWidth: true; text: modelData.frequency + " Hz"; color: muted; font.pixelSize: 9 }
                                                    Text { visible: modelData.source !== "我的波形库"; text: "只读预览"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 }
                                                    AppButton { visible: modelData.source === "我的波形库"; Layout.preferredWidth: 76; label: "载入编辑"; onClicked: { wavePage.draftName = modelData.name; wavePage.draftPoints = modelData.points.slice(); wavePage.draftFrequency = modelData.frequency; backend.loadCustomWaveform(modelData.id) } }
                                                    AppButton { visible: modelData.source === "我的波形库"; Layout.preferredWidth: 48; label: "删除"; fillColor: Qt.rgba(red.r,red.g,red.b,darkMode?0.18:0.10); labelColor: red; onClicked: backend.deleteCustomWaveform(modelData.id) }
                                                }
                                            }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true; Layout.preferredHeight: 32
                                        Text { text: "拖动卡片区域或使用滚轮浏览"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 }
                                        Item { Layout.fillWidth: true }
                                        AppButton { Layout.preferredWidth: 54; label: "‹"; onClicked: waveformCatalogList.contentX=Math.max(0,waveformCatalogList.contentX-260) }
                                        AppButton { Layout.preferredWidth: 54; label: "›"; onClicked: waveformCatalogList.contentX=Math.min(Math.max(0,waveformCatalogList.contentWidth-waveformCatalogList.width),waveformCatalogList.contentX+260) }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true; Layout.preferredHeight: 385; spacing: 15
                                AppCard {
                                    Layout.preferredWidth: 410; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 20; spacing: 10
                                        SectionTitle { title: wavePage.draftMode === "smart" ? "心率区间映射" : "固定波形"; detail: wavePage.draftMode === "smart" ? "自动切换" : "始终使用" }
                                        ScrollView {
                                            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
                                            ColumnLayout {
                                                width: parent.width; spacing: 11
                                                AppComboBox { visible: wavePage.draftMode === "fixed"; Layout.fillWidth: true; model: backend.presets; textRole: "name"; currentIndex: wavePage.presetIndex(wavePage.draftFixed); onActivated: wavePage.draftFixed=backend.presets[currentIndex].key }
                                                Repeater {
                                                    visible: wavePage.draftMode === "smart"
                                                    model: [{key:"low",label:"低心率段"},{key:"mid",label:"中心率段"},{key:"high",label:"高心率段"},{key:"action",label:"动作进程"},{key:"peak",label:"峰值边沿"}]
                                                    delegate: ColumnLayout {
                                                        required property var modelData
                                                        Layout.fillWidth: true; spacing: 4
                                                        Text { text: modelData.label; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                                        AppComboBox { Layout.fillWidth: true; model: backend.presets; textRole: "name"; currentIndex: wavePage.presetIndex(wavePage.draftMap[modelData.key]); onActivated: { let copy=Object.assign({},wavePage.draftMap); copy[modelData.key]=backend.presets[currentIndex].key; wavePage.draftMap=copy } }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 20; spacing: 10
                                        SectionTitle { title: "自定义波形设计器"; detail: wavePage.draftFrequency + " Hz · 16 点包络" }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            TextField { Layout.fillWidth: true; Layout.preferredHeight: 40; text: wavePage.draftName; placeholderText: "给波形命名"; selectByMouse: true; color: root.fg; font.family: "Microsoft YaHei UI"; onTextEdited: wavePage.draftName=text; background: Rectangle { radius: 11; color: panel2; border.color: parent.activeFocus ? cyan : border } }
                                            AppButton { label: "保存到我的波形库"; fillColor: cyan; labelColor: "#10151A"; onClicked: backend.saveCustomWaveform(wavePage.draftName,wavePage.draftPoints,wavePage.draftFrequency) }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 160; radius: 15; color: darkMode ? "#0B1220" : "#F0F4F9"; border.color: border
                                            Canvas {
                                                id: customCanvas; anchors.fill: parent; anchors.margins: 14; antialiasing: true
                                                onPaint: { const ctx=getContext("2d");ctx.reset();const p=wavePage.draftPoints;if(!p||p.length<2)return;ctx.strokeStyle=darkMode?"#29364E":"#D7DFEA";ctx.lineWidth=1;for(let i=1;i<4;i++){let y=height*i/4;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y);ctx.stroke()}ctx.strokeStyle=cyan;ctx.lineWidth=3;ctx.lineJoin="round";ctx.beginPath();for(let i=0;i<p.length;i++){let x=i/(p.length-1)*width;let y=height-(p[i]/100)*height;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}ctx.stroke();for(let i=0;i<p.length;i++){let x=i/(p.length-1)*width;let y=height-(p[i]/100)*height;ctx.fillStyle=root.fg;ctx.beginPath();ctx.arc(x,y,4,0,Math.PI*2);ctx.fill()} }
                                                Connections { target: wavePage; function onDraftPointsChanged(){customCanvas.requestPaint()} }
                                                Connections { target: root; function onDarkModeChanged(){customCanvas.requestPaint()} }
                                                MouseArea { anchors.fill: parent; cursorShape: Qt.CrossCursor; function paint(mouse){let i=Math.round(Math.max(0,Math.min(1,mouse.x/width))*15);let v=(1-Math.max(0,Math.min(1,mouse.y/height)))*100;wavePage.setPoint(i,v)} onPressed: mouse=>paint(mouse); onPositionChanged: mouse=>{if(pressed)paint(mouse)} }
                                            }
                                        }
                                        Text { text: "按住鼠标在画布上拖动即可绘制；实际输出仍受强度范围和硬上限限制。"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        RowLayout { Layout.fillWidth: true; Text { text: "频率"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 } Slider { Layout.fillWidth: true; from: 10; to: 240; stepSize: 1; value: wavePage.draftFrequency; onMoved: wavePage.draftFrequency=Math.round(value) } Text { text: wavePage.draftFrequency+" Hz"; color: cyan; font.pixelSize: 11; font.weight: Font.DemiBold } }
                                        Item { Layout.fillHeight: true }
                                        RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: "固定保存位置：" + backend.waveformLibraryFolder; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; elide: Text.ElideMiddle } AppButton { label: "打开目录"; onClicked: backend.openWaveformLibraryFolder() } }
                                    }
                                }
                            }
                            Item { Layout.preferredHeight: 2 }
                            }
                        }
                    }

                    // A/B monitor ----------------------------------------------
                    RowLayout {
                        spacing: 15
                        Repeater {
                            model: [
                                {channel:"A",name:backend.waveAName,points:backend.waveAPoints,strength:backend.outputA,color:accent,detail:"心率驱动"},
                                {channel:"B",name:backend.waveBName,points:backend.waveBPoints,strength:backend.outputB,color:violet,detail:"动作反馈"}
                            ]
                            delegate: AppCard {
                                required property var modelData
                                Layout.fillWidth: true; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 24; spacing: 12
                                    RowLayout { Layout.fillWidth: true; Rectangle { width: 44; height: 44; radius: 14; color: Qt.rgba(modelData.color.r,modelData.color.g,modelData.color.b,0.14); Text { anchors.centerIn: parent; text: modelData.channel; color: modelData.color; font.pixelSize: 18; font.weight: Font.Bold } } Column { Layout.fillWidth: true; Text { text: modelData.channel+" 通道"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 16; font.weight: Font.DemiBold } Text { text: modelData.detail; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } } Text { text: modelData.strength.toFixed(1)+" / "+backend.hardCap; color: modelData.color; font.pixelSize: 13; font.weight: Font.Bold } }
                                    WaveView { Layout.fillWidth: true; Layout.fillHeight: true; points: modelData.points; waveColor: modelData.color; animated: !backend.outputPaused }
                                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 76; radius: 15; color: panel2; RowLayout { anchors.fill: parent; anchors.margins: 14; Column { Layout.fillWidth: true; Text { text: "当前选择"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } Text { text: modelData.name; color: modelData.color; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold } } Text { text: backend.outputPaused ? "已暂停" : backend.safetyIdle ? "安全待机" : "实时输出"; color: backend.outputPaused || backend.safetyIdle ? amber : green; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; font.weight: Font.DemiBold } } }
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
                                    SectionTitle { title: "当前存档数值"; detail: backend.currentSaveSlot >= 0 ? "手动槽位 " + (backend.currentSaveSlot + 1) : "未载入槽位" }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.preferredHeight: 92; radius: 16
                                        color: panel2; border.color: border
                                        RowLayout {
                                            anchors.fill: parent; anchors.margins: 18
                                            Column { Layout.fillWidth: true; spacing: 5; Text { text: "游戏货币 / RP"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } Text { text: Math.round(backend.currentRp).toLocaleString(Qt.locale("zh_CN"), "f", 0); color: amber; font.family: "Segoe UI"; font.pixelSize: 25; font.weight: Font.Bold } }
                                            Column { Layout.fillWidth: true; spacing: 5; Text { text: "经验值 / EXP"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } Text { text: backend.exposeExp.toLocaleString(Qt.locale("zh_CN"), "f", 0); color: cyan; font.family: "Segoe UI"; font.pixelSize: 25; font.weight: Font.Bold } }
                                        }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.preferredHeight: 64; radius: 14
                                        color: Qt.rgba((backend.canEditProgress ? green : amber).r, (backend.canEditProgress ? green : amber).g, (backend.canEditProgress ? green : amber).b, darkMode ? 0.08 : 0.10)
                                        border.color: Qt.rgba((backend.canEditProgress ? green : amber).r, (backend.canEditProgress ? green : amber).g, (backend.canEditProgress ? green : amber).b, 0.28)
                                        RowLayout { anchors.fill: parent; anchors.margins: 14; Rectangle { width: 9; height: 9; radius: 5; color: backend.canEditProgress ? green : amber } Column { Layout.fillWidth: true; Text { text: backend.canEditProgress ? "可以安全写入" : "写入暂时锁定"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold } Text { text: backend.progressEditorStatus; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; elide: Text.ElideRight; width: 360 } } }
                                    }
                                    Text { Layout.fillWidth: true; text: "为了避免游戏同时写入造成冲突，请先载入目标存档，再按 Esc 打开游戏菜单。每次修改前都会自动复制原始 .sd 文件。"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; wrapMode: Text.Wrap; lineHeight: 1.35 }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: border }
                                    Text { text: "备份位置"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                    Text { Layout.fillWidth: true; text: backend.saveBackupFolder; color: root.fg; font.family: "Cascadia Mono"; font.pixelSize: 9; wrapMode: Text.WrapAnywhere }
                                    Item { Layout.fillHeight: true }
                                    RowLayout { Layout.fillWidth: true; AppButton { label: "刷新当前数值"; onClicked: progressPage.readCurrent() } AppButton { label: "立即备份"; onClicked: backend.createSaveBackup() } Item { Layout.fillWidth: true } }
                                }
                            }
                            AppCard {
                                Layout.preferredWidth: 420; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 24; spacing: 13
                                    SectionTitle { title: "修改并保存"; detail: "0–999999999" }
                                    Text { text: "游戏货币 / RP"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                    TextField {
                                        Layout.fillWidth: true; Layout.preferredHeight: 50
                                        text: progressPage.draftRp; selectByMouse: true
                                        color: root.fg; font.family: "Segoe UI"; font.pixelSize: 16
                                        validator: DoubleValidator { bottom: 0; top: 999999999; decimals: 2 }
                                        background: Rectangle { radius: 13; color: panel2; border.color: parent.activeFocus ? amber : border }
                                        onTextEdited: progressPage.draftRp = text
                                    }
                                    Text { text: "经验值 / EXP"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                    TextField {
                                        Layout.fillWidth: true; Layout.preferredHeight: 50
                                        text: progressPage.draftExp; selectByMouse: true
                                        color: root.fg; font.family: "Segoe UI"; font.pixelSize: 16
                                        validator: IntValidator { bottom: 0; top: 999999999 }
                                        background: Rectangle { radius: 13; color: panel2; border.color: parent.activeFocus ? cyan : border }
                                        onTextEdited: progressPage.draftExp = text
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.preferredHeight: 132; radius: 14
                                        color: darkMode ? "#171522" : "#FFF7E7"; border.color: Qt.rgba(amber.r, amber.g, amber.b, 0.35)
                                        Column { anchors.fill: parent; anchors.margins: 14; spacing: 6; Text { text: "写入与升级条件"; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold } Text { width: parent.width; text: "① 角色位于室外（非室内）并已载入目标存档\n② 按 Esc 暂停游戏\n③ 使用最新版游戏插件\n经验写入后：完成任意任务，再回家触发结算才会升级。"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; lineHeight: 1.35; wrapMode: Text.Wrap } }
                                    }
                                    Item { Layout.fillHeight: true }
                                    AppButton { Layout.fillWidth: true; Layout.preferredHeight: 52; label: "备份、写入并保存"; fillColor: green; labelColor: "#10151A"; onClicked: progressConfirm.open() }
                                    Text { Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; text: "不会修改技能等级、解锁项目或任务进度"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 }
                                }
                            }
                        }
                    }

                    // Mod manager ---------------------------------------------
                    Item {
                        id: modPage
                        property string section: "recommended"
                        property string filterKind: "all"
                        property string searchText: ""
                        property string v1GuideSearch: ""
                        property var filteredInventory: {
                            let result = []
                            let query = searchText.trim().toLowerCase()
                            let source = backend.modInventory
                            for (let i = 0; i < source.length; ++i) {
                                let item = source[i]
                                if (filterKind !== "all" && item.kind !== filterKind) continue
                                let haystack = (item.name + " " + item.description + " " + item.warning).toLowerCase()
                                if (query.length && haystack.indexOf(query) < 0) continue
                                result.push(item)
                            }
                            return result
                        }
                        property var filteredV1Mods: {
                            let result = []
                            let query = v1GuideSearch.trim().toLowerCase()
                            let source = backend.modInventory
                            for (let i = 0; i < source.length; ++i) {
                                let item = source[i]
                                if (item.kind !== "v1") continue
                                let haystack = (item.name + " " + item.description + " " + item.locationArea + " " + item.location + " " + item.locationNote).toLowerCase()
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
                                Layout.minimumHeight: 186
                                Layout.preferredHeight: 186
                                Layout.maximumHeight: 186
                                spacing: 14
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 17; spacing: 9
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Rectangle { width: 42; height: 42; radius: 14; color: Qt.rgba(violet.r,violet.g,violet.b,0.14); Text { anchors.centerIn: parent; text: "⬡"; color: violet; font.pixelSize: 20; font.weight: Font.Bold } }
                                            Column { Layout.fillWidth: true; spacing: 3; Text { text: "Mod 来源与扫描"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: backend.modSummary; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } }
                                            Rectangle { width: 9; height: 9; radius: 5; color: backend.modStatus.indexOf("完成") >= 0 ? green : amber }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 44; radius: 11; color: panel2; border.color: border
                                            RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; Text { text: backend.modSourceFolder.indexOf("mod_repositories") >= 0 ? "内置" : "外部"; color: violet; font.family: "Microsoft YaHei UI"; font.pixelSize: 8; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; text: backend.modSourceFolder || "尚未选择 Mod 来源"; color: root.fg; font.family: "Cascadia Mono"; font.pixelSize: 8; elide: Text.ElideMiddle } }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 7
                                            AppButton { Layout.fillWidth: true; label: "内置仓库"; enabled: backend.bundledModsAvailable; fillColor: violet; labelColor: "#11151C"; onClicked: backend.useBundledMods() }
                                            AppButton { Layout.fillWidth: true; label: "外部整合包"; onClicked: modSourceDialog.open() }
                                            AppButton { Layout.fillWidth: true; label: "重新扫描"; onClicked: backend.scanMods() }
                                        }
                                        Text { Layout.fillWidth: true; text: "⚠ 修改开关前必须完全退出游戏"; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; horizontalAlignment: Text.AlignRight }
                                    }
                                }
                                AppCard {
                                    Layout.preferredWidth: 430; Layout.fillHeight: true
                                    color: darkMode ? "#111A29" : "#F5F8FC"
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 17; spacing: 8
                                        RowLayout { Layout.fillWidth: true; Rectangle { width: 42; height: 42; radius: 14; color: Qt.rgba(cyan.r,cyan.g,cyan.b,0.13); Text { anchors.centerIn: parent; text: "＋"; color: cyan; font.pixelSize: 22; font.weight: Font.Bold } } Column { Layout.fillWidth: true; Text { text: "Drop-in 收件箱"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: "DLL / V1 JSON / V2 文件夹 / ZIP"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 8 } } }
                                        Text { Layout.fillWidth: true; text: "导入路径：incoming → dropin_mods\\repository → 开启后同步到游戏"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap }
                                        Text { Layout.fillWidth: true; text: backend.dropInStatus + " · " + backend.dropInFolder; color: cyan; font.family: "Cascadia Mono"; font.pixelSize: 8; elide: Text.ElideMiddle }
                                        Item { Layout.fillHeight: true }
                                        RowLayout { Layout.fillWidth: true; spacing: 8; AppButton { Layout.fillWidth: true; label: "打开收件箱"; onClicked: backend.openDropInFolder() } AppButton { Layout.fillWidth: true; label: "导入并扫描"; fillColor: cyan; labelColor: "#10151A"; onClicked: backend.importDropIns() } }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true; spacing: 8
                                AppButton { Layout.preferredWidth: 142; label: "★ 推荐与前置"; fillColor: modPage.section === "recommended" ? accent : panel2; labelColor: modPage.section === "recommended" ? "#11151C" : root.fg; onClicked: modPage.section = "recommended" }
                                AppButton { Layout.preferredWidth: 116; label: "全部 Mod"; fillColor: modPage.section === "all" ? violet : panel2; labelColor: modPage.section === "all" ? "#11151C" : root.fg; onClicked: modPage.section = "all" }
                                AppButton { Layout.preferredWidth: 154; label: "⌖ V1 任务与地点"; fillColor: modPage.section === "v1guide" ? cyan : panel2; labelColor: modPage.section === "v1guide" ? "#11151C" : root.fg; onClicked: modPage.section = "v1guide" }
                                Text { Layout.fillWidth: true; text: modPage.section === "recommended" ? "先启用基础前置，再启用对应任务或功能包" : modPage.section === "v1guide" ? "搜索任务名称、地图区域或触发位置" : "查看、搜索和切换来源库中的全部内容"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; horizontalAlignment: Text.AlignRight }
                            }
                            StackLayout {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                currentIndex: modPage.section === "recommended" ? 0 : modPage.section === "all" ? 1 : 2
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 12; spacing: 9
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 54; radius: 13
                                            color: Qt.rgba(cyan.r,cyan.g,cyan.b,darkMode ? 0.08 : 0.10); border.color: Qt.rgba(cyan.r,cyan.g,cyan.b,0.25)
                                            RowLayout { anchors.fill: parent; anchors.margins: 12; Text { text: "依赖顺序"; color: cyan; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; text: "V1 任务 → CustomMission 1　　V2 包 → CustomMission 2"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } }
                                        }
                                        GridView {
                                            id: recommendedModList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                                            model: backend.recommendedModInventory
                                            cellWidth: width / 2; cellHeight: 114
                                            delegate: Rectangle {
                                                required property var modelData
                                                width: recommendedModList.cellWidth - 7; height: 106; radius: 15
                                                color: darkMode ? "#141E2F" : "#EDF2F8"
                                                border.color: modelData.enabled ? Qt.rgba(green.r,green.g,green.b,0.42) : border
                                                RowLayout {
                                                    anchors.fill: parent; anchors.margins: 14; spacing: 13
                                                    Rectangle { width: 46; height: 46; radius: 14; color: Qt.rgba((modelData.accent === "cyan" ? cyan : modelData.accent === "violet" ? violet : modelData.accent === "amber" ? amber : accent).r,(modelData.accent === "cyan" ? cyan : modelData.accent === "violet" ? violet : modelData.accent === "amber" ? amber : accent).g,(modelData.accent === "cyan" ? cyan : modelData.accent === "violet" ? violet : modelData.accent === "amber" ? amber : accent).b,0.14); Text { anchors.centerIn: parent; text: modelData.kind === "plugin" ? "DLL" : "V2"; color: modelData.accent === "cyan" ? cyan : modelData.accent === "violet" ? violet : modelData.accent === "amber" ? amber : accent; font.pixelSize: 10; font.weight: Font.Bold } }
                                                    ColumnLayout {
                                                        Layout.fillWidth: true; spacing: 3
                                                        RowLayout { Layout.fillWidth: true; Text { text: modelData.displayName; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold } Rectangle { width: roleText.width + 14; height: 21; radius: 7; color: panel2; Text { id: roleText; anchors.centerIn: parent; text: modelData.role; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 8 } } Item { Layout.fillWidth: true } Text { text: modelData.status; color: modelData.enabled ? green : modelData.available ? muted : red; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; font.weight: Font.DemiBold } }
                                                        Text { Layout.fillWidth: true; text: modelData.summary; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; elide: Text.ElideRight }
                                                        Text { Layout.fillWidth: true; visible: modelData.requiredPluginName && !modelData.dependencyReady; text: modelData.dependencyAvailable ? "⚠ 需要先启用 " + modelData.requiredPluginName : "⚠ 当前来源库缺少 " + modelData.requiredPluginName; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 }
                                                    }
                                                    Switch { checked: modelData.enabled; enabled: modelData.available; onClicked: backend.setModEnabled(modelData.id, checked); palette.highlight: green }
                                                }
                                            }
                                            ScrollBar.vertical: ScrollBar { contentItem: Rectangle { implicitWidth: 5; radius: 3; color: muted } background: Rectangle { color: "transparent" } }
                                        }
                                    }
                                }
                                Item {
                                    ColumnLayout {
                                        anchors.fill: parent; spacing: 10
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 8
                                            Repeater {
                                                model: [{key:"all",text:"全部"},{key:"plugin",text:"插件"},{key:"v1",text:"V1 任务"},{key:"v2",text:"V2 包"}]
                                                delegate: AppButton { required property var modelData; Layout.preferredWidth: 88; label: modelData.text; fillColor: modPage.filterKind === modelData.key ? accent : panel2; labelColor: modPage.filterKind === modelData.key ? "#11151C" : root.fg; onClicked: modPage.filterKind = modelData.key }
                                            }
                                            Item { Layout.fillWidth: true }
                                            TextField {
                                                Layout.preferredWidth: 300; Layout.preferredHeight: 42
                                                placeholderText: "搜索名称、说明或冲突…"; selectByMouse: true; color: root.fg; font.family: "Microsoft YaHei UI"
                                                onTextEdited: modPage.searchText = text
                                                background: Rectangle { radius: 12; color: panel; border.color: parent.activeFocus ? accent : border }
                                            }
                                        }
                                        AppCard {
                                            Layout.fillWidth: true; Layout.fillHeight: true
                                            GridView {
                                                id: modList; anchors.fill: parent; anchors.margins: 10; clip: true
                                                model: modPage.filteredInventory
                                                cellWidth: width / 2; cellHeight: 190
                                                delegate: Rectangle {
                                                    required property var modelData
                                                    width: modList.cellWidth - 7; height: 182; radius: 15
                                                    color: darkMode ? "#141E2F" : "#EDF2F8"; border.color: modelData.enabled ? Qt.rgba(green.r,green.g,green.b,0.40) : border
                                                    RowLayout {
                                                        anchors.fill: parent; anchors.margins: 14; spacing: 12
                                                        Rectangle {
                                                            Layout.alignment: Qt.AlignTop; width: 46; height: 46; radius: 14
                                                            color: Qt.rgba((modelData.kind === "plugin" ? violet : modelData.kind === "v1" ? cyan : accent).r,(modelData.kind === "plugin" ? violet : modelData.kind === "v1" ? cyan : accent).g,(modelData.kind === "plugin" ? violet : modelData.kind === "v1" ? cyan : accent).b,0.13)
                                                            Text { anchors.centerIn: parent; text: modelData.kind === "plugin" ? "DLL" : modelData.kind.toUpperCase(); color: modelData.kind === "plugin" ? violet : modelData.kind === "v1" ? cyan : accent; font.family: "Segoe UI"; font.pixelSize: 10; font.weight: Font.Bold }
                                                        }
                                                        ColumnLayout {
                                                            Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 5
                                                            RowLayout {
                                                                Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 7
                                                                Text { Layout.fillWidth: true; text: modelData.name; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold; wrapMode: Text.Wrap }
                                                                Rectangle { width: kindText.width+14; height: 22; radius: 7; color: panel2; Text { id: kindText; anchors.centerIn: parent; text: modelData.kindLabel + (modelData.fileCount > 1 ? " · " + modelData.fileCount : ""); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 8 } }
                                                                Text { text: modelData.status; color: modelData.enabled ? green : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; font.weight: Font.DemiBold }
                                                            }
                                                            Text { Layout.fillWidth: true; text: modelData.description; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap }
                                                            Text { Layout.fillWidth: true; visible: modelData.requiredPluginName && !modelData.dependencyReady; text: modelData.dependencyAvailable ? "⚠ 需要先启用 " + modelData.requiredPluginName : "⚠ 当前来源库缺少 " + modelData.requiredPluginName; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap }
                                                            Text { Layout.fillWidth: true; visible: modelData.warning.length > 0; text: "⚠ " + modelData.warning; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap }
                                                        }
                                                        Switch { checked: modelData.enabled; enabled: modelData.available; onClicked: backend.setModEnabled(modelData.id, checked); palette.highlight: green }
                                                    }
                                                }
                                                ScrollBar.vertical: ScrollBar { contentItem: Rectangle { implicitWidth: 5; radius: 3; color: muted } background: Rectangle { color: "transparent" } }
                                                footer: Item { width: 1; height: 8 }
                                            }
                                            Text { anchors.centerIn: parent; visible: modPage.filteredInventory.length === 0; text: backend.modInventory.length ? "没有符合筛选条件的项目" : "选择整合包目录后，这里会列出你拥有的 Mod"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 12 }
                                        }
                                    }
                                }
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 14; spacing: 10
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 12
                                            Rectangle { width: 46; height: 46; radius: 14; color: Qt.rgba(cyan.r,cyan.g,cyan.b,0.14); Text { anchors.centerIn: parent; text: "⌖"; color: cyan; font.pixelSize: 20; font.weight: Font.Bold } }
                                            Column { Layout.fillWidth: true; spacing: 3; Text { text: "CustomMission 1 任务与起始点"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: "每张卡可直接启用 Mod；有资料的任务同时显示地图起点"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } }
                                            TextField {
                                                Layout.preferredWidth: 320; Layout.preferredHeight: 42
                                                placeholderText: "例如：公园、家里、blackmail…"; selectByMouse: true; color: root.fg; font.family: "Microsoft YaHei UI"
                                                onTextEdited: modPage.v1GuideSearch = text
                                                background: Rectangle { radius: 12; color: panel2; border.color: parent.activeFocus ? cyan : border }
                                            }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 12
                                            color: Qt.rgba(amber.r,amber.g,amber.b,darkMode ? 0.07 : 0.10); border.color: Qt.rgba(amber.r,amber.g,amber.b,0.24)
                                            Text { anchors.fill: parent; anchors.margins: 11; verticalAlignment: Text.AlignVCenter; text: "部分系列会直接加入游戏的 Tab 任务列表，不一定在地图上显示独立起点。地点可能受任务版本、已启用章节和画质设置影响。"; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap }
                                        }
                                        GridView {
                                            id: v1LocationList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                                            model: modPage.filteredV1Mods
                                                cellWidth: width / 2; cellHeight: 198
                                            delegate: Rectangle {
                                                required property var modelData
                                                width: v1LocationList.cellWidth - 7; height: 190; radius: 14
                                                color: darkMode ? "#141E2F" : "#EDF2F8"; border.color: modelData.enabled ? Qt.rgba(green.r,green.g,green.b,0.42) : border
                                                RowLayout {
                                                    anchors.fill: parent; anchors.margins: 13; spacing: 12
                                                    Rectangle { Layout.alignment: Qt.AlignTop; width: 42; height: 42; radius: 13; color: Qt.rgba(cyan.r,cyan.g,cyan.b,0.13); Text { anchors.centerIn: parent; text: "V1"; color: cyan; font.family: "Segoe UI"; font.pixelSize: 9; font.weight: Font.Bold } }
                                                    ColumnLayout {
                                                        Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 4
                                                        RowLayout {
                                                            Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 7
                                                            Text { Layout.fillWidth: true; text: modelData.name; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; font.weight: Font.DemiBold; wrapMode: Text.Wrap }
                                                            Rectangle { visible: modelData.hasLocationGuide; width: areaText.width + 14; height: 20; radius: 7; color: panel2; Text { id: areaText; anchors.centerIn: parent; text: modelData.locationArea; color: cyan; font.family: "Microsoft YaHei UI"; font.pixelSize: 8 } }
                                                            Rectangle { width: countText.width + 14; height: 20; radius: 7; color: panel2; Text { id: countText; anchors.centerIn: parent; text: modelData.fileCount + " 个 JSON"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 8 } }
                                                            Text { text: modelData.status; color: modelData.enabled ? green : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; font.weight: Font.DemiBold }
                                                        }
                                                        Text { Layout.fillWidth: true; text: modelData.hasLocationGuide ? "⌖ " + modelData.location : "整理文件中没有这项 Mod 的地点记录"; color: modelData.hasLocationGuide ? root.fg : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap }
                                                        Text { Layout.fillWidth: true; visible: modelData.locationNote.length > 0; text: "⚠ " + modelData.locationNote; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 8; wrapMode: Text.Wrap }
                                                    }
                                                    Switch { checked: modelData.enabled; enabled: modelData.available; onClicked: backend.setModEnabled(modelData.id, checked); palette.highlight: green }
                                                }
                                            }
                                            ScrollBar.vertical: ScrollBar { contentItem: Rectangle { implicitWidth: 5; radius: 3; color: muted } background: Rectangle { color: "transparent" } }
                                        }
                                        Text { Layout.fillWidth: true; visible: modPage.filteredV1Mods.length === 0; text: "没有找到匹配的 V1 Mod 或地点"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter }
                                    }
                                }
                            }
                            Text { Layout.fillWidth: true; text: "第三方文件不会被打包进本软件。停用内容会保存在游戏目录的 ManakaModManager\\disabled，V2 存档与配置不会删除。"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap }
                        }
                    }

                    // Logs ------------------------------------------------------
                    AppCard {
                        color: panel
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 20; spacing: 12
                            RowLayout { Layout.fillWidth: true; Text { text: "最近 " + backend.logs.length + " 条记录"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } Item { Layout.fillWidth: true } AppButton { label: "清空日志"; onClicked: backend.clearLogs() } }
                            Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true; radius: 14
                                color: darkMode ? "#090E18" : "#F2F5FA"; border.color: border
                                ListView {
                                    id: logList; anchors.fill: parent; anchors.margins: 8; clip: true; model: backend.logs; spacing: 2
                                    delegate: Rectangle { required property var modelData; required property int index; width: logList.width; height: 34; radius: 8; color: index % 2 ? "transparent" : (darkMode ? "#111A2A" : "#E8EEF7"); Text { anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 10; text: modelData; color: darkMode ? "#E9EEF8" : "#182033"; font.family: "Cascadia Mono"; font.pixelSize: 11; elide: Text.ElideRight } }
                                    ScrollBar.vertical: ScrollBar { contentItem: Rectangle { implicitWidth: 5; radius: 3; color: muted } background: Rectangle { color: "transparent" } }
                                    onCountChanged: positionViewAtEnd()
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    FolderDialog { id: folderDialog; title: "选择游戏根目录"; onAccepted: backend.setGameFolder(selectedFolder.toString()) }
    FolderDialog { id: modSourceDialog; title: "选择已有 Mod 整合包的根目录"; onAccepted: backend.setModSourceFolder(selectedFolder.toString()) }

    Dialog {
        id: progressConfirm; anchors.centerIn: parent; modal: true; title: "确认修改当前存档"; standardButtons: Dialog.Yes | Dialog.No
        contentItem: Text { text: "将把游戏货币修改为 " + progressPage.draftRp + "，经验值修改为 " + progressPage.draftExp + "。\n软件会先创建备份，再调用游戏自己的保存流程。\n\n请确认角色当前位于室外（非室内）。经验写入后，需要完成任意任务并回家触发结算，等级才会刷新。"; color: root.fg; font.family: "Microsoft YaHei UI"; padding: 18; wrapMode: Text.Wrap }
        background: Rectangle { color: panel; border.color: border; radius: 16 }
        onAccepted: backend.applyProgressValues(progressPage.draftRp, progressPage.draftExp)
    }

    Popup {
        id: toast; x: root.width-width-24; y: root.height-height-24; width: 360; height: 104; modal: false; closePolicy: Popup.NoAutoClose
        property string toastTitle: ""; property string toastMessage: ""
        background: Rectangle { color: panel; border.color: border; radius: 17 }
        contentItem: Column { spacing: 6; Text { text: toast.toastTitle; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold } Text { width: 320; text: toast.toastMessage; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap } }
        Timer { id: toastTimer; interval: 3200; onTriggered: toast.close() }
    }
    Connections { target: backend; function onToastRequested(title,message){toast.toastTitle=title;toast.toastMessage=message;toast.open();toastTimer.restart()} }

    Dialog {
        id: agreementDialog
        anchors.centerIn: parent
        width: Math.min(760, root.width - 80)
        height: Math.min(650, root.height - 60)
        modal: true
        closePolicy: Popup.NoAutoClose
        padding: 0
        background: Rectangle { color: panel; border.color: border; border.width: 1; radius: 22 }
        contentItem: ColumnLayout {
            spacing: 0
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 82
                color: darkMode ? "#171322" : "#FFF2F6"
                radius: 22
                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 22; color: parent.color }
                Column { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 24; spacing: 4; Text { text: "使用协议与风险知情确认"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 20; font.weight: Font.Bold } Text { text: "请完整阅读；不同意不会启动任何设备连接服务"; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } }
            }
            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.margins: 18
                clip: true; contentWidth: availableWidth
                Text { width: parent.width; text: backend.agreementText; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; lineHeight: 1.45; wrapMode: Text.Wrap }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: border }
            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 76; Layout.leftMargin: 18; Layout.rightMargin: 18; spacing: 12
                AppButton { Layout.preferredWidth: 160; label: "不同意并退出"; fillColor: darkMode ? "#241822" : "#F4E3E8"; labelColor: red; onClicked: backend.declineAgreement() }
                Item { Layout.fillWidth: true }
                AppButton { Layout.preferredWidth: 210; label: "我已阅读并同意"; fillColor: accent; labelColor: "#10151A"; onClicked: { backend.acceptAgreement(); agreementDialog.close() } }
            }
        }
    }
    Component.onCompleted: { if (!backend.agreementAccepted) agreementDialog.open() }

    Timer { interval: 33; running: true; repeat: true; onTriggered: root.wavePhase=(root.wavePhase+0.006)%1 }
}
