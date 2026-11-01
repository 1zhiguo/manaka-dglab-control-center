import QtQuick
import "components" as UI
import QtQuick.Controls
import QtQuick.Layouts

UI.Dialog {
    id: dialog
    objectName: "hudSettingsDialog"
    popupType: Popup.Item
    required property var theme
    parent:Overlay.overlay;anchors.centerIn:parent;width:Math.min(850,parent.width-48);height:Math.min(740,parent.height-40);padding:24;modal:true
    property var draft: ({scale:100,opacity:35,anchor:"game_safe",x:30,y:96,show_pulse:true,show_ovc:true,show_a:true,show_b:true,show_numbers:true,show_status:true,show_waveforms:true})
    readonly property var anchorsList: [tr("游戏安全区域 · 底部靠左","Game Safe Area"),tr("左上","Top Left"),tr("顶部居中","Top Center"),tr("右上","Top Right"),tr("左下","Bottom Left"),tr("底部居中","Bottom Center"),tr("右下","Bottom Right"),tr("自定义位置","Custom Position")]
    readonly property var anchorKeys:["game_safe","top_left","top_center","top_right","bottom_left","bottom_center","bottom_right","custom"]
    function tr(zh,en){return backend.language==="en"?en:zh}
    function openSettings(){draft=JSON.parse(JSON.stringify(backend.hudSettings));open()}
    function change(key,value){let p=Object.assign({},draft);p[key]=value;draft=p}
    background:Rectangle{color:dialog.theme.panel;radius:22;border.color:dialog.theme.border}
    component Setting: RowLayout {
        required property string optionKey
        required property string label
        property int minimum:0
        property int maximum:100
        property int step:1
        Layout.fillWidth:true
        Label{text:label;color:dialog.theme.fg;Layout.preferredWidth:150;wrapMode:Text.Wrap}
        Slider{from:minimum;to:maximum;stepSize:step;value:dialog.draft[optionKey]||0;Layout.fillWidth:true;onMoved:dialog.change(optionKey,Math.round(value))}
        Label{text:(dialog.draft[optionKey]||0)+"%";color:dialog.theme.muted;Layout.preferredWidth:44;horizontalAlignment:Text.AlignRight}
    }
    component Option: UI.CheckBox {
        required property string optionKey
        checked:dialog.draft[optionKey]||false
        onClicked:dialog.change(optionKey,checked)
        Layout.fillWidth:true
    }
    contentItem:ColumnLayout {
        spacing:14
        RowLayout {Layout.fillWidth:true;Label{text:dialog.tr("HUD 显示设置","HUD Display Settings");color:dialog.theme.fg;font.pixelSize:22;font.bold:true;Layout.fillWidth:true} UI.Button {text:dialog.tr("关闭","Close");onClicked:dialog.close()}}
        ScrollView {
            Layout.fillWidth:true;Layout.fillHeight:true;clip:true;contentWidth:availableWidth
            ColumnLayout {
                width:parent.width;spacing:14
                Label{text:dialog.tr("仅显示预览，不发送设备输出","Display preview only — no device output");color:dialog.theme.muted}
                Label{Layout.fillWidth:true;text:backend.hudPluginHint;color:dialog.theme.amber;wrapMode:Text.Wrap;font.pixelSize:12}
                Rectangle {
                    Layout.fillWidth:true;Layout.preferredHeight:125;radius:14;color:"#24182E";border.color:dialog.theme.border;clip:true
                    ManakaHudPreview{anchors.centerIn:parent;width:Math.min(parent.width-20,696*(dialog.draft.scale||100)/100);height:Math.min(108,72*(dialog.draft.scale||100)/100);options:dialog.draft}
                }
                Setting{optionKey:"scale";label:dialog.tr("HUD 大小","HUD Size");minimum:60;maximum:180;step:10}
                Setting{optionKey:"opacity";label:dialog.tr("背景不透明度","Background Opacity");minimum:0;maximum:100;step:5}
                RowLayout{Layout.fillWidth:true;Label{text:dialog.tr("显示位置","Position");color:dialog.theme.fg;Layout.preferredWidth:150} ComboBox{Layout.fillWidth:true;model:dialog.anchorsList;currentIndex:dialog.anchorKeys.indexOf(dialog.draft.anchor);onActivated:dialog.change("anchor",dialog.anchorKeys[currentIndex])}}
                Setting{visible:dialog.draft.anchor==="custom";optionKey:"x";label:dialog.tr("水平位置","Horizontal")}
                Setting{visible:dialog.draft.anchor==="custom";optionKey:"y";label:dialog.tr("垂直位置","Vertical")}
                Label{text:dialog.tr("显示内容","Visible Content");color:dialog.theme.fg;font.bold:true}
                GridLayout{columns:2;Layout.fillWidth:true;columnSpacing:28
                    Option{optionKey:"show_pulse";text:dialog.tr("郊狼 Pulse","Coyote Pulse")}
                    Option{optionKey:"show_ovc";text:dialog.tr("负鼠振动","Opossum Vibration")}
                    Option{optionKey:"show_a";text:dialog.tr("A 通道","Channel A")}
                    Option{optionKey:"show_b";text:dialog.tr("B 通道","Channel B")}
                    Option{optionKey:"show_numbers";text:dialog.tr("数字强度","Intensity Numbers")}
                    Option{optionKey:"show_status";text:dialog.tr("连接与输出状态","Connection / Output Status")}
                    Option{optionKey:"show_waveforms";text:dialog.tr("郊狼波形","Pulse Waveforms")}
                }
                Label{Layout.fillWidth:true;wrapMode:Text.Wrap;text:dialog.tr("游戏原生画布适配窗口、全屏与分辨率变化。默认避开右下角游戏面板；五格按硬上限显示比例。数值不是硬件实测。隐藏 HUD 不会停止设备。","The native game canvas follows window, fullscreen and resolution changes. Default placement avoids the lower-right game UI. Bars are relative to the cap; values are not physical measurements. Hiding the HUD does not stop output.");color:dialog.theme.muted;font.pixelSize:12}
            }
        }
        RowLayout{Layout.fillWidth:true
            UI.Button {text:dialog.tr("恢复默认","Defaults");onClicked:dialog.draft={scale:100,opacity:35,anchor:"game_safe",x:30,y:96,show_pulse:true,show_ovc:true,show_a:true,show_b:true,show_numbers:true,show_status:true,show_waveforms:true}}
            Item{Layout.fillWidth:true}
            UI.Button {text:dialog.tr("取消","Cancel");onClicked:dialog.close()}
            UI.Button {text:dialog.tr("应用并保存","Apply & Save");enabled:(dialog.draft.show_pulse||dialog.draft.show_ovc)&&(dialog.draft.show_a||dialog.draft.show_b);onClicked:if(backend.saveHudSettings(dialog.draft))dialog.close()}
        }
    }
}
