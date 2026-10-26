import QtQuick

Item {
    id: preview
    property var points: []
    property color lineColor: "#EE81C8"
    property bool animate: false
    property real phase: 0
    property int cycles: 1
    clip: true
    Canvas {
        id: canvas; anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            let ctx=getContext("2d");ctx.reset()
            ctx.strokeStyle=Qt.rgba(preview.lineColor.r,preview.lineColor.g,preview.lineColor.b,.12);ctx.lineWidth=1
            for(let i=1;i<4;i++){ctx.beginPath();ctx.moveTo(0,i*height/4);ctx.lineTo(width,i*height/4);ctx.stroke()}
            let source=preview.points;if(!source || source.length<2)return
            let p=[];for(let cycle=0;cycle<preview.cycles;cycle++)p=p.concat(source)
            ctx.strokeStyle=preview.lineColor;ctx.lineWidth=2;ctx.lineJoin="round";ctx.beginPath()
            for(let j=0;j<p.length;j++){let x=2+j*(width-4)/(p.length-1),y=height-2-Math.max(0,Math.min(100,p[j]))*(height-4)/100;if(j===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}ctx.stroke()
        }
    }
    onPointsChanged: canvas.requestPaint()
    onCyclesChanged: canvas.requestPaint()
    onLineColorChanged: canvas.requestPaint()
    Rectangle { visible: preview.animate; width: 1; height: parent.height; x: preview.phase * Math.max(0,parent.width-1); color: preview.lineColor; opacity: .5 }
    Timer { interval: 33; repeat: true; running: preview.animate && preview.visible; onTriggered: preview.phase=(preview.phase+.013)%1 }
}
