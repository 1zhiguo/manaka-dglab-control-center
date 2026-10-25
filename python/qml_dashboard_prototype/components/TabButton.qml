import QtQuick
import QtQuick.Controls.Basic as C
C.TabButton {
    id:control; implicitHeight:40; font.family:Theme.fontFamily; font.pixelSize:Theme.bodySize
    contentItem:Text { text:control.text; font:control.font; color:control.checked ? Theme.textPrimary : Theme.textSecondary; horizontalAlignment:Text.AlignHCenter; verticalAlignment:Text.AlignVCenter; elide:Text.ElideRight }
    background:Rectangle { radius:6; color:control.checked ? Theme.selection : "transparent"; border.color:control.visualFocus ? Theme.accent : "transparent"; Rectangle { anchors.bottom:parent.bottom; anchors.horizontalCenter:parent.horizontalCenter; width:parent.width-24; height:2; color:control.checked ? Theme.accent : "transparent" } }
}
