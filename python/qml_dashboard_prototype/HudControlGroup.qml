import QtQuick
import QtQuick.Layouts
import "components" as UI
RowLayout {
    id:group
    required property var theme
    signal settingsRequested()
    spacing:4
    UI.Switch { objectName:"hudToggle"; text:"HUD"; Layout.preferredWidth:94; checked:backend.gameHudEnabled; onClicked:backend.setGameHudEnabled(checked) }
    UI.Button { objectName:"hudSettingsButton"; Layout.preferredWidth:42; implicitWidth:42; text:"⚙"; leftPadding:8; rightPadding:8; Accessible.name:UI.Theme.t("HUD 设置","HUD Settings"); onClicked:group.settingsRequested() }
}
