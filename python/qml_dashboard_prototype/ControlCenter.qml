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
    onPageIndexChanged: backend.setActivePage(pageIndex)
    property bool darkMode: backend.theme !== "light"
    property url guidePreviewSource: ""
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
    property var pageTitles: [t("实时仪表盘"), t("设备与游戏"), t("个性化范围"), t("波形工作台"), t("负鼠工作台"), t("存档工具"), t("Mod 管理器"), t("创意工坊"), t("NPC 语音"), t("事件记录"), t("设置")]
    property var pageSubtitles: [
        t("游戏状态、心率与设备输出总览"),
        t("安装游戏插件，选择 V3 或 V4 连接"),
        t("设置心率映射范围与安全硬上限"),
        t("选择官方预设或创建自定义波形"),
        t("跟随游戏振动器档位，独立控制负鼠"),
        t("安全修改当前存档的经验值与游戏货币"),
        t("管理你已有的插件、V1 任务与 V2 功能包"),
        t("从原作者页面发现任务、插件与工具"),
        "",
        t("检查连接、安全归零和游戏事件"),
        t("外观、语言与通用偏好")
    ]

    // Cover-inspired: plum-gray surfaces, silver text, rose-magenta highlights.
    // Cyan remains a contrasting live-channel/device indicator.
    readonly property color bg: darkMode ? "#17121D" : "#F5F0F7"
    readonly property color panel: darkMode ? "#231B2B" : "#FFFAFF"
    readonly property color panel2: darkMode ? "#30263A" : "#EAE0EE"
    readonly property color border: darkMode ? "#58435F" : "#CDB8D5"
    readonly property color fg: darkMode ? "#F5F0FA" : "#2B2032"
    readonly property color muted: darkMode ? "#BCA9C6" : "#7D6288"
    readonly property color track: darkMode ? "#47364F" : "#D8C6DF"
    readonly property color accent: darkMode ? "#EE81C8" : "#B02592"
    readonly property color violet: darkMode ? "#B9A0E8" : "#7850AB"
    readonly property color cyan: darkMode ? "#68D7E5" : "#167B88"
    readonly property color green: darkMode ? "#80D5A0" : "#16725A"
    readonly property color amber: darkMode ? "#FFC857" : "#A96B00"
    readonly property color red: darkMode ? "#FF708C" : "#C84556"

    color: bg
    palette.window: bg
    palette.windowText: fg
    palette.base: panel
    palette.alternateBase: panel2
    palette.text: fg
    palette.button: panel2
    palette.buttonText: fg
    palette.highlight: accent
    palette.placeholderText: muted
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
            color: darkMode ? "#A36DAB" : "#FFF9FF"
            opacity: 0.65
        }
        Item { id: cardContent; anchors.fill: parent }
    }

    component AppButton: WorkbenchButton {
        id: button
        theme: root
        property alias label: button.text
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
        Layout.preferredHeight: 36
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
            ctx.strokeStyle = darkMode ? "#4B3B58" : "#D5C3DF"
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

    component SectionTitle: RowLayout {
        property string title: "标题"
        property string detail: ""
        Layout.fillWidth: true
        Text { text: parent.title; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Item { Layout.fillWidth: true }
        Text { text: parent.detail; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
    }

    component TutorialLine: Rectangle {
        id: tutorialLine
        property string numberText: "1"
        property string title: ""
        property string detail: ""
        Layout.fillWidth: true
        Layout.preferredHeight: 72
        radius: 15
        color: panel2
        border.color: border
        RowLayout {
            anchors.fill: parent; anchors.margins: 13; spacing: 13
            Rectangle {
                Layout.preferredWidth: 38; Layout.preferredHeight: 38; radius: 19
                color: Qt.rgba(accent.r, accent.g, accent.b, darkMode ? 0.18 : 0.14)
                Text { anchors.centerIn: parent; text: tutorialLine.numberText; color: accent; font.family: "Segoe UI"; font.pixelSize: 15; font.weight: Font.Bold }
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                Text { Layout.fillWidth: true; text: tutorialLine.title; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight }
                Text { Layout.fillWidth: true; text: tutorialLine.detail; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: darkMode ? "#251A2C" : "#EFE5F3" }
            GradientStop { position: 1; color: darkMode ? "#17131D" : "#FAF7FC" }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 224
            Layout.fillHeight: true
            color: darkMode ? "#1C1623" : "#F5EDF8"
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
                NavItem { targetPage: 4; iconText: "≈"; label: root.t("负鼠工作台") }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; Layout.topMargin: 7; Layout.bottomMargin: 7; color: root.border }
                NavItem { targetPage: 5; iconText: "✦"; label: root.t("存档工具") }
                NavItem { targetPage: 6; iconText: "⬡"; label: root.t("Mod 管理器") }
                NavItem { targetPage: 7; iconText: "✧"; label: root.t("创意工坊") }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; Layout.topMargin: 7; Layout.bottomMargin: 7; color: root.border }
                NavItem { targetPage: 8; iconText: "♫"; label: root.t("NPC 语音") }
                NavItem { targetPage: 9; iconText: "◎"; label: root.t("事件记录") }
                Item { Layout.fillHeight: true }
                NavItem { targetPage: 10; iconText: "⚙"; label: root.t("设置") }
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
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.minimumWidth: 100; spacing: 1
                        Text { Layout.fillWidth: true; elide: Text.ElideRight; text: pageTitles[pageIndex]; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 22; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; elide: Text.ElideRight; text: pageSubtitles[pageIndex]; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                    }
                    HudControlGroup { Layout.preferredWidth: 146; Layout.preferredHeight: 40; theme: root; onSettingsRequested: hudSettingsDialog.openSettings() }
                    AppButton {
                        Layout.leftMargin: 5
                        Layout.preferredWidth: 92
                        label: root.t("新手教程")
                        onClicked: onboardingDialog.openFromStart()
                    }
                    Rectangle {
                        Layout.preferredWidth: 142; Layout.preferredHeight: 38; radius: 19
                        color: Qt.rgba((backend.deviceConnected ? green : amber).r, (backend.deviceConnected ? green : amber).g, (backend.deviceConnected ? green : amber).b, darkMode ? 0.10 : 0.09)
                        border.color: Qt.rgba((backend.deviceConnected ? green : amber).r, (backend.deviceConnected ? green : amber).g, (backend.deviceConnected ? green : amber).b, 0.26)
                        Row { anchors.centerIn: parent; spacing: 7; Rectangle { width: 8; height: 8; radius: 4; color: backend.deviceConnected ? green : amber; anchors.verticalCenter: parent.verticalCenter } Text { text: backend.deviceConnected ? root.t("DG-LAB 已连接") : root.t("等待设备连接"); color: backend.deviceConnected ? green : amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; font.weight: Font.DemiBold } }
                    }
                    AppButton { Layout.preferredWidth: 82; label: root.t("全部停止"); fillColor: Qt.rgba(red.r,red.g,red.b,0.16); labelColor: red; onClicked: backend.emergencyStopAll() }
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
                                MetricBar { Layout.fillWidth: true; label: "A · "+(backend.pulseChannelSources.A==="heart" ? (backend.language==="en"?"Heart rate":"心率") : (backend.language==="en"?"Action":"动作")); valueText: backend.outputA.toFixed(1) + " / " + backend.hardCap; value: backend.outputA; maximum: backend.hardCap; barColor: accent }
                                MetricBar { Layout.fillWidth: true; label: "B · "+(backend.pulseChannelSources.B==="heart" ? (backend.language==="en"?"Heart rate":"心率") : (backend.language==="en"?"Action":"动作")); valueText: backend.outputB.toFixed(1) + " / " + backend.hardCap; value: backend.outputB; maximum: backend.hardCap; barColor: violet }
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
                                Layout.fillWidth: true; Layout.preferredHeight: 400; spacing: 15
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    StatusGlow { active: !backend.demoMode && (backend.gameRunning || backend.telemetryOnline); tint: backend.telemetryOnline ? root.green : root.accent }
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 22; spacing: 12
                                        SectionTitle { title: root.t("游戏插件"); detail: backend.telemetryOnline && !backend.demoMode ? (backend.language === "en" ? "Game Connected" : "游戏遥测已连接") : root.t("自动部署") }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Rectangle { width: 8; height: 8; radius: 4; color: backend.gameRunning ? green : muted }
                                            Text { text: backend.demoMode ? (backend.language === "en" ? "Demo · no process scan" : "演示模式 · 不检测进程") : backend.gameRunning ? (backend.language === "en" ? "Game running" : "游戏已启动") : (backend.language === "en" ? "Game not detected" : "未检测到游戏进程"); color: backend.gameRunning ? green : muted; font.pixelSize: 12 }
                                            Item { Layout.fillWidth: true }
                                            Text { visible: !backend.demoMode && backend.gameRunning; text: backend.telemetryOnline ? (backend.language === "en" ? "Telemetry ready" : "遥测已连接") : (backend.language === "en" ? "Waiting for telemetry" : "等待遥测连接"); color: backend.telemetryOnline ? green : amber; font.pixelSize: 11 }
                                        }
                                        Text { text: root.t("请选择能直接看到 SecretFlasherManaka.exe 的文件夹。\n不要选择 BepInEx、plugins 或游戏 Data 文件夹。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        TextField { Layout.fillWidth: true; text: backend.gameFolder; color: root.fg; font.family: "Microsoft YaHei UI"; selectByMouse: true; placeholderText: root.t("游戏根目录"); background: Rectangle { radius: 12; color: panel2; border.color: border } onEditingFinished: backend.setGameFolder(text) }
                                        Text { text: backend.gameStatus; color: backend.gameStatus.indexOf("就绪") >= 0 ? green : amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                        RowLayout { Layout.fillWidth: true; AppButton { label: root.t("选择目录"); onClicked: folderDialog.open() } AppButton { label: root.t("安装 / 修复运行环境"); onClicked: backend.installPlugin() } }
                                        AppButton { Layout.fillWidth: true; Layout.preferredHeight: 48; label: root.t("一键安装并启动游戏"); fillColor: accent; labelColor: "#11151C"; onClicked: backend.installAndLaunch() }
                                        Item { Layout.fillHeight: true }
                                        Text { text: root.t("正式支持游戏 v1.1.1 / v1.1.2 / v1.1.3；纯原版无需预装 BepInEx，控制中心会自动配置对应运行库。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                    }
                                }
                                ConnectionPanel { Layout.preferredWidth: 435; Layout.fillHeight: true; theme: root; onHelpRequested: networkHelpDialog.open() }
                            }
                            DeviceRoutes { visible: backend.socketProtocol === "v4"; Layout.fillWidth: true; theme: root; onWorkbenchRequested: page => root.pageIndex = page }
                            AppCard {
                                visible: backend.socketProtocol === "v3"
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
                                                Layout.fillWidth: true; Layout.fillHeight: true; radius: 14; color: panel2; border.color: border
                                                 clip: true
                                                 Image {
                                                     anchors.fill: parent; anchors.margins: 8; source: modelData
                                                     fillMode: Image.PreserveAspectFit; asynchronous: true; smooth: true; mipmap: true
                                                     scale: guideHit.containsMouse ? 1.025 : 1.0
                                                     Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                                                 }
                                                Rectangle { anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 8; width: 26; height: 26; radius: 13; color: accent; Text { anchors.centerIn: parent; text: index+1; color: "#11151C"; font.weight: Font.Bold } }
                                                 Rectangle {
                                                     anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 10
                                                     width: 30; height: 30; radius: 15
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
                            id: capConfirm; width: 480; anchors.centerIn: parent; modal: true; title: root.t("提高安全硬上限"); standardButtons: Dialog.Yes | Dialog.No
                            contentItem: Text { text: root.t("你正在把安全硬上限提高到 30 以上。\n请先确认个人可承受范围，并从低强度逐步测试。"); color: root.fg; font.family: "Microsoft YaHei UI"; padding: 18 }
                            background: Rectangle { color: panel; border.color: border; radius: 16 }
                            onAccepted: backend.savePersonalSettings(personalPage.draftTrigger,personalPage.draftFull,personalPage.draftMin,personalPage.draftMax,personalPage.draftCap,true)
                        }
                    }

                    // Waveform studio ------------------------------------------
                    Item {
                        id: wavePage
                        objectName: "pulseWorkbenchPage"
                        property string draftMode: backend.waveMode
                        property var draftSources: Object.assign({}, backend.pulseChannelSources)
                        property string editingChannel: "A"
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
                        function activeActionWave() { for (let i=0;i<backend.actionWaveMappings.length;i++) if (backend.actionWaveMappings[i].action===backend.action) return backend.actionWaveMappings[i]; return ({waveName:backend.language==="en"?"Action Output Off":"关闭动作输出",points:[0,0,0,0],color:muted}) }
                        function setSource(channel,source) { let copy=Object.assign({},draftSources);copy[channel]=source;draftSources=copy }
                        function openSourceMapping(channel) { editingChannel=channel;if(draftSources[channel]==="heart")heartMappingDialog.open();else actionMappingDialog.open() }
                        function saveStrategy() { return backend.saveWaveSettings(draftMode,draftFixed,draftMap.low,draftMap.mid,draftMap.high,draftMap.action,draftMap.peak,draftName,draftPoints,draftFrequency,draftSources.A,draftSources.B) }
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
                            draftSources={A:"heart",B:"action"}
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
                                AppButton { label: root.t("保存波形策略"); fillColor: green; labelColor: "#11151C"; onClicked: wavePage.saveStrategy() }
                            }
                            AppCard {
                                Layout.fillWidth: true; Layout.preferredHeight: 282
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 16; spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionTitle { title: root.t("波形预设与我的波形库"); detail: wavePage.filteredCatalog.length + root.t(" 个波形") }
                                        Repeater {
                                            model: [{key:"all",label:root.t("全部")},{key:"official",label:root.t("官方波形")},{key:"custom",label:backend.language==="en"?"Custom":root.t("自定义波形")},{key:"builtin",label:root.t("内置波形")}]
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
                                Layout.fillWidth: true; Layout.preferredHeight: wavePage.draftMode === "fixed" ? 420 : 350; spacing: 15
                                AppCard {
                                    Layout.preferredWidth: 410; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 20; spacing: 10
                                        SectionTitle { title: root.t("通道策略"); detail: "A / B" }
                                        WaveComboBox { visible: wavePage.draftMode === "fixed"; Layout.fillWidth: true; Layout.preferredHeight: 62; model: backend.presets; currentIndex: wavePage.presetIndex(wavePage.draftFixed); onActivated: wavePage.draftFixed=backend.presets[currentIndex].key }
                                        Repeater {
                                            model: ["A","B"]
                                            delegate: Rectangle {
                                                required property string modelData
                                                property bool heartSource: wavePage.draftSources[modelData]==="heart"
                                                property color sourceColor: heartSource ? cyan : violet
                                                Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 110
                                                radius: 15; color: panel2; border.color: sourceColor
                                                HoverHandler { id: sourceHover }
                                                ColumnLayout {
                                                    anchors.fill: parent; anchors.margins: 12; spacing: 7
                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        Text { text: modelData; color: sourceColor; font.pixelSize: 20; font.weight: Font.Bold }
                                                        Text { Layout.fillWidth: true; text: heartSource ? (backend.language==="en"?"Heart rate":"心率驱动") : (backend.action==="None"?root.t("等待游戏动作"):backend.actionDisplay); color: root.fg; font.pixelSize: 12; elide: Text.ElideRight }
                                                        WaveView { Layout.preferredWidth: 108; Layout.preferredHeight: 34; points: wavePage.draftMode==="fixed" ? wavePage.waveOption(wavePage.draftFixed).points : heartSource ? wavePage.waveOption(wavePage.draftMap.mid).points : wavePage.activeActionWave().points; waveColor: sourceColor; animated: sourceHover.hovered }
                                                    }
                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        ThemedComboBox { objectName: "pulseSource"+modelData; theme: root; Layout.fillWidth: true; Layout.preferredHeight: 36; model: backend.language==="en"?["Heart rate","Game action"]:["心率","游戏动作"]; currentIndex: heartSource?0:1; onActivated: wavePage.setSource(modelData,currentIndex===0?"heart":"action") }
                                                        AppButton { visible: wavePage.draftMode==="smart"; Layout.preferredWidth: 94; Layout.preferredHeight: 36; label: backend.language==="en"?"Configure":"配置波形"; onClicked: wavePage.openSourceMapping(modelData) }
                                                    }
                                                }
                                            }
                                        }
                                        Text { Layout.fillWidth: true; text: backend.language==="en"?"Save to apply. Channels with the same source share waveform rules.":"保存后生效；相同来源共用波形分配。"; color: muted; font.pixelSize: 10; wrapMode: Text.Wrap }
                                    }
                                }
                                AppCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 20; spacing: 10
                                        SectionTitle { title: root.t("自定义波形设计器"); detail: root.t("独立窗口编辑") }
                                        Rectangle {
                                            id: customSummary; Layout.fillWidth: true; Layout.fillHeight: true; radius: 15; color: darkMode ? "#100D07" : "#FFF8E5"; border.color: customSummaryHover.hovered ? cyan : border
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
                            objectName: "pulseHeartMappingDialog"
                            anchors.centerIn: parent; width: Math.min(780,root.width-90); height: Math.min(590,root.height-70); modal: true; padding: 0
                            background: Rectangle { color: panel; border.color: border; radius: 20 }
                            contentItem: ColumnLayout {
                                anchors.fill: parent; anchors.margins: 22; spacing: 12
                                RowLayout { Layout.fillWidth: true; ColumnLayout { spacing: 3; Text { text: wavePage.editingChannel + (backend.language==="en"?" · Heart rate":" 通道 · 心率波形"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 22; font.weight: Font.Bold } Text { text: root.t("为低、中、高心率和 Climax 分别选择波形"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } } Item { Layout.fillWidth: true } AppButton { Layout.preferredWidth: 110; label: root.t("恢复推荐"); onClicked: wavePage.resetHeartMapping() } AppButton { Layout.preferredWidth: 84; label: backend.language==="en"?"Close":root.t("关闭"); onClicked: heartMappingDialog.close() } }
                                Repeater {
                                    model: [{key:"low",label:root.t("低心率段"),detail:backend.heartRateBands.start+" ≤ BPM < "+backend.heartRateBands.lowEnd},{key:"mid",label:root.t("中心率段"),detail:backend.heartRateBands.lowEnd+" ≤ BPM < "+backend.heartRateBands.highStart},{key:"high",label:root.t("高心率段"),detail:"BPM ≥ "+backend.heartRateBands.highStart},{key:"peak",label:"Climax",detail:root.t("峰值包络")}]
                                    delegate: Rectangle {
                                        required property var modelData
                                        Layout.fillWidth: true; Layout.fillHeight: true; radius: 14; color: panel2; border.color: modelData.key==="peak"?accent:border
                                        RowLayout { anchors.fill: parent; anchors.margins: 12; spacing: 13; ColumnLayout { Layout.preferredWidth: 150; spacing: 3; Text { text: modelData.label; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold } Text { text: modelData.detail; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } } WaveComboBox { Layout.fillWidth: true; model: backend.presets; currentIndex: wavePage.presetIndex(wavePage.draftMap[modelData.key]); onActivated: { let copy=Object.assign({},wavePage.draftMap);copy[modelData.key]=backend.presets[currentIndex].key;wavePage.draftMap=copy } } }
                                    }
                                }
                                Text { Layout.fillWidth: true; text: backend.language==="en" ? "Below "+backend.heartRateBands.start+" BPM: zero target. Full level at "+backend.heartRateBands.full+" BPM. Heart-rate channels share these rules." : "低于 "+backend.heartRateBands.start+" BPM 目标为零，"+backend.heartRateBands.full+" BPM 达到满幅；心率通道共用这些分配。"; color: muted; font.pixelSize: 11; wrapMode: Text.Wrap }
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
                                    Layout.fillWidth: true; Layout.fillHeight: true; radius: 16; color: darkMode ? "#0C0A06" : "#F5EFF9"; border.color: cyan
                                    Canvas {
                                        id: editorCanvas; anchors.fill: parent; anchors.margins: 18; antialiasing: true
                                        onPaint: { const ctx=getContext("2d");ctx.reset();const p=wavePage.draftPoints;ctx.strokeStyle=darkMode?"#29364E":"#D7DFEA";ctx.lineWidth=1;for(let i=0;i<=4;i++){let y=height*i/4;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y);ctx.stroke()}for(let i=0;i<16;i++){let x=width*i/15;ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,height);ctx.stroke()}if(!p||p.length<2)return;ctx.strokeStyle=cyan;ctx.lineWidth=4;ctx.lineJoin="round";ctx.beginPath();for(let i=0;i<p.length;i++){let x=i/(p.length-1)*width;let y=height-(p[i]/100)*height;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}ctx.stroke();for(let i=0;i<p.length;i++){let x=i/(p.length-1)*width;let y=height-(p[i]/100)*height;ctx.fillStyle=root.fg;ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fill()} }
                                        Connections { target: wavePage; function onDraftPointsChanged(){editorCanvas.requestPaint()} }
                                        Connections { target: root; function onDarkModeChanged(){editorCanvas.requestPaint()} }
                                        Rectangle {
                                            id: editorPlayhead
                                            property real phase: 0
                                            visible: waveformEditor.visible
                                            width: 2; height: parent.height
                                            color: Qt.rgba(cyan.r,cyan.g,cyan.b,0.55)
                                            x: phase * Math.max(0,editorCanvas.width-width)
                                            Timer { interval: 33; repeat: true; running: editorPlayhead.visible; onTriggered: editorPlayhead.phase=(editorPlayhead.phase+0.006)%1 }
                                        }
                                        MouseArea { anchors.fill: parent; cursorShape: Qt.CrossCursor; function paint(mouse){let i=Math.round(Math.max(0,Math.min(1,mouse.x/width))*15);let v=(1-Math.max(0,Math.min(1,mouse.y/height)))*100;wavePage.setPoint(i,v)} onPressed: mouse=>paint(mouse); onPositionChanged: mouse=>{if(pressed)paint(mouse)}; onReleased: wavePage.commitEditHistory() }
                                    }
                                }
                                RowLayout { Layout.fillWidth: true; spacing: 8; AppButton { Layout.preferredWidth: 82; label: root.t("撤销"); enabled: wavePage.editHistoryIndex>0; onClicked: wavePage.undoEdit() } AppButton { Layout.preferredWidth: 82; label: root.t("重做"); enabled: wavePage.editHistoryIndex+1<wavePage.editHistory.length; onClicked: wavePage.redoEdit() } AppButton { Layout.preferredWidth: 82; label: root.t("平滑"); onClicked: wavePage.smoothPoints() } AppButton { Layout.preferredWidth: 82; label: root.t("镜像"); onClicked: wavePage.mirrorPoints() } AppButton { Layout.preferredWidth: 88; label: root.t("归一化"); onClicked: wavePage.normalizePoints() } AppButton { Layout.preferredWidth: 82; label: root.t("清空"); onClicked: wavePage.applyTemplate("clear") } Item { Layout.fillWidth: true } Text { text: root.t("实际输出仍受强度范围和硬上限限制"); color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 } }
                                RowLayout { Layout.fillWidth: true; Text { text: root.t("频率"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 } Slider { Layout.fillWidth: true; from: 10; to: 240; stepSize: 1; value: wavePage.draftFrequency; onMoved: wavePage.draftFrequency=Math.round(value) } Text { text: wavePage.draftFrequency+" Hz"; color: cyan; font.pixelSize: 12; font.weight: Font.DemiBold } AppButton { Layout.preferredWidth: 190; Layout.preferredHeight: 46; label: root.t("保存到我的波形库"); fillColor: cyan; labelColor: "#10151A"; onClicked: { if(backend.saveCustomWaveform(wavePage.draftName,wavePage.draftPoints,wavePage.draftFrequency)){wavePage.draftName=backend.customName;waveformEditor.close()} } } }
                            }
                        }

                        Dialog {
                            id: actionMappingDialog
                            objectName: "pulseActionMappingDialog"
                            anchors.centerIn: parent; width: Math.min(980,root.width-70); height: Math.min(700,root.height-50); modal: true; padding: 0
                            background: Rectangle { color: panel; border.color: border; radius: 20 }
                            contentItem: ColumnLayout {
                                anchors.fill: parent; anchors.margins: 20; spacing: 10
                                RowLayout { Layout.fillWidth: true; ColumnLayout { spacing: 3; Text { text: wavePage.editingChannel+" · "+root.t("动作类型与波形"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 21; font.weight: Font.Bold } Text { text: backend.language==="en"?"Action channels share these rules. Changes apply immediately.":"动作通道共用这些分配；此处的动作波形修改即时保存。"; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } } Item { Layout.fillWidth: true } AppButton { Layout.preferredWidth: 104; label: root.t("恢复推荐"); onClicked: backend.resetActionWaveforms() } AppButton { Layout.preferredWidth: 84; label: root.t("关闭"); onClicked: actionMappingDialog.close() } }
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

                    // Independent Opossum workbench ---------------------------
                    OvcWorkbench { theme: root; onConnectionSettingsRequested: root.pageIndex = 1 }

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
                                    color: darkMode ? "#251D2D" : "#F6F0FA"
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
                                            color: darkMode ? "#291F31" : "#EEE5F4"; border.color: border
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
                                                color: modelData.pinned ? (darkMode ? "#38263F" : "#F6E4F4") : (darkMode ? "#291F31" : "#EEE5F4")
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
                                                color: darkMode ? "#291F31" : "#EEE5F4"
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
                                                    color: darkMode ? "#291F31" : "#EEE5F4"; border.color: modelData.enabled ? Qt.rgba(green.r,green.g,green.b,0.40) : border
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
                                                color: modelData.enabled ? (darkMode ? "#291F31" : "#EEE5F4") : (darkMode ? "#12100B" : "#EEE2BD")
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
                                    color: darkMode ? "#291F31" : "#EEE5F4"; border.color: border
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
                                        color: modelData.pinned ? (darkMode ? "#38263F" : "#F6E4F4") : (darkMode ? "#291F31" : "#EEE5F4")
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
                                            color: darkMode ? "#302238" : "#EDDFEF"; border.color: Qt.rgba(violet.r,violet.g,violet.b,0.38)
                                            RowLayout {
                                                anchors.fill: parent; anchors.margins: 14; spacing: 12
                                                Rectangle { width: 38; height: 38; radius: 12; color: Qt.rgba(violet.r,violet.g,violet.b,0.16); Text { anchors.centerIn: parent; text: "↗"; color: violet; font.pixelSize: 16; font.weight: Font.Bold } }
                                                ColumnLayout { Layout.fillWidth: true; spacing: 4; Text { text: root.t("F95Zone 汉化整合原帖"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold } Text { Layout.fillWidth: true; text: root.t("查看使用说明、更新记录与作者声明"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap } }
                                                AppButton { Layout.preferredWidth: 112; Layout.preferredHeight: 38; label: root.t("打开原帖"); fillColor: violet; labelColor: "#10151A"; onClicked: backend.openExternalUrl("https://f95zone.to/threads/secret-flasher-manaka-custom-missions-1-2-1-version-2-4-0.263276/post-20360819") }
                                            }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.fillHeight: true; radius: 15
                                            color: darkMode ? "#291F31" : "#EEE5F4"; border.color: border
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
                                        color: darkMode ? "#302238" : "#F3E1F2"; border.color: Qt.rgba(violet.r,violet.g,violet.b,0.55); border.width: 1
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
                                                        color: darkMode ? "#291F31" : "#FFFAFF"; border.color: border
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
                                        width: 48; height: 48; radius: 15
                                        color: Qt.rgba(cyan.r, cyan.g, cyan.b, 0.14)
                                        Text { anchors.centerIn: parent; text: "♫"; color: cyan; font.pixelSize: 23; font.weight: Font.Bold }
                                    }
                                    Text { Layout.fillWidth: true; text: root.t("NPC 语气与字幕"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 20; font.weight: Font.Bold }
                                    Rectangle {
                                        width: npcVoiceStatusText.width + 26; height: 34; radius: 12
                                        color: Qt.rgba((backend.npcVoiceInstalled ? green : amber).r, (backend.npcVoiceInstalled ? green : amber).g, (backend.npcVoiceInstalled ? green : amber).b, 0.13)
                                        Text { id: npcVoiceStatusText; anchors.centerIn: parent; text: backend.npcVoiceInstalled ? root.t("已就绪") : root.t("等待安装"); color: backend.npcVoiceInstalled ? green : amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    }
                                }

                                Rectangle {
                                    id: npcMasterCard
                                    property bool active: backend.npcVoiceInstalled && backend.npcVoiceEnabled
                                    Layout.fillWidth: true; Layout.preferredHeight: 112; radius: 18
                                    color: Qt.rgba((active ? green : muted).r, (active ? green : muted).g, (active ? green : muted).b, darkMode ? 0.11 : 0.09)
                                    border.color: Qt.rgba((active ? green : muted).r, (active ? green : muted).g, (active ? green : muted).b, 0.35)
                                    Behavior on color { ColorAnimation { duration: 180 } }
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: 18; spacing: 18
                                        Rectangle {
                                            Layout.preferredWidth: 54; Layout.preferredHeight: 54; radius: 18
                                            color: Qt.rgba((npcMasterCard.active ? green : muted).r, (npcMasterCard.active ? green : muted).g, (npcMasterCard.active ? green : muted).b, 0.18)
                                            Text { anchors.centerIn: parent; text: npcMasterCard.active ? "♫" : "×"; color: npcMasterCard.active ? green : muted; font.pixelSize: 24; font.weight: Font.Bold }
                                        }
                                        ColumnLayout {
                                            Layout.fillWidth: true; spacing: 5
                                            Text { text: root.t("NPC 功能总开关"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 17; font.weight: Font.Bold }
                                            Text { text: !backend.npcVoiceInstalled ? root.t("尚未安装") : npcMasterCard.active ? root.t("NPC 语气词与字幕已开启") : root.t("NPC 语气词与字幕已关闭"); color: npcMasterCard.active ? green : muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; font.weight: Font.DemiBold }
                                            Text { text: backend.npcVoiceInstalled ? root.t("切换后重新启动游戏生效；语言、台词和细分设置会保留。") : root.t("请先安装 NPC 语音插件，再使用总开关。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                        }
                                        Rectangle {
                                            id: npcMasterSwitch
                                            property bool active: npcMasterCard.active
                                            Layout.preferredWidth: 166; Layout.preferredHeight: 58; radius: 29
                                            opacity: backend.npcVoiceInstalled ? 1 : 0.45
                                            color: active ? green : track
                                            border.color: active ? Qt.lighter(green, 1.08) : border
                                            Behavior on color { ColorAnimation { duration: 180 } }
                                            Text {
                                                anchors.verticalCenter: parent.verticalCenter
                                                anchors.left: active ? parent.left : undefined
                                                anchors.right: active ? undefined : parent.right
                                                anchors.leftMargin: 24; anchors.rightMargin: 24
                                                text: active ? root.t("开启") : root.t("关闭")
                                                color: active ? "#102018" : root.fg
                                                font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.Bold
                                            }
                                            Rectangle {
                                                width: 46; height: 46; radius: 23
                                                y: 6; x: npcMasterSwitch.active ? npcMasterSwitch.width - width - 6 : 6
                                                color: darkMode ? "#F5F0FA" : "#FFFFFF"
                                                border.color: Qt.rgba(0, 0, 0, 0.12)
                                                Behavior on x { NumberAnimation { duration: 190; easing.type: Easing.OutCubic } }
                                            }
                                            MouseArea {
                                                anchors.fill: parent
                                                enabled: backend.npcVoiceInstalled
                                                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                                onClicked: backend.setNpcVoiceEnabled(!backend.npcVoiceEnabled)
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true; Layout.preferredHeight: 104; radius: 16
                                    color: darkMode ? "#201926" : "#F5EFF9"; border.color: border
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: 16; spacing: 18
                                        ColumnLayout {
                                            Layout.fillWidth: true; spacing: 5
                                            Text { text: root.t("当前状态"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                            Text { Layout.fillWidth: true; text: backend.npcVoiceInstallStatus; color: backend.npcVoiceInstalled ? green : amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold; wrapMode: Text.Wrap }
                                            Text { Layout.fillWidth: true; text: backend.gameFolder.length ? backend.gameFolder : root.t("尚未选择游戏目录"); color: muted; font.family: "Cascadia Mono"; font.pixelSize: 9; elide: Text.ElideMiddle }
                                        }
                                        AppButton { Layout.preferredWidth: 260; Layout.preferredHeight: 48; label: backend.npcVoiceInstalled ? root.t("更新 / 修复 NPC 语音") : root.t("一键安装 NPC 语音"); fillColor: accent; labelColor: "#10151A"; enabled: backend.gameFolder.length > 0; onClicked: backend.installNpcVoices() }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true; Layout.preferredHeight: 124; radius: 16
                                    color: darkMode ? "#30263A" : "#EFE4F4"; border.color: border
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 16; spacing: 10
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: root.t("字幕与语音设置"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 15; font.weight: Font.DemiBold }
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
                                            Text { text: root.t("字幕语言"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                                            Repeater {
                                                model: [{key:"zh",label:"中文"},{key:"ja",label:"日本語"},{key:"en",label:"English"}]
                                                delegate: AppButton {
                                                    required property var modelData
                                                    Layout.preferredWidth: 126; Layout.preferredHeight: 38
                                                    label: modelData.label
                                                    fillColor: backend.npcVoiceLanguage === modelData.key ? cyan : panel
                                                    labelColor: backend.npcVoiceLanguage === modelData.key ? "#10151A" : root.fg
                                                    onClicked: backend.setNpcVoiceLanguage(modelData.key)
                                                }
                                            }
                                            Item { Layout.fillWidth: true }
                                            Text { text: root.t("语气词"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                                            Switch { id: npcAudioSwitch; checked: backend.npcVoiceAudioEnabled; palette.highlight: green; onClicked: backend.setNpcVoicePlayback(checked, npcSubtitleSwitch.checked) }
                                            Text { text: root.t("字幕"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                                            Switch { id: npcSubtitleSwitch; checked: backend.npcVoiceSubtitlesEnabled; palette.highlight: green; onClicked: backend.setNpcVoicePlayback(npcAudioSwitch.checked, checked) }
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
                            RowLayout { Layout.fillWidth: true; Text { text: root.t("最近 ") + backend.logs.length + root.t(" 条记录"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 } Item { Layout.fillWidth: true } AppButton { label: root.t("清空日志"); onClicked: backend.clearLogs() } }
                            Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true; radius: 14
                                color: darkMode ? "#201926" : "#F5EFF9"; border.color: border
                                ListView {
                                    id: logList; anchors.fill: parent; anchors.margins: 8; clip: true; model: backend.logs; spacing: 2
                                    delegate: Rectangle { required property var modelData; required property int index; width: logList.width; height: 34; radius: 8; color: index % 2 ? "transparent" : (darkMode ? "#30263A" : "#E6DAEE"); Text { anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 10; text: modelData; color: root.fg; font.family: "Cascadia Mono"; font.pixelSize: 11; elide: Text.ElideRight } }
                                    ScrollBar.vertical: ScrollBar { contentItem: Rectangle { implicitWidth: 5; radius: 3; color: muted } background: Rectangle { color: "transparent" } }
                                    onCountChanged: positionViewAtEnd()
                                }
                            }
                        }
                    }

                    SettingsPage { theme: root; onHudSettingsRequested: hudSettingsDialog.openSettings(); onTutorialRequested: onboardingDialog.openFromStart() }
                }
            }
        }
    }

    HudSettingsDialog { id: hudSettingsDialog; theme: root }
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
        id: npcTextEditorDialog
        anchors.centerIn: parent
        width: Math.min(940, root.width - 70)
        height: Math.min(700, root.height - 54)
        modal: true
        closePolicy: Popup.CloseOnEscape
        padding: 0
        background: Rectangle { color: panel; border.color: border; border.width: 1; radius: 20 }
        contentItem: ColumnLayout {
            spacing: 0
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 82; radius: 20
                color: darkMode ? "#302238" : "#EDDFEF"
                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 20; color: parent.color }
                Column {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 24; spacing: 3
                    Text { text: root.t("NPC 字幕台词"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 20; font.weight: Font.Bold }
                    Text { text: root.t("声音固定为日文短语气词；这里仅编辑字幕文本。"); color: cyan; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                }
                AppButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: 20; width: 96; height: 40; label: root.t("关闭"); onClicked: npcTextEditorDialog.close() }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.margins: 22; spacing: 12
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Text { text: root.t("字幕语言"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; Layout.preferredWidth: 70 }
                    Repeater {
                        model: [{key:"zh",label:"中文"},{key:"ja",label:"日本語"},{key:"en",label:"English"}]
                        delegate: AppButton {
                            required property var modelData
                            Layout.preferredWidth: 120; Layout.preferredHeight: 38
                            label: modelData.label
                            fillColor: root.npcTextLanguage === modelData.key ? cyan : panel2
                            labelColor: root.npcTextLanguage === modelData.key ? "#10151A" : root.fg
                            onClicked: { root.npcTextLanguage = modelData.key; root.reloadNpcTextEditor() }
                        }
                    }
                    Item { Layout.fillWidth: true }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Text { text: root.t("分类"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; Layout.preferredWidth: 52 }
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
                            fillColor: root.npcTextState === modelData.key ? violet : panel2
                            labelColor: root.npcTextState === modelData.key ? "#10151A" : root.fg
                            onClicked: { root.npcTextState = modelData.key; root.reloadNpcTextEditor() }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    Text { text: root.t("角色"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; Layout.preferredWidth: 52 }
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
                            fillColor: root.npcTextProfile === modelData.key ? cyan : panel2
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
                    font.family: "Microsoft YaHei UI"
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
                ScrollView {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    clip: true
                    background: Rectangle { color: darkMode ? "#201926" : "#F6F0FA"; border.color: border; radius: 14 }
                    TextArea {
                        id: npcTextArea
                        padding: 16
                        color: root.fg
                        selectionColor: accent
                        selectedTextColor: "#10151A"
                        font.family: "Microsoft YaHei UI"
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

    Dialog {
        id: guidePreviewDialog
        anchors.centerIn: parent
        width: Math.min(1120, root.width - 64)
        height: Math.min(720, root.height - 54)
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: 14
        background: Rectangle {
            color: darkMode ? "#201926" : "#F6F0FA"
            border.color: accent; border.width: 1; radius: 20
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
                border.color: border
                Text { anchors.centerIn: parent; text: "×"; color: root.fg; font.pixelSize: 23 }
                MouseArea {
                    id: closeGuideHit; anchors.fill: parent; hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor; onClicked: guidePreviewDialog.close()
                }
            }
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
                color: darkMode ? "#302238" : "#EDDFEF"
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
        background: Rectangle { color: panel; border.color: border; border.width: 1; radius: 22 }
        contentItem: ColumnLayout {
            spacing: 0
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 92; radius: 22
                color: darkMode ? "#302238" : "#EDDFEF"
                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 22; color: parent.color }
                Column {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; anchors.leftMargin: 26; spacing: 4
                    Text { text: root.t("第一次使用 Manaka × DG-LAB？"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 21; font.weight: Font.Bold }
                    Text { text: root.t("从游戏准备到安全连接，一步一步完成；所有步骤都可以跳过"); color: accent; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                }
                Row {
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: 25; spacing: 6
                    Repeater {
                        model: 7
                        Rectangle {
                            required property int index
                            width: onboardingDialog.step === index ? 28 : 9; height: 9; radius: 5
                            color: onboardingDialog.step === index ? accent : border
                            Behavior on width { NumberAnimation { duration: 170; easing.type: Easing.OutCubic } }
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
                        Text { Layout.fillWidth: true; text: root.t("先告诉我你的情况"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 22; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter }
                        Text { Layout.fillWidth: true; text: root.t("向导不会替你下载游戏，也不会上传任何文件。你可以稍后从窗口顶部重新打开它。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 16
                            Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true; radius: 18; color: panel2; border.color: border
                                ColumnLayout { anchors.fill: parent; anchors.margins: 22; spacing: 10
                                    Rectangle { width: 52; height: 52; radius: 26; color: Qt.rgba(green.r,green.g,green.b,0.16); Text { anchors.centerIn: parent; text: "✓"; color: green; font.pixelSize: 25; font.weight: Font.Bold } }
                                    Text { text: root.t("我已经有游戏"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 17; font.weight: Font.Bold }
                                    Text { Layout.fillWidth: true; text: root.t("从选择 SecretFlasherManaka 游戏根目录开始，然后安装连接所需的运行环境与插件。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; lineHeight: 1.35; wrapMode: Text.Wrap }
                                    Item { Layout.fillHeight: true }
                                    AppButton { Layout.fillWidth: true; Layout.preferredHeight: 48; label: root.t("从安装开始"); fillColor: green; labelColor: "#10151A"; onClicked: onboardingDialog.step = 2 }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true; radius: 18; color: panel2; border.color: border
                                ColumnLayout { anchors.fill: parent; anchors.margins: 22; spacing: 10
                                    Rectangle { width: 52; height: 52; radius: 26; color: Qt.rgba(accent.r,accent.g,accent.b,0.16); Text { anchors.centerIn: parent; text: "↗"; color: accent; font.pixelSize: 23; font.weight: Font.Bold } }
                                    Text { text: root.t("我还没有游戏"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 17; font.weight: Font.Bold }
                                    Text { Layout.fillWidth: true; text: root.t("先前往 DLsite 购买并下载正版游戏。准备完成后，再回来继续安装。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; lineHeight: 1.35; wrapMode: Text.Wrap }
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
                        Text { text: root.t("1 · 获取正版游戏"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 22; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("在 DLsite 的作品页面购买并下载游戏。下载结束后完整解压，记住能直接看到 SecretFlasherManaka.exe 的文件夹位置。"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; lineHeight: 1.45; wrapMode: Text.Wrap }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 120; radius: 17; color: panel2; border.color: accent
                            RowLayout { anchors.fill: parent; anchors.margins: 18; spacing: 16
                                Rectangle { width: 52; height: 52; radius: 16; color: Qt.rgba(accent.r,accent.g,accent.b,0.16); Text { anchors.centerIn: parent; text: "DL"; color: accent; font.pixelSize: 16; font.weight: Font.Bold } }
                                ColumnLayout { Layout.fillWidth: true; spacing: 4
                                    Text { text: "Secret Flasher Manaka · RJ01389782"; color: root.fg; font.family: "Segoe UI"; font.pixelSize: 14; font.weight: Font.DemiBold }
                                    Text { Layout.fillWidth: true; text: root.t("官方购买页将在浏览器中打开；购买、下载和账号登录均由 DLsite 处理。"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap }
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
                        Text { text: root.t("2 · 选择游戏目录"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 22; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("请选择能直接看到 SecretFlasherManaka.exe 的文件夹。不要选择 BepInEx、plugins 或游戏 Data 文件夹。"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; lineHeight: 1.4; wrapMode: Text.Wrap }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 120; radius: 17; color: panel2; border.color: backend.gameFolder.length > 0 ? green : border
                            ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 8
                                Text { text: root.t("当前游戏目录"); color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 9 }
                                Text { Layout.fillWidth: true; text: backend.gameFolder || root.t("尚未选择游戏目录"); color: root.fg; font.family: "Cascadia Mono"; font.pixelSize: 10; elide: Text.ElideMiddle }
                                Text { Layout.fillWidth: true; text: backend.gameStatus; color: backend.gameFolder.length > 0 ? green : amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; wrapMode: Text.Wrap }
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
                        Text { text: root.t("3 · 安装连接插件"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 22; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("关闭游戏后点击安装。软件会为纯原版配置 BepInEx 6，并安装 Manaka DG-LAB 遥测插件；已有环境则会检查并修复。"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; lineHeight: 1.45; wrapMode: Text.Wrap }
                        TutorialLine { numberText: "1"; title: root.t("完全退出游戏"); detail: root.t("不要停留在标题画面，确认游戏进程已经关闭") }
                        TutorialLine { numberText: "2"; title: root.t("安装运行环境"); detail: root.t("自动配置 BepInEx 与本软件的遥测插件") }
                        TutorialLine { numberText: "3"; title: root.t("首次启动游戏"); detail: root.t("进入存档后，控制中心会开始收到游戏数据") }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 58; radius: 14; color: panel2; border.color: border; Text { anchors.fill: parent; anchors.margins: 14; text: backend.gameStatus; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 10; verticalAlignment: Text.AlignVCenter; wrapMode: Text.Wrap } }
                        AppButton { Layout.preferredWidth: 230; Layout.preferredHeight: 48; label: root.t("安装 / 修复运行环境"); fillColor: accent; labelColor: "#10151A"; onClicked: backend.installPlugin() }
                        Item { Layout.fillHeight: true }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 34; spacing: 15
                        Text { text: root.t("4 · 连接 DG-LAB"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 22; font.weight: Font.Bold }
                        Text { Layout.fillWidth: true; text: root.t("让手机和电脑连接同一个 Wi‑Fi。先在 DG-LAB App 连接蓝牙主机，再进入 SOCKET 控制扫描下方二维码。"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; lineHeight: 1.4; wrapMode: Text.Wrap }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 22
                            Rectangle { Layout.preferredWidth: 220; Layout.preferredHeight: 220; radius: 18; color: "white"; Image { anchors.fill: parent; anchors.margins: 10; source: backend.qrSource; fillMode: Image.PreserveAspectFit; visible: source !== "" } Text { anchors.centerIn: parent; visible: backend.qrSource === ""; text: root.t("正在生成二维码…"); color: "#4B5565"; font.pixelSize: 11 } }
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
                        Text { text: root.t("5 · 常用页面"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 22; font.weight: Font.Bold }
                        TutorialLine { numberText: "◈"; title: root.t("实时仪表盘"); detail: root.t("查看游戏心率、场景、动作以及 A/B 通道实时输出") }
                        TutorialLine { numberText: "⌁"; title: root.t("设备与游戏"); detail: root.t("选择游戏、安装插件、启动游戏并扫描设备二维码") }
                        TutorialLine { numberText: "◫"; title: root.t("个性化范围"); detail: root.t("设置心率触发区间、日常强度范围和安全硬上限") }
                        TutorialLine { numberText: "〰"; title: root.t("波形工作台"); detail: root.t("选择官方波形、编辑自定义波形，并给不同动作分配反馈") }
                        TutorialLine { numberText: "≈"; title: root.t("负鼠工作台"); detail: root.t("跟随游戏振动器档位，独立控制负鼠") }
                        Item { Layout.fillHeight: true }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 30; spacing: 12
                        Text { text: root.t("6 · 管理与排查页面"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 22; font.weight: Font.Bold }
                        TutorialLine { numberText: "✦"; title: root.t("存档工具"); detail: root.t("备份并修改当前存档的经验与游戏货币；按页面提示触发结算") }
                        TutorialLine { numberText: "⬡"; title: root.t("Mod 管理器"); detail: root.t("扫描本地插件和任务，查看说明，并在下次启动前启用或停用") }
                        TutorialLine { numberText: "✧"; title: root.t("创意工坊"); detail: root.t("前往原作者页面获取 Mod，或使用 user9527 汉化整合导入向导") }
                        TutorialLine { numberText: "◎"; title: root.t("事件记录"); detail: root.t("连接或输出异常时，查看最近的游戏事件与安全归零记录") }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 78; radius: 15
                            color: Qt.rgba(green.r,green.g,green.b,darkMode?0.10:0.09); border.color: Qt.rgba(green.r,green.g,green.b,0.35)
                            Text { anchors.fill: parent; anchors.margins: 15; text: root.t("准备完成！建议第一次把强度保持在“低”，确认设备和动作反馈都符合预期后再逐步调整。教程以后可从顶部“新手教程”重新打开。"); color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; lineHeight: 1.35; wrapMode: Text.Wrap; verticalAlignment: Text.AlignVCenter }
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
                Text { visible: onboardingDialog.step > 0; text: (onboardingDialog.step + 1) + " / 7"; color: muted; font.family: "Cascadia Mono"; font.pixelSize: 10 }
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

    Dialog {
        id: progressConfirm; width: 640; anchors.centerIn: parent; modal: true; title: root.t("确认修改当前存档"); standardButtons: Dialog.Yes | Dialog.No
        contentItem: Text { text: backend.language === "en" ? "Currency will be set to " + progressPage.draftRp + " and EXP to " + progressPage.draftExp + ".\nThe original save is backed up before the game save flow runs.\n\nConfirm that the character is outdoors. After editing EXP, complete any mission and return home to trigger settlement before the level updates." : "将把游戏货币修改为 " + progressPage.draftRp + "，经验值修改为 " + progressPage.draftExp + "。\n软件会先创建备份，再调用游戏自己的保存流程。\n\n请确认角色当前位于室外（非室内）。经验写入后，需要完成任意任务并回家触发结算，等级才会刷新。"; color: root.fg; font.family: "Microsoft YaHei UI"; padding: 18; wrapMode: Text.Wrap }
        background: Rectangle { color: panel; border.color: border; radius: 16 }
        onAccepted: backend.applyProgressValues(progressPage.draftRp, progressPage.draftExp)
    }
    Dialog {
        id: modDeleteConfirm
        width: 600
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
        id: toast; x: root.width-width-24; y: root.height-height-24; width: 380; height: Math.max(104, toastContent.implicitHeight + 36); modal: false; closePolicy: Popup.NoAutoClose
        property string toastTitle: ""; property string toastMessage: ""
        background: Rectangle { color: panel; border.color: border; radius: 17 }
        contentItem: Column { id: toastContent; spacing: 6; Text { text: toast.toastTitle; color: root.fg; font.family: "Microsoft YaHei UI"; font.pixelSize: 14; font.weight: Font.DemiBold } Text { width: 340; text: toast.toastMessage; color: muted; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; wrapMode: Text.Wrap } }
        Timer { id: toastTimer; interval: 5000; onTriggered: toast.close() }
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
                color: darkMode ? "#35233B" : "#F9E8F7"
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
                AppButton { Layout.preferredWidth: 170; label: root.t("不同意并退出"); fillColor: darkMode ? "#382330" : "#EFD9E6"; labelColor: red; onClicked: backend.declineAgreement() }
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
