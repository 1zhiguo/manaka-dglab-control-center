import QtQuick
import QtQuick.Controls.Basic as C
C.ScrollBar {
    id:control; policy:C.ScrollBar.AsNeeded; implicitWidth:8; implicitHeight:8; minimumSize:0.08
    contentItem:Rectangle { implicitWidth:6; implicitHeight:6; radius:3; color:control.pressed ? Theme.accent : Theme.textSecondary; opacity:control.size>=1 ? 0 : control.active || control.hovered ? 0.8 : 0.35 }
    background:Item {}
}
