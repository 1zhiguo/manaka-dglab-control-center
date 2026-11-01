import QtQuick
import "components" as UI
import QtQuick.Controls

SpinBox {
    id: spin
    required property var theme
    implicitWidth: 130; implicitHeight: UI.Theme.controlHeight
    leftPadding: 34; rightPadding: 34
    font.family: "Microsoft YaHei UI"; font.pixelSize: UI.Theme.bodySize
    background: Rectangle { radius:UI.Theme.controlRadius; color:spin.theme.panel2; border.color:spin.activeFocus?spin.theme.accent:spin.theme.border }
    contentItem: Text { text:spin.textFromValue(spin.value,spin.locale);font:spin.font;color:spin.enabled?spin.theme.fg:spin.theme.muted;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter }
    up.indicator: Rectangle {x:spin.width-width;width:32;height:spin.height;radius:UI.Theme.controlRadius;color:spin.up.pressed?spin.theme.track:"transparent";Text{anchors.centerIn:parent;text:"+";color:spin.up.enabled?spin.theme.fg:spin.theme.muted;font.pixelSize:20}}
    down.indicator: Rectangle {width:32;height:spin.height;radius:UI.Theme.controlRadius;color:spin.down.pressed?spin.theme.track:"transparent";Text{anchors.centerIn:parent;text:"−";color:spin.down.enabled?spin.theme.fg:spin.theme.muted;font.pixelSize:20}}
}
