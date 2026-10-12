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

    property int pageIndex: initialPageIndex >= 0 ? initialPageIndex : 0
    property bool darkMode: backend.theme !== "light"
    property real wavePhase: 0
    function t(source) {
        const languageDependency = backend.language
        return backend.translate(source)
    }
    property var pageTitles: [t("实时仪表盘"), t("设备与游戏"), t("个性化范围"), t("波形工作台"), t("A/B 波形监视"), t("存档工具"), t("Mod 管理器"), t("创意工坊"), t("事件记录")]
    property var pageSubtitles: [
        t("游戏状态、心率与设备输出总览"),
        t("安装游戏插件并使用 DG-LAB 3.0 扫码"),
        t("设置心率映射范围与安全硬上限"),
        t("选择官方预设或创建自定义波形"),
        t("查看两个通道当前选择的波形和实际强度"),
        t("安全修改当前存档的经验值与游戏货币"),
        t("管理你已有的插件、V1 任务与 V2 功能包"),
        t("从原作者页面发现任务、插件与工具"),
        t("检查连接、安全归零和游戏事件")
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

    component WaveComboBox: ComboBox {
        id: waveCombo
        property var selectedWave: currentIndex >= 0 && model && currentIndex < model.length ? model[currentIndex] : null
        implicitHeight: 52
        leftPadding: 10
        rightPadding: 38
        hoverEnabled: true
        font.family: "Microsoft YaHei UI"
        font.pixelSize: 11
        textRole: "name"
        background: Rectangle {
            radius: 12
            color: waveCombo.pressed ? Qt.darker(panel2, 1.08) : panel2
            border.color: waveCombo.popup.visible ? accent : border
        }
        contentItem: RowLayout {
            spacing: 9
            WaveView {
                Layout.preferredWidth: 86
                Layout.fillHeight: true
                points: waveCombo.selectedWave ? waveCombo.selectedWave.points : []
                waveColor: waveCombo.selectedWave ? waveCombo.selectedWave.color : muted
                animated: waveCombo.hovered && !waveCombo.popup.visible
            }
            Text {
                Layout.fillWidth: true
                text: waveCombo.selectedWave ? waveCombo.selectedWave.name : ""
                color: root.fg
                font: waveCombo.font
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }
        indicator: Text {
            x: waveCombo.width - width - 14
            anchors.verticalCenter: parent.verticalCenter
            text: waveCombo.popup.visible ? "⌃" : "⌄"
            color: waveCombo.popup.visible ? accent : muted
            font.pixelSize: 16
        }
        delegate: ItemDelegate {
            required property int index
            id: waveOption
            width: waveCombo.popup.width - 12
            height: 62
            leftPadding: 10
            rightPadding: 10
            HoverHandler { id: optionHover }
            contentItem: RowLayout {
                spacing: 10
                WaveView {
                    Layout.preferredWidth: 126
                    Layout.fillHeight: true
                    points: waveCombo.model[index] ? waveCombo.model[index].points : []
                    waveColor: waveCombo.model[index] ? waveCombo.model[index].color : muted
                    animated: optionHover.hovered
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text { Layout.fillWidth: true; text: waveCombo.textAt(index); color: root.fg; font: waveCombo.font; elide: Text.ElideRight }
                    Text { Layout.fillWidth: true; text: waveCombo.model[index] && waveCombo.model[index].frequency ? waveCombo.model[index].frequency + " Hz" : root.t("无输出"); color: muted; font.pixelSize: 9; elide: Text.ElideRight }
                }
            }
            background: Rectangle {
                radius: 9
                color: highlighted ? Qt.rgba(accent.r, accent.g, accent.b, darkMode ? 0.18 : 0.12) : optionHover.hovered ? Qt.rgba(cyan.r, cyan.g, cyan.b, darkMode ? 0.10 : 0.07) : "transparent"
            }
        }
        popup: Popup {
            x: Math.min(0, waveCombo.width - width)
            y: waveCombo.height + 5
            width: Math.max(waveCombo.width, 370)
            implicitHeight: Math.min(contentItem.implicitHeight + 12, 390)
            padding: 6
            background: Rectangle { radius: 13; color: panel; border.color: border }
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: waveCombo.popup.visible ? waveCombo.delegateModel : null
                currentIndex: waveCombo.highlightedIndex
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
        clip: true
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
                const cursor = (wavePhase % 1) * (total - 1)
                const sampleIndex = Math.floor(cursor)
                const nextIndex = Math.min(total - 1, sampleIndex + 1)
                const fraction = cursor - sampleIndex
                const firstSample = points[sampleIndex % points.length] / 100
                const nextSample = points[nextIndex % points.length] / 100
                const sample = firstSample + (nextSample - firstSample) * fraction
                const playX = 4 + cursor / (total - 1) * Math.max(0, w - 8)
                const playY = h * 0.82 - sample * h * 0.64
                ctx.fillStyle = waveColor
                ctx.beginPath(); ctx.arc(playX, playY, 4, 0, Math.PI * 2); ctx.fill()
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
                Text { Layout.leftMargin: 7; Layout.bottomMargin: 4; text: root.t("控制中心"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; font.letterSpacing: 1.3 }
                NavItem { targetPage: 0; iconText: "◈"; label: root.t("实时仪表盘") }
                NavItem { targetPage: 1; iconText: "⌁"; label: root.t("设备与游戏") }
                NavItem { targetPage: 2; iconText: "◫"; label: root.t("个性化范围") }
                NavItem { targetPage: 3; iconText: "〰"; label: root.t("波形工作台") }
                NavItem { targetPage: 4; iconText: "◉"; label: root.t("A/B 波形监视") }
                NavItem { targetPage: 5; iconText: "✦"; label: root.t("存档工具") }
                NavItem { targetPage: 6; iconText: "⬡"; label: root.t("Mod 管理器") }
                NavItem { targetPage: 7; iconText: "✧"; label: root.t("创意工坊") }
                NavItem { targetPage: 8; iconText: "◎"; label: root.t("事件记录") }
                Item { Layout.fillHeight: true }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 98; radius: 17
                    color: Qt.rgba((backend.telemetryOnline ? green : amber).r, (backend.telemetryOnline ? green : amber).g, (backend.telemetryOnline ? green : amber).b, darkMode ? 0.08 : 0.09)
                    border.color: Qt.rgba((backend.telemetryOnline ? green : amber).r, (backend.telemetryOnline ? green : amber).g, (backend.telemetryOnline ? green : amber).b, 0.24)
                    Column {
                        anchors.fill: parent; anchors.margins: 14; spacing: 6
                        Row { spacing: 7; Rectangle { width: 8; height: 8; radius: 4; color: backend.telemetryOnline ? green : amber; anchors.verticalCenter: parent.verticalCenter } Text { text: backend.telemetryStatus; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold } }
                        Text { text: backend.demoMode ? root.t("演示数据 · 无设备输出") : "10 Hz · Local UDP"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
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
                        Row { anchors.centerIn: parent; spacing: 7; Rectangle { width: 8; height: 8; radius: 4; color: backend.deviceConnected ? green : amber; anchors.verticalCenter: parent.verticalCenter } Text { text: backend.deviceConnected ? root.t("DG-LAB 已连接") : root.t("等待设备连接"); color: backend.deviceConnected ? green : amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; font.weight: Font.DemiBold } }
                    }
                    AppButton { Layout.leftMargin: 8; Layout.preferredWidth: 76; label: backend.language === "zh" ? "EN" : "中文"; onClicked: backend.setLanguage(backend.language === "zh" ? "en" : "zh") }
                    AppButton { Layout.leftMargin: 4; Layout.preferredWidth: 94; label: darkMode ? root.t("☀  日间") : root.t("☾  夜间"); onClicked: { darkMode = !darkMode; backend.setTheme(darkMode ? "dark" : "light") } }
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
                                        Connections { target: backend; function onStateChanged(){ gauge.requestPaint() } }
                                        Connections { target: root; function onDarkModeChanged(){ gauge.requestPaint() } }
                                    }
                                    Column { anchors.centerIn: parent; spacing: -4; Text { anchors.horizontalCenter: parent.horizontalCenter; text: Math.round(backend.heartRate); color: root.fg; font.family: "Segoe UI Variable Display"; font.pixelSize: 56; font.weight: Font.Bold } Text { anchors.horizontalCenter: parent.horizontalCenter; text: "BPM"; color: accent; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 2.2 } }
                                }
                                Text { text: backend.stage + "  ·  " + backend.actionDisplay; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; Layout.alignment: Qt.AlignHCenter }
                            }
                        }
                        AppCard {
                            Layout.columnSpan: 5; Layout.rowSpan: 7; Layout.fillWidth: true; Layout.fillHeight: true
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 22; spacing: 8
                                SectionTitle { title: root.t("输出通道"); detail: root.t("安全上限 ") + backend.hardCap }
                                Text { text: backend.deviceStatus; color: backend.safetyIdle || backend.outputPaused ? amber : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                MetricBar { Layout.fillWidth: true; label: root.t("A · 心跳 Pulse"); valueText: backend.outputA.toFixed(1) + " / " + backend.hardCap; value: backend.outputA; maximum: backend.hardCap; barColor: accent }
                                MetricBar { Layout.fillWidth: true; label: root.t("B · 动作反馈"); valueText: backend.outputB.toFixed(1) + " / " + backend.hardCap; value: backend.outputB; maximum: backend.hardCap; barColor: violet }
                                Item { Layout.fillHeight: true }
                                Rectangle {
                                    Layout.fillWidth: true; Layout.preferredHeight: 68; radius: 15; color: panel2
                                    RowLayout { anchors.fill: parent; anchors.margins: 13; Column { Layout.fillWidth: true; Text { text: root.t("当前波形"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } Text { text: backend.waveAName; color: cyan; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; font.weight: Font.DemiBold } } Text { text: backend.waveMode === "smart" ? root.t("智能策略") : root.t("固定预设"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } }
                                }
                            }
                        }
                        AppCard {
                            Layout.columnSpan: 3; Layout.rowSpan: 7; Layout.fillWidth: true; Layout.fillHeight: true
                            color: backend.outputPaused ? Qt.rgba(amber.r,amber.g,amber.b,darkMode?0.08:0.10) : panel
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 21; spacing: 9
                                Text { text: root.t("会话控制"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                Text { text: backend.outputPaused ? root.t("输出已经归零\n设备连接保持不变") : root.t("随时暂停 A/B 输出\n再次点击即可继续"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; lineHeight: 1.45 }
                                Item { Layout.fillHeight: true }
                                Rectangle {
                                    Layout.alignment: Qt.AlignHCenter; width: 116; height: 116; radius: 58
                                    color: backend.outputPaused ? green : backend.deviceConnected ? amber : panel2
                                    scale: pauseHit.containsMouse ? 1.04 : 1
                                    Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                                    Column { anchors.centerIn: parent; spacing: 4; Text { anchors.horizontalCenter: parent.horizontalCenter; text: backend.outputPaused ? "▶" : "Ⅱ"; color: "#11151C"; font.pixelSize: 30; font.weight: Font.Bold } Text { anchors.horizontalCenter: parent.horizontalCenter; text: backend.outputPaused ? root.t("继续输出") : root.t("暂停输出"); color: backend.deviceConnected ? "#11151C" : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.Bold } }
                                    MouseArea { id: pauseHit; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: backend.toggleOutput() }
                                }
                                Item { Layout.fillHeight: true }
                                Text { Layout.alignment: Qt.AlignHCenter; text: backend.outputPaused ? "PAUSED" : backend.safetyIdle ? "SAFETY IDLE" : "OUTPUT ACTIVE"; color: backend.outputPaused || backend.safetyIdle ? amber : green; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1.4 }
                            }
                        }
                        AppCard {
                            Layout.columnSpan: 8; Layout.rowSpan: 5; Layout.fillWidth: true; Layout.fillHeight: true
                            ColumnLayout { anchors.fill: parent; anchors.margins: 20; spacing: 7; SectionTitle { title: root.t("实时波形"); detail: root.t("A 通道 · ") + backend.waveAName } WaveView { Layout.fillWidth: true; Layout.fillHeight: true; points: backend.waveAPoints; waveColor: accent; animated: !backend.outputPaused } }
                        }
                        AppCard {
                            Layout.columnSpan: 4; Layout.rowSpan: 5; Layout.fillWidth: true; Layout.fillHeight: true
                            ColumnLayout { anchors.fill: parent; anchors.margins: 20; spacing: 8; SectionTitle { title: root.t("场景状态"); detail: backend.stage } MetricBar { Layout.fillWidth: true; label: root.t("NPC 警觉度"); valueText: Math.round(backend.alertLevel)+"%"; value: backend.alertLevel; barColor: amber } MetricBar { Layout.fillWidth: true; label: root.t("兴奋度"); valueText: Math.round(backend.excitement)+"%"; value: backend.excitement; barColor: violet } Item { Layout.fillHeight: true } Text { text: root.t("当前动作    ") + backend.actionDisplay; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } }
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
                                        Text { text: root.t("请选择能直接看到 SecretFlasherManaka.exe 的文件夹。\n不要选择 BepInEx、plugins 或游戏 Data 文件夹。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        TextField { Layout.fillWidth: true; text: backend.gameFolder; color: root.fg; font.family: "Microsoft YaHei UI"; selectByMouse: true; placeholderText: root.t("游戏根目录"); background: Rectangle { radius: 12; color: panel2; border.color: border } onEditingFinished: backend.setGameFolder(text) }
                                        Text { text: backend.gameStatus; color: backend.gameStatus.indexOf("就绪") >= 0 ? green : amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        RowLayout { Layout.fillWidth: true; AppButton { label: root.t("选择目录"); onClicked: folderDialog.open() } AppButton { label: root.t("安装 / 修复运行环境"); onClicked: backend.installPlugin() } }
                                        AppButton { Layout.fillWidth: true; Layout.preferredHeight: 48; label: root.t("一键安装并启动游戏"); fillColor: accent; labelColor: "#11151C"; onClicked: backend.installAndLaunch() }
                                        Item { Layout.fillHeight: true }
                                        Text { text: root.t("纯原版无需预装 BepInEx；安装器会配置已验证的 v1.1.3 运行环境与独立遥测插件。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                    }
                                }
                                AppCard {
                                    Layout.preferredWidth: 400; Layout.fillHeight: true
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: 22; spacing: 18
                                        ColumnLayout { Layout.fillWidth: true; Text { text: "DG-LAB Socket"; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 16; font.weight: Font.DemiBold } Text { text: backend.deviceStatus; color: backend.deviceConnected ? green : amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true } Item { Layout.fillHeight: true } Text { text: backend.lanAddress; color: muted; font.pixelSize: 10 } AppButton { visible: !backend.deviceConnected; Layout.preferredWidth: 136; label: root.t("连接不上？"); fillColor: Qt.rgba(amber.r,amber.g,amber.b,darkMode?0.18:0.12); labelColor: amber; onClicked: networkHelpDialog.open() } }
                                        Rectangle { Layout.preferredWidth: 210; Layout.preferredHeight: 210; radius: 14; color: "white"; Image { anchors.fill: parent; anchors.margins: 8; source: backend.qrSource; fillMode: Image.PreserveAspectFit; visible: source !== "" } Text { anchors.centerIn: parent; visible: backend.qrSource === ""; text: backend.demoMode ? root.t("演示模式\n不生成二维码") : root.t("正在生成二维码…"); horizontalAlignment: Text.AlignHCenter; color: "#4B5565"; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 } }
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
                                        Text { text: root.t("快速预设"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                        Item { Layout.fillWidth: true }
                                        AppButton { label: root.t("低 · 5–30"); onClicked: { personalPage.draftTrigger=90; personalPage.draftFull=160; personalPage.draftMin=5; personalPage.draftMax=30 } }
                                        AppButton { label: root.t("中 · 5–50"); fillColor: Qt.rgba(violet.r,violet.g,violet.b,darkMode?0.20:0.13); onClicked: { personalPage.draftTrigger=85; personalPage.draftFull=160; personalPage.draftMin=5; personalPage.draftMax=50 } }
                                        AppButton { label: root.t("高 · 10–90"); fillColor: Qt.rgba(red.r,red.g,red.b,darkMode?0.20:0.13); onClicked: { personalPage.draftTrigger=80; personalPage.draftFull=160; personalPage.draftMin=10; personalPage.draftMax=90 } }
                                    }
                                    Text { text: root.t("预设只填写心率和日常输出范围，不会改变安全硬上限；点击底部“应用并保存”后生效。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                    SectionTitle { title: root.t("心率触发范围"); detail: personalPage.draftTrigger + " – " + personalPage.draftFull + " BPM" }
                                    Text { text: root.t("左端开始输出，右端达到设定的日常最高强度。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                                    RangeSlider { Layout.fillWidth: true; from: 60; to: 160; stepSize: 1; first.value: personalPage.draftTrigger; second.value: personalPage.draftFull; first.onMoved: personalPage.draftTrigger = Math.round(first.value); second.onMoved: personalPage.draftFull = Math.round(second.value) }
                                    RowLayout { Layout.fillWidth: true; Text { text: "60 BPM"; color: muted; font.pixelSize: 10 } Item { Layout.fillWidth: true } Text { text: "160 BPM"; color: muted; font.pixelSize: 10 } }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: border }
                                    SectionTitle { title: root.t("输出强度范围"); detail: personalPage.draftMin + " – " + personalPage.draftMax }
                                    Text { text: root.t("心率在触发区间升高时，强度会在此范围内平滑变化。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                                    RangeSlider { Layout.fillWidth: true; from: 0; to: 100; stepSize: 1; first.value: personalPage.draftMin; second.value: personalPage.draftMax; first.onMoved: personalPage.draftMin = Math.round(first.value); second.onMoved: personalPage.draftMax = Math.round(second.value) }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: border }
                                    SectionTitle { title: root.t("安全硬上限"); detail: personalPage.draftCap + " / 100" }
                                    Text { text: root.t("独立于上方预设；实际输出、Climax 和设备命令都不能突破此值。初始推荐 30。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                                    Slider { Layout.fillWidth: true; from: 1; to: 100; stepSize: 1; value: personalPage.draftCap; onMoved: personalPage.draftCap = Math.round(value) }
                                    Item { Layout.fillHeight: true }
                                    RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } AppButton { label: root.t("恢复当前设置"); onClicked: { personalPage.draftTrigger=backend.triggerBpm; personalPage.draftFull=backend.fullBpm; personalPage.draftMin=backend.minStrength; personalPage.draftMax=backend.outputMax; personalPage.draftCap=backend.hardCap } } AppButton { label: root.t("应用并保存"); fillColor: green; labelColor: "#10151A"; onClicked: { if (personalPage.draftCap > 30 && personalPage.draftCap > backend.hardCap) capConfirm.open(); else backend.savePersonalSettings(personalPage.draftTrigger,personalPage.draftFull,personalPage.draftMin,personalPage.draftMax,personalPage.draftCap,false) } } }
                                }
                            }
                        }
                        Dialog {
                            id: capConfirm; anchors.centerIn: parent; modal: true; title: root.t("提高安全硬上限"); standardButtons: Dialog.Yes | Dialog.No
                            contentItem: Text { text: root.t("你正在把安全硬上限提高到 30 以上。\n请先确认个人可承受范围，并从低强度逐步测试。"); color: root.fg; font.family: "Microsoft YaHei UI"; padding: 18 }
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
                        property string catalogFilter: "all"
                        property string actionFilter: "all"
                        property string actionSearch: ""
                        property var editHistory: []
                        property int editHistoryIndex: -1
                        property var filteredCatalog: {
                            let values = []
                            for (let i = 0; i < backend.waveformCatalog.length; ++i) {
                                let item = backend.waveformCatalog[i]
                                if (catalogFilter === "all" || item.group === catalogFilter) values.push(item)
                            }
                            return values
                        }
                        property var filteredActions: {
                            let values = []
                            let query = actionSearch.trim().toLowerCase()
                            for (let i = 0; i < backend.actionWaveMappings.length; ++i) {
                                let item = backend.actionWaveMappings[i]
                                if (actionFilter !== "all" && item.style !== actionFilter) continue
                                if (query.length && item.action.toLowerCase().indexOf(query) < 0 && item.actionLabel.toLowerCase().indexOf(query) < 0 && item.waveName.toLowerCase().indexOf(query) < 0) continue
                                values.push(item)
                            }
                            return values
                        }
                        function presetIndex(key) { for (let i=0;i<backend.presets.length;i++) if (backend.presets[i].key===key) return i; return 0 }
                        function optionIndex(key) { for (let i=0;i<backend.assignableWaveforms.length;i++) if (backend.assignableWaveforms[i].key===key) return i; return 0 }
                        function waveOption(key) { for (let i=0;i<backend.assignableWaveforms.length;i++) if (backend.assignableWaveforms[i].key===key) return backend.assignableWaveforms[i]; return backend.assignableWaveforms[0] }
                        function activeActionWave() { for (let i=0;i<backend.actionWaveMappings.length;i++) if (backend.actionWaveMappings[i].action===backend.action) return backend.actionWaveMappings[i]; return ({waveName:root.t("关闭 B 通道"),points:[0,0,0,0],color:muted}) }
                        function resetHeartMapping() { let copy=Object.assign({},draftMap);copy.low="official_breath";copy.mid="official_heartbeat";copy.high="official_pulsating";copy.peak="climax";draftMap=copy }
                        function setPoint(index,value) { let copy=draftPoints.slice(); copy[index]=Math.max(0,Math.min(100,Math.round(value))); draftPoints=copy }
                        function resetEditHistory() { editHistory=[draftPoints.slice()]; editHistoryIndex=0 }
                        function commitEditHistory() { let copy=editHistory.slice(0,editHistoryIndex+1); copy.push(draftPoints.slice()); editHistory=copy; editHistoryIndex=copy.length-1 }
                        function undoEdit() { if(editHistoryIndex>0){editHistoryIndex--;draftPoints=editHistory[editHistoryIndex].slice()} }
                        function redoEdit() { if(editHistoryIndex+1<editHistory.length){editHistoryIndex++;draftPoints=editHistory[editHistoryIndex].slice()} }
                        function applyPoints(points) { draftPoints=points.slice(); commitEditHistory() }
                        function applyTemplate(key) {
                            if(key==="breath") applyPoints([0,8,20,38,60,82,100,88,70,48,28,12,0,0,0,0])
                            else if(key==="heartbeat") applyPoints([0,100,24,0,62,12,0,0,0,100,24,0,62,12,0,0])
                            else if(key==="ramp") applyPoints([0,7,14,21,28,35,42,50,58,66,74,82,90,100,55,0])
                            else if(key==="steps") applyPoints([12,12,30,30,48,48,66,66,84,84,100,100,65,42,20,0])
                            else applyPoints([0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0])
                        }
                        function smoothPoints() { let source=draftPoints.slice();let out=source.slice();for(let i=1;i<source.length-1;i++)out[i]=Math.round((source[i-1]+source[i]*2+source[i+1])/4);applyPoints(out) }
                        function mirrorPoints() { applyPoints(draftPoints.slice().reverse()) }
                        function normalizePoints() { let high=Math.max.apply(Math,draftPoints);if(high<=0)return;applyPoints(draftPoints.map(value=>Math.round(value/high*100))) }
                        function openNewEditor() { draftName=backend.nextCustomWaveformName;draftPoints=[0,18,48,82,100,58,20,0,0,25,68,45,15,0,0,0];draftFrequency=92;resetEditHistory();waveformEditor.open() }
                        function openWaveEditor(name,points,frequency) { draftName=name;draftPoints=points.slice();draftFrequency=frequency;resetEditHistory();waveformEditor.open() }
                        function restoreDefaults() {
                            draftMode="smart"; draftFixed="official_heartbeat"
                            draftMap={low:"official_breath",mid:"official_heartbeat",high:"official_pulsating",action:"official_tide",peak:"climax"}
                            draftName=root.t("我的波形"); draftPoints=[0,18,48,82,100,58,20,0,0,25,68,45,15,0,0,0]; draftFrequency=92
                            backend.resetWaveSettings()
                        }
                        ScrollView {
                            anchors.fill: parent; clip: true; contentWidth: availableWidth
                            ColumnLayout {
                            width: parent.width; spacing: 15
                            RowLayout {
                                Layout.fillWidth: true; Layout.preferredHeight: 46
                                AppButton { label: root.t("智能分段"); fillColor: wavePage.draftMode === "smart" ? accent : panel2; labelColor: wavePage.draftMode === "smart" ? "#11151C" : root.fg; onClicked: wavePage.draftMode="smart" }
                                AppButton { label: root.t("固定预设"); fillColor: wavePage.draftMode === "fixed" ? accent : panel2; labelColor: wavePage.draftMode === "fixed" ? "#11151C" : root.fg; onClicked: wavePage.draftMode="fixed" }
                                Item { Layout.fillWidth: true }
                                AppButton { label: root.t("一键恢复默认"); onClicked: wavePage.restoreDefaults() }
                                AppButton { label: root.t("保存波形策略"); fillColor: green; labelColor: "#11151C"; onClicked: backend.saveWaveSettings(wavePage.draftMode,wavePage.draftFixed,wavePage.draftMap.low,wavePage.draftMap.mid,wavePage.draftMap.high,wavePage.draftMap.action,wavePage.draftMap.peak,wavePage.draftName,wavePage.draftPoints,wavePage.draftFrequency) }
                            }
                            AppCard {
                                Layout.fillWidth: true; Layout.preferredHeight: 282
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 16; spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionTitle { title: root.t("波形预设与我的波形库"); detail: wavePage.filteredCatalog.length + root.t(" 个波形") }
                                        Repeater {
                                            model: [{key:"all",label:root.t("全部")},{key:"official",label:root.t("官方波形")},{key:"custom",label:root.t("自定义波形")},{key:"builtin",label:root.t("内置波形")}]
                                            delegate: AppButton { required property var modelData; Layout.preferredWidth: 92; Layout.preferredHeight: 34; label: modelData.label; fillColor: wavePage.catalogFilter===modelData.key ? accent : panel2; labelColor: wavePage.catalogFilter===modelData.key ? "#10151A" : root.fg; onClicked: wavePage.catalogFilter=modelData.key }
                                        }
                                    }
                                    ListView {
                                        id: waveformCatalogList
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        orientation: ListView.Horizontal; spacing: 10; clip: true; interactive: true
                                        boundsBehavior: Flickable.StopAtBounds
                                        model: wavePage.filteredCatalog
                                        delegate: Rectangle {
                                            required property var modelData
                                            id: waveformCard
                                            width: 250; height: waveformCatalogList.height; radius: 13
                                            z: waveformHover.hovered ? 2 : 1
                                            scale: waveformHover.hovered ? 1.018 : 1
                                            color: waveformHover.hovered ? Qt.lighter(panel2, 1.08) : panel2
                                            border.color: modelData.group === "custom" ? Qt.rgba(cyan.r,cyan.g,cyan.b,0.55) : waveformHover.hovered ? modelData.color : border
                                            Behavior on scale { NumberAnimation { duration: 120 } }
                                            HoverHandler { id: waveformHover }
                                            ColumnLayout {
                                                anchors.fill: parent; anchors.margins: 10; spacing: 4
                                                RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: modelData.name; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold; elide: Text.ElideRight } Text { text: modelData.group === "custom" ? root.t("自定义") : modelData.source; color: modelData.group === "custom" ? cyan : muted; font.pixelSize: 8 } }
                                                WaveView { Layout.fillWidth: true; Layout.fillHeight: true; points: modelData.points; waveColor: modelData.color; animated: waveformHover.hovered }
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    Text { Layout.fillWidth: true; text: modelData.frequency + " Hz"; color: muted; font.pixelSize: 9 }
                                                    Text { visible: modelData.group !== "custom"; text: waveformHover.hovered ? root.t("正在预览") : root.t("悬停预览"); color: waveformHover.hovered ? modelData.color : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 }
                                                    AppButton { visible: modelData.group === "custom"; Layout.preferredWidth: 88; label: root.t("载入编辑"); onClicked: wavePage.openWaveEditor(modelData.name,modelData.points,modelData.frequency) }
                                                    AppButton { visible: modelData.group === "custom"; Layout.preferredWidth: 62; label: root.t("删除"); fillColor: Qt.rgba(red.r,red.g,red.b,darkMode?0.18:0.10); labelColor: red; onClicked: backend.deleteCustomWaveform(modelData.id) }
                                                }
                                            }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true; Layout.preferredHeight: 32
                                        Text { text: root.t("拖动卡片区域或使用滚轮浏览"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 }
                                        Item { Layout.fillWidth: true }
                                        AppButton { Layout.preferredWidth: 54; label: "‹"; onClicked: waveformCatalogList.contentX=Math.max(0,waveformCatalogList.contentX-260) }
                                        AppButton { Layout.preferredWidth: 54; label: "›"; onClicked: waveformCatalogList.contentX=Math.min(Math.max(0,waveformCatalogList.contentWidth-waveformCatalogList.width),waveformCatalogList.contentX+260) }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true; Layout.preferredHeight: 330; spacing: 15
                                AppCard {
                                    Layout.preferredWidth: 410; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 20; spacing: 10
                                        SectionTitle { title: wavePage.draftMode === "smart" ? root.t("通道策略") : root.t("固定波形"); detail: wavePage.draftMode === "smart" ? "A / B" : root.t("始终使用") }
                                        WaveComboBox { visible: wavePage.draftMode === "fixed"; Layout.fillWidth: true; Layout.preferredHeight: 62; model: backend.presets; currentIndex: wavePage.presetIndex(wavePage.draftFixed); onActivated: wavePage.draftFixed=backend.presets[currentIndex].key }
                                        Item { visible: wavePage.draftMode === "fixed"; Layout.fillHeight: true }
                                        Rectangle {
                                            visible: wavePage.draftMode === "smart"; Layout.fillWidth: true; Layout.fillHeight: true; radius: 15; color: panel2; border.color: cyan
                                            RowLayout { anchors.fill: parent; anchors.margins: 13; spacing: 11; Rectangle { width: 46; height: 46; radius: 14; color: Qt.rgba(cyan.r,cyan.g,cyan.b,0.15); Text { anchors.centerIn: parent; text: "A"; color: cyan; font.pixelSize: 19; font.weight: Font.Bold } } ColumnLayout { Layout.fillWidth: true; spacing: 2; Text { text: root.t("A 通道 · 心率"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: root.t("低、中、高心率与 Climax"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } } WaveView { Layout.preferredWidth: 112; Layout.fillHeight: true; points: wavePage.waveOption(wavePage.draftMap.mid).points; waveColor: cyan; animated: channelAHover.hovered } Text { text: "›"; color: cyan; font.pixelSize: 24 } }
                                            HoverHandler { id: channelAHover }
                                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: heartMappingDialog.open() }
                                        }
                                        Rectangle {
                                            visible: wavePage.draftMode === "smart"; Layout.fillWidth: true; Layout.fillHeight: true; radius: 15; color: panel2; border.color: backend.action !== "None" ? violet : border
                                            RowLayout { anchors.fill: parent; anchors.margins: 13; spacing: 11; Rectangle { width: 46; height: 46; radius: 14; color: Qt.rgba(violet.r,violet.g,violet.b,0.15); Text { anchors.centerIn: parent; text: "B"; color: violet; font.pixelSize: 19; font.weight: Font.Bold } } ColumnLayout { Layout.fillWidth: true; spacing: 2; Text { text: root.t("B 通道 · 动作"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: backend.action === "None" ? root.t("等待游戏动作") : backend.actionDisplay; color: backend.action === "None" ? muted : violet; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; elide: Text.ElideRight } } WaveView { Layout.preferredWidth: 112; Layout.fillHeight: true; points: wavePage.activeActionWave().points; waveColor: wavePage.activeActionWave().color; animated: channelBHover.hovered } Text { text: "›"; color: violet; font.pixelSize: 24 } }
                                            HoverHandler { id: channelBHover }
                                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: actionMappingDialog.open() }
                                        }
                                    }
                                }
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 20; spacing: 10
                                        SectionTitle { title: root.t("自定义波形设计器"); detail: root.t("独立窗口编辑") }
                                        Rectangle {
                                            id: customSummary; Layout.fillWidth: true; Layout.fillHeight: true; radius: 15; color: darkMode ? "#0B1220" : "#F0F4F9"; border.color: customSummaryHover.hovered ? cyan : border
                                            HoverHandler { id: customSummaryHover }
                                            ColumnLayout { anchors.fill: parent; anchors.margins: 14; spacing: 7; RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: wavePage.draftName; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold; elide: Text.ElideRight } Text { text: wavePage.draftFrequency+" Hz"; color: cyan; font.pixelSize: 10 } } WaveView { Layout.fillWidth: true; Layout.fillHeight: true; points: wavePage.draftPoints; waveColor: cyan; animated: customSummaryHover.hovered } Text { Layout.fillWidth: true; text: root.t("悬停查看播放位置；打开编辑器可使用模板、平滑、镜像与撤销。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap } }
                                        }
                                        RowLayout { Layout.fillWidth: true; AppButton { Layout.fillWidth: true; label: root.t("新建波形"); onClicked: wavePage.openNewEditor() } AppButton { Layout.fillWidth: true; label: root.t("编辑当前波形"); fillColor: cyan; labelColor: "#10151A"; onClicked: wavePage.openWaveEditor(wavePage.draftName,wavePage.draftPoints,wavePage.draftFrequency) } AppButton { Layout.preferredWidth: 96; label: root.t("打开目录"); onClicked: backend.openWaveformLibraryFolder() } }
                                    }
                                }
                            }
                            Item { Layout.preferredHeight: 2 }
                            }
                        }

                        Dialog {
                            id: heartMappingDialog
                            anchors.centerIn: parent; width: Math.min(780,root.width-90); height: Math.min(590,root.height-70); modal: true; padding: 0
                            background: Rectangle { color: panel; border.color: border; radius: 20 }
                            contentItem: ColumnLayout {
                                anchors.fill: parent; anchors.margins: 22; spacing: 12
                                RowLayout { Layout.fillWidth: true; ColumnLayout { spacing: 3; Text { text: root.t("A 通道 · 心率波形"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 22; font.weight: Font.Bold } Text { text: root.t("为低、中、高心率和 Climax 分别选择波形"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } } Item { Layout.fillWidth: true } AppButton { Layout.preferredWidth: 110; label: root.t("恢复推荐"); onClicked: wavePage.resetHeartMapping() } AppButton { Layout.preferredWidth: 84; label: root.t("关闭"); onClicked: heartMappingDialog.close() } }
                                Repeater {
                                    model: [{key:"low",label:root.t("低心率段"),detail:root.t("轻柔起步")},{key:"mid",label:root.t("中心率段"),detail:root.t("稳定节奏")},{key:"high",label:root.t("高心率段"),detail:root.t("高频输出")},{key:"peak",label:"Climax",detail:root.t("峰值包络")}]
                                    delegate: Rectangle {
                                        required property var modelData
                                        Layout.fillWidth: true; Layout.fillHeight: true; radius: 14; color: panel2; border.color: modelData.key==="peak"?accent:border
                                        RowLayout { anchors.fill: parent; anchors.margins: 12; spacing: 13; ColumnLayout { Layout.preferredWidth: 150; spacing: 3; Text { text: modelData.label; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold } Text { text: modelData.detail; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } } WaveComboBox { Layout.fillWidth: true; model: backend.presets; currentIndex: wavePage.presetIndex(wavePage.draftMap[modelData.key]); onActivated: { let copy=Object.assign({},wavePage.draftMap);copy[modelData.key]=backend.presets[currentIndex].key;wavePage.draftMap=copy } } }
                                    }
                                }
                                Text { Layout.fillWidth: true; text: root.t("修改后返回波形工作台，点击“保存波形策略”生效。"); color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; horizontalAlignment: Text.AlignRight }
                            }
                        }

                        Dialog {
                            id: waveformEditor
                            anchors.centerIn: parent; width: Math.min(980,root.width-70); height: Math.min(690,root.height-50); modal: true; padding: 0
                            background: Rectangle { color: panel; border.color: border; radius: 20 }
                            contentItem: ColumnLayout {
                                anchors.fill: parent; anchors.margins: 22; spacing: 12
                                RowLayout { Layout.fillWidth: true; ColumnLayout { spacing: 3; Text { text: root.t("自定义波形编辑器"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 22; font.weight: Font.Bold } Text { text: root.t("从模板开始，或直接在大画布上绘制 16 点包络"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } } Item { Layout.fillWidth: true } AppButton { Layout.preferredWidth: 90; label: root.t("关闭"); onClicked: waveformEditor.close() } }
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 8
                                    TextField { Layout.fillWidth: true; Layout.preferredHeight: 42; text: wavePage.draftName; placeholderText: backend.nextCustomWaveformName; selectByMouse: true; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; onTextEdited: wavePage.draftName=text; background: Rectangle { radius: 11; color: panel2; border.color: parent.activeFocus ? cyan : border } }
                                    AppButton { Layout.preferredWidth: 88; label: root.t("呼吸"); onClicked: wavePage.applyTemplate("breath") }
                                    AppButton { Layout.preferredWidth: 88; label: root.t("心跳"); onClicked: wavePage.applyTemplate("heartbeat") }
                                    AppButton { Layout.preferredWidth: 88; label: root.t("渐强"); onClicked: wavePage.applyTemplate("ramp") }
                                    AppButton { Layout.preferredWidth: 88; label: root.t("阶梯"); onClicked: wavePage.applyTemplate("steps") }
                                }
                                Rectangle {
                                    Layout.fillWidth: true; Layout.fillHeight: true; radius: 16; color: darkMode ? "#090F1B" : "#F1F5FA"; border.color: cyan
                                    Canvas {
                                        id: editorCanvas; anchors.fill: parent; anchors.margins: 18; antialiasing: true
                                        onPaint: { const ctx=getContext("2d");ctx.reset();const p=wavePage.draftPoints;ctx.strokeStyle=darkMode?"#29364E":"#D7DFEA";ctx.lineWidth=1;for(let i=0;i<=4;i++){let y=height*i/4;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y);ctx.stroke()}for(let i=0;i<16;i++){let x=width*i/15;ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,height);ctx.stroke()}if(!p||p.length<2)return;ctx.strokeStyle=cyan;ctx.lineWidth=4;ctx.lineJoin="round";ctx.beginPath();for(let i=0;i<p.length;i++){let x=i/(p.length-1)*width;let y=height-(p[i]/100)*height;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}ctx.stroke();for(let i=0;i<p.length;i++){let x=i/(p.length-1)*width;let y=height-(p[i]/100)*height;ctx.fillStyle=root.fg;ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fill()}let playX=(root.wavePhase%1)*width;ctx.strokeStyle=Qt.rgba(cyan.r,cyan.g,cyan.b,0.55);ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(playX,0);ctx.lineTo(playX,height);ctx.stroke() }
                                        Connections { target: wavePage; function onDraftPointsChanged(){editorCanvas.requestPaint()} }
                                        Connections { target: root; function onWavePhaseChanged(){if(waveformEditor.visible)editorCanvas.requestPaint()} function onDarkModeChanged(){editorCanvas.requestPaint()} }
                                        MouseArea { anchors.fill: parent; cursorShape: Qt.CrossCursor; function paint(mouse){let i=Math.round(Math.max(0,Math.min(1,mouse.x/width))*15);let v=(1-Math.max(0,Math.min(1,mouse.y/height)))*100;wavePage.setPoint(i,v)} onPressed: mouse=>paint(mouse); onPositionChanged: mouse=>{if(pressed)paint(mouse)}; onReleased: wavePage.commitEditHistory() }
                                    }
                                }
                                RowLayout { Layout.fillWidth: true; spacing: 8; AppButton { Layout.preferredWidth: 82; label: root.t("撤销"); enabled: wavePage.editHistoryIndex>0; onClicked: wavePage.undoEdit() } AppButton { Layout.preferredWidth: 82; label: root.t("重做"); enabled: wavePage.editHistoryIndex+1<wavePage.editHistory.length; onClicked: wavePage.redoEdit() } AppButton { Layout.preferredWidth: 82; label: root.t("平滑"); onClicked: wavePage.smoothPoints() } AppButton { Layout.preferredWidth: 82; label: root.t("镜像"); onClicked: wavePage.mirrorPoints() } AppButton { Layout.preferredWidth: 88; label: root.t("归一化"); onClicked: wavePage.normalizePoints() } AppButton { Layout.preferredWidth: 82; label: root.t("清空"); onClicked: wavePage.applyTemplate("clear") } Item { Layout.fillWidth: true } Text { text: root.t("实际输出仍受强度范围和硬上限限制"); color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } }
                                RowLayout { Layout.fillWidth: true; Text { text: root.t("频率"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 } Slider { Layout.fillWidth: true; from: 10; to: 240; stepSize: 1; value: wavePage.draftFrequency; onMoved: wavePage.draftFrequency=Math.round(value) } Text { text: wavePage.draftFrequency+" Hz"; color: cyan; font.pixelSize: 12; font.weight: Font.DemiBold } AppButton { Layout.preferredWidth: 190; Layout.preferredHeight: 46; label: root.t("保存到我的波形库"); fillColor: cyan; labelColor: "#10151A"; onClicked: { if(backend.saveCustomWaveform(wavePage.draftName,wavePage.draftPoints,wavePage.draftFrequency)){wavePage.draftName=backend.customName;waveformEditor.close()} } } }
                            }
                        }

                        Dialog {
                            id: actionMappingDialog
                            anchors.centerIn: parent; width: Math.min(980,root.width-70); height: Math.min(700,root.height-50); modal: true; padding: 0
                            background: Rectangle { color: panel; border.color: border; radius: 20 }
                            contentItem: ColumnLayout {
                                anchors.fill: parent; anchors.margins: 20; spacing: 10
                                RowLayout { Layout.fillWidth: true; ColumnLayout { spacing: 3; Text { text: root.t("动作类型与波形"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 21; font.weight: Font.Bold } Text { text: root.t("只根据游戏报告的动作类型切换；普通交互默认关闭，静态姿势与规律动作采用不同推荐。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } } Item { Layout.fillWidth: true } AppButton { Layout.preferredWidth: 104; label: root.t("恢复推荐"); onClicked: backend.resetActionWaveforms() } AppButton { Layout.preferredWidth: 84; label: root.t("关闭"); onClicked: actionMappingDialog.close() } }
                                RowLayout { Layout.fillWidth: true; TextField { Layout.fillWidth: true; Layout.preferredHeight: 40; placeholderText: root.t("搜索动作或波形"); text: wavePage.actionSearch; onTextEdited: wavePage.actionSearch=text; color: root.fg; font.family: "Microsoft YaHei UI"; background: Rectangle { radius: 11; color: panel2; border.color: parent.activeFocus?violet:border } } Repeater { model: [{key:"all",label:root.t("全部")},{key:"rhythmic",label:root.t("规律动作")},{key:"static",label:root.t("静态姿势")},{key:"off",label:root.t("普通交互")}]; delegate: AppButton { required property var modelData; Layout.preferredWidth: 92; Layout.preferredHeight: 36; label: modelData.label; fillColor: wavePage.actionFilter===modelData.key?violet:panel2; labelColor: wavePage.actionFilter===modelData.key?"#10151A":root.fg; onClicked: wavePage.actionFilter=modelData.key } } }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 9; color: panel2; RowLayout { anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14; spacing: 10; Text { Layout.preferredWidth: 220; text: root.t("游戏动作类型"); color: muted; font.pixelSize: 9 } Text { Layout.preferredWidth: 82; text: root.t("分类"); color: muted; font.pixelSize: 9 } Text { Layout.fillWidth: true; text: root.t("波形预览"); color: muted; font.pixelSize: 9 } Text { Layout.preferredWidth: 280; text: root.t("使用波形"); color: muted; font.pixelSize: 9 } } }
                                ListView {
                                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6; model: wavePage.filteredActions
                                    delegate: Rectangle {
                                        required property var modelData
                                        width: ListView.view.width; height: 70; radius: 12; color: panel2; border.color: modelData.isOverride?violet:border
                                        RowLayout { anchors.fill: parent; anchors.margins: 10; spacing: 10; Text { Layout.preferredWidth: 220; text: modelData.actionLabel; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; elide: Text.ElideRight; ToolTip.visible: actionNameHover.hovered; ToolTip.text: modelData.actionLabel + "\n" + modelData.action; HoverHandler { id: actionNameHover } } Text { Layout.preferredWidth: 82; text: modelData.styleLabel; color: modelData.style==="rhythmic"?violet:modelData.style==="static"?cyan:muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } WaveView { Layout.fillWidth: true; Layout.preferredHeight: 46; points: modelData.points; waveColor: modelData.color; animated: actionRowHover.hovered } WaveComboBox { Layout.preferredWidth: 280; model: backend.assignableWaveforms; currentIndex: wavePage.optionIndex(modelData.waveKey); onActivated: backend.setActionWaveform(modelData.action,backend.assignableWaveforms[currentIndex].key) } }
                                        HoverHandler { id: actionRowHover }
                                    }
                                    ScrollBar.vertical: ScrollBar { }
                                }
                            }
                        }
                    }

                    // A/B monitor ----------------------------------------------
                    RowLayout {
                        spacing: 15
                        Repeater {
                            model: [
                                {channel:"A",name:backend.waveAName,points:backend.waveAPoints,strength:backend.outputA,color:accent,detail:root.t("心率驱动")},
                                {channel:"B",name:backend.waveBName,points:backend.waveBPoints,strength:backend.outputB,color:violet,detail:root.t("动作反馈")}
                            ]
                            delegate: AppCard {
                                required property var modelData
                                Layout.fillWidth: true; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 24; spacing: 12
                                    RowLayout { Layout.fillWidth: true; Rectangle { width: 44; height: 44; radius: 14; color: Qt.rgba(modelData.color.r,modelData.color.g,modelData.color.b,0.14); Text { anchors.centerIn: parent; text: modelData.channel; color: modelData.color; font.pixelSize: 18; font.weight: Font.Bold } } Column { Layout.fillWidth: true; Text { text: modelData.channel+root.t(" 通道"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 16; font.weight: Font.DemiBold } Text { text: modelData.detail; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } } Text { text: modelData.strength.toFixed(1)+" / "+backend.hardCap; color: modelData.color; font.pixelSize: 13; font.weight: Font.Bold } }
                                    WaveView { Layout.fillWidth: true; Layout.fillHeight: true; points: modelData.points; waveColor: modelData.color; animated: !backend.outputPaused }
                                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 76; radius: 15; color: panel2; RowLayout { anchors.fill: parent; anchors.margins: 14; Column { Layout.fillWidth: true; Text { text: root.t("当前选择"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } Text { text: modelData.name; color: modelData.color; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold } } Text { text: backend.outputPaused ? root.t("已暂停") : backend.safetyIdle ? root.t("安全待机") : root.t("实时输出"); color: backend.outputPaused || backend.safetyIdle ? amber : green; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; font.weight: Font.DemiBold } } }
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
                                        Layout.fillWidth: true; Layout.preferredHeight: 92; radius: 16
                                        color: panel2; border.color: border
                                        RowLayout {
                                            anchors.fill: parent; anchors.margins: 18
                                            Column { Layout.fillWidth: true; spacing: 5; Text { text: root.t("游戏货币 / RP"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } Text { text: Math.round(backend.currentRp).toLocaleString(Qt.locale(backend.language === "zh" ? "zh_CN" : "en_US"), "f", 0); color: amber; font.family: "Segoe UI"; font.pixelSize: 25; font.weight: Font.Bold } }
                                            Column { Layout.fillWidth: true; spacing: 5; Text { text: root.t("经验值 / EXP"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } Text { text: backend.exposeExp.toLocaleString(Qt.locale(backend.language === "zh" ? "zh_CN" : "en_US"), "f", 0); color: cyan; font.family: "Segoe UI"; font.pixelSize: 25; font.weight: Font.Bold } }
                                        }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.preferredHeight: 64; radius: 14
                                        color: Qt.rgba((backend.canEditProgress ? green : amber).r, (backend.canEditProgress ? green : amber).g, (backend.canEditProgress ? green : amber).b, darkMode ? 0.08 : 0.10)
                                        border.color: Qt.rgba((backend.canEditProgress ? green : amber).r, (backend.canEditProgress ? green : amber).g, (backend.canEditProgress ? green : amber).b, 0.28)
                                        RowLayout { anchors.fill: parent; anchors.margins: 14; Rectangle { width: 9; height: 9; radius: 5; color: backend.canEditProgress ? green : amber } Column { Layout.fillWidth: true; Text { text: backend.canEditProgress ? root.t("可以安全写入") : root.t("写入暂时锁定"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold } Text { text: backend.progressEditorStatus; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; elide: Text.ElideRight; width: 360 } } }
                                    }
                                    Text { Layout.fillWidth: true; text: root.t("为了避免游戏同时写入造成冲突，请先载入目标存档，再按 Esc 打开游戏菜单。每次修改前都会自动复制原始 .sd 文件。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; wrapMode: Text.Wrap; lineHeight: 1.35 }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: border }
                                    Text { text: root.t("备份位置"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                    Text { Layout.fillWidth: true; text: backend.saveBackupFolder; color: root.fg; font.family: "Cascadia Mono"; font.pixelSize: 9; wrapMode: Text.WrapAnywhere }
                                    Item { Layout.fillHeight: true }
                                    RowLayout { Layout.fillWidth: true; AppButton { label: root.t("刷新当前数值"); onClicked: progressPage.readCurrent() } AppButton { label: root.t("立即备份"); onClicked: backend.createSaveBackup() } Item { Layout.fillWidth: true } }
                                }
                            }
                            AppCard {
                                Layout.preferredWidth: 420; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 24; spacing: 13
                                    SectionTitle { title: root.t("修改并保存"); detail: "0–999999999" }
                                    Text { text: root.t("游戏货币 / RP"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                    TextField {
                                        Layout.fillWidth: true; Layout.preferredHeight: 50
                                        text: progressPage.draftRp; selectByMouse: true
                                        color: root.fg; font.family: "Segoe UI"; font.pixelSize: 16
                                        validator: DoubleValidator { bottom: 0; top: 999999999; decimals: 2 }
                                        background: Rectangle { radius: 13; color: panel2; border.color: parent.activeFocus ? amber : border }
                                        onTextEdited: progressPage.draftRp = text
                                    }
                                    Text { text: root.t("经验值 / EXP"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
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
                                        Column { anchors.fill: parent; anchors.margins: 14; spacing: 6; Text { text: root.t("写入与升级条件"); color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold } Text { width: parent.width; text: root.t("① 角色位于室外（非室内）并已载入目标存档\n② 按 Esc 暂停游戏\n③ 使用最新版游戏插件\n经验写入后：完成任意任务，再回家触发结算才会升级。"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; lineHeight: 1.35; wrapMode: Text.Wrap } }
                                    }
                                    Item { Layout.fillHeight: true }
                                    AppButton { Layout.fillWidth: true; Layout.preferredHeight: 52; label: root.t("备份、写入并保存"); fillColor: green; labelColor: "#10151A"; onClicked: progressConfirm.open() }
                                    Text { Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; text: root.t("不会修改技能等级、解锁项目或任务进度"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 }
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
                                            Rectangle { width: 42; height: 42; radius: 14; color: Qt.rgba(violet.r,violet.g,violet.b,0.14); Text { anchors.centerIn: parent; text: "⬡"; color: violet; font.pixelSize: 20; font.weight: Font.Bold } }
                                            Column { Layout.fillWidth: true; spacing: 3; Text { text: root.t("本地 Mod 扫描"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: backend.modSummary; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } }
                                            Rectangle { width: 9; height: 9; radius: 5; color: backend.modStatus.indexOf("完成") >= 0 ? green : amber }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 44; radius: 11; color: panel2; border.color: border
                                            RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; Text { text: root.t("游戏目录"); color: violet; font.family: "Microsoft YaHei UI"; font.pixelSize: 8; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; text: backend.gameFolder || root.t("尚未选择游戏目录"); color: root.fg; font.family: "Cascadia Mono"; font.pixelSize: 8; elide: Text.ElideMiddle } }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 7
                                            Text { Layout.fillWidth: true; text: root.t("这里只显示并管理当前游戏目录中的内容"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap }
                                            AppButton { Layout.preferredWidth: 150; label: root.t("重新扫描"); fillColor: violet; labelColor: "#11151C"; onClicked: backend.scanMods() }
                                        }
                                        Text { Layout.fillWidth: true; text: root.t("⚠ 修改开关前必须完全退出游戏"); color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; horizontalAlignment: Text.AlignRight }
                                    }
                                }
                                AppCard {
                                    Layout.preferredWidth: 430; Layout.fillHeight: true
                                    color: darkMode ? "#111A29" : "#F5F8FC"
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 17; spacing: 8
                                        RowLayout { Layout.fillWidth: true; Rectangle { width: 42; height: 42; radius: 14; color: Qt.rgba(cyan.r,cyan.g,cyan.b,0.13); Text { anchors.centerIn: parent; text: "＋"; color: cyan; font.pixelSize: 22; font.weight: Font.Bold } } Column { Layout.fillWidth: true; Text { text: root.t("Drop-in 收件箱"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: "DLL / V1 JSON / V2 folders / ZIP"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 8 } } }
                                        Text { Layout.fillWidth: true; text: root.t("导入路径：incoming → dropin_mods\\repository → 开启后同步到游戏"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap }
                                        Text { Layout.fillWidth: true; text: backend.dropInStatus + " · " + backend.dropInFolder; color: cyan; font.family: "Cascadia Mono"; font.pixelSize: 8; elide: Text.ElideMiddle }
                                        Item { Layout.fillHeight: true }
                                        RowLayout { Layout.fillWidth: true; spacing: 8; AppButton { Layout.fillWidth: true; label: root.t("打开收件箱"); onClicked: backend.openDropInFolder() } AppButton { Layout.fillWidth: true; label: root.t("导入历史"); onClicked: backend.openDropInArchive() } AppButton { Layout.fillWidth: true; label: root.t("导入并扫描"); fillColor: cyan; labelColor: "#10151A"; onClicked: backend.importDropIns() } }
                                    }
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true; spacing: 8
                                AppButton { Layout.preferredWidth: 142; label: root.t("本地 Mod"); fillColor: modPage.section === "all" ? violet : panel2; labelColor: modPage.section === "all" ? "#11151C" : root.fg; onClicked: modPage.section = "all" }
                                AppButton { Layout.preferredWidth: 144; label: root.t("● 当前加载"); fillColor: modPage.section === "loaded" ? green : panel2; labelColor: modPage.section === "loaded" ? "#11151C" : root.fg; onClicked: { modPage.section = "loaded"; backend.scanMods() } }
                                AppButton { Layout.preferredWidth: 142; label: root.t("★ 前置组件"); fillColor: modPage.section === "recommended" ? amber : panel2; labelColor: modPage.section === "recommended" ? "#11151C" : root.fg; onClicked: modPage.section = "recommended" }
                                Text { Layout.fillWidth: true; text: modPage.section === "recommended" ? root.t("检查本地前置组件") : modPage.section === "loaded" ? root.t("查看游戏目录中理论上会加载的文件") : root.t("扫描、导入、启停和删除本地 Mod"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; horizontalAlignment: Text.AlignRight }
                            }
                            StackLayout {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                currentIndex: modPage.section === "sources" ? 0 : modPage.section === "recommended" ? 1 : modPage.section === "all" ? 2 : 3
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 14; spacing: 10
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 58; radius: 13
                                            color: Qt.rgba(accent.r,accent.g,accent.b,darkMode ? 0.09 : 0.11); border.color: Qt.rgba(accent.r,accent.g,accent.b,0.28)
                                            RowLayout {
                                                anchors.fill: parent; anchors.margins: 12; spacing: 12
                                                Rectangle { width: 34; height: 34; radius: 11; color: Qt.rgba(accent.r,accent.g,accent.b,0.16); Text { anchors.centerIn: parent; text: "↗"; color: accent; font.pixelSize: 17; font.weight: Font.Bold } }
                                                Column { Layout.fillWidth: true; spacing: 2; Text { text: root.t("只做管理器，不做 Mod 下载平台"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; font.weight: Font.DemiBold } Text { width: parent.width; text: root.t("第三方 Mod、任务与汉化内容请从作者发布页获取，并遵守各自的授权、转载与更新规则。本工具不代替作者授权。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 8; wrapMode: Text.Wrap } }
                                            }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 62; radius: 13
                                            color: darkMode ? "#141E2F" : "#EDF2F8"; border.color: border
                                            RowLayout {
                                                anchors.fill: parent; anchors.margins: 10; spacing: 8
                                                Column {
                                                    Layout.fillWidth: true; spacing: 2
                                                    Text { text: root.t("选择获取路线"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                                    Text { width: parent.width; text: root.t("自行挑选原作者内容，或前往 user9527 的中文汉化整合帖。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 8; elide: Text.ElideRight }
                                                }
                                                AppButton { Layout.preferredWidth: 176; Layout.preferredHeight: 36; label: root.t("F95Zone 原作者目录"); fillColor: cyan; labelColor: "#10151A"; onClicked: backend.openExternalUrl("https://f95zone.to/threads/secret-flasher-manaka-custom-missions-1-2-1-version-2-4-0.263276/") }
                                                AppButton { Layout.preferredWidth: 176; Layout.preferredHeight: 36; label: root.t("user9527 汉化帖"); fillColor: violet; labelColor: "#10151A"; onClicked: backend.openExternalUrl("https://f95zone.to/threads/secret-flasher-manaka-custom-missions-1-2-1-version-2-4-0.263276/post-20360819") }
                                                AppButton { Layout.preferredWidth: 132; Layout.preferredHeight: 36; label: root.t("Mega 目录"); onClicked: backend.openExternalUrl("https://mega.nz/folder/QAEiCThB#V3T3H3c60jmQ_Pqm2R2eRA") }
                                            }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 10
                                            Column { Layout.fillWidth: true; Text { text: root.t("Mod 与任务来源目录"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold } Text { text: root.t("CustomMission 1/2 已置顶；其余条目按类型整理。只跳转作者页面，不托管文件。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 8 } }
                                            TextField {
                                                Layout.preferredWidth: 250; Layout.preferredHeight: 38
                                                placeholderText: root.t("搜索名称、作者、类型或楼层")
                                                text: modPage.sourceSearch; selectByMouse: true; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 10
                                                onTextEdited: modPage.sourceSearch = text
                                                background: Rectangle { radius: 11; color: panel2; border.color: parent.activeFocus ? accent : border }
                                            }
                                            Text { text: modPage.filteredSources.length + " / " + backend.modSourceLinks.length; color: accent; font.family: "Cascadia Mono"; font.pixelSize: 8; font.weight: Font.DemiBold }
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
                                                width: modSourceList.cellWidth - 7; height: 134; radius: 14
                                                color: modelData.pinned ? (darkMode ? "#182033" : "#E7F8FB") : (darkMode ? "#141E2F" : "#EDF2F8")
                                                border.color: modelData.pinned ? accent : border
                                                RowLayout {
                                                    anchors.fill: parent; anchors.margins: 12; spacing: 11
                                                    Rectangle { Layout.alignment: Qt.AlignTop; width: 40; height: 40; radius: 12; color: Qt.rgba(accent.r,accent.g,accent.b,0.13); Text { anchors.centerIn: parent; text: modelData.pinned ? "★" : "↗"; color: accent; font.pixelSize: 15; font.weight: Font.Bold } }
                                                    ColumnLayout {
                                                        Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 3
                                                        RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: modelData.displayName; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold; wrapMode: Text.Wrap } Rectangle { width: sourceGroupText.width + 12; height: 19; radius: 6; color: panel2; Text { id: sourceGroupText; anchors.centerIn: parent; text: modelData.categoryLabel; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 7 } } }
                                                        Text { Layout.fillWidth: true; text: modelData.alternateName; color: muted; font.family: "Segoe UI"; font.pixelSize: 8; elide: Text.ElideRight }
                                                        Text { Layout.fillWidth: true; text: modelData.author + " · " + modelData.kind + " · " + modelData.reference; color: cyan; font.family: "Microsoft YaHei UI"; font.pixelSize: 8; wrapMode: Text.Wrap }
                                                        Text { Layout.fillWidth: true; visible: modelData.note.length > 0; text: modelData.note; color: muted; font.family: "Segoe UI"; font.pixelSize: 8; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                                                    }
                                                    AppButton { Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 86; Layout.preferredHeight: 32; label: root.t("打开原帖页"); onClicked: backend.openExternalUrl(modelData.url) }
                                                }
                                            }
                                            ScrollBar.vertical: ScrollBar { contentItem: Rectangle { implicitWidth: 5; radius: 3; color: muted } background: Rectangle { color: "transparent" } }
                                        }
                                        Text { Layout.fillWidth: true; text: root.t("支持 Mod 作者以及整合汉化工作者的劳动，是所有人都该守护的。"); color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
                                    }
                                }
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 12; spacing: 9
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 54; radius: 13
                                            color: Qt.rgba(cyan.r,cyan.g,cyan.b,darkMode ? 0.08 : 0.10); border.color: Qt.rgba(cyan.r,cyan.g,cyan.b,0.25)
                                            RowLayout { anchors.fill: parent; anchors.margins: 12; Text { text: root.t("依赖顺序"); color: cyan; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; text: root.t("V1 任务 → CustomMission 1　　V2 包 → CustomMission 2"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } }
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
                                                        Text { Layout.fillWidth: true; visible: modelData.requiredPluginName && !modelData.dependencyReady; text: modelData.dependencyAvailable ? root.t("⚠ 需要先启用 ") + modelData.requiredPluginName : root.t("⚠ 当前来源库缺少 ") + modelData.requiredPluginName; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 }
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
                                            TextField {
                                                Layout.preferredWidth: 245; Layout.preferredHeight: 42
                                                placeholderText: root.t("搜索名称、详情、地点…"); selectByMouse: true; color: root.fg; font.family: "Microsoft YaHei UI"
                                                onTextEdited: modPage.searchText = text
                                                background: Rectangle { radius: 12; color: panel; border.color: parent.activeFocus ? accent : border }
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
                                                    width: modList.cellWidth - 7; height: 222; radius: 15
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
                                                                Rectangle { width: kindText.width+14; height: 22; radius: 7; color: panel2; Text { id: kindText; anchors.centerIn: parent; text: root.t(modelData.categoryLabel); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } }
                                                                Text { text: modelData.status; color: modelData.enabled ? green : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; font.weight: Font.DemiBold }
                                                            }
                                                            Text { Layout.fillWidth: true; text: modelData.description; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; lineHeight: 1.2; wrapMode: Text.Wrap }
                                                            Text { Layout.fillWidth: true; visible: modelData.kind === "v1"; text: modelData.hasLocationGuide ? root.t("起始地点：") + modelData.location : root.t("起始地点：说明中暂无记录"); color: modelData.hasLocationGuide ? cyan : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold; wrapMode: Text.Wrap }
                                                            Text { Layout.fillWidth: true; visible: modelData.locationNote.length > 0; text: "⚠ " + modelData.locationNote; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap }
                                                            Text { Layout.fillWidth: true; visible: modelData.requiredPluginName && !modelData.dependencyReady; text: modelData.dependencyAvailable ? root.t("⚠ 需要先启用 ") + modelData.requiredPluginName : root.t("⚠ 当前来源库缺少 ") + modelData.requiredPluginName; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap }
                                                            Text { Layout.fillWidth: true; visible: modelData.warning.length > 0; text: "⚠ " + modelData.warning; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap }
                                                        }
                                                        ColumnLayout {
                                                            Layout.alignment: Qt.AlignTop; spacing: 8
                                                            Switch { checked: modelData.enabled; enabled: modelData.available; onClicked: backend.setModEnabled(modelData.id, checked); palette.highlight: green }
                                                            AppButton {
                                                                visible: modelData.userImported
                                                                Layout.preferredWidth: 58; Layout.preferredHeight: 30
                                                                label: root.t("删除"); fillColor: Qt.rgba(red.r,red.g,red.b,darkMode ? 0.18 : 0.10); labelColor: red
                                                                onClicked: { modDeleteConfirm.entryId = modelData.id; modDeleteConfirm.modName = modelData.name; modDeleteConfirm.open() }
                                                            }
                                                        }
                                                    }
                                                }
                                                ScrollBar.vertical: ScrollBar { contentItem: Rectangle { implicitWidth: 5; radius: 3; color: muted } background: Rectangle { color: "transparent" } }
                                                footer: Item { width: 1; height: 8 }
                                            }
                                            Text { anchors.centerIn: parent; visible: modPage.filteredInventory.length === 0; text: backend.modInventory.length ? root.t("没有符合筛选条件的项目") : root.t("当前游戏目录中还没有可管理的 Mod"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 12 }
                                        }
                                    }
                                }
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 14; spacing: 10
                                        RowLayout {
                                            Layout.fillWidth: true; spacing: 12
                                            Rectangle { width: 46; height: 46; radius: 14; color: Qt.rgba(green.r,green.g,green.b,0.14); Text { anchors.centerIn: parent; text: "ON"; color: green; font.family: "Segoe UI"; font.pixelSize: 10; font.weight: Font.Bold } }
                                            Column { Layout.fillWidth: true; spacing: 3; Text { text: root.t("当前已启用的 Mod"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: root.t("按游戏目录中的文件状态筛选；不读取运行日志"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } }
                                            AppButton { Layout.preferredWidth: 110; label: root.t("重新扫描"); onClicked: backend.scanMods() }
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
                                                delegate: AppButton { required property var modelData; Layout.preferredWidth: 94; label: modelData.text; fillColor: modPage.loadedFilterCategory === modelData.key ? green : panel2; labelColor: modPage.loadedFilterCategory === modelData.key ? "#11151C" : root.fg; onClicked: modPage.loadedFilterCategory = modelData.key }
                                            }
                                            Item { Layout.fillWidth: true }
                                            TextField {
                                                Layout.preferredWidth: 245; Layout.preferredHeight: 42
                                                placeholderText: root.t("搜索名称或详情…"); selectByMouse: true; color: root.fg; font.family: "Microsoft YaHei UI"
                                                onTextEdited: modPage.loadedSearchText = text
                                                background: Rectangle { radius: 12; color: panel; border.color: parent.activeFocus ? green : border }
                                            }
                                        }
                                        GridView {
                                            id: loadedModList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                                            model: modPage.filteredLoadedInventory
                                            cellWidth: width / 2; cellHeight: 126
                                            delegate: Rectangle {
                                                required property var modelData
                                                width: loadedModList.cellWidth - 7; height: 118; radius: 14
                                                color: modelData.enabled ? (darkMode ? "#141E2F" : "#EDF2F8") : (darkMode ? "#111722" : "#E7EAF0")
                                                border.color: modelData.enabled ? Qt.rgba(green.r,green.g,green.b,0.40) : Qt.rgba(muted.r,muted.g,muted.b,0.35)
                                                opacity: modelData.enabled ? 1.0 : 0.72
                                                RowLayout {
                                                    anchors.fill: parent; anchors.margins: 13; spacing: 12
                                                    Rectangle { width: 42; height: 42; radius: 13; color: Qt.rgba((modelData.enabled ? green : muted).r,(modelData.enabled ? green : muted).g,(modelData.enabled ? green : muted).b,0.13); Text { anchors.centerIn: parent; text: modelData.kind === "plugin" ? "DLL" : modelData.kind.toUpperCase(); color: modelData.enabled ? green : muted; font.family: "Segoe UI"; font.pixelSize: 9; font.weight: Font.Bold } }
                                                    ColumnLayout {
                                                        Layout.fillWidth: true; spacing: 4
                                                        RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: modelData.name; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; font.weight: Font.DemiBold; wrapMode: Text.Wrap } Text { text: modelData.kindLabel; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 8 } }
                                                        Text { Layout.fillWidth: true; text: modelData.enabled ? root.t("文件已启用 · 理论上会随游戏加载") : root.t("本次会话已关闭 · 重新扫描后隐藏"); color: modelData.enabled ? green : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; font.weight: Font.DemiBold }
                                                        Text { Layout.fillWidth: true; text: modelData.description; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                                                        Text { Layout.fillWidth: true; visible: modelData.requiredPluginName && !modelData.dependencyReady; text: root.t("⚠ 需要启用 ") + modelData.requiredPluginName + root.t(" 才能实际加载"); color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 8; wrapMode: Text.Wrap }
                                                    }
                                                    Switch { checked: modelData.enabled; enabled: modelData.available; onClicked: backend.setLoadedModEnabled(modelData.id, checked); palette.highlight: green }
                                                }
                                            }
                                            ScrollBar.vertical: ScrollBar { contentItem: Rectangle { implicitWidth: 5; radius: 3; color: muted } background: Rectangle { color: "transparent" } }
                                        }
                                        Text { Layout.fillWidth: true; visible: modPage.filteredLoadedInventory.length === 0; text: backend.loadedModInventory.length ? root.t("没有符合筛选条件的项目") : root.t("游戏目录中暂时没有处于启用位置的 Mod。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter }
                                    }
                                }
                            }
                            Text { Layout.fillWidth: true; text: root.t("同名 Drop-in 会替换仓库版本，并在游戏关闭时同步已启用副本。删除按钮只会出现在用户导入的 Mod 上。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap }
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
                                    Layout.fillWidth: true; Layout.preferredHeight: 58; radius: 13
                                    color: darkMode ? "#141E2F" : "#EDF2F8"; border.color: border
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: 8; spacing: 8
                                        AppButton { Layout.fillWidth: true; Layout.preferredHeight: 42; label: root.t("路线 1 · F95Zone 原帖"); fillColor: workshopPage.route === "f95" ? cyan : panel2; labelColor: workshopPage.route === "f95" ? "#10151A" : root.fg; onClicked: workshopPage.route = "f95" }
                                        AppButton { Layout.fillWidth: true; Layout.preferredHeight: 42; label: root.t("路线 2 · user9527 汉化整合"); fillColor: workshopPage.route === "user9527" ? violet : panel2; labelColor: workshopPage.route === "user9527" ? "#10151A" : root.fg; onClicked: workshopPage.route = "user9527" }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 10; visible: workshopPage.route === "f95"
                                    Column { Layout.fillWidth: true; spacing: 3; Text { text: root.t("Mod 与任务来源目录"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 16; font.weight: Font.DemiBold } Text { text: root.t("CustomMission 1/2 已置顶；其余条目按类型整理。只跳转作者页面，不托管文件。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } }
                                    TextField {
                                        Layout.preferredWidth: 270; Layout.preferredHeight: 38
                                        placeholderText: root.t("搜索名称、作者、类型或楼层")
                                        text: workshopPage.searchText; selectByMouse: true; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11
                                        onTextEdited: workshopPage.searchText = text
                                        background: Rectangle { radius: 11; color: panel2; border.color: parent.activeFocus ? accent : border }
                                    }
                                    Text { text: workshopPage.filteredSources.length + " / " + backend.modSourceLinks.length; color: accent; font.family: "Cascadia Mono"; font.pixelSize: 10; font.weight: Font.DemiBold }
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
                                        width: workshopSourceList.cellWidth - 7; height: 150; radius: 14
                                        color: modelData.pinned ? (darkMode ? "#182033" : "#E7F8FB") : (darkMode ? "#141E2F" : "#EDF2F8")
                                        border.color: modelData.pinned ? accent : border
                                        RowLayout {
                                            anchors.fill: parent; anchors.margins: 12; spacing: 11
                                            Rectangle { Layout.alignment: Qt.AlignTop; width: 40; height: 40; radius: 12; color: Qt.rgba(accent.r,accent.g,accent.b,0.13); Text { anchors.centerIn: parent; text: modelData.pinned ? "★" : "↗"; color: accent; font.pixelSize: 15; font.weight: Font.Bold } }
                                            ColumnLayout {
                                                Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 3
                                                RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: modelData.displayName; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold; wrapMode: Text.Wrap } Rectangle { width: workshopGroupText.width + 14; height: 22; radius: 7; color: panel2; Text { id: workshopGroupText; anchors.centerIn: parent; text: modelData.categoryLabel; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } } }
                                                Text { Layout.fillWidth: true; text: modelData.alternateName; color: muted; font.family: "Segoe UI"; font.pixelSize: 10; elide: Text.ElideRight }
                                                Text { Layout.fillWidth: true; text: modelData.author + " · " + modelData.kind + " · " + modelData.reference; color: cyan; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap }
                                                Text { Layout.fillWidth: true; visible: modelData.note.length > 0; text: modelData.note; color: muted; font.family: "Segoe UI"; font.pixelSize: 9; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                                            }
                                            AppButton { Layout.alignment: Qt.AlignVCenter; Layout.preferredWidth: 98; Layout.preferredHeight: 36; label: root.t("打开原帖页"); onClicked: backend.openExternalUrl(modelData.url) }
                                        }
                                    }
                                    ScrollBar.vertical: ScrollBar { contentItem: Rectangle { implicitWidth: 5; radius: 3; color: muted } background: Rectangle { color: "transparent" } }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true; Layout.fillHeight: true; visible: workshopPage.route === "user9527"; spacing: 11
                                    Text { Layout.fillWidth: true; text: root.t("user9527 中文汉化整合"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 21; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter }
                                    Text { Layout.fillWidth: true; text: root.t("选择原帖查看说明，或打开作者提供的文件目录。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter }
                                    RowLayout {
                                        Layout.fillWidth: true; Layout.preferredHeight: 126; Layout.minimumHeight: 126; Layout.maximumHeight: 126; spacing: 12
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.fillHeight: true; radius: 15
                                            color: darkMode ? "#171827" : "#F2EFFB"; border.color: Qt.rgba(violet.r,violet.g,violet.b,0.38)
                                            RowLayout {
                                                anchors.fill: parent; anchors.margins: 14; spacing: 12
                                                Rectangle { width: 38; height: 38; radius: 12; color: Qt.rgba(violet.r,violet.g,violet.b,0.16); Text { anchors.centerIn: parent; text: "↗"; color: violet; font.pixelSize: 16; font.weight: Font.Bold } }
                                                ColumnLayout { Layout.fillWidth: true; spacing: 4; Text { text: root.t("F95Zone 汉化整合原帖"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; text: root.t("查看使用说明、更新记录与作者声明"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap } }
                                                AppButton { Layout.preferredWidth: 112; Layout.preferredHeight: 38; label: root.t("打开原帖"); fillColor: violet; labelColor: "#10151A"; onClicked: backend.openExternalUrl("https://f95zone.to/threads/secret-flasher-manaka-custom-missions-1-2-1-version-2-4-0.263276/post-20360819") }
                                            }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.fillHeight: true; radius: 15
                                            color: darkMode ? "#141E2F" : "#EDF2F8"; border.color: border
                                            RowLayout {
                                                anchors.fill: parent; anchors.margins: 14; spacing: 12
                                                Rectangle { width: 38; height: 38; radius: 12; color: Qt.rgba(cyan.r,cyan.g,cyan.b,0.14); Text { anchors.centerIn: parent; text: "⌁"; color: cyan; font.pixelSize: 16; font.weight: Font.Bold } }
                                                ColumnLayout { Layout.fillWidth: true; spacing: 4; Text { text: root.t("作者文件目录"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; text: root.t("打开作者在原帖中提供的 Mega 目录"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap } }
                                                AppButton { Layout.preferredWidth: 112; Layout.preferredHeight: 38; label: root.t("打开目录"); fillColor: cyan; labelColor: "#10151A"; onClicked: backend.openExternalUrl("https://mega.nz/folder/QAEiCThB#V3T3H3c60jmQ_Pqm2R2eRA") }
                                            }
                                        }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 230; radius: 18
                                        color: darkMode ? "#171827" : "#F4F0FF"; border.color: Qt.rgba(violet.r,violet.g,violet.b,0.55); border.width: 1
                                        ColumnLayout {
                                            anchors.fill: parent; anchors.margins: 20; spacing: 13
                                            Text { Layout.fillWidth: true; text: root.t("导入 9527 汉化整合"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 20; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter }
                                            Text { Layout.fillWidth: true; text: root.t("下载并解压整合包后，可使用专用向导安全备份、导入并应用精简启动预设。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
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
                                                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.maximumHeight: 108; radius: 14
                                                        color: darkMode ? "#141E2F" : "#FFFFFF"; border.color: border
                                                        RowLayout {
                                                            anchors.fill: parent; anchors.margins: 13; spacing: 10
                                                            Rectangle { width: 38; height: 38; radius: 19; color: modelData.number === "3" ? violet : panel2; Text { anchors.centerIn: parent; text: modelData.number; color: modelData.number === "3" ? "#10151A" : root.fg; font.pixelSize: 16; font.weight: Font.Bold } }
                                                            ColumnLayout { Layout.fillWidth: true; spacing: 3; Text { Layout.fillWidth: true; text: modelData.title; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold; wrapMode: Text.Wrap } Text { Layout.fillWidth: true; text: modelData.detail; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap } }
                                                        }
                                                    }
                                                }
                                            }
                                            AppButton { Layout.alignment: Qt.AlignHCenter; Layout.preferredWidth: 330; Layout.preferredHeight: 52; label: root.t("开始导入 9527 汉化整合"); fillColor: violet; labelColor: "#10151A"; onClicked: { backend.reset9527Import(); pack9527Wizard.step = 0; pack9527Wizard.open() } }
                                        }
                                    }
                                }
                                Text { Layout.fillWidth: true; visible: workshopPage.route === "f95"; text: root.t("支持 Mod 作者以及整合汉化工作者的劳动，是所有人都该守护的。"); color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
                            }
                        }
                    }

                    // Logs ------------------------------------------------------
                    AppCard {
                        color: panel
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 20; spacing: 12
                            RowLayout { Layout.fillWidth: true; Text { text: root.t("最近 ") + backend.logs.length + root.t(" 条记录"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } Item { Layout.fillWidth: true } AppButton { label: root.t("清空日志"); onClicked: backend.clearLogs() } }
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

    FolderDialog { id: folderDialog; title: root.t("选择游戏根目录"); onAccepted: backend.setGameFolder(selectedFolder.toString()) }
    FolderDialog {
        id: pack9527FolderDialog
        title: root.t("选择解压后的 9527 整合包")
        onAccepted: {
            backend.inspect9527Pack(selectedFolder.toString())
            pack9527Wizard.step = 1
        }
    }

    Dialog {
        id: pack9527Wizard
        property int step: 0
        property bool confirmed: false
        anchors.centerIn: parent
        width: Math.min(790, root.width - 70)
        height: Math.min(650, root.height - 50)
        modal: true
        closePolicy: Popup.NoAutoClose
        padding: 0
        background: Rectangle { color: panel; border.color: border; border.width: 1; radius: 20 }
        Timer {
            id: pack9527InstallTimer
            interval: 80
            onTriggered: pack9527Wizard.step = backend.install9527Pack() ? 4 : 2
        }
        contentItem: ColumnLayout {
            spacing: 0
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 86; radius: 20
                color: darkMode ? "#171827" : "#F2EFFB"
                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 20; color: parent.color }
                Column {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 24; spacing: 4
                    Text { text: root.t("导入 user9527 汉化整合"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 20; font.weight: Font.Bold }
                    Text { text: root.t("校验来源、备份现有文件，并应用安全的精简启动预设"); color: violet; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                }
                Row {
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: 24; spacing: 7
                    Repeater {
                        model: 4
                        Rectangle {
                            required property int index
                            width: 30; height: 30; radius: 15
                            color: pack9527Wizard.step >= index || pack9527Wizard.step === 4 ? accent : panel2
                            Text { anchors.centerIn: parent; text: index + 1; color: parent.color === accent ? "#10151A" : muted; font.family: "Cascadia Mono"; font.pixelSize: 10; font.weight: Font.Bold }
                        }
                    }
                }
            }
            StackLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; currentIndex: pack9527Wizard.step
                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 28; spacing: 16
                        Text { Layout.fillWidth: true; text: root.t("开始之前"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 18; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("请先在“设备与游戏”选择原版游戏目录，并完成 BepInEx 运行环境安装。游戏必须完全退出，不能只停留在标题画面。"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; lineHeight: 1.4; wrapMode: Text.Wrap }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 118; radius: 14; color: panel2; border.color: border
                            Column { anchors.fill: parent; anchors.margins: 16; spacing: 7
                                Text { text: root.t("你需要选择解压后的目录，其中应直接包含："); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                Text { text: "BepInEx  ·  CustomMissions  ·  CustomMissions2  ·  " + root.t("必读说明"); color: cyan; font.family: "Cascadia Mono"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                Text { width: parent.width; text: root.t("软件不会执行整合包中的 EXE、BAT 或脚本，也不会上传这些文件。"); color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap }
                            }
                        }
                        Item { Layout.fillHeight: true }
                        RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } AppButton { label: root.t("取消"); onClicked: pack9527Wizard.close() } AppButton { Layout.preferredWidth: 190; label: root.t("选择解压目录"); fillColor: accent; labelColor: "#10151A"; onClicked: pack9527FolderDialog.open() } }
                    }
                }
                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 28; spacing: 14
                        Text { text: root.t("目录校验"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 18; font.weight: Font.Bold }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 12; color: panel2; border.color: backend.pack9527Ready ? green : amber; Text { anchors.fill: parent; anchors.margins: 13; text: backend.pack9527Folder || root.t("尚未选择目录"); color: root.fg; font.family: "Cascadia Mono"; font.pixelSize: 9; elide: Text.ElideMiddle; verticalAlignment: Text.AlignVCenter } }
                        Text { Layout.fillWidth: true; text: backend.pack9527Status; color: backend.pack9527Ready ? green : amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; wrapMode: Text.Wrap }
                        GridLayout {
                            Layout.fillWidth: true; columns: 3; rowSpacing: 8; columnSpacing: 8
                            Repeater {
                                model: [
                                    { title: root.t("插件 DLL"), value: backend.pack9527Analysis.plugins || 0 },
                                    { title: root.t("V1 JSON 任务"), value: backend.pack9527Analysis.v1_missions || 0 },
                                    { title: root.t("V2 任务包"), value: backend.pack9527Analysis.v2_packages || 0 }
                                ]
                                Rectangle { required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 86; radius: 13; color: panel2; border.color: border; Column { anchors.centerIn: parent; spacing: 4; Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.value; color: accent; font.family: "Cascadia Mono"; font.pixelSize: 22; font.weight: Font.Bold } Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.title; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } } }
                            }
                        }
                        Text { Layout.fillWidth: true; text: root.t("识别到的说明文件：") + ((backend.pack9527Analysis.readmes || []).join(" · ") || root.t("无")); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap }
                        Item { Layout.fillHeight: true }
                        RowLayout { Layout.fillWidth: true; AppButton { label: root.t("重新选择"); onClicked: pack9527FolderDialog.open() } Item { Layout.fillWidth: true } AppButton { label: root.t("关闭"); onClicked: pack9527Wizard.close() } AppButton { Layout.preferredWidth: 170; enabled: backend.pack9527Ready; label: root.t("查看安装计划"); fillColor: backend.pack9527Ready ? accent : panel2; labelColor: backend.pack9527Ready ? "#10151A" : muted; onClicked: pack9527Wizard.step = 2 } }
                    }
                }
                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 28; spacing: 13
                        Text { text: root.t("精简启动安装计划"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 18; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("软件会先备份将被替换的文件，然后导入配置与附属资源。首次启动只保留两个任务加载器，其余内容进入停用区，可随时在“本地 Mod”中开启。"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; lineHeight: 1.4; wrapMode: Text.Wrap }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 150; radius: 14; color: panel2; border.color: border
                            Column { anchors.fill: parent; anchors.margins: 16; spacing: 9
                                Text { text: root.t("安装后默认状态"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 }
                                Text { text: "● SFM_custom_mission.dll   " + root.t("启用"); color: green; font.family: "Cascadia Mono"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                Text { text: "● SFM_custom_mission_v2.dll   " + root.t("启用"); color: green; font.family: "Cascadia Mono"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                Text { text: root.t("○ 其他插件、全部 V1/V2 任务   默认停用"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                Text { text: root.t("DG-LAB 遥测插件保持启用，不会被精简预设关闭。"); color: cyan; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 }
                            }
                        }
                        CheckBox { id: pack9527Confirm; text: root.t("我已阅读 9527 的必读说明，并确认游戏已经完全退出"); checked: pack9527Wizard.confirmed; onToggled: pack9527Wizard.confirmed = checked; palette.windowText: root.fg }
                        Text { Layout.fillWidth: true; text: root.t("提示：第一次导入可能需要一些时间，请勿在处理中关闭软件。"); color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap }
                        Item { Layout.fillHeight: true }
                        RowLayout { Layout.fillWidth: true; AppButton { label: root.t("上一步"); onClicked: pack9527Wizard.step = 1 } Item { Layout.fillWidth: true } AppButton { label: root.t("取消"); onClicked: pack9527Wizard.close() } AppButton { Layout.preferredWidth: 190; enabled: pack9527Wizard.confirmed; label: root.t("备份并开始导入"); fillColor: pack9527Wizard.confirmed ? accent : panel2; labelColor: pack9527Wizard.confirmed ? "#10151A" : muted; onClicked: { pack9527Wizard.step = 3; pack9527InstallTimer.start() } } }
                    }
                }
                Item {
                    ColumnLayout { anchors.centerIn: parent; width: Math.min(500, parent.width - 60); spacing: 16; BusyIndicator { Layout.alignment: Qt.AlignHCenter; running: pack9527Wizard.step === 3 } Text { Layout.fillWidth: true; text: root.t("正在备份与导入…"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 18; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter } Text { Layout.fillWidth: true; text: root.t("正在复制配置、插件与任务，并应用精简启动预设。请勿关闭软件或启动游戏。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter } }
                }
                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 28; spacing: 15
                        Item { Layout.fillHeight: true }
                        Rectangle { Layout.alignment: Qt.AlignHCenter; width: 72; height: 72; radius: 36; color: Qt.rgba(green.r,green.g,green.b,0.15); Text { anchors.centerIn: parent; text: "✓"; color: green; font.pixelSize: 34; font.weight: Font.Bold } }
                        Text { Layout.fillWidth: true; text: root.t("9527 汉化整合已导入"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 21; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter }
                        Text { Layout.fillWidth: true; text: backend.pack9527Status; color: green; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter }
                        Text { Layout.fillWidth: true; text: root.t("接下来可关闭向导，在“本地 Mod”里只开启你真正需要的任务和插件。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter }
                        Item { Layout.fillHeight: true }
                        RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } AppButton { visible: backend.pack9527Backup.length > 0; label: root.t("打开备份目录"); onClicked: backend.open9527Backup() } AppButton { Layout.preferredWidth: 170; label: root.t("完成"); fillColor: accent; labelColor: "#10151A"; onClicked: { pack9527Wizard.close(); modPage.section = "all" } } }
                    }
                }
            }
        }
        onOpened: { confirmed = false; pack9527Confirm.checked = false }
    }

    Dialog {
        id: progressConfirm; anchors.centerIn: parent; modal: true; title: root.t("确认修改当前存档"); standardButtons: Dialog.Yes | Dialog.No
        contentItem: Text { text: backend.language === "en" ? "Currency will be set to " + progressPage.draftRp + " and EXP to " + progressPage.draftExp + ".\nThe original save is backed up before the game save flow runs.\n\nConfirm that the character is outdoors. After editing EXP, complete any mission and return home to trigger settlement before the level updates." : "将把游戏货币修改为 " + progressPage.draftRp + "，经验值修改为 " + progressPage.draftExp + "。\n软件会先创建备份，再调用游戏自己的保存流程。\n\n请确认角色当前位于室外（非室内）。经验写入后，需要完成任意任务并回家触发结算，等级才会刷新。"; color: root.fg; font.family: "Microsoft YaHei UI"; padding: 18; wrapMode: Text.Wrap }
        background: Rectangle { color: panel; border.color: border; radius: 16 }
        onAccepted: backend.applyProgressValues(progressPage.draftRp, progressPage.draftExp)
    }
    Dialog {
        id: modDeleteConfirm
        property string entryId: ""
        property string modName: ""
        anchors.centerIn: parent; modal: true; title: root.t("删除导入的 Mod"); standardButtons: Dialog.Yes | Dialog.No
        contentItem: Text { text: backend.language === "en" ? "This will delete the Mod from the Drop-in repository, game folder, and disabled quarantine:\n" + modDeleteConfirm.modName + "\n\nThe game must be fully closed. The original import remains in dropin_mods\\archive and can be returned to the inbox later." : "将从 Drop-in 仓库、游戏目录和停用隔离区删除：\n" + modDeleteConfirm.modName + "\n\n游戏必须完全退出。原始导入包仍保存在 dropin_mods\\archive，需要时可以重新放回收件箱。"; color: root.fg; font.family: "Microsoft YaHei UI"; padding: 18; wrapMode: Text.Wrap }
        onAccepted: backend.deleteDropInMod(entryId)
    }

    Dialog {
        id: networkHelpDialog
        property string selectedAddress: backend.lanAddresses.length > 0 ? backend.lanAddresses[0] : ""
        anchors.centerIn: parent
        width: Math.min(680, root.width - 80)
        height: Math.min(520, root.height - 60)
        modal: true
        title: root.t("DG-LAB 扫码连接排查")
        padding: 0
        background: Rectangle { color: panel; border.color: border; border.width: 1; radius: 18 }
        onOpened: {
            const current = backend.lanAddress.split(":")[0]
            selectedAddress = backend.lanAddresses.indexOf(current) >= 0 ? current : (backend.lanAddresses.length > 0 ? backend.lanAddresses[0] : "")
        }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 22; spacing: 14
            Text { Layout.fillWidth: true; text: root.t("先确认手机与电脑连接同一 Wi‑Fi，并暂时关闭手机流量、电脑 VPN/代理。DG-LAB App 中应先连接蓝牙主机，再进入 SOCKET 控制扫码。"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; lineHeight: 1.35; wrapMode: Text.Wrap }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: border }
            Text { text: root.t("1 选择二维码使用的电脑地址"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold }
            Text { Layout.fillWidth: true; text: root.t("如果安装过 VPN、虚拟机或同时连接有线/无线，请选择与手机 IP 前三段相同的地址。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                AppComboBox { id: lanAddressPicker; Layout.fillWidth: true; model: backend.lanAddresses; onActivated: networkHelpDialog.selectedAddress = currentText }
                AppButton { label: root.t("应用并刷新二维码"); Layout.preferredWidth: 158; enabled: networkHelpDialog.selectedAddress !== ""; onClicked: backend.selectLanAddress(networkHelpDialog.selectedAddress) }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: border }
            Text { text: root.t("2 修复 Windows 网络权限"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold }
            Text { Layout.fillWidth: true; text: root.t("仅在可信任的家庭网络中使用。系统会弹出管理员确认，将当前网卡设为“专用网络”，并仅放行本软件使用的 TCP 9999 端口。"); color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; lineHeight: 1.3; wrapMode: Text.Wrap }
            RowLayout {
                Layout.fillWidth: true
                AppButton { label: root.t("管理员修复网络权限"); Layout.preferredWidth: 190; enabled: backend.serverReady; fillColor: Qt.rgba(amber.r,amber.g,amber.b,darkMode?0.22:0.14); labelColor: amber; onClicked: backend.repairNetworkAccess() }
                Item { Layout.fillWidth: true }
                AppButton { label: root.t("关闭"); onClicked: networkHelpDialog.close() }
            }
            Text { Layout.fillWidth: true; text: root.t("修复完成后无需重启电脑，直接回到 DG-LAB App 重新扫描当前二维码。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap }
        }
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
                Column { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 24; spacing: 4; Text { text: root.t("使用协议与风险知情确认"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 20; font.weight: Font.Bold } Text { text: root.t("请完整阅读；不同意不会启动任何设备连接服务"); color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } }
                AppButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: 22; width: 78; label: backend.language === "zh" ? "English" : "中文"; onClicked: backend.setLanguage(backend.language === "zh" ? "en" : "zh") }
            }
            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.margins: 18
                clip: true; contentWidth: availableWidth
                Text { width: parent.width; text: backend.agreementText; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; lineHeight: 1.45; wrapMode: Text.Wrap }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: border }
            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 76; Layout.leftMargin: 18; Layout.rightMargin: 18; spacing: 12
                AppButton { Layout.preferredWidth: 170; label: root.t("不同意并退出"); fillColor: darkMode ? "#241822" : "#F4E3E8"; labelColor: red; onClicked: backend.declineAgreement() }
                Item { Layout.fillWidth: true }
                AppButton { Layout.preferredWidth: 210; label: root.t("我已阅读并同意"); fillColor: accent; labelColor: "#10151C"; onClicked: { backend.acceptAgreement(); agreementDialog.close() } }
            }
        }
    }
    Component.onCompleted: { if (!backend.agreementAccepted) agreementDialog.open() }

    Timer { interval: 33; running: true; repeat: true; onTriggered: root.wavePhase=(root.wavePhase+0.006)%1 }
}
