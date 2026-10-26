pragma Singleton
import QtQuick
QtObject {
    property bool dark:true
    property string language:"zh"
    readonly property string fontFamily:language === "en" ? "Segoe UI" : "Microsoft YaHei UI"
    readonly property int bodySize:14
    readonly property int captionSize:12
    readonly property int headingSize:18
    readonly property int titleSize:24
    readonly property int controlHeight:40
    readonly property int controlRadius:6
    readonly property int cardRadius:10
    readonly property int motionDuration:140
    readonly property color background:dark ? "#11100E" : "#F6F4EF"
    readonly property color surface:dark ? "#191713" : "#FFFEFB"
    readonly property color surfaceRaised:dark ? "#23211D" : "#F0EDE6"
    readonly property color textPrimary:dark ? "#F4F1E9" : "#25231F"
    readonly property color textSecondary:dark ? "#B9B3A6" : "#6F695E"
    readonly property color textDisabled:dark ? "#817C73" : "#938C80"
    readonly property color borderDecorative:dark ? "#37342E" : "#DDD8CD"
    readonly property color borderControl:dark ? "#777064" : "#837A6C"
    readonly property color accent:dark ? "#E7C36B" : "#916710"
    readonly property color primaryFill:"#E7C36B"
    readonly property color onPrimary:"#25231F"
    readonly property color selection:dark ? "#4D4025" : "#F3E4BB"
    readonly property color hover:dark ? "#302D26" : "#E9E4D9"
    readonly property color disabledFill:dark ? "#201E1A" : "#EEEAE3"
    readonly property color danger:dark ? "#F28C9F" : "#B32A43"
    readonly property color success:dark ? "#87D0A0" : "#226B3C"
    readonly property color info:dark ? "#80CFDD" : "#176A79"
    readonly property color warning:dark ? "#E8BF6A" : "#875F0B"
    function t(zh,en) { return language === "en" ? en : zh }
}
