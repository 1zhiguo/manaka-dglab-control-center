import QtQuick
import QtQuick.Controls.Basic as C
C.Button {
    id:control
    property alias label:control.text
    property string iconText:""
    property bool primary:false
    property bool destructive:false
    property color fillColor:primary ? Theme.primaryFill : Theme.surfaceRaised
    property color labelColor:primary ? Theme.onPrimary : destructive ? Theme.danger : Theme.textPrimary
    implicitWidth:Math.max(84,labelItem.implicitWidth+32)
    implicitHeight:Theme.controlHeight
    leftPadding:16; rightPadding:16; topPadding:8; bottomPadding:8
    font.family:Theme.fontFamily; font.pixelSize:Theme.bodySize
    font.weight:primary ? Font.DemiBold : Font.Normal
    hoverEnabled:true
    Accessible.name:text
    contentItem:Text {
        id:labelItem; text:(control.iconText ? control.iconText+"  " : "")+control.text
        font:control.font; color:control.enabled ? control.labelColor : Theme.textDisabled
        horizontalAlignment:Text.AlignHCenter; verticalAlignment:Text.AlignVCenter; elide:Text.ElideRight
    }
    background:Rectangle {
        radius:Theme.controlRadius
        color:!control.enabled ? Theme.disabledFill : control.down ? Qt.darker(control.fillColor,1.12) : control.hovered ? Qt.lighter(control.fillColor,1.07) : control.fillColor
        border.color:control.visualFocus ? Theme.accent : control.destructive ? Theme.danger : Theme.borderControl
        border.width:control.visualFocus ? 2 : 1
    }
    C.ToolTip.visible:hovered && labelItem.truncated
    C.ToolTip.text:text; C.ToolTip.delay:600
}
