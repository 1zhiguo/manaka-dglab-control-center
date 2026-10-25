import QtQuick
import QtQuick.Controls.Basic as C
C.TextField {
    id:control
    property bool searchField:false
    property bool invalid:false
    implicitHeight:Theme.controlHeight; implicitWidth:220
    font.family:Theme.fontFamily; font.pixelSize:Theme.bodySize
    color:enabled ? Theme.textPrimary : Theme.textDisabled; placeholderTextColor:Theme.textSecondary
    verticalAlignment:TextInput.AlignVCenter; selectByMouse:true; clip:true
    selectionColor:Theme.selection; selectedTextColor:Theme.textPrimary
    leftPadding:searchField ? 36 : 12; rightPadding:searchField ? 38 : 12; topPadding:8; bottomPadding:8
    background:Rectangle { radius:Theme.controlRadius; color:control.enabled ? Theme.surfaceRaised : Theme.disabledFill; border.color:control.invalid ? Theme.danger : control.activeFocus ? Theme.accent : Theme.borderControl; border.width:control.activeFocus ? 2 : 1 }
    Canvas {
        visible:control.searchField; x:12; y:(parent.height-height)/2; width:16; height:16
        property color ink:Theme.textSecondary; onInkChanged:requestPaint()
        onPaint:{ let c=getContext("2d"); c.clearRect(0,0,width,height); c.strokeStyle=ink; c.lineWidth=1.5; c.beginPath(); c.arc(6,6,4,0,2*Math.PI); c.moveTo(9,9); c.lineTo(14,14); c.stroke() }
    }
    C.ToolButton {
        objectName:control.objectName+"Clear"; visible:control.searchField && control.text.length>0
        x:control.width-width-2; y:2; width:34; height:control.height-4
        text:"×"; Accessible.name:Theme.t("清空搜索","Clear search")
        onClicked:{control.clear();control.forceActiveFocus()}
        contentItem:Text { text:parent.text; font.pixelSize:20; color:Theme.textSecondary; horizontalAlignment:Text.AlignHCenter; verticalAlignment:Text.AlignVCenter }
        background:Rectangle { radius:4; color:parent.hovered ? Theme.hover : "transparent"; border.color:parent.visualFocus ? Theme.accent : "transparent" }
    }
}
