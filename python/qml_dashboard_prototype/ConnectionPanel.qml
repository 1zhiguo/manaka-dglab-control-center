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
            model: ["V3 · DG-LAB 3", "V4 · DG-LAB 4"]
            currentIndex: backend.socketProtocol === "v4" ? 1 : 0
            onActivated: backend.selectSocketProtocol(currentIndex === 1 ? "v4" : "v3")
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            ColumnLayout {
                Layout.fillWidth: true; spacing: 10
                Label { Layout.fillWidth: true; text: backend.socketProtocol === "v4" ? backend.v4Status : backend.deviceStatus; wrapMode: Text.Wrap; color: panel.theme.muted; font.pixelSize: 12 }
                Label { Layout.fillWidth: true; text: backend.socketProtocol === "v3" ? panel.tr("手机与电脑连接同一局域网，使用 DG-LAB App 扫描二维码。", "Use the same LAN and scan the QR code with DG-LAB App.") : panel.tr("手机与电脑连接同一局域网。V4 自动选择已发现设备，硬件就绪后仍需手动启用输出。", "Use the same LAN. V4 auto-selects discovered devices; enable output manually after hardware is ready."); wrapMode: Text.Wrap; color: panel.theme.muted; font.pixelSize: 11 }
                Label { Layout.fillWidth: true; text: backend.lanAddress; color: panel.theme.cyan; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
            }
            Rectangle {
                Layout.preferredWidth: 170; Layout.preferredHeight: 170; color: "white"; radius: 14
                Image { objectName:"connectionQr"; anchors.fill: parent; anchors.margins: 7; source: backend.qrSource; fillMode: Image.PreserveAspectFit; visible: source !== "" }
                Text { anchors.centerIn: parent; visible: backend.qrSource === ""; text: backend.demoMode ? panel.tr("演示模式\n二维码不可用", "Demo mode\nQR unavailable") : backend.connectionHint; color: "#51435C"; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 12 }
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
