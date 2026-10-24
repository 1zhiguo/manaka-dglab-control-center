import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ComboBox {
    id: picker
    required property var theme
    function openChoices() { popup.open() }
    readonly property var choice:currentIndex>=0 && model && model[currentIndex]?model[currentIndex]:null
    implicitHeight:54;leftPadding:10;rightPadding:32;textRole:"name";hoverEnabled:true
    background:Rectangle {radius:12;color:picker.theme.panel2;border.color:picker.popup.visible?picker.theme.accent:picker.theme.border}
    contentItem:RowLayout {spacing:10
        VibrationPreview {Layout.preferredWidth:90;Layout.fillHeight:true;points:picker.choice?picker.choice.points:[];lineColor:picker.choice?picker.choice.color:picker.theme.muted;cycles:2;animate:picker.hovered&&!picker.popup.visible}
        Text {Layout.fillWidth:true;text:picker.choice?picker.choice.name:"—";color:picker.theme.fg;font.pixelSize:12;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter}
    }
    indicator:Text {x:picker.width-width-13;anchors.verticalCenter:parent.verticalCenter;text:"⌄";color:picker.theme.muted;font.pixelSize:18}
    delegate:ItemDelegate {
        id:option
        required property int index
        width:picker.popup.width-12;height:62
        HoverHandler{id:optionHover}
        contentItem:RowLayout {spacing:10
            VibrationPreview {Layout.preferredWidth:130;Layout.fillHeight:true;points:picker.model[index].points||[];lineColor:picker.model[index].color||picker.theme.cyan;cycles:2;animate:optionHover.hovered}
            Text {Layout.fillWidth:true;text:picker.textAt(index);color:picker.theme.fg;font.pixelSize:12;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter}
        }
        background:Rectangle {radius:9;color:option.highlighted?Qt.rgba(picker.theme.accent.r,picker.theme.accent.g,picker.theme.accent.b,.18):"transparent"}
    }
    popup:Popup {
        popupType:Popup.Item;x:Math.min(0,picker.width-width);y:picker.height+5
        width:Math.max(picker.width,360);implicitHeight:Math.min(contentItem.implicitHeight+12,390);padding:6
        background:Rectangle {radius:13;color:picker.theme.panel;border.color:picker.theme.border}
        contentItem:ListView {clip:true;implicitHeight:contentHeight;model:picker.popup.visible?picker.delegateModel:null;currentIndex:picker.highlightedIndex;ScrollIndicator.vertical:ScrollIndicator{}}
    }
}
