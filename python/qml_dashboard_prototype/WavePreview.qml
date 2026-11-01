import QtQuick
import QtQuick.Window
import "components" as UI

// Short waves show three cycles in slow motion; long waves show five seconds.
// A full screen always scrolls in five wall-clock seconds. Only preview time is
// scaled: samples, source duration and device playback remain untouched.
Item {
    id:preview
    clip:true
    property var samples:[]
    property real durationMs:0
    property string waveformKey:""
    property color lineColor:"#F6D878"
    property color gridColor:"#B9A978"
    property real elapsedMs:0
    property real startedAt:0
    readonly property real screenTravelMs:5000
    readonly property real windowMs:durationMs>0 ? Math.min(5000,durationMs*3) : 5000
    readonly property real playbackRate:windowMs/screenTravelMs
    readonly property real slowFactor:1/playbackRate
    readonly property real sourceTimeMs:elapsedMs*playbackRate
    readonly property real displayCycleMs:durationMs/playbackRate
    readonly property real pixelsPerMs:width/windowMs
    readonly property real sampleIntervalMs:samples.length && durationMs>0 ? durationMs/samples.length : 25
    readonly property real plotHeight:Math.max(0,height-24)
    readonly property real positionMs:durationMs>0 ? sourceTimeMs%durationMs : 0
    readonly property int completedLoops:durationMs>0 ? Math.floor(sourceTimeMs/durationMs) : 0
    readonly property bool animating:visible && (!Window.window || (Window.window.visible && Window.window.visibility !== Window.Minimized)) && durationMs>0 && samples.length>0
    function sampleAt(timeMs) {
        if(!samples.length || durationMs<=0) return 0
        const time=((timeMs%durationMs)+durationMs)%durationMs
        return samples[Math.min(samples.length-1,Math.floor(time/sampleIntervalMs))]
    }
    function reset() { elapsedMs=0; startedAt=Date.now(); trace.requestPaint() }
    onSamplesChanged:reset()
    onDurationMsChanged:reset()
    onWaveformKeyChanged:reset()
    onElapsedMsChanged:if(visible) trace.requestPaint()
    onAnimatingChanged:if(animating) { startedAt=Date.now()-elapsedMs; trace.requestPaint() }
    onLineColorChanged:trace.requestPaint()
    onGridColorChanged:grid.requestPaint()
    Component.onCompleted:reset()
    Timer {
        objectName:"wavePreviewClock"
        interval:33; repeat:true; running:preview.animating
        onTriggered:preview.elapsedMs=Math.max(0,Date.now()-preview.startedAt)
    }
    Canvas {
        id:grid; width:parent.width; height:preview.plotHeight
        onWidthChanged:requestPaint(); onHeightChanged:requestPaint()
        onPaint: {
            let c=getContext("2d"); c.clearRect(0,0,width,height)
            c.strokeStyle=preview.gridColor; c.globalAlpha=0.3; c.lineWidth=1
            for(let y=0;y<=4;y++) { c.beginPath(); c.moveTo(0,2+(height-4)*y/4); c.lineTo(width,2+(height-4)*y/4); c.stroke() }
            for(let x=0;x<=5;x++) { c.beginPath(); c.moveTo(width*x/5,2); c.lineTo(width*x/5,height-2); c.stroke() }
        }
    }
    Canvas {
        id:trace; objectName:"wavePreviewTrace"
        width:parent.width; height:preview.plotHeight
        onWidthChanged:requestPaint(); onHeightChanged:requestPaint()
        onPaint: {
            let c=getContext("2d"); c.clearRect(0,0,width,height)
            if(!preview.samples.length || preview.durationMs<=0 || width<=0) return
            const step=Math.max(1,preview.sampleIntervalMs)
            const first=Math.floor(preview.sourceTimeMs/step)*step
            const count=Math.ceil(preview.windowMs/step)+2
            c.strokeStyle=preview.lineColor; c.lineWidth=2; c.beginPath()
            let y=2+(height-4)*(1-preview.sampleAt(first)/100)
            c.moveTo((first-preview.sourceTimeMs)*preview.pixelsPerMs,y)
            for(let i=1;i<=count;i++) {
                const time=first+i*step, x=(time-preview.sourceTimeMs)*preview.pixelsPerMs
                c.lineTo(x,y)
                y=2+(height-4)*(1-preview.sampleAt(time)/100)
                c.lineTo(x,y)
            }
            c.stroke()
        }
    }
    Repeater {
        model:6
        delegate:Text {
            required property int index
            text:Number((index*preview.windowMs/5000).toFixed(2))+" s"; color:preview.gridColor; font.pixelSize:11
            x:Math.min(preview.width-width,Math.max(0,index*preview.width/5-width/2))
            y:preview.plotHeight+7
        }
    }
}
