import QtQuick
import QtQuick.Controls

Button {
    id: button
    required property var theme
    property color fillColor: highlighted ? theme.accent : theme.panel2
    property color labelColor: highlighted ? (theme.darkMode ? "#11151C" : "#FFFFFF") : theme.fg
    implicitWidth: Math.max(118, label.implicitWidth + 28)
    implicitHeight: 42
    hoverEnabled: true
    opacity: enabled ? 1 : 0.48
    font.family: "Microsoft YaHei UI"
    font.pixelSize: 13
    font.weight: Font.DemiBold
    background: Rectangle {
        radius: 13
        color: button.down ? Qt.darker(button.fillColor, 1.10) : button.hovered ? Qt.lighter(button.fillColor, 1.06) : button.fillColor
        border.color: button.activeFocus ? button.theme.accent : Qt.rgba(button.labelColor.r,button.labelColor.g,button.labelColor.b,0.18)
        Behavior on color { ColorAnimation { duration: 120 } }
    }
    contentItem: Text {
        id: label
        text: button.text; color: button.labelColor; font: button.font
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
}
