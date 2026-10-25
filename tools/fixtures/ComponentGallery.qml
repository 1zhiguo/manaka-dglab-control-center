import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../../python/qml_dashboard_prototype/components" as UI
ApplicationWindow {
    id:root; width:1020; height:680; visible:true; color:UI.Theme.background
    property bool dark:false
    property string language:"en"
    property int acceptedCount:0
    property real enteredValue:0
    Binding { target:UI.Theme; property:"dark"; value:root.dark }
    Binding { target:UI.Theme; property:"language"; value:root.language }
    ColumnLayout {
        anchors.fill:parent; anchors.margins:24; spacing:16
        Label { text:UI.Theme.t("公共控件与交互状态","Shared controls and interaction states"); color:UI.Theme.textPrimary; font.pixelSize:24 }
        RowLayout {
            UI.Button { objectName:"primary"; text:UI.Theme.t("保存设置","Save settings"); primary:true }
            UI.Button { text:UI.Theme.t("次要操作","Secondary") }
            UI.Button { text:UI.Theme.t("删除","Delete"); destructive:true }
            UI.Button { text:UI.Theme.t("不可用","Disabled"); enabled:false }
        }
        RowLayout {
            UI.TextField { objectName:"search"; Layout.fillWidth:true; searchField:true; placeholderText:UI.Theme.t("搜索波形","Search waveforms") }
            UI.TextField { Layout.fillWidth:true; text:UI.Theme.t("错误值","Invalid value"); invalid:true }
            UI.TextField { Layout.fillWidth:true; text:UI.Theme.t("不可用","Disabled"); enabled:false }
        }
        RowLayout {
            UI.ComboBox { objectName:"choice"; Layout.fillWidth:true; model:["A","B","A + B"] }
            UI.ComboBox { Layout.fillWidth:true; model:[UI.Theme.t("不可用","Disabled")]; enabled:false }
            UI.CheckBox { objectName:"check"; text:UI.Theme.t("只看收藏","Favorites only") }
            UI.CheckBox { text:UI.Theme.t("已选中","Selected"); checked:true }
            UI.CheckBox { text:UI.Theme.t("不可用","Disabled"); enabled:false; checked:true }
        }
        RowLayout {
            UI.NumberField { objectName:"number"; label:UI.Theme.t("强度","Intensity"); maximum:200; onEdited:root.enteredValue=newValue }
            UI.NumberField { label:UI.Theme.t("错误","Error"); invalid:true; value:30 }
            UI.NumberField { label:UI.Theme.t("不可用","Disabled"); enabled:false; value:10 }
        }
        RowLayout {
            UI.Switch { objectName:"toggle"; text:UI.Theme.t("语气词","Reactions") }
            UI.Switch { text:UI.Theme.t("已开启","Enabled"); checked:true }
            UI.Switch { text:UI.Theme.t("不可用","Disabled"); enabled:false }
            Item { Layout.fillWidth:true }
            UI.Switch { objectName:"master"; large:true; checked:true }
        }
        UI.Caption { text:UI.Theme.t("未保存 · 已保存 · 重启游戏后生效","Unsaved · Saved · Restart the game to apply") }
        RowLayout {
            UI.Button { objectName:"dialogButton"; text:UI.Theme.t("打开确认框","Open confirmation"); onClicked:confirmation.open() }
            BusyIndicator { running:true; implicitWidth:32; implicitHeight:32 }
            UI.Caption { text:UI.Theme.t("加载中 / 空列表 / 校验失败","Loading / Empty list / Validation error") }
        }
        Item { Layout.fillHeight:true }
    }
    UI.Dialog {
        id:confirmation; objectName:"confirmation"; anchors.centerIn:parent; width:460
        title:UI.Theme.t("确认保存设置","Confirm settings")
        standardButtons:Dialog.Ok | Dialog.Cancel
        UI.Caption { width:parent.width; text:UI.Theme.t("控件状态检查，不会连接设备。","Component checks do not connect to a device.") }
        onAccepted:root.acceptedCount++
    }
}
