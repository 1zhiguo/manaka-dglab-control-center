import QtQuick

Item {
    id: hud
    required property var options
    property var strengths: [18,24,10,20]
    readonly property int count: (Number(!!options.show_pulse)+Number(!!options.show_ovc))*(Number(!!options.show_a)+Number(!!options.show_b))
    implicitWidth: 696; implicitHeight: 72
    Rectangle {anchors.fill:parent;color:Qt.rgba(.08,.025,.08,Number(hud.options.opacity)/100);radius:3}
    Rectangle {anchors.top:parent.top;width:parent.width;height:1;color:"#F04C9E";opacity:.65}
    Rectangle {anchors.bottom:parent.bottom;width:parent.width;height:1;color:"#D9B4E6";opacity:.3}
    Row {
        anchors.fill:parent;anchors.margins:6;spacing:10
        Repeater {model:4
            delegate:Item {
                id:cell;required property int index
                readonly property color accent: index%2===0?"#FF459F":"#C9A8FF"
                visible:(index<2?hud.options.show_pulse:hud.options.show_ovc)&&(index%2===0?hud.options.show_a:hud.options.show_b)
                width:(parent.width-Math.max(0,hud.count-1)*10)/Math.max(1,hud.count);height:parent.height
                Rectangle {width:2;height:parent.height;color:cell.accent}
                Text {x:8;y:1;text:(cell.index%2===0?"A":"B")+(cell.index<2?" / PULSE":" / OVC");color:cell.accent;font.bold:true;font.pixelSize:Math.max(8,hud.height*.17)}
                Text {visible:hud.options.show_numbers;anchors.right:parent.right;y:0;text:hud.strengths[cell.index];color:"#FFF4FE";font.bold:true;font.pixelSize:Math.max(10,hud.height*.23)}
                Text {visible:hud.options.show_status;x:8;anchors.bottom:parent.bottom;text:"SYNC";color:cell.accent;opacity:.8;font.pixelSize:Math.max(7,hud.height*.12)}
                VibrationPreview {visible:cell.index<2 && hud.options.show_waveforms;x:8;y:parent.height*.36;width:parent.width-12;height:parent.height*.36;points:cell.index===0?[0,10,20,65,100,25,0,40,65,20,0]:[0,90,10,60,25,0,80,30,50,0];lineColor:cell.accent}
                Row {visible:cell.index>=2 || !hud.options.show_waveforms;anchors.right:parent.right;anchors.bottom:parent.bottom;spacing:3
                    Repeater {model:5;Rectangle {required property int index;width:Math.max(2,cell.width*.065);height:(6+index*3)*hud.height/72;color:cell.accent;opacity:index<cell.index+1?1:.15;anchors.bottom:parent.bottom}}
                }
            }
        }
    }
}
