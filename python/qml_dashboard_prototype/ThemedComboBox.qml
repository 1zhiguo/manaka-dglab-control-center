import QtQuick
import "components" as UI
UI.ComboBox {
    required property var theme
    function openChoices() { popup.open() }
}
