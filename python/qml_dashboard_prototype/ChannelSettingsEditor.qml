import QtQuick
import "components" as UI
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: editor
    objectName: "channelEditor"
    required property var controller
    property var draft: JSON.parse(JSON.stringify(controller.channelSettings))
    property string savedRevision: controller.configurationRevision
    property string savedDraft: JSON.stringify(draft)
    property int revision: 0
    property var channelKeys: ["A", "B"]
    property string saveMessage: ""
    property var preview: ({})
    property bool independent: { revision; return draft.mode === "independent" }
    readonly property bool dirty: { revision; return JSON.stringify(draft) !== savedDraft }
    readonly property string validationError: { revision; return controller.validateChannelSettings(JSON.stringify(draft)).error }
    readonly property bool dark: controller.theme !== "light"
    readonly property color surface: UI.Theme.surfaceRaised
    readonly property color line: UI.Theme.borderDecorative
    readonly property color ink: UI.Theme.textPrimary
    readonly property color secondary: UI.Theme.textSecondary
    readonly property color accent: UI.Theme.accent
    readonly property color danger: UI.Theme.danger
    property var sources: [
        {key:"vibrator",label:t("振动器实际档位", "Effective vibrator mode")}, {key:"piston",label:t("活塞实际档位", "Effective piston mode")},
        {key:"device",label:t("绑定设备的档位比例", "Bound device level")}, {key:"action_active",label:t("动作发生", "Action active")},
        {key:"heart",label:t("心率", "Heart rate")}, {key:"action",label:t("动作进度", "Action progress")},
        {key:"ecstasy",label:t("兴奋度", "Ecstasy")}, {key:"npc_alert",label:t("NPC 警觉度", "NPC alert")}
    ]
    signal closeRequested()
    signal closeCancelled()
    function t(zh, en) { return controller.language === "en" ? en : zh }
    function newBinding() { return {source:"vibrator",weight:1,low:90,high:160,weak:30,medium:50,strong:70,wave:"auto",phase_ms:0,input_start:0,input_full:100,curve:"linear"} }
    function edit(target, key, value) { target[key]=value; revision++; saveMessage=""; preview=({}) }
    function reload() {
        channelKeys=[]
        draft=JSON.parse(JSON.stringify(controller.channelSettings))
        savedDraft=JSON.stringify(draft); savedRevision=controller.configurationRevision; revision++; saveMessage=""; preview=({})
        channelKeys=["A", "B"]
    }
    Component.onCompleted: reload()
    Connections { target: editor.controller; function onConfigChanged() { if (!editor.dirty) editor.reload() } }
    function applyChanges(confirmed) {
        forceActiveFocus()
        if (validationError) return false
        if (!confirmed) {
            let old=controller.channelSettings
            if (draft.A.hard_cap>Math.max(30,old.A.hard_cap) || draft.B.hard_cap>Math.max(30,old.B.hard_cap)) {
                confirm.open(); return false
            }
        }
        if (!controller.saveIntensitySettings(JSON.stringify(draft),savedRevision,confirmed)) return false
        reload()
        saveMessage=t("已保存，等待新的游戏数据。", "Saved. Waiting for fresh game data.")
        return true
    }
    function requestClose() {
        forceActiveFocus()
        if (dirty) discard.open()
        else closeRequested()
    }
    spacing: 12
    focus: true
    Keys.onEscapePressed: requestClose()

    component Caption: UI.Caption { }
    component ActionButton: UI.Button { }
    component Choice: UI.ComboBox { Layout.fillWidth:true }
    component NumberField: UI.NumberField { }
    component Section: UI.Section { }
    RowLayout {
        Layout.fillWidth: true
        ColumnLayout {
            Layout.fillWidth: true
            Caption { text: editor.t("只调整输出强度。检测内容、动作和波形切换请在玩法设置中调整。", "Adjust output strength here. Configure detection, actions and wave switching in Gameplay settings.") }
        }

    }
    GridLayout {
        columns:3; Layout.fillWidth:true; columnSpacing:14
        NumberField { objectName:"A-hard_cap"; maximum:200; label:editor.t("A 通道硬上限", "A safety cap"); value:editor.draft.A.hard_cap; onEdited:value => editor.edit(editor.draft.A,"hard_cap",value) }
        NumberField { objectName:"B-hard_cap"; maximum:200; label:editor.t("B 通道硬上限", "B safety cap"); value:editor.draft.B.hard_cap; onEdited:value => editor.edit(editor.draft.B,"hard_cap",value) }
        ColumnLayout {
            Layout.fillWidth:true
            Caption { text:editor.t("同步强度（保留各自上限）", "Intensity sync (separate limits)") }
            Choice { objectName:"intensitySync"; model:[editor.t("关闭 · 分别计算", "Off · independent"),editor.t("A 同步到 B", "A to B"),editor.t("B 同步到 A", "B to A")]; currentIndex:["off","A_to_B","B_to_A"].indexOf(editor.draft.intensity_sync); onActivated:editor.edit(editor.draft,"intensity_sync",["off","A_to_B","B_to_A"][currentIndex]) }
        }
    }
    Caption { text:editor.t("A/B 上限分别生效，设备上限仍会限制各自输出。同步只复制强度，不复制波形；通道关闭或无波形时保持停止。", "Each channel retains its own software and device limits. Sync copies intensity, not waveforms; disabled channels or channels without a waveform remain stopped.") }
    RowLayout {
        Layout.fillWidth: true
        TabBar {
            id: tabs; objectName: "channelTabs"; visible: editor.independent; Layout.preferredWidth: 260
            Repeater { model: ["A","B"]; UI.TabButton {
                required property string modelData; text:modelData+editor.t(" 通道", " channel")
            } }
        }
        Caption { text: editor.independent ? editor.controller.channelSourceStatus : editor.t("原版心率 / 动作模式 · 可在玩法设置切换 A/B 独立模式", "Original heart / action mode · Switch modes in Gameplay settings") }
    }
    ScrollView {
        id: channelScroll; objectName: "channelScroll"
        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical: UI.ScrollBar { objectName:"personalScrollBar" }
        ColumnLayout {
            width: channelScroll.availableWidth-12; spacing: 14
            Section {
                visible: !editor.independent
                RowLayout {
                    anchors.fill:parent; spacing:16
                    NumberField { objectName:"legacy-min_strength"; maximum:200; label:editor.t("日常最低强度", "Ordinary minimum intensity"); value:editor.draft.legacy.min_strength; onEdited:value => editor.edit(editor.draft.legacy,"min_strength",value) }
                    NumberField { objectName:"legacy-output_max"; maximum:200; label:editor.t("日常最高强度", "Ordinary maximum intensity"); value:editor.draft.legacy.output_max; onEdited:value => editor.edit(editor.draft.legacy,"output_max",value) }
                }
            }
            Caption { visible:!editor.independent; text:editor.t("原版保持原有心率/动作强度曲线、Climax、失败事件和前五秒峰值 +15 规则。这里只调整日常范围及 A/B 最大强度。", "Original mode retains the original heart/action curves, Climax, failure event and previous-five-second peak +15 rule. Adjust ordinary range and separate caps here.") }
            Repeater {
                model: editor.channelKeys
                delegate: ColumnLayout {
                    id: channel
                    required property string modelData
                    property var config: editor.draft[modelData]
                    visible: editor.independent && tabs.currentIndex === (modelData === "A" ? 0 : 1)
                    Layout.fillWidth: true; spacing: 14
                    Section {
                        GridLayout {
                            anchors.fill: parent; columns:3; columnSpacing:16; rowSpacing:12
                            Repeater {
                                model: [{key:"minimum",zh:"日常最低强度",en:"Ordinary minimum intensity",min:0,dec:0},{key:"maximum",zh:"日常最高强度",en:"Ordinary maximum intensity",min:0,dec:0},{key:"attack",zh:"强度上升速度（每秒）",en:"Intensity rise per second",min:0.1,dec:1},{key:"release",zh:"强度下降速度（每秒）",en:"Intensity fall per second",min:0.1,dec:1}]
                                delegate: NumberField {
                                    required property var modelData
                                    objectName:channel.modelData+"-"+modelData.key
                                    maximum:["minimum","maximum"].indexOf(modelData.key)>=0 ? 200 : 100; label:editor.t(modelData.zh,modelData.en); minimum:modelData.min; decimals:modelData.dec; step:modelData.dec ? 0.1 : 1
                                    value:channel.config[modelData.key]; onEdited:value => editor.edit(channel.config,modelData.key,value)
                                }
                            }
                            Caption { text: { editor.revision; return editor.t("最终软件上限：", "Effective software cap: ")+channel.config.hard_cap+editor.t("\n设备上限仍然生效。", "\nDevice limits also apply.") } }
                        }
                    }
                    RowLayout {
                        Caption { text:editor.t("多个强度来源的计算方式", "Combine intensity sources") }
                        Choice { Layout.maximumWidth:300; model:[editor.t("取最大值", "Maximum"),editor.t("加权相加", "Weighted sum")]; currentIndex:channel.config.combine === "weighted" ? 1 : 0; onActivated:editor.edit(channel.config,"combine",currentIndex ? "weighted" : "max") }
                    }
                    Repeater {
                        model:channel.config.bindings.length
                        delegate: Section {
                            id: bindingRow; objectName:"sourceBinding"
                            required property int index
                            property var modelData: { editor.revision; return editor.draft[channel.modelData].bindings[index] }
                            readonly property bool discrete:modelData.source === "vibrator" || modelData.source === "piston" || modelData.source === "device"
                            ColumnLayout {
                                anchors.fill:parent; spacing:10
                                Label { text:(editor.sources.find(x => x.key === bindingRow.modelData.source) || {}).label; color:editor.ink; font.bold:true }
                                GridLayout {
                                    Layout.fillWidth:true; columns:4; columnSpacing:12
                                    NumberField { label:editor.t("强度权重 %", "Strength weight %"); maximum:1000; value:bindingRow.modelData.weight*100; onEdited:value => editor.edit(bindingRow.modelData,"weight",value/100) }
                                    NumberField { visible:bindingRow.discrete; label:editor.t("弱档比例 %", "Weak %"); value:bindingRow.modelData.weak; onEdited:value => editor.edit(bindingRow.modelData,"weak",value) }
                                    NumberField { objectName:"mediumMode"+channel.modelData+bindingRow.index; visible:bindingRow.modelData.source === "piston" || (bindingRow.modelData.source === "device" && channel.config.device === "piston"); label:editor.t("中档比例 %", "Medium %"); value:bindingRow.modelData.medium; onEdited:value => editor.edit(bindingRow.modelData,"medium",value) }
                                    NumberField { visible:bindingRow.discrete; label:editor.t("强档比例 %", "Strong %"); value:bindingRow.modelData.strong; onEdited:value => editor.edit(bindingRow.modelData,"strong",value) }
                                }
                            }
                        }
                    }
                    Section {
                        ColumnLayout {
                            anchors.fill:parent; spacing:10
                            Caption { text:editor.t("事件强度以日常最高强度为基准；事件开关与持续时间由玩法设置中的规则决定。", "Event strength is a percentage of ordinary maximum. Gameplay rules control activation and timing.") }
                            RowLayout {
                                Layout.fillWidth:true; spacing:16
                                NumberField { label:editor.t("高潮事件（%）", "Climax event (%)"); value:channel.config.climax.percent; onEdited:value => editor.edit(channel.config.climax,"percent",value) }
                                NumberField { label:editor.t("失败事件（%）", "Failure event (%)"); value:channel.config.failure.percent; onEdited:value => editor.edit(channel.config.failure,"percent",value) }
                            }
                        }
                    }
                }
            }
        }
    }
    Rectangle { Layout.fillWidth: true; height: 1; color: editor.line }
    Caption {
        objectName: "settingsFeedback"
        text: editor.validationError || editor.saveMessage || (editor.dirty ? editor.t("有未保存的修改", "Unsaved changes") : editor.t("已保存", "Saved"))
        color: editor.validationError ? editor.danger : editor.dirty ? editor.accent : editor.secondary
    }
    RowLayout {
        Layout.fillWidth: true; spacing: 10
        ActionButton { objectName:"reloadChannels"; text:editor.t("恢复已保存", "Reload saved"); enabled:editor.dirty; onClicked:editor.reload() }
        Item { Layout.fillWidth:true }
        ActionButton { objectName:"closeChannels"; text:editor.t("返回控制中心", "Back to dashboard"); onClicked:editor.requestClose() }
        ActionButton { objectName:"saveChannels"; text:editor.t("应用并保存", "Apply and save"); primary:true; enabled:editor.dirty && !editor.validationError; onClicked:editor.applyChanges(false) }
    }
    UI.Dialog {
        id: confirm; objectName:"capConfirmation"
        anchors.centerIn: parent; width:Math.min(editor.width-40,520); modal:true
        title:editor.t("提高硬上限", "Raise safety caps")
        contentItem: Label { color:editor.ink; text:editor.t("硬上限将提高到 30 以上。确认已校准个人可承受范围后再保存。", "Safety caps will exceed 30. Confirm your calibrated limits before saving."); wrapMode:Text.Wrap; font.pixelSize:UI.Theme.bodySize }
        footer: UI.DialogButtonBox {
            ActionButton { text:editor.t("取消", "Cancel"); DialogButtonBox.buttonRole:DialogButtonBox.RejectRole }
            ActionButton { text:editor.t("确认并保存", "Confirm and save"); DialogButtonBox.buttonRole:DialogButtonBox.AcceptRole }
        }
        onAccepted:editor.applyChanges(true)
    }
    UI.Dialog {
        id: discard; objectName:"discardChannelChanges"
        anchors.centerIn:parent; width:Math.min(editor.width-40,460); modal:true
        title:editor.t("有未保存的修改", "Unsaved changes")
        onRejected: editor.closeCancelled()
        contentItem: Label { color:editor.ink; text:editor.t("关闭将放弃本次修改，已保存的设置不受影响。", "Closing discards these edits. Your saved settings will remain intact."); wrapMode:Text.Wrap; font.pixelSize:UI.Theme.bodySize }
        footer: UI.DialogButtonBox {
            ActionButton { objectName:"keepChannelEdits"; text:editor.t("继续编辑", "Keep editing"); DialogButtonBox.buttonRole:DialogButtonBox.RejectRole }
            ActionButton { objectName:"discardChannelEdits"; text:editor.t("放弃修改", "Discard changes"); DialogButtonBox.buttonRole:DialogButtonBox.DestructiveRole; onClicked: { editor.reload(); discard.close(); editor.closeRequested() } }
        }
    }
}
