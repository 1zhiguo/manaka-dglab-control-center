import QtQuick
import "components" as UI
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    objectName: "ovcWorkbenchPage"
    required property var theme
    readonly property bool available: backend.socketProtocol === "v4"
    signal connectionSettingsRequested()
    property var draft: ({})
    property string savedSnapshot: ""
    property string saveFeedback: ""
    property bool saveSucceeded: false
    property string channel: "A"
    property string query: ""
    property bool showStrength: false
    property string actionFilter: "all"
    property string catalogFilter: "all"
    property var customModes: ({A:"action",B:"action"})
    readonly property var filteredCatalog: catalog.filter(w=>catalogFilter==="all"||w.group===catalogFilter)
    readonly property bool ready: draft.channels !== undefined
    readonly property var policy: ready ? draft.channels[channel] : ({})
    readonly property bool dirty: ready && JSON.stringify(draft) !== savedSnapshot
    readonly property var catalog: backend.ovcWaveforms
    readonly property var actions: backend.ovcActions.filter(a=> (actionFilter==="all" || a.style===actionFilter) && (!query.length || (a.key+" "+a.name).toLowerCase().indexOf(query.toLowerCase())>=0))
    readonly property var actionOptions: [{mode:"sync",wave:"",name:tr("同步游戏振动器","Sync Vibrator"),points:[100,100,100,100],color:theme.cyan},
        {mode:"random",wave:"",name:tr("随机波形池","Random Pool"),points:[0,70,20,100,0,50,0],color:theme.violet},
        {mode:"off",wave:"",name:tr("关闭本动作输出","Off"),points:[0,0,0,0],color:theme.muted}].concat(catalog.map(w=>Object.assign({},w,{mode:"wave",wave:w.key})))
    function tr(zh,en) { return backend.language === "en" ? en : zh }
    function reload() { draft=JSON.parse(JSON.stringify(backend.ovcProfile));savedSnapshot=JSON.stringify(draft) }
    function change(key,value) {
        let p=JSON.parse(JSON.stringify(draft));p[key]=value
        if(key==="hard_cap") {
            for(let level of ["low","medium","high"])p[level]=Math.min(p[level],value)
            for(let ch of ["A","B"]) {
                p.channels[ch].strength=Math.min(p.channels[ch].strength,value)
                for(let action in p.channels[ch].actions)p.channels[ch].actions[action].strength=Math.min(p.channels[ch].actions[action].strength,value)
            }
        }
        draft=p
    }
    function setPolicy(key,value) { let p=JSON.parse(JSON.stringify(draft));p.channels[channel][key]=value;p.channel_a=p.channels.A.enabled;p.channel_b=p.channels.B.enabled;draft=p }
    function rule(action) { return policy.actions && policy.actions[action] ? policy.actions[action] : ({mode:"sync",wave:"ovc_breathe",strength:Math.min(20,draft.hard_cap||0)}) }
    function setRule(action,key,value) {let p=JSON.parse(JSON.stringify(draft));let r=Object.assign({},rule(action));r[key]=value;p.channels[channel].actions[action]=r;draft=p}
    function indexFor(key) { for(let i=0;i<catalog.length;i++)if(catalog[i].key===key)return i;return -1 }
    function wavePoints(key) {let i=indexFor(key);return i>=0 ? catalog[i].points : []}
    function actionOptionIndex(rule) {return actionOptions.findIndex(o=>o.mode===rule.mode && (o.mode!=="wave" || o.wave===rule.wave))}
    function actionOption(rule) {let i=actionOptionIndex(rule);return i>=0?actionOptions[i]:({points:[],color:theme.muted})}
    function chooseAction(action,option) {let p=JSON.parse(JSON.stringify(draft));let r=Object.assign({},rule(action));r.mode=option.mode;if(option.mode==="wave")r.wave=option.wave;p.channels[channel].actions[action]=r;draft=p}
    function saveProfile() {
        if(!available)return false
        let ok=backend.saveOvcProfile(draft)
        if(ok)reload()
        saveSucceeded=ok
        saveFeedback=ok?tr("已保存","Saved")+" · "+Qt.formatTime(new Date(),"HH:mm:ss"):tr("保存失败：检查波形、强度和硬上限","Save failed: check envelope, strength and cap")
        feedbackTimer.restart()
        return ok
    }
    onDirtyChanged: {if(dirty){saveFeedback="";feedbackTimer.stop()}}
    Timer {id:feedbackTimer;interval:2500;onTriggered:page.saveFeedback=""}
    Component.onCompleted: reload()
    Connections {target:backend;function onOvcProfileChanged(){if(!page.dirty)page.reload()}}
    function modeName(mode) { return mode==="sync"?tr("同步游戏振动器","Sync Vibrator"):mode==="action"?tr("动作分配","Actions"):mode==="random"?tr("随机轮播","Random"):mode==="fixed"?tr("固定波形","Fixed"):tr("关闭","Off") }
    function selectCategory(category) {
        if(category==="sync") {
            if(["action","random","fixed"].indexOf(policy.mode)>=0) {let modes=Object.assign({},customModes);modes[channel]=policy.mode;customModes=modes}
            setPolicy("mode","sync")
        } else if(policy.mode==="sync"||policy.mode==="off") setPolicy("mode",customModes[channel]||"action")
    }
    function openChannel(ch) { if(available){channel=ch;channelDialog.open()} }
    function editWave(key) { if(available)waveEditor.openEditor(key) }
    onAvailableChanged: {if(!available){channelDialog.close();waveEditor.close()}}
    function chooseWave(key) {
        if(policy.mode==="random") {
            let pool=(policy.random_waves||[]).slice(),i=pool.indexOf(key)
            if(i>=0)pool.splice(i,1);else pool.push(key)
            setPolicy("random_waves",pool)
        } else setPolicy("wave",key)
    }
    function channelPoints(ch) {
        if(!ready)return []
        let p=draft.channels[ch]
        if(!p.enabled||p.mode==="off")return [0,0,0,0]
        if(p.mode==="sync")return [100,100,100,100]
        if(p.mode==="action") {
            let r=(p.actions||{})[backend.action]
            if(!r||r.mode==="sync")return [100,100,100,100]
            if(r.mode==="off")return [0,0,0,0]
            return wavePoints(r.mode==="random"?(p.random_waves||[])[0]:r.wave)
        }
        return wavePoints(p.mode==="random"?(p.random_waves||[])[0]:p.wave)
    }
    ColumnLayout {
        visible:page.available;enabled:page.available
        anchors.fill:parent;spacing:14
        RowLayout {
            Layout.fillWidth:true;spacing:8
            WorkbenchButton {theme:page.theme;text:page.tr("直接同步游戏","Game Sync");highlighted:page.ready&&page.draft.mode==="sync";onClicked:page.change("mode","sync")}
            WorkbenchButton {theme:page.theme;text:page.tr("A/B 独立配置","Independent A/B");highlighted:page.ready&&page.draft.mode==="independent";onClicked:page.change("mode","independent")}
            WorkbenchButton {theme:page.theme;visible:page.ready&&page.draft.mode==="independent";text:page.tr("档位 / 上限","Levels / Cap");highlighted:page.showStrength;onClicked:page.showStrength=!page.showStrength}
            Item {Layout.fillWidth:true}
            Label {text:"A "+backend.ovcOutputA+" / B "+backend.ovcOutputB;color:page.theme.cyan;font.pixelSize:12}
            WorkbenchButton {theme:page.theme;text:backend.ovcEnabled?page.tr("停止负鼠","Stop"):page.tr("启用负鼠","Enable");fillColor:backend.ovcEnabled?page.theme.panel2:page.theme.cyan;labelColor:backend.ovcEnabled?page.theme.fg:page.theme.darkMode?"#11151C":"#FFFFFF";onClicked:backend.toggleOvcOutput()}
        }
        ScrollView {
            Layout.fillWidth:true;Layout.fillHeight:true;contentWidth:availableWidth;clip:true
            ColumnLayout {
                width:parent.width;spacing:16
                Rectangle {
                    visible:page.ready&&(page.draft.mode==="sync"||page.showStrength)
                    Layout.fillWidth:true;implicitHeight:260;radius:22;color:page.theme.panel;border.color:page.theme.border
                    ColumnLayout {anchors.fill:parent;anchors.margins:22;spacing:12
                        Label {text:page.tr("振动器档位与安全上限","Vibrator Levels & Cap");color:page.theme.fg;font.pixelSize:18;font.bold:true}
                        Label {Layout.fillWidth:true;wrapMode:Text.Wrap;color:page.theme.muted;font.pixelSize:12;text:page.tr("随机档跟随游戏实际档位切换。强度 0–200，10 步进；中档供扩展 Mod 使用。","Random follows the game's effective mode. Strength 0–200, in steps of 10. Medium is reserved for mods.")}
                        GridLayout {columns:4;Layout.fillWidth:true;columnSpacing:12;rowSpacing:8
                            Repeater {model:[page.tr("低档","Low"),page.tr("中档 · 扩展","Medium · Mods"),page.tr("高档","High"),page.tr("硬上限","Hard Cap")];Label {required property string modelData;text:modelData;color:page.theme.fg;Layout.fillWidth:true}}
                            Repeater {model:["low","medium","high","hard_cap"]
                                WorkbenchSpinBox {theme:page.theme;required property string modelData;from:0;to:200;stepSize:10;value:page.draft[modelData]||0;Layout.fillWidth:true;onValueModified:page.change(modelData,value)}
                            }
                        }
                        RowLayout {visible:page.ready&&page.draft.mode==="sync";Layout.fillWidth:true
                            UI.CheckBox {text:page.tr("A 配件","Accessory A");checked:page.ready&&page.draft.channels.A.enabled;onClicked:{page.channel="A";page.setPolicy("enabled",checked)}}
                            UI.CheckBox {text:page.tr("B 配件","Accessory B");checked:page.ready&&page.draft.channels.B.enabled;onClicked:{page.channel="B";page.setPolicy("enabled",checked)}}
                            Item {Layout.fillWidth:true}
                            Label {text:page.tr("游戏关闭 = 0","Game Off = zero");color:page.theme.muted;font.pixelSize:12}
                        }
                    }
                }
                Rectangle {
                    visible:page.ready&&page.draft.mode==="independent"
                    Layout.fillWidth:true;implicitHeight:268;radius:22;color:page.theme.panel;border.color:page.theme.border
                    ColumnLayout {anchors.fill:parent;anchors.margins:18;spacing:12
                        RowLayout {Layout.fillWidth:true
                            Label {Layout.fillWidth:true;text:page.tr("振动波形与我的波形库","Vibration Envelope Library");color:page.theme.fg;font.pixelSize:17;font.bold:true}
                            Repeater {model:[{key:"all",name:page.tr("全部","All")},{key:"built_in",name:page.tr("内置","Built-in")},{key:"custom",name:page.tr("自定义","Custom")},{key:"shared",name:page.tr("共用","Shared")}]
                                WorkbenchButton {theme:page.theme;required property var modelData;implicitWidth:80;implicitHeight:34;text:modelData.name;highlighted:page.catalogFilter===modelData.key;onClicked:page.catalogFilter=modelData.key}
                            }
                            WorkbenchButton {theme:page.theme;implicitWidth:100;implicitHeight:34;text:page.tr("新建波形","New");onClicked:page.editWave("")}
                        }
                        ListView {
                            id:library;Layout.fillWidth:true;Layout.fillHeight:true;orientation:ListView.Horizontal;spacing:10;clip:true;model:page.filteredCatalog
                            delegate:Rectangle {
                                id:waveCard;required property var modelData
                                width:225;height:library.height;radius:13;color:page.theme.panel2;border.color:libraryHover.hovered?modelData.color:page.theme.border
                                ColumnLayout {anchors.fill:parent;anchors.margins:12;spacing:8
                                    Label {Layout.fillWidth:true;text:waveCard.modelData.name;color:page.theme.fg;font.pixelSize:13;font.bold:true;elide:Text.ElideRight}
                                    VibrationPreview {Layout.fillWidth:true;Layout.fillHeight:true;points:waveCard.modelData.points;lineColor:waveCard.modelData.color;animate:libraryHover.hovered}
                                    RowLayout {Layout.fillWidth:true
                                        Label {Layout.fillWidth:true;text:waveCard.modelData.group==="custom"?page.tr("自定义","Custom"):waveCard.modelData.group==="shared"?page.tr("共用曲线","Shared"):page.tr("内置包络","Built-in");color:page.theme.muted;font.pixelSize:10}
                                        WorkbenchButton {theme:page.theme;implicitWidth:80;implicitHeight:30;text:page.tr("编辑","Edit");onClicked:page.editWave(waveCard.modelData.key)}
                                    }
                                }
                                HoverHandler{id:libraryHover}
                            }
                            ScrollBar.horizontal:ScrollBar{}
                        }
                        Label {text:page.tr("悬停预览波形 · 在下方 A/B 通道策略中分配","Hover to preview · assign envelopes in the A/B channel strategies below");color:page.theme.muted;font.pixelSize:11}
                    }
                }
                RowLayout {
                    visible:page.ready&&page.draft.mode==="independent"
                    Layout.fillWidth:true;Layout.preferredHeight:310;spacing:16
                    Rectangle {
                        Layout.preferredWidth:355;Layout.fillHeight:true;radius:22;color:page.theme.panel;border.color:page.theme.border
                        ColumnLayout {anchors.fill:parent;anchors.margins:20;spacing:12
                            Label {text:page.tr("通道策略","Channel Strategy");color:page.theme.fg;font.pixelSize:18;font.bold:true}
                            Repeater {model:["A","B"]
                                Rectangle {
                                    id:channelCard;required property string modelData
                                    readonly property var channelPolicy:page.ready?page.draft.channels[modelData]:({})
                                    Layout.fillWidth:true;Layout.fillHeight:true;radius:15;color:page.theme.panel2;border.color:modelData==="A"?page.theme.cyan:page.theme.violet
                                    RowLayout {anchors.fill:parent;anchors.margins:14;spacing:12
                                        Label {text:channelCard.modelData;color:channelCard.modelData==="A"?page.theme.cyan:page.theme.violet;font.pixelSize:23;font.bold:true}
                                        ColumnLayout {Layout.fillWidth:true;spacing:7
                                            Label {Layout.fillWidth:true;text:page.tr("通道 ","Channel ")+channelCard.modelData;color:page.theme.fg;font.pixelSize:14;font.bold:true}
                                            Label {Layout.fillWidth:true;text:channelCard.channelPolicy.enabled?page.modeName(channelCard.channelPolicy.mode):page.tr("通道未启用","Channel Disabled");color:page.theme.muted;font.pixelSize:12;elide:Text.ElideRight}
                                        }
                                        VibrationPreview {Layout.preferredWidth:85;Layout.fillHeight:true;points:page.channelPoints(channelCard.modelData);lineColor:channelCard.modelData==="A"?page.theme.cyan:page.theme.violet;animate:channelHover.hovered}
                                        Label {text:"›";color:page.theme.muted;font.pixelSize:24}
                                    }
                                    HoverHandler{id:channelHover}
                                    MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:page.openChannel(channelCard.modelData)}
                                }
                            }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth:true;Layout.fillHeight:true;radius:22;color:page.theme.panel;border.color:page.theme.border
                        ColumnLayout {anchors.fill:parent;anchors.margins:20;spacing:12
                            Label {text:page.tr("A/B 输出与预览","A/B Output & Preview");color:page.theme.fg;font.pixelSize:18;font.bold:true}
                            Repeater {model:["A","B"]
                                ColumnLayout {required property string modelData;Layout.fillWidth:true;Layout.fillHeight:true;spacing:6
                                    RowLayout {Layout.fillWidth:true;Label {text:modelData;color:modelData==="A"?page.theme.cyan:page.theme.violet;font.pixelSize:14;font.bold:true}Item{Layout.fillWidth:true}Label{text:(modelData==="A"?backend.ovcOutputA:backend.ovcOutputB)+" / "+(page.draft.hard_cap||0);color:page.theme.muted;font.pixelSize:12}}
                                    VibrationPreview {Layout.fillWidth:true;Layout.fillHeight:true;points:page.channelPoints(modelData);lineColor:modelData==="A"?page.theme.cyan:page.theme.violet}
                                }
                            }
                            Label {Layout.fillWidth:true;wrapMode:Text.Wrap;text:page.tr("图形显示所选包络；数字为请求强度，非硬件实测值。","Graphs show selected envelopes; numbers are requested strength, not hardware measurements.");color:page.theme.muted;font.pixelSize:10}
                        }
                    }
                }
                Label {Layout.fillWidth:true;text:backend.ovcStatus;color:page.theme.muted;wrapMode:Text.Wrap;font.pixelSize:12}
            }
        }
        RowLayout {
            Layout.fillWidth:true
            Label {Layout.fillWidth:true;wrapMode:Text.Wrap;color:page.saveSucceeded&&page.saveFeedback.length?page.theme.green:page.theme.amber;font.pixelSize:12;text:page.saveFeedback.length?page.saveFeedback:page.dirty?page.tr("尚未保存；保存后停止负鼠，需手动重新启用","Unsaved. Saving stops Opossum; explicitly re-enable."):""}
            WorkbenchButton {theme:page.theme;text:page.tr("恢复已保存设置","Reload");onClicked:page.reload()}
            WorkbenchButton {theme:page.theme;text:page.tr("保存负鼠配置","Save Opossum");fillColor:page.theme.green;labelColor:page.theme.darkMode?"#11151C":"#FFFFFF";onClicked:page.saveProfile()}
        }
    }
    Rectangle {
        objectName:"ovcV3Unavailable"
        anchors.fill:parent;visible:!page.available
        radius:22;color:page.theme.panel;border.color:page.theme.border
        ColumnLayout {
            anchors.centerIn:parent;width:Math.min(640,parent.width-64);spacing:20
            Label {Layout.fillWidth:true;text:page.tr("当前使用 V3，负鼠工作台不可用","Opossum Is Unavailable in V3");wrapMode:Text.Wrap;color:page.theme.fg;font.pixelSize:24;font.bold:true}
            Label {Layout.fillWidth:true;text:page.tr("V3 用于郊狼单设备连接。要使用负鼠，请前往「设备与游戏」，将扫码连接协议切换为 V4，并使用 DG-LAB 4 App 重新扫码。","V3 is for a single Coyote device. To use Opossum, open Setup, select V4 and scan again with DG-LAB 4 App.");wrapMode:Text.Wrap;color:page.theme.muted;font.pixelSize:15;lineHeight:1.3}
            WorkbenchButton {objectName:"ovcGoToConnectionSettings";theme:page.theme;text:page.tr("前往切换 V4","Open V4 Setup");highlighted:true;onClicked:page.connectionSettingsRequested()}
        }
    }
    OvcChannelDialog {id:channelDialog;theme:page.theme;workbench:page}
    OvcWaveEditor {id:waveEditor;theme:page.theme;onSaved:key=>{let p=JSON.parse(JSON.stringify(page.draft));p.custom_waves=backend.ovcProfile.custom_waves;page.draft=p;page.setPolicy("wave",key)}}
}
