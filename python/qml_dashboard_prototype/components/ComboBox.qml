import QtQuick
import QtQuick.Controls.Basic as C
C.ComboBox {
    id:control
    implicitWidth:220; implicitHeight:Theme.controlHeight
    font.family:Theme.fontFamily; font.pixelSize:Theme.bodySize
    leftPadding:12; rightPadding:32; hoverEnabled:true
    background:Rectangle { radius:Theme.controlRadius; color:control.enabled ? Theme.surfaceRaised : Theme.disabledFill; border.color:control.activeFocus ? Theme.accent : Theme.borderControl; border.width:control.activeFocus ? 2 : 1 }
    contentItem:Text { text:control.displayText; font:control.font; color:control.enabled ? Theme.textPrimary : Theme.textDisabled; verticalAlignment:Text.AlignVCenter; elide:Text.ElideRight }
    indicator:Canvas {
        x:control.width-24; y:(control.height-height)/2; width:12; height:8
        property color ink:Theme.textSecondary; onInkChanged:requestPaint()
        onPaint:{let c=getContext("2d");c.clearRect(0,0,width,height);c.strokeStyle=ink;c.lineWidth=1.5;c.beginPath();c.moveTo(1,1);c.lineTo(6,6);c.lineTo(11,1);c.stroke()}
    }
    delegate:C.ItemDelegate {
        required property int index
        width:control.width-8; implicitHeight:40
        text:control.textAt(index); highlighted:control.highlightedIndex===index
        contentItem:Text { text:parent.text; font:control.font; color:Theme.textPrimary; elide:Text.ElideRight; verticalAlignment:Text.AlignVCenter }
        background:Rectangle { radius:4; color:parent.highlighted ? Theme.selection : Theme.surface }
    }
    popup:C.Popup {
        y:control.height+4; width:control.width; padding:4; implicitHeight:Math.min(320,contentItem.implicitHeight+8)
        background:Rectangle { color:Theme.surface; border.color:Theme.borderControl; radius:Theme.controlRadius }
        contentItem:ListView { clip:true; implicitHeight:contentHeight; model:control.popup.visible ? control.delegateModel : null; currentIndex:control.highlightedIndex; C.ScrollBar.vertical:ScrollBar {} }
    }
    C.ToolTip.visible:hovered; C.ToolTip.text:displayText; C.ToolTip.delay:700
}
