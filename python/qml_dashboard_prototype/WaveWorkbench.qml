import QtQuick
import "components" as UI
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ColumnLayout {
    id:studio
    objectName:"waveWorkbench"
    required property var controller
    property string selectedAsset:"official_breath"
    property int assetRevision:0
    readonly property var asset: { assetRevision; return controller.waveAsset(selectedAsset) }
    property string originalAssetText:""
    readonly property bool dirty:assetDialog.opened && (assetName.text !== asset.name || assetCategory.text !== asset.category || rawFrames.text !== originalAssetText)
    property string message:""
    property bool failed:false
    signal closeRequested()
    signal closeCancelled()
    function t(zh,en) { return controller.language === "en" ? en : zh }
    function feedback(result,success) { failed=!result.ok; message=result.error || success; return result.ok }
    function requestClose() { if (dirty) discard.open(); else closeRequested() }
    readonly property bool dark: controller.theme !== "light"
    readonly property color surface: UI.Theme.surfaceRaised
    readonly property color line: UI.Theme.borderDecorative
    readonly property color ink: UI.Theme.textPrimary
    readonly property color secondary: UI.Theme.textSecondary
    readonly property color accent: UI.Theme.accent
    readonly property color danger: UI.Theme.danger
    function assetResult(result) {
        if (feedback(result,t("波形库已更新", "Library updated")) && result.key) selectedAsset=result.key
        assetRevision++
    }
    function openAssetEditor() {
        assetRevision++; originalAssetText=asset.framesText
        assetName.text=asset.name; assetCategory.text=asset.category; rawFrames.text=asset.framesText; assetError.text=""; assetDialog.open()
    }
    Connections { target:studio.controller; function onConfigChanged() { studio.assetRevision++ } }
    spacing:12
    RowLayout {
        Layout.fillWidth:true; Layout.fillHeight:true; spacing:18
        ColumnLayout {
            Layout.preferredWidth:300; Layout.fillHeight:true
            ThemedField { id:search; objectName:"waveSearch"; searchField:true; Layout.fillWidth:true; placeholderText:studio.t("搜索名称或分类", "Search name or category") }
            ThemedCheck { id:favorites; objectName:"waveFavorites"; text:studio.t("只看收藏", "Favorites only") }
            ListView {
                id:libraryList; objectName:"waveLibraryList"; Layout.fillWidth:true; Layout.fillHeight:true; clip:true; spacing:6
                model: studio.controller.waveAssets.filter(x => (!favorites.checked || x.favorite) && (x.name+" "+x.category).toLowerCase().indexOf(search.text.toLowerCase()) >= 0)
                delegate: ItemDelegate {
                    required property var modelData
                    width:ListView.view.width; height:64
                    highlighted:studio.selectedAsset === modelData.key
                    contentItem: Column {
                        Label { width:parent.width; text:(modelData.favorite ? "★ " : "")+modelData.name; color:studio.ink; elide:Text.ElideRight }
                        Label { width:parent.width; text:modelData.category+" · "+(modelData.durationMs/1000).toFixed(1)+" s"; color:studio.secondary; font.pixelSize:12; elide:Text.ElideRight }
                    }
                    background:Rectangle { radius:6; color:parent.highlighted ? studio.surface : "transparent"; border.color:parent.highlighted ? studio.accent : studio.line }
                    objectName:"waveAsset_"+modelData.key
                    onClicked:studio.selectedAsset=modelData.key
                }
                ScrollBar.vertical:ThinScroll {}
            }
            RowLayout {
                Layout.fillWidth:true
                ActionButton { text:studio.t("导入文件", "Import file"); primary:true; onClicked:importFile.open() }
                ActionButton { text:studio.t("新建", "New"); onClicked: { let r=studio.controller.saveWaveAsset("",studio.t("新波形", "New waveform"),"User","0A0A0A0A00000000"); studio.assetResult(r); if(r.ok) studio.openAssetEditor() } }
            }
        }
        ColumnLayout {
            Layout.fillWidth:true; Layout.fillHeight:true; spacing:14
            Label { Layout.fillWidth:true; text:studio.asset.name || ""; color:studio.ink; font.pixelSize:22; wrapMode:Text.Wrap }
            Caption { text:(studio.asset.source || "")+" · "+(studio.asset.frames || 0)+studio.t(" 帧 · ", " frames · ")+(Number(studio.asset.durationMs || 0)/1000).toFixed(1)+" s" }
            Rectangle {
                Layout.fillWidth:true; Layout.fillHeight:true; Layout.minimumHeight:130; color:studio.surface; radius:8; border.color:studio.line
                WavePreview {
                    id:wavePreview; objectName:"wavePreview"; anchors.fill:parent; anchors.margins:16
                    samples:studio.asset.amplitudes || []; durationMs:Number(studio.asset.durationMs || 0)
                    waveformKey:studio.selectedAsset; lineColor:studio.accent; gridColor:studio.secondary
                }
            }
            Caption { objectName:"wavePreviewStatus"; text:wavePreview.slowFactor>1.001 ? studio.t("自适应预览 · 3 个周期 · 慢放 ", "Adaptive preview · 3 cycles · ")+wavePreview.slowFactor.toFixed(1)+studio.t("×（不改变实际播放速度）", "× slower (actual playback unchanged)") : studio.t("自适应预览 · 5 秒窗口 · 实际速度", "Adaptive preview · 5-second window · Actual speed") }
            Flow {
                Layout.fillWidth:true; Layout.preferredHeight:childrenRect.height; spacing:8
                ActionButton { text:studio.asset.favorite ? studio.t("取消收藏", "Unfavorite") : studio.t("收藏", "Favorite"); onClicked:studio.assetResult(studio.controller.favoriteWaveAsset(studio.selectedAsset,!studio.asset.favorite)) }
                ActionButton { text:studio.t("复制", "Duplicate"); onClicked:studio.assetResult(studio.controller.duplicateWaveAsset(studio.selectedAsset)) }
                ActionButton { text:studio.t("编辑 / 重命名", "Edit / rename"); enabled:!studio.asset.readOnly; onClicked:studio.openAssetEditor() }
                ActionButton { text:studio.t("导出", "Export"); onClicked:exportFile.open() }
                ActionButton { destructive:true; text:studio.t("删除", "Delete"); enabled:!studio.asset.readOnly; onClicked:deleteConfirm.open() }
            }
            Caption { text:studio.t("支持 Dungeonlab .pulse、V3 HEX / 数字文本、JSON 波形集及16 点兼容 JSON。波形库操作立即保存。通道规则与检测绑定请前往「玩法设置」。", "Import Dungeonlab .pulse, V3 HEX / numeric text, JSON collections and compatible 16-point JSON. Library changes save immediately. Configure rules and bindings in Gameplay settings.") }
        }
    }
    Caption { text:studio.message; visible:text !== ""; color:studio.failed ? studio.danger : studio.secondary }
    FileDialog { id:importFile; title:studio.t("导入波形", "Import waveform"); nameFilters:["Waveforms (*.pulse *.txt *.json)","All files (*)"]; onAccepted:studio.assetResult(studio.controller.importWaveFile(selectedFile.toString())) }
    FileDialog { id:exportFile; title:studio.t("导出完整 V3 波形", "Export complete V3 waveform"); fileMode:FileDialog.SaveFile; defaultSuffix:"json"; nameFilters:["JSON (*.json)"]; onAccepted:studio.feedback(studio.controller.exportWaveAsset(studio.selectedAsset,selectedFile.toString()),studio.t("已导出", "Exported")) }
    UI.Dialog {
        id:assetDialog; objectName:"waveAssetEditor"; parent:Overlay.overlay; anchors.centerIn:parent
        width:Math.min(850,parent.width-64); height:Math.min(650,parent.height-64); modal:true; closePolicy:Popup.NoAutoClose
        padding:18; background:Rectangle { color:studio.surface; radius:10; border.color:studio.line }
        title:studio.t("编辑完整波形", "Edit complete waveform")
        contentItem:ColumnLayout {
            spacing:10
            RowLayout { Layout.fillWidth:true; ThemedField { id:assetName; Layout.fillWidth:true; placeholderText:studio.t("名称", "Name") }
 ThemedField { id:assetCategory; Layout.fillWidth:true; placeholderText:studio.t("分类", "Category") } }
            Caption { text:studio.t("每行一个 100 ms 帧：16 位 HEX，或 8 个十进制字节（前四个为频率码，后四个为振幅）。", "One 100 ms frame per line: 16 HEX characters or eight decimal bytes (four frequency codes, four amplitudes).") }
            ScrollView { Layout.fillWidth:true; Layout.fillHeight:true; clip:true; ScrollBar.vertical:ThinScroll {}
 TextArea { id:rawFrames; objectName:"waveRawFrames"; selectByMouse:true; wrapMode:TextEdit.NoWrap; font.family:"Consolas"; font.pixelSize:UI.Theme.bodySize; color:studio.ink; selectionColor:studio.accent; selectedTextColor:"#211A09"; background:Rectangle { color:studio.surface; border.color:studio.line; radius:6 } } }
            Caption { id:assetError; color:studio.danger }
        }
        footer:UI.DialogButtonBox {
            ActionButton { text:studio.t("取消", "Cancel"); DialogButtonBox.buttonRole:DialogButtonBox.RejectRole }
            ActionButton { text:studio.t("保存波形", "Save waveform"); primary:true; onClicked:{ let result=studio.controller.saveWaveAsset(studio.selectedAsset,assetName.text,assetCategory.text,rawFrames.text); if(result.ok){assetDialog.close();studio.assetResult(result)} else assetError.text=result.error } }
        }
    }
    UI.Dialog {
        id:deleteConfirm; objectName:"deleteWaveConfirm"; anchors.centerIn:parent; width:460; modal:true; title:studio.t("删除波形", "Delete waveform")
        palette.button:studio.surface; palette.buttonText:studio.ink
        contentItem:Label { color:studio.ink; text:studio.t("删除当前自定义波形？已保存规则引用的波形会阻止删除。", "Delete this custom waveform? Saved rule references prevent deletion."); wrapMode:Text.Wrap }
        confirmText:studio.t("删除", "Delete"); standardButtons:Dialog.Cancel | Dialog.Ok
        onAccepted: { let result=studio.controller.deleteWaveAsset(studio.selectedAsset); studio.feedback(result,studio.t("已删除", "Deleted")); if(result.ok) studio.selectedAsset="official_breath" }
    }
    UI.Dialog {
        id:discard; objectName:"discardWorkbenchChanges"; anchors.centerIn:parent; width:460; modal:true; title:studio.t("有未保存的修改", "Unsaved changes")
        palette.button:studio.surface; palette.buttonText:studio.ink
        contentItem:Label { color:studio.ink; text:studio.t("关闭将放弃工作台草稿。", "Closing discards the workbench draft."); wrapMode:Text.Wrap }
        unsavedChanges:true; standardButtons:Dialog.Cancel | Dialog.Discard
        onRejected:studio.closeCancelled()
        onDiscarded:{ assetDialog.close();studio.closeRequested() }
    }
    component ThemedField: UI.TextField { }
    component ThemedCheck: UI.CheckBox { }
    component ThinScroll: UI.ScrollBar { }
    component Caption: UI.Caption { }
    component ActionButton: UI.Button { }
}
