import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: editor
    objectName: "ovcWaveEditor"
    popupType: Popup.Item
    required property var theme
    parent: Overlay.overlay; anchors.centerIn: parent
    width: Math.min(1000,parent.width-60); height: Math.min(650,parent.height-60); padding: 24; modal: true
    property var points: [0,10,20,40,60,80,95,100,95,80,60,40,20,10,0,0]
    property var history: []
    property int historyIndex: 0
    property string waveKey: ""
    signal saved(string key)
    function tr(zh,en) { return backend.language === "en" ? en : zh }
    function openEditor(key) {
        waveKey=key || "";name.text=""
        let wave=backend.ovcWaveforms.find(w=>w.key===key)
        if(wave){points=wave.points.slice();name.text=key.indexOf("ovc_custom:")===0 ? wave.name : ""}
        if(waveKey.indexOf("ovc_custom:")!==0)waveKey=""
        history=[points.slice()];historyIndex=0;open()
    }
    function commit(p) { points=p.slice();history=history.slice(0,historyIndex+1).concat([points.slice()]);historyIndex=history.length-1 }
    function paint(mouse) { let p=points.slice(),i=Math.round(Math.max(0,Math.min(1,mouse.x/draw.width))*15);p[i]=Math.round(100*(1-Math.max(0,Math.min(1,mouse.y/draw.height))));points=p }
    background: Rectangle { color: editor.theme.panel; radius: 22; border.color: editor.theme.border }
    contentItem: ColumnLayout {
        spacing: 16
        RowLayout {
            Layout.fillWidth: true
            Label { text: editor.tr("自定义振动波形", "Custom Vibration Envelope"); font.pixelSize: 22; font.bold: true; color: editor.theme.fg; Layout.fillWidth: true }
            WorkbenchButton {theme:editor.theme; text: editor.tr("关闭", "Close"); onClicked: editor.close() }
        }
        Label { text: editor.tr("拖动 16 个控制点。只编辑振动包络，不改变郊狼波形或输出强度。", "Draw 16 control points. This edits a vibration envelope, not electrical frequency or strength."); wrapMode: Text.Wrap; Layout.fillWidth: true; color: editor.theme.muted }
        TextField { id: name; Layout.fillWidth: true; placeholderText: editor.tr("留空自动命名：自定义振动 1、2、3…", "Leave blank for automatic numbering") }
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true; radius: 14; color: editor.theme.bg; border.color: editor.theme.cyan
            Item { id: draw; anchors.fill: parent; anchors.margins: 18
                VibrationPreview { anchors.fill: parent; points: editor.points; lineColor: editor.theme.cyan }
                Repeater { model: 16
                    Rectangle { required property int index; width: 9; height: 9; radius: 5; color: editor.theme.fg; x:index*(draw.width-4)/15-2; y:(100-editor.points[index])*(draw.height-4)/100-2 }
                }
                MouseArea { anchors.fill: parent; cursorShape: Qt.CrossCursor; onPressed: mouse=>editor.paint(mouse); onPositionChanged: mouse=>{if(pressed)editor.paint(mouse)}; onReleased: editor.commit(editor.points) }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            WorkbenchButton {theme:editor.theme; text: editor.tr("撤销", "Undo"); enabled: editor.historyIndex>0; onClicked: {editor.historyIndex--;editor.points=editor.history[editor.historyIndex].slice()} }
            WorkbenchButton {theme:editor.theme; text: editor.tr("重做", "Redo"); enabled: editor.historyIndex<editor.history.length-1; onClicked:{editor.historyIndex++;editor.points=editor.history[editor.historyIndex].slice()} }
            WorkbenchButton {theme:editor.theme; text: editor.tr("平滑", "Smooth"); onClicked:{let p=editor.points;editor.commit(p.map((v,i)=>Math.round((p[Math.max(0,i-1)]+v+p[Math.min(15,i+1)])/3)))} }
            WorkbenchButton {theme:editor.theme; text: editor.tr("镜像", "Mirror"); onClicked:editor.commit(editor.points.slice().reverse()) }
            WorkbenchButton {theme:editor.theme; text: editor.tr("清空", "Clear"); onClicked:editor.commit(new Array(16).fill(0)) }
            Item { Layout.fillWidth: true }
            WorkbenchButton {theme:editor.theme; text: editor.tr("保存波形", "Save Envelope"); onClicked: {let key=backend.saveOvcWaveform(name.text,editor.points,editor.waveKey);if(key){editor.saved(key);editor.close()}} }
        }
    }
}
