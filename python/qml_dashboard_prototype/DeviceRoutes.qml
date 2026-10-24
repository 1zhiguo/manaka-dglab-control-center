import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: routes
    required property var theme
    implicitHeight: 270
    signal workbenchRequested(int page)
    function tr(zh,en) { return backend.language === "en" ? en : zh }
    function selected(items) { for(let i=0;i<items.length;i++) if(items[i].selected) return i; return 0 }
    RowLayout {
        anchors.fill: parent; spacing: 15
        Repeater {
            model: ["coyote", "ovc"]
            delegate: Rectangle {
                id: device
                required property string modelData
                readonly property bool vibration: modelData === "ovc"
                readonly property var choices: vibration ? backend.ovcDevices : backend.coyoteDevices
                Layout.fillWidth: true; Layout.fillHeight: true
                radius: 22; color: routes.theme.panel; border.color: routes.theme.border
                StatusGlow { active: device.vibration ? backend.ovcRunning : backend.coyoteRunning; tint: device.vibration ? routes.theme.cyan : routes.theme.accent }
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 22; spacing: 12
                    Label { text: device.vibration ? routes.tr("负鼠振动", "Opossum Vibration") : routes.tr("郊狼 Pulse", "Coyote Pulse"); color: device.vibration ? routes.theme.cyan : routes.theme.accent; font.pixelSize: 18; font.bold: true }
                    ThemedComboBox {
                        theme:routes.theme
                        Layout.fillWidth: true; visible: device.vibration || backend.socketProtocol === "v4"
                        model: device.choices; textRole: "label"; currentIndex: routes.selected(model)
                        onActivated: backend.selectV4Device(device.modelData, model[currentIndex].clientId, model[currentIndex].slotId)
                    }
                    Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: routes.theme.muted; font.pixelSize: 12
                        text: device.vibration ? backend.ovcStatus : backend.socketProtocol === "v4" ? backend.coyoteChannelStatus : backend.deviceStatus
                    }
                    Item { Layout.fillHeight: true }
                    RowLayout {
                        Layout.fillWidth: true
                        Button { text: routes.tr("进入工作台", "Workbench"); Layout.fillWidth: true; onClicked: routes.workbenchRequested(device.vibration ? 4 : 3) }
                        Button {
                            Layout.fillWidth: true
                            text: device.vibration ? (backend.ovcEnabled ? routes.tr("暂停负鼠", "Pause") : routes.tr("启用负鼠", "Enable")) : (backend.coyoteRunning ? routes.tr("暂停郊狼", "Pause") : routes.tr("启用郊狼", "Enable"))
                            opacity: !backend.demoMode && (device.vibration ? backend.ovcEnabled || backend.ovcConnected : backend.coyoteRunning || backend.deviceConnected) ? 1 : 0.6
                            onClicked: device.vibration ? backend.toggleOvcOutput() : backend.toggleOutput()
                        }
                    }
                }
            }
        }
    }
}
