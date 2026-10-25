import QtQuick
import QtQuick.Controls.Basic as C
C.Switch {
    id:control
    property bool large:false
    property string onLabel:Theme.t("开启","ON")
    property string offLabel:Theme.t("关闭","OFF")
    implicitWidth:large ? 166 : text ? contentItem.implicitWidth : 52
    implicitHeight:large ? 58 : Theme.controlHeight
    padding:0; spacing:10; hoverEnabled:true
    Accessible.name:text || Theme.t("开关","Toggle")
    font.family:Theme.fontFamily; font.pixelSize:Theme.bodySize; font.weight:large ? Font.DemiBold : Font.Normal
    indicator:Rectangle {
        id:track; objectName:control.objectName+"Track"
        width:control.large ? control.width : 46; height:control.large ? control.height : 26
        x:0; y:(control.height-height)/2; radius:control.large ? Theme.cardRadius : 13
        color:!control.enabled ? Theme.disabledFill : control.checked ? Theme.primaryFill : Theme.surfaceRaised
        border.color:control.visualFocus ? Theme.accent : control.enabled ? Theme.borderControl : Theme.borderDecorative; border.width:control.visualFocus ? 2 : 1
        Text {
            objectName:control.objectName+"Label"; visible:control.large
            x:control.checked ? 6 : 58; width:track.width-64; height:track.height
            text:control.checked ? control.onLabel : control.offLabel
            font:control.font
            color:!control.enabled ? Theme.textDisabled : control.checked ? Theme.onPrimary : Theme.textPrimary
            horizontalAlignment:Text.AlignHCenter; verticalAlignment:Text.AlignVCenter
        }
        Rectangle {
            objectName:control.objectName+"Knob"
            width:control.large ? 46 : 18; height:width; radius:control.large ? Theme.controlRadius : 9
            y:(track.height-height)/2; x:control.checked ? track.width-width-y : y
            color:control.enabled ? control.checked ? Theme.onPrimary : Theme.textPrimary : Theme.textDisabled
            Behavior on x { NumberAnimation { duration:Theme.motionDuration; easing.type:Easing.OutCubic } }
        }
    }
    contentItem:Text { visible:!control.large && control.text.length>0; text:control.text; font:control.font; leftPadding:control.large ? 0 : 56; color:control.enabled ? Theme.textPrimary : Theme.textDisabled; verticalAlignment:Text.AlignVCenter }
}
