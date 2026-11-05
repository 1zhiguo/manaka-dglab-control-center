import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: routes
    required property var theme
    readonly property bool bluetooth: backend.socketProtocol === "ble"
    implicitHeight: bluetooth ? 355 : 270
    signal workbenchRequested(int page)
    function tr(zh,en) { return backend.language === "en" ? en : zh }
    function selected(items, pending) {
        if (pending) for (let i=0;i<items.length;i++) if(items[i].address===pending) return i
        for(let i=0;i<items.length;i++) if(items[i].selected) return i
        return 0
    }
    RowLayout {
        anchors.fill: parent; spacing: 15
        Repeater {
            model: ["coyote", "ovc"]
            delegate: Rectangle {
                id: device
                required property string modelData
                readonly property bool vibration: modelData === "ovc"
                property string pendingAddress: ""
                readonly property bool connecting: routes.bluetooth && (vibration ? backend.bleOvcConnecting : backend.bleCoyoteConnecting)
                readonly property var choices: routes.bluetooth
                    ? (vibration ? backend.bleOvcDevices : backend.bleCoyoteDevices)
                    : (vibration ? backend.ovcDevices : backend.coyoteDevices)
                readonly property bool connected: !backend.demoMode && (vibration ? backend.ovcConnected : routes.bluetooth ? backend.bleConnected : backend.deviceConnected)
                Layout.fillWidth: true; Layout.fillHeight: true
                radius: 22; color: routes.theme.panel; border.color: routes.theme.border
                StatusGlow { active: device.vibration ? backend.ovcRunning : backend.coyoteRunning; tint: device.vibration ? routes.theme.cyan : routes.theme.accent }
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 22; spacing: 10
                    Label { text: device.vibration ? routes.tr("负鼠振动", "Opossum Vibration") : routes.tr("郊狼 Pulse", "Coyote Pulse"); color: device.vibration ? routes.theme.cyan : routes.theme.accent; font.pixelSize: 18; font.bold: true }
                    ThemedComboBox {
                        id: choice
                        objectName: device.vibration ? "ovcDeviceChoice" : "coyoteDeviceChoice"
                        theme:routes.theme
                        Layout.fillWidth: true
                        model: device.choices; textRole: "label"; currentIndex: routes.selected(model,device.pendingAddress)
                        onActivated: {
                            if(routes.bluetooth) device.pendingAddress=model[currentIndex].address
                            else backend.selectV4Device(device.modelData, model[currentIndex].clientId, model[currentIndex].slotId)
                        }
                    }
                    RowLayout {
                        visible:routes.bluetooth;Layout.fillWidth:true
                        WorkbenchButton {
                            theme:routes.theme;Layout.fillWidth:true;text:device.connecting?routes.tr("正在连接…","Connecting…"):routes.tr("连接","Connect")
                            enabled:!device.connecting && choice.currentIndex>=0 && !!choice.model[choice.currentIndex].address
                            onClicked:backend.connectBleRole(device.modelData,choice.model[choice.currentIndex].address)
                        }
                        WorkbenchButton {
                            theme:routes.theme;Layout.fillWidth:true;text:device.connecting?routes.tr("取消连接","Cancel"):routes.tr("断开","Disconnect")
                            enabled:device.connected||device.connecting
                            onClicked:backend.connectBleRole(device.modelData,"")
                        }
                    }
                    Label {
                        Layout.fillWidth: true; wrapMode: Text.Wrap; color: routes.theme.muted; font.pixelSize: 12
                        text: routes.bluetooth
                            ? (device.vibration ? backend.bleOvcStatus+"\n"+backend.bleOvcFeedback : backend.bleStatus+"\n"+backend.bleFeedback)
                            : device.vibration ? backend.ovcStatus : backend.coyoteChannelStatus
                    }
                    Label {
                        visible:routes.bluetooth && device.vibration;Layout.fillWidth:true;wrapMode:Text.Wrap
                        font.pixelSize:11;color:routes.theme.muted
                        text:routes.tr("直连协议不提供配件插入状态，请确认振动配件已插好。","Direct BLE does not report accessory insertion; check the vibrator plugs.")
                    }
                    Item { Layout.fillHeight: true }
                    RowLayout {
                        Layout.fillWidth: true
                        WorkbenchButton { theme:routes.theme;text: routes.tr("进入工作台", "Workbench"); Layout.fillWidth: true; onClicked: routes.workbenchRequested(device.vibration ? 4 : 3) }
                        WorkbenchButton {
                            theme:routes.theme;Layout.fillWidth: true
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
