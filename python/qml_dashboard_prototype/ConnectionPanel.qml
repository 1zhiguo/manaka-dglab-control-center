import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: panel
    required property var theme
    color: theme.panel; radius: 22; border.color: theme.border
    StatusGlow { active: backend.phoneConnected; tint: panel.theme.accent }
    function tr(zh,en) { return backend.language === "en" ? en : zh }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 22; spacing: 10
        Label { text: panel.tr("2 · 扫码连接", "2 · Scan & Connect"); font.pixelSize: 18; font.bold: true; color: panel.theme.fg }
        ThemedComboBox {
            theme:panel.theme
            objectName: "connectionProtocolChoice"
            Layout.fillWidth: true; implicitHeight: 40
            model: ["V3 · DG-LAB 3 App", "V4 · DG-LAB 4 App"]
            currentIndex: backend.socketProtocol === "v4" ? 1 : 0
            onActivated: backend.selectSocketProtocol(currentIndex === 1 ? "v4" : "v3")
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            ColumnLayout {
                Layout.fillWidth: true; spacing: 10
                Label { Layout.fillWidth: true; text: backend.socketProtocol === "v4" ? backend.v4Status : backend.deviceStatus; wrapMode: Text.Wrap; color: panel.theme.muted; font.pixelSize: 12 }
                Label { Layout.fillWidth: true; text: backend.socketProtocol === "v3" ? panel.tr("手机与电脑连接同一局域网，使用 DG-LAB App 扫描二维码。", "Use the same LAN and scan the QR code with DG-LAB App.") : panel.tr("郊狼 2.0 / 3.0 与负鼠均可通过 DG-LAB 4 App 的 V4 连接。扫码后还需在手机连接设备蓝牙，确认归零后手动启用。", "Coyote 2.0 / 3.0 and Opossum use V4 through DG-LAB 4 App. After scanning, connect hardware Bluetooth in the App, then enable output after confirmed zero."); wrapMode: Text.Wrap; color: panel.theme.muted; font.pixelSize: 11 }
                Label { Layout.fillWidth: true; text: backend.lanAddress; color: panel.theme.cyan; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
            }
            Rectangle {
                Layout.preferredWidth: 170; Layout.preferredHeight: 170; color: "white"; radius: 14
                Image { anchors.fill: parent; anchors.margins: 7; source: backend.qrSource; fillMode: Image.PreserveAspectFit; visible: source !== "" }
                Text { anchors.centerIn: parent; visible: backend.qrSource === ""; text: backend.demoMode ? panel.tr("演示模式\n二维码不可用", "Demo mode\nQR unavailable") : panel.tr("等待连接服务…", "Waiting for server…"); color: "#51435C"; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 12 }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            WorkbenchButton { theme:panel.theme; text: panel.tr("连接不上？", "Connection Help"); Layout.fillWidth: true; onClicked: panel.helpRequested() }
            WorkbenchButton { theme:panel.theme; visible: backend.socketProtocol === "v3"; Layout.fillWidth:true; text: !backend.deviceConnected ? panel.tr("启用输出", "Enable Output") : backend.outputPaused ? panel.tr("继续输出", "Resume Output") : panel.tr("暂停输出", "Pause Output"); onClicked: backend.toggleOutput() }
        }
    }
    signal helpRequested()
}
