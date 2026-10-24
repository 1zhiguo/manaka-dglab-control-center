import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: "ovcChannelDialog"
    required property var theme
    required property var workbench
    readonly property var page: workbench
    parent: Overlay.overlay; anchors.centerIn: parent
    popupType: Popup.Item
    width: Math.min(1160, parent.width-56); height: Math.min(780, parent.height-56)
    padding: 24; modal: true
    background: Rectangle { radius:22;color:dialog.theme.panel;border.color:dialog.theme.border }
    contentItem: ColumnLayout {
        spacing: 12
        RowLayout {
            Layout.fillWidth:true
            Label {Layout.fillWidth:true;text:page.tr("通道策略 · ","Channel Strategy · ")+page.channel;color:dialog.theme.fg;font.pixelSize:22;font.bold:true}
            CheckBox {text:page.tr("启用此通道","Use Channel");checked:page.policy.enabled||false;onClicked:page.setPolicy("enabled",checked)}
            WorkbenchButton {theme:dialog.theme;text:page.tr("完成配置","Done");onClicked:dialog.close()}
        }
        RowLayout {
            Layout.fillWidth:true;spacing:12
            WorkbenchButton {theme:dialog.theme;Layout.fillWidth:true;Layout.preferredHeight:66;highlighted:page.policy.mode==="sync";text:page.tr("同步游戏振动器强度","Sync Game Vibrator");onClicked:page.selectCategory("sync")}
            WorkbenchButton {theme:dialog.theme;Layout.fillWidth:true;Layout.preferredHeight:66;highlighted:page.policy.mode!=="sync";text:page.tr("自定义","Custom");onClicked:page.selectCategory("custom")}
        }
        Rectangle {
            visible:page.policy.mode==="sync";Layout.fillWidth:true;Layout.fillHeight:true
            radius:16;color:dialog.theme.panel2;border.color:dialog.theme.cyan
            ColumnLayout {
                anchors.fill:parent;anchors.margins:24;spacing:18
                Label {text:page.tr("跟随游戏实际档位","Follow the In-game Mode");color:dialog.theme.fg;font.pixelSize:20;font.bold:true}
                Label {Layout.fillWidth:true;wrapMode:Text.Wrap;text:page.tr("游戏振动器关闭时输出为 0。随机档跟随游戏自动切换到的实际低／高档，不额外生成随机强度。","Game Off outputs zero. Random follows the game's actual Low/High changes, without a separate random strength.");color:dialog.theme.muted;font.pixelSize:14}
                RowLayout {Layout.fillWidth:true
                    Repeater {model:[{name:page.tr("低档","Low"),value:page.draft.low},{name:page.tr("高档","High"),value:page.draft.high},{name:page.tr("硬上限","Cap"),value:page.draft.hard_cap}]
                        Rectangle {required property var modelData;Layout.fillWidth:true;implicitHeight:96;radius:13;color:dialog.theme.panel
                            Column {anchors.centerIn:parent;spacing:8;Label{text:modelData.name;color:dialog.theme.muted;font.pixelSize:13}Label{text:modelData.value||0;color:dialog.theme.cyan;font.pixelSize:25;font.bold:true}}
                        }
                    }
                }
                VibrationPreview {Layout.fillWidth:true;Layout.fillHeight:true;points:[100,100,100,100];lineColor:dialog.theme.cyan}
                Label {Layout.fillWidth:true;wrapMode:Text.Wrap;text:page.tr("档位与硬上限可在工作台上方的「档位 / 上限」调整。此通道与另一通道独立。","Change levels and cap under Levels / Cap. This channel is independent of the other channel.");color:dialog.theme.muted;font.pixelSize:12}
            }
        }
        RowLayout {
            visible:page.policy.mode!=="sync";Layout.fillWidth:true;spacing:8
            Repeater {model:[{key:"action",name:page.tr("动作分配","Actions")},{key:"random",name:page.tr("随机轮播","Random")},{key:"fixed",name:page.tr("固定波形","Fixed")}]
                WorkbenchButton {required property var modelData;theme:dialog.theme;text:modelData.name;highlighted:page.policy.mode===modelData.key;onClicked:page.setPolicy("mode",modelData.key)}
            }
            Item {Layout.fillWidth:true}
            Label {visible:page.policy.mode!=="action";text:page.tr("强度","Strength");color:dialog.theme.fg}
            WorkbenchSpinBox {visible:page.policy.mode!=="action";theme:dialog.theme;from:0;to:page.draft.hard_cap||0;stepSize:10;value:page.policy.strength||0;onValueModified:page.setPolicy("strength",value)}
            Label {visible:page.policy.mode==="random";text:page.tr("间隔秒数","Seconds");color:dialog.theme.muted}
            WorkbenchSpinBox {visible:page.policy.mode==="random";theme:dialog.theme;implicitWidth:110;from:1;to:60;value:page.policy.random_seconds||4;onValueModified:page.setPolicy("random_seconds",value)}
        }
        Label {
            visible:page.policy.mode!=="sync";Layout.fillWidth:true;wrapMode:Text.Wrap;font.pixelSize:12;color:dialog.theme.muted
            text:page.policy.mode==="action"?page.tr("为动作选择波形、随机池或同步游戏。悬停预览；未配置动作默认同步游戏。","Choose a waveform, random pool or game sync per action. Hover to preview; unmapped actions follow the game."):page.policy.mode==="random"?page.tr("点击卡片加入或移出随机池。只从选中的波形轮播。","Click cards to add or remove them from the random pool."):page.tr("选择一个波形持续使用。悬停只预览，不发送输出。","Select one waveform. Hover previews never send output.")
        }
        GridView {
            visible:page.policy.mode!=="sync"&&page.policy.mode!=="action";Layout.fillWidth:true;Layout.fillHeight:true
            cellWidth:width/3;cellHeight:175;clip:true;model:page.catalog
            delegate:Rectangle {
                id:tile;required property var modelData
                readonly property bool selected:page.policy.mode==="random"?(page.policy.random_waves||[]).indexOf(modelData.key)>=0:page.policy.wave===modelData.key
                width:GridView.view.cellWidth-10;height:165;radius:13;color:tile.selected?Qt.rgba(dialog.theme.accent.r,dialog.theme.accent.g,dialog.theme.accent.b,.13):dialog.theme.panel2;border.color:tile.selected?dialog.theme.accent:dialog.theme.border
                ColumnLayout {anchors.fill:parent;anchors.margins:14;spacing:8
                    Label {Layout.fillWidth:true;text:tile.modelData.name;color:dialog.theme.fg;font.pixelSize:14;font.bold:true;elide:Text.ElideRight}
                    VibrationPreview {Layout.fillWidth:true;Layout.fillHeight:true;points:tile.modelData.points;lineColor:tile.modelData.color;animate:waveHover.hovered}
                    Label {text:tile.selected?page.tr("已选择","Selected"):page.tr("点击选择 · 双击编辑副本","Select · double-click to edit a copy");color:tile.selected?dialog.theme.accent:dialog.theme.muted;font.pixelSize:11}
                }
                HoverHandler{id:waveHover}
                MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:page.chooseWave(tile.modelData.key);onDoubleClicked:page.editWave(tile.modelData.key)}
            }
            ScrollBar.vertical:ScrollBar{}
        }
        RowLayout {
            visible:page.policy.mode==="action";Layout.fillWidth:true;spacing:8
            TextField {Layout.fillWidth:true;implicitHeight:42;placeholderText:page.tr("搜索动作","Search Actions");onTextChanged:page.query=text;color:dialog.theme.fg;leftPadding:14;background:Rectangle{radius:13;color:dialog.theme.panel2;border.color:dialog.theme.border}}
            Repeater {model:[{key:"all",name:page.tr("全部","All")},{key:"rhythmic",name:page.tr("规律动作","Rhythmic")},{key:"static",name:page.tr("静态姿势","Static")},{key:"off",name:page.tr("普通交互","Interaction")}]
                WorkbenchButton {required property var modelData;theme:dialog.theme;implicitWidth:100;text:modelData.name;highlighted:page.actionFilter===modelData.key;onClicked:page.actionFilter=modelData.key}
            }
        }
        RowLayout {
            visible:page.policy.mode==="action";Layout.fillWidth:true;spacing:8
            Label {text:page.tr("游戏动作","Game Action");color:dialog.theme.muted;Layout.preferredWidth:170;font.pixelSize:11}
            Label {text:page.tr("分类","Type");color:dialog.theme.muted;Layout.preferredWidth:76;font.pixelSize:11}
            Label {text:page.tr("波形预览","Envelope Preview");color:dialog.theme.muted;Layout.fillWidth:true;font.pixelSize:11}
            Label {text:page.tr("使用波形","Assignment");color:dialog.theme.muted;Layout.preferredWidth:250;font.pixelSize:11}
            Label {text:page.tr("强度","Intensity");color:dialog.theme.muted;Layout.preferredWidth:110;font.pixelSize:11}
        }
        ListView {
            visible:page.policy.mode==="action";Layout.fillWidth:true;Layout.fillHeight:true;clip:true;spacing:8;model:page.ready?page.actions:[]
            delegate:Rectangle {
                id:actionRow;required property var modelData
                readonly property var rule:page.rule(modelData.key)
                readonly property var selected:page.actionOption(rule)
                width:ListView.view.width;height:82;radius:13;color:dialog.theme.panel2;border.color:rule.mode!=="sync"?dialog.theme.violet:dialog.theme.border
                HoverHandler{id:rowHover}
                RowLayout {anchors.fill:parent;anchors.margins:10;spacing:8
                    Label {Layout.preferredWidth:160;text:actionRow.modelData.name;color:dialog.theme.fg;elide:Text.ElideRight;font.pixelSize:12;ToolTip.text:actionRow.modelData.key;ToolTip.visible:rowHover.hovered}
                    Label {Layout.preferredWidth:76;text:actionRow.modelData.styleLabel;color:dialog.theme.muted;font.pixelSize:11;elide:Text.ElideRight}
                    VibrationPreview {Layout.fillWidth:true;Layout.minimumWidth:50;Layout.preferredHeight:52;points:actionRow.selected.points;lineColor:actionRow.selected.color;cycles:3;animate:rowHover.hovered}
                    OvcWavePicker {objectName:"ovcActionPicker_"+actionRow.modelData.key;theme:dialog.theme;Layout.preferredWidth:250;model:page.actionOptions;currentIndex:page.actionOptionIndex(actionRow.rule);onActivated:page.chooseAction(actionRow.modelData.key,model[currentIndex])}
                    WorkbenchSpinBox {theme:dialog.theme;Layout.preferredWidth:110;from:0;to:page.draft.hard_cap||0;stepSize:10;value:Math.min(actionRow.rule.strength,page.draft.hard_cap||0);enabled:actionRow.rule.mode==="wave"||actionRow.rule.mode==="random";onValueModified:page.setRule(actionRow.modelData.key,"strength",value)}
                }
            }
            ScrollBar.vertical:ScrollBar{}
        }
        Label {Layout.fillWidth:true;text:page.tr("修改保留在草稿中，回到工作台点击「保存负鼠配置」后应用。","Changes stay in the draft. Save Opossum in the workbench to apply them.");wrapMode:Text.Wrap;color:dialog.theme.amber;font.pixelSize:11}
    }
}
