import QtQuick
import "components" as UI
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id:studio
    objectName:"gameplaySettings"
    required property var controller
    property var draft: controller.waveWorkbench
    property string savedDraft: JSON.stringify(draft)
    property int revision: 0
    property string message: ""
    property bool failed: false
    property string channelKey: section.currentIndex === 1 ? "B" : "A"
    property var channel: { revision; return draft.policy[channelKey] }
    property int ruleIndex: -1
    property var rule: { revision; return ruleIndex >= 0 && ruleIndex < channel.rules.length ? JSON.parse(JSON.stringify(channel.rules[ruleIndex])) : null }
    readonly property bool dirty: { revision; return JSON.stringify(draft) !== savedDraft }
    property bool modeConfirmed:false
    property string pendingMode:""
    readonly property bool independent: { revision; return draft.mapping.mode === "independent" }
    function reselect() { forceActiveFocus(); pendingMode=draft.mapping.mode; modeConfirmed=false }
    function confirmMode() {
        if (pendingMode !== "legacy_v1" && pendingMode !== "independent") return
        edit(draft.mapping,"mode",pendingMode)
        modeConfirmed=true
        section.currentIndex=0
    }
    readonly property bool dark: controller.theme !== "light"
    readonly property color surface: UI.Theme.surfaceRaised
    readonly property color line: UI.Theme.borderDecorative
    readonly property color ink: UI.Theme.textPrimary
    readonly property color secondary: UI.Theme.textSecondary
    readonly property color accent: UI.Theme.accent
    readonly property color danger: UI.Theme.danger
    property var sourceKeys: ["always","action","heart","ecstasy","vibrator","piston","npc_alert","climax","failure"]
    property var intensityKeys:["device","action_active","heart","ecstasy","action","npc_alert","vibrator","piston"]
    property var intensityNames:[t("绑定设备的档位", "Bound device level"),t("动作发生", "Action active"),t("心率", "Heart rate"),t("兴奋度", "Ecstasy"),t("动作进度", "Action progress"),t("NPC 警觉度", "NPC alert"),t("振动器档位", "Vibrator level"),t("活塞机档位", "Piston level")]
    property var sourceNames: [t("始终", "Always"),t("游戏动作", "Game action"),t("心率", "Heart rate"),t("兴奋度", "Ecstasy"),t("振动器", "Vibrator"),t("活塞机", "Piston"),t("NPC 警觉度", "NPC alert"),t("高潮事件", "Climax"),t("失败事件", "Failure")]
    property var waveOptions: [{key:"off",name:t("停止此通道波形", "Stop channel waveform")}].concat(controller.waveAssets)
    property var legacyOptions: controller.waveAssets
    property string legacyAction: ""
    property string pickerTarget: "rule"
    property var pickedActions: []
    function openActions(target) {
        pickerTarget=target
        pickedActions=target === "rule" && rule && rule.value ? rule.value.split("|") : []
        actionSearch.text=""; actionPicker.open()
    }
    signal closeRequested()
    signal closeCancelled()
    function modeLabel(value) { return ({low:t("弱档","Low"),medium:t("中档","Medium"),high:t("强档","High")})[value] || value }
    function t(zh,en) { return controller.language === "en" ? en : zh }
    function edit(target,key,value) { if (target === rule && ruleIndex >= 0) channel.rules[ruleIndex][key]=value; else target[key]=value; revision++; message=""; failed=false }
    function reload() { ruleIndex=-1; draft=JSON.parse(JSON.stringify(controller.waveWorkbench)); savedDraft=JSON.stringify(draft); revision++; message=""; failed=false }
    function feedback(result,success) { failed=!result.ok; message=result.error || success; return result.ok }
    function save() { forceActiveFocus(); let result=controller.saveWaveWorkbench(JSON.stringify(draft)); if (result.ok) reload(); return feedback(result,t("玩法设置已保存，等待新的游戏数据。", "Gameplay settings saved. Waiting for fresh game data.")) }
    function requestClose() { if (dirty) discard.open(); else closeRequested() }
    function newBinding() { return {origin:-1,source:"heart",low:90,high:160,input_start:0,input_full:100,curve:"linear"} }
    function template(telemetry) {
        draft.mapping.mode="independent"
        for (let key of ["A","B"]) {
            let config=draft.mapping[key]
            config.device=key === "A" ? "vibrator" : "piston"
            let source=telemetry ? "heart" : "device"
            let row=config.bindings.find(x => x.source === source) || newBinding()
            row.source=source
            config.bindings=[row]
            draft.policy[key].default_wave="donor_"+config.device
            draft.policy[key].rules=draft.policy[key].rules.filter(x => x.source === "climax" || x.source === "failure")
            for(let rule of draft.policy[key].rules) if(rule.source === "climax") rule.wave="donor_climax"
        }
        revision++
    }
    function addRule() {
        let value={id:"rule-"+Date.now()+"-"+Math.floor(Math.random()*10000),source:"always",wave:channel.default_wave === "off" ? "official_breath" : channel.default_wave,value:"",minimum:0,maximum:300,priority:10,stable_ms:300,hold_ms:800,transition:"immediate",playback:"loop",duration_ms:1300,cooldown_ms:5000,enabled:true}
        channel.rules=channel.rules.concat([value]); revision++; ruleIndex=channel.rules.length-1
    }
    Component.onCompleted: reload()
    Connections { target:studio.controller; function onConfigChanged() { if (!studio.dirty) studio.reload() } }
    spacing:12
    RowLayout {
        Layout.fillWidth:true
        ColumnLayout {
            Layout.fillWidth:true
            Caption { text:!studio.modeConfirmed ? studio.t("选择一种玩法并确认，再调整对应设置。", "Choose and confirm a gameplay mode to configure it.") : studio.independent ? studio.t("当前编辑：A/B 独立绑定", "Editing: independent A/B") : studio.t("当前编辑：原版心率 / 动作", "Editing: original heart / action") }
        }
        ActionButton { objectName:"reselectGameplay"; visible:studio.modeConfirmed; text:studio.t("重新选择", "Change mode"); onClicked:studio.reselect() }
        ActionButton { objectName:"reloadWorkbench"; visible:studio.modeConfirmed; text:studio.t("恢复已保存", "Reload saved"); enabled:studio.dirty; onClicked:studio.reload() }
        ActionButton { objectName:"saveWorkbench"; visible:studio.modeConfirmed; text:studio.t("保存玩法设置", "Save gameplay"); primary:true; enabled:studio.dirty; onClicked:studio.save() }
    }
    ColumnLayout {
        objectName:"gameplayChooser"; visible:!studio.modeConfirmed; Layout.fillWidth:true; Layout.fillHeight:true; spacing:18
        Item { Layout.fillHeight:true }
        RowLayout {
            Layout.fillWidth:true; spacing:16
            Repeater {
                model:[{key:"legacy_v1",name:studio.t("原版心率 / 动作", "Original heart / action"),description:studio.t("沿用心率变化、动作渐升及高潮／失败事件逻辑，按阶段或动作选择波形。", "Keep heart-rate ramps, action progression and climax/failure events. Select waveforms by stage or action.")},
                       {key:"independent",name:studio.t("A/B 独立绑定", "Independent A/B"),description:studio.t("分别绑定设备与强度来源，为 A、B 通道配置默认波形和触发规则。", "Bind devices and intensity sources independently. Set default waveforms and trigger rules for A and B.")}]
                delegate:Button {
                    id:modeCard; required property var modelData
                    objectName:"chooseGameplay"+modelData.key
                    Layout.fillWidth:true; Layout.preferredWidth:1; implicitHeight:190; padding:20
                    checked:studio.pendingMode === modelData.key
                    onClicked:studio.pendingMode=modelData.key
                    background:Rectangle { radius:10; color:studio.surface; border.width:modeCard.checked || modeCard.activeFocus ? 2 : 1; border.color:modeCard.checked || modeCard.activeFocus ? studio.accent : studio.line }
                    contentItem:ColumnLayout {
                        spacing:12
                        Label { Layout.fillWidth:true; text:(modeCard.checked ? "●  " : "○  ")+modeCard.modelData.name; font.pixelSize:18; font.bold:true; color:studio.ink; wrapMode:Text.Wrap }
                        Caption { text:modeCard.modelData.description }
                        Item { Layout.fillHeight:true }
                    }
                }
            }
        }
        Caption { text:studio.t("确认后进入编辑；点击「保存玩法设置」才会生效。重新选择会保留两种玩法的未保存配置。强度数值在「个性化范围」设置。", "Confirm to edit; changes take effect only after Save gameplay. Changing modes retains both drafts. Set intensity values in Intensity Range.") }
        ActionButton { objectName:"confirmGameplay"; Layout.alignment:Qt.AlignHCenter; text:studio.t("确认玩法并设置", "Confirm and configure"); enabled:studio.pendingMode !== ""; primary:true; onClicked:studio.confirmMode() }
        Item { Layout.fillHeight:true }
    }
    TabBar {
        id:section; objectName:"gameplayTabs"; visible:studio.modeConfirmed && studio.independent; Layout.fillWidth:true
        onCurrentIndexChanged:studio.ruleIndex=-1
        WorkbenchTab { text:studio.t("A 通道规则", "A rules") }
        WorkbenchTab { text:studio.t("B 通道规则", "B rules") }
        WorkbenchTab { text:studio.t("检测绑定", "Detection bindings") }
    }
    RowLayout {
        visible:studio.modeConfirmed && studio.independent && (section.currentIndex === 0 || section.currentIndex === 1); Layout.fillWidth:true; Layout.fillHeight:true; spacing:16
        ColumnLayout {
            Layout.preferredWidth:300; Layout.fillHeight:true
            Caption { text:studio.t("无规则匹配时的默认波形", "Default waveform when no rule matches") }
            Choice { model:studio.waveOptions; textRole:"name"; currentIndex:studio.waveOptions.findIndex(x => x.key === studio.channel.default_wave); onActivated:studio.edit(studio.channel,"default_wave",studio.waveOptions[currentIndex].key) }
            Choice { model:[studio.t("循环播放", "Loop"),studio.t("单次播放", "Play once")]; currentIndex:studio.channel.default_playback === "once" ? 1 : 0; onActivated:studio.edit(studio.channel,"default_playback",currentIndex ? "once" : "loop") }
            ListView {
                id:rulesList; objectName:"waveRulesList"; Layout.fillWidth:true; Layout.fillHeight:true; clip:true; spacing:4
                model: { studio.revision; return studio.channel.rules }
                delegate: ItemDelegate {
                    required property var modelData
                    required property int index
                    width:ListView.view.width; height:58
                    text:(modelData.enabled ? "" : "○ ")+(modelData.source === "climax" ? studio.t("最高", "Highest") : modelData.source === "failure" ? studio.t("事件", "Event") : modelData.priority)+" · "+studio.sourceNames[studio.sourceKeys.indexOf(modelData.source)]+(modelData.value ? " · "+(modelData.source === "action" ? studio.controller.actionSummary(modelData.value) : studio.modeLabel(modelData.value)) : "")
                    highlighted:studio.ruleIndex === index
                    contentItem:Label { text:parent.text; color:studio.ink; wrapMode:Text.Wrap; maximumLineCount:2; elide:Text.ElideRight }
                    background:Rectangle { color:parent.highlighted ? studio.surface : "transparent"; radius:6; border.color:parent.highlighted ? studio.accent : studio.line }
                    onClicked:studio.ruleIndex=index
                }
                ScrollBar.vertical:ThinScroll {}
            }
            RowLayout {
                ActionButton { objectName:"addWaveRule"; text:studio.t("新增规则", "Add rule"); enabled:studio.channel.rules.length<128; onClicked:studio.addRule() }
                ActionButton { text:studio.t("移除", "Remove"); enabled:studio.rule !== null; onClicked:{ let i=studio.ruleIndex; studio.ruleIndex=-1; studio.edit(studio.channel,"rules",studio.channel.rules.filter((x,n) => n !== i)) } }
            }
        }
        ScrollView {
            id:ruleScroll; Layout.fillWidth:true; Layout.fillHeight:true; contentWidth:availableWidth; clip:true
            ScrollBar.horizontal.policy:ScrollBar.AlwaysOff; ScrollBar.vertical:ThinScroll {}
            ColumnLayout {
                width:ruleScroll.availableWidth-12; spacing:12
                Caption { visible:!studio.rule; text:studio.t("选择左侧规则，或新增规则。", "Select a rule or add one.") }
                ColumnLayout {
                    visible:studio.rule !== null; Layout.fillWidth:true; spacing:12
                    ThemedCheck { objectName:"ruleEnabled"; text:studio.t("启用规则", "Enable rule"); checked:studio.rule ? studio.rule.enabled : false; onToggled:if(studio.rule) studio.edit(studio.rule,"enabled",checked) }
                    GridLayout {
                        Layout.fillWidth:true; columns:2; columnSpacing:14; rowSpacing:10
                        ColumnLayout { Caption { text:studio.t("触发内容", "Condition") }
 Choice { model:studio.sourceNames; currentIndex:studio.rule ? studio.sourceKeys.indexOf(studio.rule.source) : 0; onActivated: { studio.edit(studio.rule,"source",studio.sourceKeys[currentIndex]); studio.edit(studio.rule,"value","") } } }
                        ColumnLayout { Caption { text:studio.t("播放波形", "Waveform") }
 Choice { model:studio.waveOptions; textRole:"name"; currentIndex:studio.rule ? studio.waveOptions.findIndex(x => x.key === studio.rule.wave) : 0; onActivated:studio.edit(studio.rule,"wave",studio.waveOptions[currentIndex].key) } }
                        NumberField { visible:studio.rule && ["climax","failure"].indexOf(studio.rule.source)<0; label:studio.t("普通规则优先级", "Ordinary rule priority"); maximum:1000; value:studio.rule ? studio.rule.priority : 0; onEdited:value => studio.edit(studio.rule,"priority",value) }
                        ColumnLayout { Caption { text:studio.t("播放方式", "Playback") }
 Choice { model:[studio.t("循环", "Loop"),studio.t("单次，重新进入规则后重播", "Once; replay on rule re-entry")]; currentIndex:studio.rule && studio.rule.playback === "once" ? 1 : 0; onActivated:studio.edit(studio.rule,"playback",currentIndex ? "once" : "loop") } }
                    }
                    ColumnLayout {
                        Layout.fillWidth:true; visible:studio.rule && ["action","vibrator","piston"].indexOf(studio.rule.source)>=0
                        Caption { text:studio.t("匹配的动作或档位", "Matching actions or level") }
                        ActionButton { objectName:"ruleActionPicker"; visible:studio.rule && studio.rule.source === "action"; Layout.fillWidth:true; text:studio.rule ? studio.controller.actionSummary(studio.rule.value) : ""; onClicked:studio.openActions("rule") }
                        Choice { objectName:"ruleConditionValue"; visible:studio.rule && studio.rule.source !== "action"; property var keys:studio.rule && studio.rule.source === "vibrator" ? ["","low","high"] : ["","low","medium","high"]; model:keys.map(x => x ? studio.modeLabel(x) : studio.t("全部档位","All levels")); currentIndex:studio.rule ? keys.indexOf(studio.rule.value) : 0; onActivated:studio.edit(studio.rule,"value",keys[currentIndex]) }
                    }
                    GridLayout {
                        Layout.fillWidth:true; columns:2; columnSpacing:14; rowSpacing:12
                        visible:studio.rule && ["always","action","climax","failure","vibrator","piston"].indexOf(studio.rule.source)<0
                        NumberField { label:studio.rule && studio.rule.source === "heart" ? studio.t("范围下界 / BPM", "Minimum / BPM") : studio.t("范围下界 %", "Minimum %"); maximum:300; value:studio.rule ? studio.rule.minimum : 0; onEdited:value => studio.edit(studio.rule,"minimum",value) }
                        NumberField { label:studio.rule && studio.rule.source === "heart" ? studio.t("范围上界 / BPM", "Maximum / BPM") : studio.t("范围上界 %", "Maximum %"); maximum:300; value:studio.rule ? studio.rule.maximum : 100; onEdited:value => studio.edit(studio.rule,"maximum",value) }
                    }
                    GridLayout {
                        Layout.fillWidth:true; columns:2; columnSpacing:14; rowSpacing:12
                        visible:studio.rule && ["climax","failure"].indexOf(studio.rule.source)<0
                        NumberField { label:studio.t("条件稳定时间 / ms", "Debounce / ms"); maximum:10000; step:100; value:studio.rule ? studio.rule.stable_ms : 0; onEdited:value => studio.edit(studio.rule,"stable_ms",value) }
                        NumberField { label:studio.t("最短保持时间 / ms", "Minimum hold / ms"); maximum:10000; step:100; value:studio.rule ? studio.rule.hold_ms : 0; onEdited:value => studio.edit(studio.rule,"hold_ms",value) }
                        ColumnLayout { Layout.columnSpan:2; Caption { text:studio.t("切入方式", "Switch into this rule") }
 Choice { model:[studio.t("条件满足后切换", "Switch when ready"),studio.t("等待当前波形周期结束", "Wait for current cycle")]; currentIndex:studio.rule && studio.rule.transition === "cycle" ? 1 : 0; onActivated:studio.edit(studio.rule,"transition",currentIndex ? "cycle" : "immediate") } }
                    }
                    GridLayout {
                        Layout.fillWidth:true; columns:2; columnSpacing:14
                        visible:studio.rule && ["climax","failure"].indexOf(studio.rule.source)>=0
                        NumberField { label:studio.t("事件窗口 / ms", "Event window / ms"); minimum:100; maximum:5000; step:100; value:studio.rule ? studio.rule.duration_ms : 1300; onEdited:value => studio.edit(studio.rule,"duration_ms",value) }
                        NumberField { label:studio.t("冷却时间 / ms", "Cooldown / ms"); minimum:100; maximum:60000; step:100; value:studio.rule ? studio.rule.cooldown_ms : 5000; onEdited:value => studio.edit(studio.rule,"cooldown_ms",value) }
                    }
                    Caption { text:studio.t("事件规则立即抢占，事件窗口结束后重新匹配；单次波形播完即停止，即使事件窗口尚未结束。强度仍由个性化范围控制。", "Events preempt immediately and re-evaluate when the event window ends. Once mode stops when the waveform finishes, even within the event window. Personal settings control intensity.") }
                    Caption { visible:studio.rule && studio.rule.source === "climax"; text:studio.t("高潮规则固定最高优先级，不受普通规则优先级或保持时间阻挡。", "Climax always has highest priority, unaffected by ordinary rule priorities or hold times.") }
                }
            }
        }
    }
    ScrollView {
        id:bindingScroll; visible:studio.modeConfirmed && studio.independent && section.currentIndex === 2; Layout.fillWidth:true; Layout.fillHeight:true; contentWidth:availableWidth; clip:true
        ScrollBar.horizontal.policy:ScrollBar.AlwaysOff; ScrollBar.vertical:ThinScroll {}
        ColumnLayout {
            width:bindingScroll.availableWidth-12; spacing:14
            RowLayout {
                Layout.fillWidth:true
                ActionButton { objectName:"donorTemplate"; text:studio.t("档位控制强度", "Device-level intensity"); onClicked:studio.template(false) }
                ActionButton { objectName:"legacyTemplate"; text:studio.t("游戏数据控制强度", "Game-data intensity"); onClicked:studio.template(true) }
            }
            Caption { text:studio.t("先绑定各通道的振动器或活塞机，再选择强度来源。设备关闭时日常输出停止；高潮可抢占。波形可另用心率、动作等规则选择。", "Bind each channel to a device, then choose intensity sources. Ordinary output stops when that device is off; climax can preempt. Select waveforms separately using heart rate, actions or other rules.") }
            Repeater {
                model:["A","B"]
                delegate:Section {
                    id:bound; required property string modelData
                    property var config: { studio.revision; return studio.draft.mapping[modelData] }
                    visible:studio.draft.mapping.mode === "independent"
                    ColumnLayout {
                        anchors.fill:parent; spacing:10
                        RowLayout {
                            ThemedCheck { objectName:"channelEnabled"+bound.modelData; text:bound.modelData+studio.t(" 通道启用", " channel enabled"); checked:bound.config.enabled; onToggled:studio.edit(bound.config,"enabled",checked) }
                            Item { Layout.fillWidth:true }
                            ActionButton { text:studio.t("添加检测来源", "Add source"); enabled:bound.config.bindings.length<6; onClicked:studio.edit(bound.config,"bindings",bound.config.bindings.concat([studio.newBinding()])) }
                        }
                        Caption { text:studio.t("此通道绑定的设备", "Device bound to this channel") }
                        Choice { objectName:"boundDevice"+bound.modelData; model:[studio.t("振动器", "Vibrator"),studio.t("活塞机", "Piston"),studio.t("不绑定设备（通用映射）", "No device (general mapping)")]; currentIndex: { studio.revision; return ["vibrator","piston","none"].indexOf(bound.config.device) }
 onActivated:studio.edit(bound.config,"device",["vibrator","piston","none"][currentIndex]) }
                        Caption { text:studio.t("强度来源（波形由 A/B 规则独立决定）", "Intensity source (waveforms use separate A/B rules)") }
                        Repeater {
                            model: { studio.revision; return bound.config.bindings.length }
                            delegate:ColumnLayout {
                                id:sourceRow; required property int index
                                property var modelData: { studio.revision; return studio.draft.mapping[bound.modelData].bindings[index] }
                                readonly property string sourceKey: { studio.revision; return modelData.source }
                                Layout.fillWidth:true
                                RowLayout {
                                    Layout.fillWidth:true
                                    Choice { objectName:"intensitySource"+bound.modelData+sourceRow.index; model:studio.intensityNames; currentIndex:studio.intensityKeys.indexOf(sourceRow.sourceKey); onActivated:studio.edit(sourceRow.modelData,"source",studio.intensityKeys[currentIndex]) }
                                    ActionButton { text:studio.t("移除", "Remove"); enabled:bound.config.bindings.length>1; onClicked:studio.edit(bound.config,"bindings",bound.config.bindings.filter((x,i) => i !== sourceRow.index)) }
                                }
                                GridLayout {
                                    visible:["device","vibrator","piston","action_active"].indexOf(sourceRow.sourceKey)<0
                                    columns:3; Layout.fillWidth:true; columnSpacing:14
                                    NumberField { objectName:"sourceStart"+bound.modelData+sourceRow.index; label:sourceRow.sourceKey === "heart" ? studio.t("最低心率（BPM）", "Minimum heart rate (BPM)") : studio.intensityNames[studio.intensityKeys.indexOf(sourceRow.sourceKey)]+" · "+studio.t("最低值（%）", "Minimum (%)"); maximum:sourceRow.sourceKey === "heart" ? 299 : 99; value:sourceRow.sourceKey === "heart" ? sourceRow.modelData.low : sourceRow.modelData.input_start; onEdited:value => studio.edit(sourceRow.modelData,sourceRow.sourceKey === "heart" ? "low" : "input_start",value) }
                                    NumberField { objectName:"sourceFull"+bound.modelData+sourceRow.index; label:sourceRow.sourceKey === "heart" ? studio.t("最高心率（BPM）", "Maximum heart rate (BPM)") : studio.intensityNames[studio.intensityKeys.indexOf(sourceRow.sourceKey)]+" · "+studio.t("最高值（%）", "Maximum (%)"); maximum:sourceRow.sourceKey === "heart" ? 300 : 100; minimum:1; value:sourceRow.sourceKey === "heart" ? sourceRow.modelData.high : sourceRow.modelData.input_full; onEdited:value => studio.edit(sourceRow.modelData,sourceRow.sourceKey === "heart" ? "high" : "input_full",value) }
                                    ColumnLayout { Caption { text:studio.t("映射曲线", "Mapping curve") }
 Choice { model:[studio.t("线性", "Linear"),studio.t("缓慢上升", "Ease in"),studio.t("快速上升", "Ease out")]; currentIndex:["linear","ease_in","ease_out"].indexOf(sourceRow.modelData.curve); onActivated:studio.edit(sourceRow.modelData,"curve",["linear","ease_in","ease_out"][currentIndex]) } }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    ScrollView {
        id:legacyScroll; visible:studio.modeConfirmed && !studio.independent; Layout.fillWidth:true; Layout.fillHeight:true; contentWidth:availableWidth; clip:true
        ScrollBar.horizontal.policy:ScrollBar.AlwaysOff; ScrollBar.vertical:ThinScroll {}
        ColumnLayout {
            width:legacyScroll.availableWidth-12; spacing:14
            Caption { text:studio.t("按心率、动作及高潮／失败事件切换波形。这里的设置仅用于原版；A/B 通道规则仅用于 A/B 独立。强度范围和通道上限在「个性化范围」设置。", "Switch waveforms by heart rate, actions and climax/failure events. These settings apply to Original; A/B channel rules apply to Independent A/B. Set intensity ranges and channel caps in Intensity Range.") }
            RowLayout {
                Layout.fillWidth:true
                NumberField { objectName:"legacyStart"; label:studio.t("最低心率（BPM）", "Minimum heart rate (BPM)"); minimum:60; maximum:159; value:studio.draft.mapping.legacy.trigger_bpm; onEdited:value => studio.edit(studio.draft.mapping.legacy,"trigger_bpm",value) }
                NumberField { objectName:"legacyFull"; label:studio.t("最高心率（BPM）", "Maximum heart rate (BPM)"); minimum:61; maximum:160; value:studio.draft.mapping.legacy.full_bpm; onEdited:value => studio.edit(studio.draft.mapping.legacy,"full_bpm",value) }
            }
            Choice { objectName:"legacyWaveMode"; model:[studio.t("自动切换波形", "Automatic waveform selection"),studio.t("固定波形", "Fixed waveform")]; currentIndex:studio.draft.legacy_wave.mode === "fixed" ? 1 : 0; onActivated:studio.edit(studio.draft.legacy_wave,"mode",currentIndex ? "fixed" : "smart") }
            Choice { visible:studio.draft.legacy_wave.mode === "fixed"; model:studio.legacyOptions; textRole:"name"; currentIndex:studio.legacyOptions.findIndex(x => x.key === studio.draft.legacy_wave.fixed); onActivated:studio.edit(studio.draft.legacy_wave,"fixed",studio.legacyOptions[currentIndex].key) }
            GridLayout {
                visible:studio.draft.legacy_wave.mode === "smart"; Layout.fillWidth:true; columns:2; columnSpacing:16; rowSpacing:12
                Repeater {
                    model:["low","mid","high","action","peak"]
                    delegate:ColumnLayout {
                        required property string modelData
                        Caption { text:({low:studio.t("低心率波形", "Low heart-rate waveform"),mid:studio.t("中等心率波形", "Medium heart-rate waveform"),high:studio.t("高心率波形", "High heart-rate waveform"),action:studio.t("动作波形", "Action waveform"),peak:studio.t("高潮／失败波形", "Climax / failure waveform")})[modelData] }
                        Choice { model:studio.legacyOptions; textRole:"name"; currentIndex:studio.legacyOptions.findIndex(x => x.key === studio.draft.legacy_wave.zones[modelData]); onActivated:studio.edit(studio.draft.legacy_wave.zones,modelData,studio.legacyOptions[currentIndex].key) }
                    }
                }
            }
            Caption { text:studio.t("B 通道动作波形（未单独指定的动作使用默认推荐波形）", "B action waveform (unspecified actions use default recommended waveforms)") }
            ActionButton { objectName:"legacyActionPicker"; text:studio.legacyAction ? studio.controller.actionSummary(studio.legacyAction) : studio.t("搜索并选择动作", "Search and select an action"); onClicked:studio.openActions("legacy") }
            Choice { visible:studio.legacyAction !== ""; property var options:[{key:"recommended",name:studio.t("使用默认推荐波形", "Default recommended waveform")}].concat(studio.waveOptions); model:options; textRole:"name"; currentIndex: { studio.revision; return options.findIndex(x => x.key === (studio.draft.legacy_wave.actions[studio.legacyAction] || "recommended")) }
 onActivated: { if(options[currentIndex].key === "recommended") { delete studio.draft.legacy_wave.actions[studio.legacyAction]; studio.revision++ } else studio.edit(studio.draft.legacy_wave.actions,studio.legacyAction,options[currentIndex].key) } }
        }
    }
    UI.Dialog {
        id:actionPicker; objectName:"actionPicker"; parent:Overlay.overlay; anchors.centerIn:parent
        width:Math.min(680,parent.width-64); height:Math.min(600,parent.height-64); modal:true; padding:18
        background:Rectangle { color:studio.surface; radius:10; border.color:studio.line }
        title:studio.t("选择游戏动作", "Choose game actions")
        contentItem:ColumnLayout {
            ThemedField { id:actionSearch; objectName:"actionSearch"; searchField:true; Layout.fillWidth:true; placeholderText:studio.t("搜索中文动作名", "Search actions") }
            Caption { text:studio.pickerTarget === "rule" ? studio.t("可多选；不勾选任何项表示匹配所有动作。", "Select multiple; no selection matches all actions.") : studio.t("选择要单独设置波形的动作。", "Choose an action to customize its waveform.") }
            ListView {
                Layout.fillWidth:true; Layout.fillHeight:true; clip:true
                model:studio.controller.actionChoices.filter(x => (x.label+" "+x.key).toLowerCase().indexOf(actionSearch.text.toLowerCase()) >= 0)
                delegate:ThemedCheck {
                    required property var modelData; width:ListView.view.width; text:modelData.label
                    objectName:"actionChoice"+modelData.key
                    checked:studio.pickedActions.indexOf(modelData.key)>=0
                    onToggled: {
                        if(studio.pickerTarget === "legacy") { studio.legacyAction=modelData.key; actionPicker.close() }
                        else studio.pickedActions=checked ? studio.pickedActions.concat([modelData.key]) : studio.pickedActions.filter(x => x !== modelData.key)
                    }
                }
                ScrollBar.vertical:ThinScroll {}
            }
            RowLayout {
                ActionButton { visible:studio.pickerTarget === "rule"; text:studio.t("清空选择", "Clear selection"); onClicked:studio.pickedActions=[] }
                Item { Layout.fillWidth:true }
                ActionButton { text:studio.t("取消", "Cancel"); onClicked:actionPicker.close() }
                ActionButton { objectName:"applyActionChoices"; visible:studio.pickerTarget === "rule"; text:studio.t("应用选择", "Apply selection"); primary:true; onClicked:{ studio.edit(studio.rule,"value",studio.pickedActions.join("|")); actionPicker.close() } }
            }
        }
    }
    Caption { objectName:"workbenchFeedback"; visible:studio.modeConfirmed; text:studio.message || (studio.dirty ? studio.t("玩法设置有未保存修改", "Unsaved gameplay changes") : studio.t("已保存", "Saved")); color:studio.failed ? studio.danger : studio.secondary }
    UI.Dialog {
        id:discard; objectName:"discardGameplayChanges"; anchors.centerIn:parent; width:460; modal:true; title:studio.t("有未保存的修改", "Unsaved changes")
        palette.button:studio.surface; palette.buttonText:studio.ink
        contentItem:Label { color:studio.ink; text:studio.t("关闭将放弃玩法设置草稿。", "Closing discards the gameplay draft."); wrapMode:Text.Wrap }
        unsavedChanges:true; standardButtons:Dialog.Cancel | Dialog.Discard
        onRejected:studio.closeCancelled()
        onDiscarded:{ studio.reload();studio.closeRequested() }
    }
    component ThemedField: UI.TextField { }
    component ThemedCheck: UI.CheckBox { }
    component WorkbenchTab: UI.TabButton { }
    component ThinScroll: UI.ScrollBar { }
    component Caption: UI.Caption { }
    component ActionButton: UI.Button { }
    component Choice: UI.ComboBox { Layout.fillWidth:true }
    component NumberField: UI.NumberField { }
    component Section: UI.Section { }

}
