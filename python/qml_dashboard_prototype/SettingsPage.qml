import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: page
    objectName:"settingsPage"
    required property var theme
    signal hudSettingsRequested()
    signal tutorialRequested()
    clip:true;contentWidth:availableWidth
    function tr(zh,en){return backend.language==="en"?en:zh}
    ColumnLayout {
        width:page.availableWidth;spacing:18
        Rectangle {
            Layout.fillWidth:true;implicitHeight:200;radius:22;color:page.theme.panel;border.color:page.theme.border
            ColumnLayout {anchors.fill:parent;anchors.margins:24;spacing:16
                Label {text:page.tr("外观与语言","Appearance & Language");color:page.theme.fg;font.pixelSize:19;font.bold:true}
                GridLayout {columns:2;Layout.fillWidth:true;columnSpacing:30;rowSpacing:14
                    Label {text:page.tr("界面语言","Interface Language");color:page.theme.fg;Layout.preferredWidth:160}
                    ThemedComboBox {objectName:"settingsLanguage";theme:page.theme;Layout.fillWidth:true;model:["简体中文","English"];currentIndex:backend.language==="en"?1:0;onActivated:backend.setLanguage(currentIndex===1?"en":"zh")}
                    Label {text:page.tr("主题","Theme");color:page.theme.fg}
                    ThemedComboBox {objectName:"settingsTheme";theme:page.theme;Layout.fillWidth:true;model:[page.tr("夜间 · 紫灰","Dark · Plum"),page.tr("日间 · 浅色","Light")];currentIndex:backend.theme==="light"?1:0;onActivated:backend.setTheme(currentIndex===1?"light":"dark")}
                }
            }
        }
        Rectangle {
            Layout.fillWidth:true;implicitHeight:165;radius:22;color:page.theme.panel;border.color:page.theme.border
            ColumnLayout {anchors.fill:parent;anchors.margins:24;spacing:14
                Label {text:page.tr("游戏 HUD","In-game HUD");color:page.theme.fg;font.pixelSize:19;font.bold:true}
                RowLayout {Layout.fillWidth:true
                    CheckBox {text:page.tr("显示游戏内 HUD","Show In-game HUD");checked:backend.gameHudEnabled;onClicked:backend.setGameHudEnabled(checked)}
                    Item {Layout.fillWidth:true}
                    Button {text:page.tr("内容、大小与位置","HUD Layout");onClicked:page.hudSettingsRequested()}
                }
                Label {Layout.fillWidth:true;wrapMode:Text.Wrap;text:backend.hudPluginHint;color:page.theme.muted;font.pixelSize:12}
            }
        }
        Rectangle {
            Layout.fillWidth:true;implicitHeight:195;radius:22;color:page.theme.panel;border.color:page.theme.border
            ColumnLayout {anchors.fill:parent;anchors.margins:24;spacing:14
                Label {text:page.tr("帮助与本地文件","Help & Local Files");color:page.theme.fg;font.pixelSize:19;font.bold:true}
                Flow {Layout.fillWidth:true;spacing:12
                    Button {text:page.tr("重新查看新手教程","Quick Start");onClicked:page.tutorialRequested()}
                    Button {text:page.tr("打开自定义波形目录","Waveform Folder");onClicked:backend.openWaveformLibraryFolder()}
                    Button {text:page.tr("配置与诊断目录","Diagnostics");onClicked:backend.openAppDataFolder()}
                }
                Label {Layout.fillWidth:true;wrapMode:Text.Wrap;text:page.tr("设备强度、动作规则和授权保留在各自工作台。外观与 HUD 设置不会启动或改变设备输出。","Strength, action rules and authorization remain in each workbench. Appearance and HUD settings do not start or change device output.");color:page.theme.muted;font.pixelSize:12}
            }
        }
        Label {text:"Manaka × DG-LAB · "+backend.version;color:page.theme.muted;font.pixelSize:12}
    }
}
