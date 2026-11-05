import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
 id:activity
 required property var theme
 property string prefix:"ble"
 Layout.fillWidth:true
            RowLayout {
                visible:backend.bleBusy||backend.bleScanCaption.length>0
                Layout.fillWidth:true;spacing:10
                Image {
                    id:hourglassIcon;objectName:activity.prefix+"Hourglass"
                    Layout.preferredWidth:24;Layout.preferredHeight:24
                    visible:backend.bleBusy
                    source:Qt.resolvedUrl("assets/icons/hourglass.svg")
                    sourceSize.width:32;sourceSize.height:32
                    transformOrigin:Item.Center
                    RotationAnimation {
                        target:hourglassIcon;property:"rotation";from:0;to:180
                        duration:1100;loops:Animation.Infinite;easing.type:Easing.InOutCubic
                        running:backend.bleBusy&&hourglassIcon.visible
                        onStopped:hourglassIcon.rotation=0
                    }
                }
                Label {
                    Layout.fillWidth:true;wrapMode:Text.Wrap;font.pixelSize:12;color:activity.theme.cyan
                    text:backend.bleScanCaption
                }
            }
            ProgressBar {
                id:scanProgress;objectName:activity.prefix+"ScanProgress"
                visible:backend.bleBusy||backend.bleScanProgress>0
                Layout.fillWidth:true;Layout.preferredHeight:6
                from:0;to:1;value:backend.bleScanProgress
                indeterminate:backend.bleBusy&&!backend.bleScanning
                background:Rectangle {radius:3;color:activity.theme.panel2}
                contentItem:Item {
                    id:progressTrack
                    property real movingX:0
                    implicitHeight:6;clip:true
                    Rectangle {
                        id:progressFill;objectName:activity.prefix+"ProgressFill"
                        height:parent.height;radius:3;color:activity.theme.cyan
                        width:scanProgress.indeterminate?parent.width*.28:parent.width*scanProgress.position
                        x:scanProgress.indeterminate?progressTrack.movingX:0
                    }
                    NumberAnimation {
                        target:progressTrack;property:"movingX"
                        running:scanProgress.indeterminate&&scanProgress.visible
                        from:-progressTrack.width*.28;to:progressTrack.width
                        duration:1100;loops:Animation.Infinite
                    }
                }
            }

}
