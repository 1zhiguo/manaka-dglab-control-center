import QtQuick
import QtQuick.Controls.Basic as C
C.DialogButtonBox {
    id:box
    property bool keepEditingOnCancel:false
    property string confirmText:""
    function refreshStandardLabels() {
        const labels = [
            [C.DialogButtonBox.Close,Theme.t("关闭","Close")],
            [C.DialogButtonBox.Ok,confirmText || Theme.t("确认","Confirm")],
            [C.DialogButtonBox.Yes,confirmText || Theme.t("确认","Confirm")],
            [C.DialogButtonBox.No,Theme.t("取消","Cancel")],
            [C.DialogButtonBox.Cancel,keepEditingOnCancel ? Theme.t("继续编辑","Keep editing") : Theme.t("取消","Cancel")],
            [C.DialogButtonBox.Discard,Theme.t("放弃修改","Discard changes")],
            [C.DialogButtonBox.Save,Theme.t("保存","Save")],
            [C.DialogButtonBox.Apply,Theme.t("应用","Apply")],
            [C.DialogButtonBox.Reset,Theme.t("重置","Reset")],
            [C.DialogButtonBox.RestoreDefaults,Theme.t("恢复默认","Restore defaults")],
            [C.DialogButtonBox.Help,Theme.t("帮助","Help")]
        ]
        for (const entry of labels) {
            const button=standardButton(entry[0])
            if (button) button.text=entry[1]
        }
    }
    // Qt assigns native standard-button text when it creates the delegates.
    // Apply application-language labels after creation; keep their native roles.
    onStandardButtonsChanged:Qt.callLater(refreshStandardLabels)
    onCountChanged:Qt.callLater(refreshStandardLabels)
    onKeepEditingOnCancelChanged:Qt.callLater(refreshStandardLabels)
    onConfirmTextChanged:Qt.callLater(refreshStandardLabels)
    Component.onCompleted:Qt.callLater(refreshStandardLabels)
    Connections { target:Theme; function onLanguageChanged() { Qt.callLater(box.refreshStandardLabels) } }
    padding:16; spacing:8
    background:Item {}
    delegate:Button {}
}
