import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    objectName:"booWorkbenchPage"
    required property var theme
    property var draft: ({})
    property string query:""
    property string pendingAddress:""
    property var selectedActions:[]
    property string feedback:""
    readonly property var actions:backend.gameActions.filter(a=>!query.length||(a.name+" "+a.key).toLowerCase().indexOf(query.toLowerCase())>=0)
    readonly property var modes:[tr("同步游戏","Sync"),tr("指定档位","Level"),tr("关闭","Off")]
    function tr(zh,en){return backend.language==="en"?en:zh}
    function reload(){draft=JSON.parse(JSON.stringify(backend.booProfile));selectedActions=[]}
    function saveProfile(){if(backend.saveBooProfile(page.draft)){page.feedback=page.tr("已保存","Saved");feedbackTimer.restart()}}
    function change(key,value){
        let p=JSON.parse(JSON.stringify(draft));p[key]=value
        if(key==="hard_cap"){
            for(let k of ["slow","medium","fast","vibration_level"])p[k]=Math.min(p[k],value)
            for(let a in p.actions)p.actions[a].level=Math.min(p.actions[a].level,value)
        }
        draft=p;feedback=""
    }
    function rule(key){return draft.actions&&draft.actions[key]?draft.actions[key]:({mode:"sync",level:1})}
    function setRule(key,mode,level){let p=JSON.parse(JSON.stringify(draft));p.actions[key]={mode:mode,level:Math.min(level,p.hard_cap)};draft=p;feedback=""}
    function toggle(key){let a=selectedActions.slice(),i=a.indexOf(key);if(i<0)a.push(key);else a.splice(i,1);selectedActions=a}
    function selectAll(){selectedActions=actions.map(a=>a.key)}
    function invert(){selectedActions=actions.map(a=>a.key).filter(k=>selectedActions.indexOf(k)<0)}
    function batch(mode,level){let p=JSON.parse(JSON.stringify(draft));for(let k of selectedActions)p.actions[k]={mode:mode,level:Math.min(level,p.hard_cap)};draft=p;selectedActions=[];feedback=""}
    onQueryChanged:selectedActions=[]
    Component.onCompleted:reload()
    Connections{target:backend;function onBooProfileChanged(){page.reload()}}
    Timer{id:feedbackTimer;interval:2500;onTriggered:page.feedback=""}
    ScrollView {
        anchors.fill:parent;clip:true;contentWidth:availableWidth
        ColumnLayout {
            width:parent.width;spacing:16
            Rectangle {
                Layout.fillWidth:true;implicitHeight:connection.implicitHeight+40
                radius:22;color:page.theme.panel;border.color:backend.booConnected?page.theme.accent:page.theme.border
                ColumnLayout {
                    id:connection;anchors.fill:parent;anchors.margins:20;spacing:12
                    RowLayout{
                        Layout.fillWidth:true
                        Label{text:"FN010-RX · BooBoop";font.pixelSize:20;font.bold:true;color:page.theme.fg;Layout.fillWidth:true}
                        WorkbenchButton{theme:page.theme;text:backend.booEnabled?page.tr("停止","Stop"):page.tr("启用联动","Enable");onClicked:backend.toggleBooOutput();highlighted:backend.booEnabled}
                    }
                    Label{Layout.fillWidth:true;text:page.tr("实验性蓝牙适配 · 连接后保持停止，手动启用才跟随游戏。","Experimental BLE profile · stopped on connection; enable game sync manually.");wrapMode:Text.Wrap;color:page.theme.muted;font.pixelSize:12}
                    RowLayout{
                        visible:backend.socketProtocol!=="ble";Layout.fillWidth:true
                        Label{Layout.fillWidth:true;wrapMode:Text.Wrap;color:page.theme.amber;text:page.tr("需要全局使用蓝牙直连模式。Socket 与蓝牙不会混用。","Select direct BLE for all devices. Socket and BLE are not mixed.")}
                        WorkbenchButton{theme:page.theme;text:page.tr("切换蓝牙","Use BLE");onClicked:backend.selectSocketProtocol("ble")}
                    }
                    RowLayout {
                        visible:backend.socketProtocol==="ble";Layout.fillWidth:true;spacing:10
                        ThemedComboBox{
                            id:deviceChoice;theme:page.theme;Layout.fillWidth:true
                            model:backend.booDevices;textRole:"label"
                            currentIndex:Math.max(0,backend.booDevices.findIndex(d=>page.pendingAddress?d.address===page.pendingAddress:d.selected))
                            onActivated:page.pendingAddress=backend.booDevices[currentIndex].address
                        }
                        WorkbenchButton{theme:page.theme;text:backend.bleScanning?page.tr("取消检测","Cancel Scan"):page.tr("检测并连接","Scan & Connect");enabled:!backend.bleBusy||backend.bleScanning;onClicked:{page.pendingAddress="";if(backend.bleScanning)backend.cancelBleScan();else backend.scanBooDevice()}}
                        WorkbenchButton{theme:page.theme;text:page.tr("连接","Connect");enabled:!backend.bleBusy&&deviceChoice.currentIndex>0;onClicked:backend.connectBleRole("booboop",backend.booDevices[deviceChoice.currentIndex].address)}
                        WorkbenchButton{theme:page.theme;text:backend.booConnecting?page.tr("取消","Cancel"):page.tr("断开","Disconnect");enabled:backend.booConnecting||backend.booConnected;onClicked:backend.connectBleRole("booboop","")}
                    }
                    BleActivity{theme:page.theme;prefix:"boo";visible:backend.socketProtocol==="ble"}
                    Label{Layout.fillWidth:true;text:backend.booStatus;wrapMode:Text.Wrap;color:page.theme.cyan;font.pixelSize:13}
                    Label{Layout.fillWidth:true;text:page.tr("请先关闭厂商 App 对设备的连接。此协议没有位置、行程和实际运动回报；显示的是协议档位，停止写入也不代表设备已回报停止。","Disconnect the vendor App first. This profile has no position, stroke or movement feedback. Values are protocol indices; stop writes do not confirm physical stopping.");wrapMode:Text.Wrap;color:page.theme.muted;font.pixelSize:12}
                }
            }
            Rectangle {
                Layout.fillWidth:true;implicitHeight:mapping.implicitHeight+40
                radius:22;color:page.theme.panel;border.color:page.theme.border
                ColumnLayout {
                    id:mapping;anchors.fill:parent;anchors.margins:20;spacing:12
                    RowLayout{
                        Layout.fillWidth:true
                        Label{Layout.fillWidth:true;text:page.tr("游戏活塞映射","Game Piston Mapping");font.bold:true;font.pixelSize:18;color:page.theme.fg}
                        Label{text:page.feedback;color:page.theme.cyan}
                        WorkbenchButton{objectName:"booMappingSave";theme:page.theme;highlighted:true;text:page.tr("保存配置","Save");onClicked:page.saveProfile()}
                    }
                    Label{Layout.fillWidth:true;text:backend.booGamePiston;wrapMode:Text.Wrap;color:page.theme.cyan;font.pixelSize:13}
                    Label{Layout.fillWidth:true;text:page.tr("关闭活塞、暂停、失败或游戏数据过期时停止。动作覆盖仅在活塞已开启时生效。保存配置会停止联动，之后需重新启用。","Stops when the piston is off, game is paused/failed or telemetry expires. Action overrides require the piston to be on. Saving stops sync; enable again afterwards.");wrapMode:Text.Wrap;color:page.theme.muted;font.pixelSize:12}
                    GridLayout {
                        Layout.fillWidth:true;columns:4;columnSpacing:16;rowSpacing:6
                        Repeater{model:[{key:"hard_cap",zh:"档位上限",en:"Level Cap"},{key:"slow",zh:"慢速",en:"Slow"},{key:"medium",zh:"中速",en:"Medium"},{key:"fast",zh:"快速",en:"Fast"}]
                            ColumnLayout{
                                required property var modelData
                                Layout.fillWidth:true
                                Label{text:page.tr(modelData.zh,modelData.en);color:page.theme.fg;font.pixelSize:13}
                                WorkbenchSpinBox{theme:page.theme;Layout.fillWidth:true;from:0;to:modelData.key==="hard_cap"?9:(page.draft.hard_cap||0);value:page.draft[modelData.key]||0;onValueModified:page.change(modelData.key,value)}
                            }
                        }
                    }
                    RowLayout{
                        Layout.fillWidth:true
                        CheckBox{checked:page.draft.vibration_enabled||false;text:page.tr("伴随振动","Companion Vibration");palette.windowText:page.theme.fg;onToggled:page.change("vibration_enabled",checked)}
                        WorkbenchSpinBox{theme:page.theme;from:0;to:page.draft.hard_cap||0;value:page.draft.vibration_level||0;onValueModified:page.change("vibration_level",value)}
                        Item{Layout.fillWidth:true}
                        Label{text:page.tr("请求档位：","Requested: ")+backend.booStretch+" / "+backend.booVibration;color:page.theme.cyan}
                    }
                    Label{Layout.fillWidth:true;wrapMode:Text.Wrap;text:backend.booSent;color:page.theme.muted;font.pixelSize:12}
                }
            }
            Rectangle {
                Layout.fillWidth:true;implicitHeight:assignment.implicitHeight+40
                radius:22;color:page.theme.panel;border.color:page.theme.border
                ColumnLayout {
                    id:assignment;anchors.fill:parent;anchors.margins:20;spacing:12
                    Label{text:page.tr("动作档位覆盖","Action Overrides");font.bold:true;font.pixelSize:18;color:page.theme.fg}
                    TextField{Layout.fillWidth:true;placeholderText:page.tr("搜索动作","Search Actions");onTextChanged:page.query=text;color:page.theme.fg;placeholderTextColor:page.theme.muted;background:Rectangle{color:page.theme.panel2;radius:12;border.color:page.theme.border}}
                    RowLayout {
                        Layout.fillWidth:true;spacing:8
                        WorkbenchButton{theme:page.theme;text:page.tr("全选","Select All");onClicked:page.selectAll()}
                        WorkbenchButton{theme:page.theme;text:page.tr("反选","Invert");onClicked:page.invert()}
                        Label{text:page.selectedActions.length+page.tr(" 项"," selected");color:page.theme.muted}
                        ThemedComboBox{id:batchMode;theme:page.theme;Layout.fillWidth:true;model:page.modes}
                        WorkbenchSpinBox{id:batchLevel;theme:page.theme;from:0;to:page.draft.hard_cap||0;value:1}
                        WorkbenchButton{theme:page.theme;text:page.tr("批量应用","Apply");enabled:page.selectedActions.length>0;onClicked:page.batch(["sync","level","off"][batchMode.currentIndex],batchLevel.value)}
                    }
                    ListView {
                        Layout.fillWidth:true;Layout.preferredHeight:350;clip:true;spacing:8
                        model:page.actions;ScrollBar.vertical:ScrollBar{}
                        delegate:Rectangle {
                            required property var modelData
                            width:ListView.view.width;height:62;radius:12;color:page.theme.panel2
                            RowLayout{
                                anchors.fill:parent;anchors.margins:8
                                CheckBox{checked:page.selectedActions.indexOf(modelData.key)>=0;onClicked:page.toggle(modelData.key)}
                                Label{Layout.fillWidth:true;elide:Text.ElideRight;text:modelData.name;color:page.theme.fg}
                                ThemedComboBox{theme:page.theme;Layout.preferredWidth:170;model:page.modes;currentIndex:["sync","level","off"].indexOf(page.rule(modelData.key).mode);onActivated:page.setRule(modelData.key,["sync","level","off"][currentIndex],page.rule(modelData.key).level)}
                                WorkbenchSpinBox{theme:page.theme;from:0;to:page.draft.hard_cap||0;value:page.rule(modelData.key).level;enabled:page.rule(modelData.key).mode==="level";onValueModified:page.setRule(modelData.key,"level",value)}
                            }
                        }
                    }
                    RowLayout{
                        Layout.fillWidth:true
                        WorkbenchButton{theme:page.theme;text:page.tr("官方使用说明","Vendor Site");onClicked:Qt.openUrlExternally("https://www.booboop.com/en/")}
                        WorkbenchButton{theme:page.theme;text:page.tr("社区协议来源","Protocol Notes");onClicked:Qt.openUrlExternally("https://github.com/buttplugio/buttplug/issues/968")}
                        Item{Layout.fillWidth:true}
                        Label{text:page.feedback;color:page.theme.cyan}
                        WorkbenchButton{theme:page.theme;highlighted:true;text:page.tr("保存配置","Save");onClicked:page.saveProfile()}
                    }
                }
            }
            Item{Layout.preferredHeight:8}
        }
    }
}
