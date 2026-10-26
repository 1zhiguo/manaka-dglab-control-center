import QtQuick

Item {
    id: glow
    property bool active: false
    property color tint: "#E97AC4"
    property real cornerRadius: 22
    anchors.fill: parent
    visible: active
    property real shimmer: 0.65
    SequentialAnimation on shimmer {
        running: glow.active && glow.visible
        loops: Animation.Infinite
        NumberAnimation { to: 1; duration: 1400; easing.type: Easing.InOutSine }
        NumberAnimation { to: 0.65; duration: 1400; easing.type: Easing.InOutSine }
    }
    Repeater {
        model: 4
        Rectangle {
            required property int index
            anchors.fill: parent; anchors.margins: 1 + index * 2
            radius: Math.max(0, glow.cornerRadius - index * 2)
            color: "transparent"
            border.width: index === 0 ? 2 : 1
            border.color: Qt.rgba(glow.tint.r, glow.tint.g, glow.tint.b, (index === 0 ? 0.9 : 0.26 / index) * glow.shimmer)
        }
    }
}
