import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

ApplicationWindow {
    id: root
    width: 1280
    height: 790
    minimumWidth: 1120
    minimumHeight: 720
    visible: true
    title: "Manaka / DG-LAB · Dashboard Prototype"
    color: bg

    property bool darkMode: true
    property bool outputPaused: false
    property real heartRate: 128
    property real alertLevel: 34
    property real excitement: 67
    property real rawOutputA: 18
    property real rawOutputB: 7
    readonly property real outputA: outputPaused ? 0 : rawOutputA
    readonly property real outputB: outputPaused ? 0 : rawOutputB
    property int safetyCap: 30
    property real wavePhase: 0

    readonly property color bg: darkMode ? "#070A11" : "#EEF2F8"
    readonly property color panel: darkMode ? "#101725" : "#F8FAFD"
    readonly property color panelRaised: darkMode ? "#172134" : "#E8EEF7"
    readonly property color border: darkMode ? "#2A3850" : "#C8D3E3"
    readonly property color textPrimary: darkMode ? "#F7F9FD" : "#182033"
    readonly property color textMuted: darkMode ? "#8996AA" : "#68758A"
    readonly property color track: darkMode ? "#253146" : "#CBD6E5"
    readonly property color accent: darkMode ? "#FF6FAE" : "#DF4D86"
    readonly property color violet: darkMode ? "#A78BFA" : "#7659D9"
    readonly property color cyan: darkMode ? "#5DE0EA" : "#168F9B"
    readonly property color green: darkMode ? "#4ADDA5" : "#168F68"
    readonly property color amber: darkMode ? "#F7C55B" : "#C68114"
    readonly property color danger: darkMode ? "#FF5D7A" : "#D94362"

    Behavior on color { ColorAnimation { duration: 260 } }

    component GlassCard: Rectangle {
        id: card
        property alias content: contentItem.data
        default property alias contentData: contentItem.data
        radius: 22
        color: panel
        border.color: border
        border.width: 1
        clip: true
        Behavior on color { ColorAnimation { duration: 260 } }
        Behavior on border.color { ColorAnimation { duration: 260 } }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 1
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            color: darkMode ? "#52627C" : "#FFFFFF"
            opacity: 0.72
        }
        Item { id: contentItem; anchors.fill: parent }
    }

    component SoftButton: Rectangle {
        id: softButton
        property string label: "Button"
        property color fillColor: panelRaised
        property color labelColor: textPrimary
        signal clicked()
        implicitWidth: 112
        implicitHeight: 42
        radius: 13
        color: mouseArea.pressed ? Qt.darker(fillColor, 1.08)
                                 : mouseArea.containsMouse ? Qt.lighter(fillColor, 1.06) : fillColor
        border.color: Qt.rgba(labelColor.r, labelColor.g, labelColor.b, 0.18)
        Behavior on color { ColorAnimation { duration: 120 } }

        Text {
            anchors.centerIn: parent
            text: softButton.label
            color: softButton.labelColor
            font.family: "Microsoft YaHei UI"
            font.pixelSize: 14
            font.weight: Font.DemiBold
        }
        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: softButton.clicked()
        }
    }

    component NavItem: Rectangle {
        id: nav
        property string iconText: "•"
        property string label: "Navigation"
        property bool active: false
        implicitHeight: 48
        radius: 14
        color: active ? Qt.rgba(accent.r, accent.g, accent.b, darkMode ? 0.14 : 0.11) : "transparent"
        border.color: active ? Qt.rgba(accent.r, accent.g, accent.b, 0.30) : "transparent"

        Row {
            anchors.fill: parent
            anchors.leftMargin: 16
            spacing: 13
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: nav.iconText
                color: nav.active ? accent : textMuted
                font.family: "Segoe UI Symbol"
                font.pixelSize: 18
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: nav.label
                color: nav.active ? textPrimary : textMuted
                font.family: "Microsoft YaHei UI"
                font.pixelSize: 14
                font.weight: nav.active ? Font.DemiBold : Font.Normal
            }
        }
    }

    component MetricBar: Item {
        id: metric
        property string label: "Metric"
        property string valueText: "0%"
        property real value: 0
        property color activeColor: accent
        implicitHeight: 61

        Text {
            anchors.left: parent.left
            anchors.top: parent.top
            text: metric.label
            color: textMuted
            font.family: "Microsoft YaHei UI"
            font.pixelSize: 12
        }
        Text {
            anchors.right: parent.right
            anchors.top: parent.top
            text: metric.valueText
            color: textPrimary
            font.family: "Microsoft YaHei UI"
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 8
            radius: 4
            color: track
            Rectangle {
                width: Math.max(8, parent.width * Math.max(0, Math.min(100, metric.value)) / 100)
                height: parent.height
                radius: parent.radius
                color: metric.activeColor
                Behavior on width { NumberAnimation { duration: 420; easing.type: Easing.OutCubic } }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: darkMode ? "#090D17" : "#EEF2F8" }
            GradientStop { position: 1.0; color: darkMode ? "#070A11" : "#F6F8FC" }
        }
    }

    Rectangle {
        width: 480
        height: 480
        radius: 240
        x: root.width * 0.48
        y: -310
        color: Qt.rgba(accent.r, accent.g, accent.b, darkMode ? 0.08 : 0.06)
        layer.enabled: true
        layer.effect: MultiEffect { blurEnabled: true; blur: 1.0; blurMax: 64 }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 226
            Layout.fillHeight: true
            color: darkMode ? "#0B101B" : "#F7F9FC"
            border.color: border
            Behavior on color { ColorAnimation { duration: 260 } }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 8

                Row {
                    Layout.fillWidth: true
                    Layout.bottomMargin: 25
                    spacing: 11
                    Rectangle {
                        width: 40; height: 40; radius: 13
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: accent }
                            GradientStop { position: 1.0; color: violet }
                        }
                        Text {
                            anchors.centerIn: parent
                            text: "M"
                            color: "#FFFFFF"
                            font.pixelSize: 19
                            font.weight: Font.Bold
                        }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 0
                        Text {
                            text: "MANAKA"
                            color: textPrimary
                            font.family: "Segoe UI"
                            font.pixelSize: 16
                            font.weight: Font.Bold
                            font.letterSpacing: 1.4
                        }
                        Text {
                            text: "DG-LAB CONTROL"
                            color: textMuted
                            font.family: "Segoe UI"
                            font.pixelSize: 9
                            font.letterSpacing: 1.1
                        }
                    }
                }

                Text {
                    Layout.leftMargin: 8
                    Layout.bottomMargin: 5
                    text: "控制中心"
                    color: textMuted
                    font.family: "Microsoft YaHei UI"
                    font.pixelSize: 10
                    font.letterSpacing: 1.4
                }
                NavItem { Layout.fillWidth: true; iconText: "◈"; label: "实时仪表盘"; active: true }
                NavItem { Layout.fillWidth: true; iconText: "⌁"; label: "设备连接" }
                NavItem { Layout.fillWidth: true; iconText: "⌁"; label: "波形工作台" }
                NavItem { Layout.fillWidth: true; iconText: "◎"; label: "事件记录" }

                Item { Layout.fillHeight: true }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 92
                    radius: 17
                    color: Qt.rgba(green.r, green.g, green.b, darkMode ? 0.08 : 0.09)
                    border.color: Qt.rgba(green.r, green.g, green.b, 0.24)
                    Column {
                        anchors.fill: parent
                        anchors.margins: 15
                        spacing: 6
                        Row {
                            spacing: 8
                            Rectangle { width: 8; height: 8; radius: 4; color: green; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: "游戏遥测在线"; color: textPrimary; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; font.weight: Font.DemiBold }
                        }
                        Text { text: "10 Hz · 本地 UDP"; color: textMuted; font.family: "Segoe UI"; font.pixelSize: 11 }
                        Text { text: "视觉原型 · 模拟数据"; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 28
                anchors.rightMargin: 28
                anchors.topMargin: 22
                anchors.bottomMargin: 24
                spacing: 17

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 58
                    Column {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: "实时控制台"
                            color: textPrimary
                            font.family: "Microsoft YaHei UI"
                            font.pixelSize: 23
                            font.weight: Font.Bold
                        }
                        Text {
                            text: "SecretFlasherManaka · 心率驱动会话"
                            color: textMuted
                            font.family: "Microsoft YaHei UI"
                            font.pixelSize: 12
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: 142
                        Layout.preferredHeight: 38
                        radius: 19
                        color: Qt.rgba(green.r, green.g, green.b, darkMode ? 0.10 : 0.09)
                        border.color: Qt.rgba(green.r, green.g, green.b, 0.28)
                        Row {
                            anchors.centerIn: parent
                            spacing: 8
                            Rectangle { width: 8; height: 8; radius: 4; color: green; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: "DG-LAB 已连接"; color: green; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold }
                        }
                    }

                    SoftButton {
                        Layout.leftMargin: 8
                        Layout.preferredWidth: 94
                        label: darkMode ? "☀  日间" : "☾  夜间"
                        onClicked: root.darkMode = !root.darkMode
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columns: 12
                    rows: 12
                    columnSpacing: 16
                    rowSpacing: 16

                    GlassCard {
                        Layout.columnSpan: 5
                        Layout.rowSpan: 7
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 24
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "游戏心率"; color: textPrimary; font.family: "Microsoft YaHei UI"; font.pixelSize: 16; font.weight: Font.DemiBold }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    width: 78; height: 28; radius: 14
                                    color: Qt.rgba(accent.r, accent.g, accent.b, 0.12)
                                    Text { anchors.centerIn: parent; text: "LIVE"; color: accent; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.4 }
                                }
                            }

                            Item {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Canvas {
                                    id: heartGauge
                                    width: Math.min(parent.width, parent.height) * 0.82
                                    height: width
                                    anchors.centerIn: parent
                                    antialiasing: true
                                    onPaint: {
                                        const ctx = getContext("2d")
                                        ctx.reset()
                                        const cx = width / 2
                                        const cy = height / 2
                                        const radius = width * 0.38
                                        const start = Math.PI * 0.72
                                        const sweep = Math.PI * 1.56
                                        ctx.lineCap = "round"
                                        ctx.lineWidth = width * 0.055
                                        ctx.strokeStyle = track
                                        ctx.beginPath(); ctx.arc(cx, cy, radius, start, start + sweep); ctx.stroke()
                                        const ratio = Math.max(0, Math.min(1, (heartRate - 60) / 120))
                                        const gradient = ctx.createLinearGradient(0, height, width, 0)
                                        gradient.addColorStop(0, violet)
                                        gradient.addColorStop(1, accent)
                                        ctx.strokeStyle = gradient
                                        ctx.beginPath(); ctx.arc(cx, cy, radius, start, start + sweep * ratio); ctx.stroke()
                                    }
                                    Connections {
                                        target: root
                                        function onHeartRateChanged() { heartGauge.requestPaint() }
                                        function onDarkModeChanged() { heartGauge.requestPaint() }
                                    }
                                }
                                Column {
                                    anchors.centerIn: parent
                                    spacing: -3
                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: Math.round(heartRate)
                                        color: textPrimary
                                        font.family: "Segoe UI Variable Display"
                                        font.pixelSize: 58
                                        font.weight: Font.Bold
                                    }
                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: "BPM"
                                        color: accent
                                        font.family: "Segoe UI"
                                        font.pixelSize: 11
                                        font.weight: Font.Bold
                                        font.letterSpacing: 2.4
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Rectangle { width: 8; height: 8; radius: 4; color: heartRate >= 100 ? accent : green }
                                Text { text: heartRate >= 100 ? "已进入输出范围" : "等待心率达到阈值"; color: textMuted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                                Item { Layout.fillWidth: true }
                                Text { text: "触发 100  ·  满幅 150"; color: textMuted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                            }
                        }
                    }

                    GlassCard {
                        Layout.columnSpan: 4
                        Layout.rowSpan: 7
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 22
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "输出通道"; color: textPrimary; font.family: "Microsoft YaHei UI"; font.pixelSize: 16; font.weight: Font.DemiBold }
                                Item { Layout.fillWidth: true }
                                Text { text: "安全上限  " + safetyCap; color: amber; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; font.weight: Font.DemiBold }
                            }
                            Text { text: outputPaused ? "手动暂停中，设备保持连接" : "跟随游戏心率实时映射"; color: outputPaused ? amber : textMuted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11 }
                            Item { Layout.preferredHeight: 4 }
                            MetricBar { Layout.fillWidth: true; label: "A · 心跳 Pulse"; valueText: outputA.toFixed(1) + " / " + safetyCap; value: outputA / safetyCap * 100; activeColor: accent }
                            MetricBar { Layout.fillWidth: true; label: "B · 动作反馈"; valueText: outputB.toFixed(1) + " / " + safetyCap; value: outputB / safetyCap * 100; activeColor: violet }
                            Item { Layout.fillHeight: true }
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 76
                                radius: 16
                                color: panelRaised
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    Column {
                                        Layout.fillWidth: true
                                        spacing: 4
                                        Text { text: "当前波形"; color: textMuted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                        Text { text: "官方 · 心跳节奏"; color: cyan; font.family: "Microsoft YaHei UI"; font.pixelSize: 13; font.weight: Font.DemiBold }
                                    }
                                    Text { text: "92 Hz"; color: textPrimary; font.family: "Segoe UI"; font.pixelSize: 13; font.weight: Font.DemiBold }
                                }
                            }
                        }
                    }

                    GlassCard {
                        Layout.columnSpan: 3
                        Layout.rowSpan: 7
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: outputPaused ? Qt.rgba(amber.r, amber.g, amber.b, darkMode ? 0.08 : 0.10) : panel
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 22
                            spacing: 12
                            Text { text: "会话控制"; color: textPrimary; font.family: "Microsoft YaHei UI"; font.pixelSize: 16; font.weight: Font.DemiBold }
                            Text { text: outputPaused ? "输出已经归零\n再次点击即可恢复" : "Socket 保持连接\n随时可以暂停输出"; color: textMuted; font.family: "Microsoft YaHei UI"; font.pixelSize: 11; lineHeight: 1.5 }
                            Item { Layout.fillHeight: true }
                            Rectangle {
                                Layout.alignment: Qt.AlignHCenter
                                width: 118
                                height: 118
                                radius: 59
                                color: pauseMouse.pressed ? Qt.darker(outputPaused ? green : amber, 1.08) : outputPaused ? green : amber
                                border.color: Qt.rgba(1, 1, 1, 0.35)
                                border.width: 1
                                scale: pauseMouse.containsMouse ? 1.04 : 1.0
                                Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
                                Behavior on color { ColorAnimation { duration: 220 } }
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 5
                                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: outputPaused ? "▶" : "Ⅱ"; color: "#11151C"; font.pixelSize: 31; font.weight: Font.Bold }
                                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: outputPaused ? "继续输出" : "暂停输出"; color: "#11151C"; font.family: "Microsoft YaHei UI"; font.pixelSize: 12; font.weight: Font.Bold }
                                }
                                MouseArea {
                                    id: pauseMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: outputPaused = !outputPaused
                                }
                            }
                            Item { Layout.fillHeight: true }
                            Text { Layout.alignment: Qt.AlignHCenter; text: outputPaused ? "PAUSED" : "OUTPUT ACTIVE"; color: outputPaused ? amber : green; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1.6 }
                        }
                    }

                    GlassCard {
                        Layout.columnSpan: 8
                        Layout.rowSpan: 5
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 21
                            spacing: 7
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "实时波形"; color: textPrimary; font.family: "Microsoft YaHei UI"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                Item { Layout.fillWidth: true }
                                Text { text: "A 通道 · 过去 8 秒"; color: textMuted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                            }
                            Canvas {
                                id: waveform
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                antialiasing: true
                                onPaint: {
                                    const ctx = getContext("2d")
                                    ctx.reset()
                                    const w = width
                                    const h = height
                                    ctx.lineWidth = 1
                                    ctx.strokeStyle = gridColor()
                                    for (let i = 1; i < 4; i++) {
                                        const y = h * i / 4
                                        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
                                    }
                                    const grd = ctx.createLinearGradient(0, 0, w, 0)
                                    grd.addColorStop(0, violet)
                                    grd.addColorStop(0.55, accent)
                                    grd.addColorStop(1, cyan)
                                    ctx.lineWidth = 3
                                    ctx.lineCap = "round"
                                    ctx.lineJoin = "round"
                                    ctx.strokeStyle = grd
                                    ctx.beginPath()
                                    for (let x = 0; x <= w; x += 3) {
                                        const t = x / w * Math.PI * 9 + wavePhase
                                        const pulse = Math.pow(Math.max(0, Math.sin(t)), 7)
                                        const detail = Math.sin(t * 2.15) * 0.10
                                        const y = h * (0.61 - pulse * 0.42 - detail)
                                        if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                                    }
                                    ctx.stroke()
                                }
                                function gridColor() { return darkMode ? "#243147" : "#D5DEEA" }
                                Connections {
                                    target: root
                                    function onWavePhaseChanged() { waveform.requestPaint() }
                                    function onDarkModeChanged() { waveform.requestPaint() }
                                    function onOutputPausedChanged() { waveform.requestPaint() }
                                }
                            }
                        }
                    }

                    GlassCard {
                        Layout.columnSpan: 4
                        Layout.rowSpan: 5
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 21
                            spacing: 9
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "场景状态"; color: textPrimary; font.family: "Microsoft YaHei UI"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                Item { Layout.fillWidth: true }
                                Text { text: "STAGE 02"; color: cyan; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1.2 }
                            }
                            MetricBar { Layout.fillWidth: true; label: "NPC 警觉度"; valueText: Math.round(alertLevel) + "%"; value: alertLevel; activeColor: amber }
                            MetricBar { Layout.fillWidth: true; label: "兴奋度"; valueText: Math.round(excitement) + "%"; value: excitement; activeColor: violet }
                            Item { Layout.fillHeight: true }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "当前动作"; color: textMuted; font.family: "Microsoft YaHei UI"; font.pixelSize: 10 }
                                Item { Layout.fillWidth: true }
                                Text { text: "Walking"; color: textPrimary; font.family: "Segoe UI"; font.pixelSize: 12; font.weight: Font.DemiBold }
                            }
                        }
                    }
                }
            }
        }
    }

    Timer {
        interval: 80
        running: true
        repeat: true
        onTriggered: {
            if (!outputPaused) {
                wavePhase += 0.13
                heartRate = 126 + Math.sin(wavePhase * 0.31) * 6 + Math.sin(wavePhase * 0.11) * 2
                rawOutputA = Math.min(safetyCap, 16 + Math.sin(wavePhase * 0.29) * 4)
                rawOutputB = Math.max(0, 7 + Math.sin(wavePhase * 0.17) * 3)
                alertLevel = 32 + Math.sin(wavePhase * 0.14) * 12
                excitement = 66 + Math.sin(wavePhase * 0.09) * 7
            }
        }
    }
}
