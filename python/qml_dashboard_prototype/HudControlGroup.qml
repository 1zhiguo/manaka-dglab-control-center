import QtQuick
import QtQuick.Controls

Rectangle {
    id: group
    required property var theme
    signal settingsRequested()
    implicitWidth:146;implicitHeight:40;radius:17
    color:backend.gameHudEnabled?Qt.rgba(theme.cyan.r,theme.cyan.g,theme.cyan.b,.13):theme.panel2
    border.color:backend.gameHudEnabled?theme.cyan:theme.border
    Behavior on color {ColorAnimation{duration:180}}
    Behavior on border.color {ColorAnimation{duration:180}}
    Text {x:13;anchors.verticalCenter:parent.verticalCenter;text:"HUD";color:backend.gameHudEnabled?group.theme.cyan:group.theme.muted;font.pixelSize:11;font.bold:true}
    Rectangle {x:55;anchors.verticalCenter:parent.verticalCenter;width:34;height:19;radius:10;color:backend.gameHudEnabled?group.theme.cyan:group.theme.track
        Rectangle {width:13;height:13;radius:7;y:3;x:backend.gameHudEnabled?18:3;color:backend.gameHudEnabled?"#14232D":group.theme.fg;Behavior on x {NumberAnimation{duration:180;easing.type:Easing.OutCubic}}}
    }
    MouseArea {width:101;height:parent.height;cursorShape:Qt.PointingHandCursor;onClicked:backend.setGameHudEnabled(!backend.gameHudEnabled)}
    Rectangle {x:102;y:8;width:1;height:parent.height-16;color:group.theme.border}
    Text {x:116;anchors.verticalCenter:parent.verticalCenter;text:"⚙";color:group.theme.fg;font.pixelSize:17}
    MouseArea {x:104;width:42;height:parent.height;cursorShape:Qt.PointingHandCursor;hoverEnabled:true;onClicked:group.settingsRequested();ToolTip.visible:containsMouse;ToolTip.text:backend.language==="en"?"HUD Settings":"HUD 设置"}
}
