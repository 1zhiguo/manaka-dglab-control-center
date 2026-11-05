import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: panel
    required property var theme
    color: theme.panel; radius: 22; border.color: theme.border
    StatusGlow { active: backend.socketProtocol==="ble"?(backend.bleConnected||backend.ovcConnected):backend.phoneConnected; tint: panel.theme.accent }
    function tr(zh,en) { return backend.language === "en" ? en : zh }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 22; spacing: 10
        Label { text: panel.tr("2 · 连接方式", "2 · Connection"); font.pixelSize: 18; font.bold: true; color: panel.theme.fg }
        ThemedComboBox {
            theme:panel.theme
            objectName: "connectionProtocolChoice"
            Layout.fillWidth: true; implicitHeight: 40
            model: ["V3 · DG-LAB 3 App", "V4 · DG-LAB 4 App", panel.tr("蓝牙直连 · 郊狼 + 负鼠", "Direct BLE · Coyote + Opossum")]
            currentIndex: backend.socketProtocol === "ble" ? 2 : backend.socketProtocol === "v4" ? 1 : 0
            onActivated: backend.selectSocketProtocol(currentIndex === 2 ? "ble" : currentIndex === 1 ? "v4" : "v3")
        }
        RowLayout {
            visible:backend.socketProtocol!=="ble"
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
        ColumnLayout {
            visible:backend.socketProtocol==="ble";Layout.fillWidth:true;Layout.fillHeight:true;spacing:8
            Label {
                Layout.fillWidth:true;wrapMode:Text.Wrap;color:panel.theme.fg;font.pixelSize:12
                text:panel.tr("郊狼：拨动模式按钮，切换到蓝色蓝牙模式。","Coyote: move the mode switch to blue Bluetooth mode.")
            }
            Label {
                Layout.fillWidth:true;wrapMode:Text.Wrap;color:panel.theme.muted;font.pixelSize:11
                text:panel.tr("先在手机 App 中断开设备。扫描后自动连接郊狼与负鼠，输出仍需手动启用。","Disconnect devices from the phone App. Scanning connects Coyote and Opossum automatically; enable output manually.")
            }
            WorkbenchButton {
                theme:panel.theme;Layout.fillWidth:true
                text:backend.bleScanning?panel.tr("取消检测","Cancel Scan"):backend.bleBusy?panel.tr("正在连接…","Connecting…"):panel.tr("检测并连接设备","Scan & Connect")
                enabled:!backend.bleBusy||backend.bleScanning
                onClicked:backend.bleScanning?backend.cancelBleScan():backend.scanBleDevices()
            }
            BleActivity { theme:panel.theme }
            Label {
                Layout.fillWidth:true;wrapMode:Text.Wrap;color:panel.theme.muted;font.pixelSize:11
                text:panel.tr("负鼠搜不到？连续按 5 次开机键，蓝牙图标变黄后重新检测。","Cannot find Opossum? Press its power button five times; scan again when the Bluetooth icon turns yellow.")
            }
            Item {Layout.fillHeight:true}
            Label {
                Layout.fillWidth:true;wrapMode:Text.Wrap;color:panel.theme.amber;font.pixelSize:11
                text:panel.tr("实验性功能：实体双设备输出待实测。2.0 使用 100ms 波形采样。","Experimental: physical dual-device output is untested. Coyote 2 uses 100ms waveform sampling.")
            }
        }
        RowLayout {
            visible:backend.socketProtocol!=="ble"
            Layout.fillWidth: true
            WorkbenchButton { theme:panel.theme; text: panel.tr("端口设置", "Ports"); onClicked: { portV3.value=backend.socketPortV3; portV4.value=backend.socketPortV4; portDialog.open() } }
            WorkbenchButton { theme:panel.theme; text: panel.tr("连接不上？", "Connection Help"); Layout.fillWidth: true; onClicked: panel.helpRequested() }
            WorkbenchButton { theme:panel.theme; visible: backend.socketProtocol === "v3"; Layout.fillWidth:true; text: !backend.deviceConnected ? panel.tr("启用输出", "Enable Output") : backend.outputPaused ? panel.tr("继续输出", "Resume Output") : panel.tr("暂停输出", "Pause Output"); onClicked: backend.toggleOutput() }
        }
    }
    Dialog {
        id: portDialog; objectName:"socketPortsDialog"; parent:Overlay.overlay
        anchors.centerIn:parent; width:Math.min(500,parent.width-40)
        padding:24; modal:true; popupType:Popup.Item
        background:Rectangle {radius:18;color:panel.theme.panel;border.color:panel.theme.border}
        contentItem:ColumnLayout {
            spacing:14
            Label {text:panel.tr("Socket 端口设置","Socket Ports");color:panel.theme.fg;font.pixelSize:20;font.bold:true}
            Label {Layout.fillWidth:true;wrapMode:Text.Wrap;color:panel.theme.muted;text:panel.tr("保存后连接会断开并生成新二维码，请重新扫码并手动启用设备。V3 / V4 端口不可相同。","Saving disconnects devices and creates a new QR code. Scan again and enable manually. Use different ports for V3 and V4.")}
            RowLayout {Label{text:"V3";color:panel.theme.fg} WorkbenchSpinBox{id:portV3;objectName:"socketPortV3Input";theme:panel.theme;from:1;to:65535;editable:true;textFromValue:function(v,l){return String(v)};valueFromText:function(t,l){return Number(t)};Layout.fillWidth:true}}
            RowLayout {Label{text:"V4";color:panel.theme.fg} WorkbenchSpinBox{id:portV4;objectName:"socketPortV4Input";theme:panel.theme;from:1;to:65535;editable:true;textFromValue:function(v,l){return String(v)};valueFromText:function(t,l){return Number(t)};Layout.fillWidth:true}}
            RowLayout {
                WorkbenchButton{theme:panel.theme;text:panel.tr("恢复默认","Defaults");onClicked:{portV3.value=9999;portV4.value=9998}}
                Item{Layout.fillWidth:true}
                WorkbenchButton{theme:panel.theme;text:panel.tr("取消","Cancel");onClicked:portDialog.close()}
                WorkbenchButton{theme:panel.theme;text:panel.tr("保存并重新连接","Save & Reconnect");onClicked:if(backend.saveSocketPorts(portV3.value,portV4.value))portDialog.close()}
            }
        }
    }
    signal helpRequested()
}
