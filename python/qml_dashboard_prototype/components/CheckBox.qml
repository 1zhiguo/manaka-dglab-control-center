import QtQuick
import QtQuick.Controls.Basic as C
C.CheckBox {
    id:control
    implicitHeight:Theme.controlHeight; implicitWidth:Math.max(40,contentItem.implicitWidth+leftPadding+rightPadding)
    spacing:10; padding:5; hoverEnabled:true; background:Item {}
    font.family:Theme.fontFamily; font.pixelSize:Theme.bodySize
    indicator:Rectangle {
        x:control.leftPadding; y:(control.height-height)/2; width:20; height:20; radius:4
        color:!control.enabled ? Theme.disabledFill : control.checked ? Theme.primaryFill : Theme.surfaceRaised
        border.color:!control.enabled ? Theme.borderDecorative : control.activeFocus || control.hovered ? Theme.accent : Theme.borderControl
        border.width:control.activeFocus ? 2 : 1
        Canvas {
            anchors.fill:parent; visible:control.checked
            property color ink:control.enabled ? Theme.onPrimary : Theme.textDisabled; onInkChanged:requestPaint()
            onPaint:{let c=getContext("2d"); c.clearRect(0,0,width,height); c.strokeStyle=ink; c.lineWidth=2; c.lineCap="round"; c.lineJoin="round"; c.beginPath(); c.moveTo(4,10); c.lineTo(8,14); c.lineTo(16,5); c.stroke()}
        }
    }
    contentItem:Text { text:control.text; color:control.enabled ? Theme.textPrimary : Theme.textDisabled; font:control.font; leftPadding:30; verticalAlignment:Text.AlignVCenter; elide:Text.ElideRight }
}
