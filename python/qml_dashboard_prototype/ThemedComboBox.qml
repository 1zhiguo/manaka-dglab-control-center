import QtQuick
import QtQuick.Controls

ComboBox {
    id: combo
    required property var theme
    implicitHeight: 42
    leftPadding: 14; rightPadding: 34
    font.pixelSize: 13
    function openChoices() { popup.open() }
    background: Rectangle {radius:12;color:combo.theme.panel2;border.color:combo.activeFocus?combo.theme.accent:combo.theme.border}
    contentItem: Text {text:combo.displayText;color:combo.theme.fg;font:combo.font;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight}
    indicator: Text {x:combo.width-width-14;anchors.verticalCenter:parent.verticalCenter;text:"⌄";font.pixelSize:18;color:combo.theme.muted}
    delegate: ItemDelegate {
        required property int index
        width:combo.width-12;height:40
        contentItem: Text {text:combo.textAt(index);color:combo.theme.fg;font:combo.font;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight}
        background: Rectangle {radius:8;color:highlighted||index===combo.currentIndex?Qt.rgba(combo.theme.accent.r,combo.theme.accent.g,combo.theme.accent.b,.18):"transparent"}
    }
    popup: Popup {
        y:combo.height+5;width:combo.width;padding:6;popupType:Popup.Item
        implicitHeight:Math.min(contentItem.implicitHeight+12,320)
        background:Rectangle {color:combo.theme.panel;radius:12;border.color:combo.theme.border}
        contentItem:ListView {clip:true;implicitHeight:contentHeight;model:combo.popup.visible?combo.delegateModel:null;currentIndex:combo.highlightedIndex;ScrollIndicator.vertical:ScrollIndicator{}}
    }
}
