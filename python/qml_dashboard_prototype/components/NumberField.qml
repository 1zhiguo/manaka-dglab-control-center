import QtQuick
import QtQuick.Controls.Basic as C
import QtQuick.Layouts
ColumnLayout {
        id: field
        property string label: ""
        property bool invalid:false
        property real value: 0
        property real minimum: 0
        property real maximum: 100
        property real step: 1
        property int decimals: 0
        signal edited(real newValue)
        spacing: 8
        Layout.fillWidth: true
        Layout.minimumWidth: 140
        Caption { text: field.label }
        C.SpinBox {
            id: input
            Accessible.name:field.label
            objectName: field.objectName ? field.objectName + "Input" : ""
            Layout.fillWidth: true
            implicitHeight: Theme.controlHeight
            property real factor: Math.pow(10,field.decimals)
            from: Math.round(field.minimum*factor); to: Math.round(field.maximum*factor)
            stepSize: Math.round(field.step*factor)
            value: Math.round(field.value*factor)
            editable: true; live: false
            font.family:Theme.fontFamily; font.pixelSize:Theme.bodySize
            leftPadding: 30; rightPadding: 30
            textFromValue: function(value,locale) { return Number(value/factor).toLocaleString(locale,'f',field.decimals) }
            valueFromText: function(text,locale) { return Math.round(Number.fromLocaleString(locale,text)*factor) }
            validator: DoubleValidator { bottom: field.minimum; top: field.maximum; decimals: field.decimals; locale: input.locale.name }
            onValueModified: field.edited(value/factor)
            contentItem: TextInput {
                text: input.displayText
                font: input.font; color: input.enabled ? Theme.textPrimary : Theme.textDisabled
                selectionColor:Theme.selection; selectedTextColor:Theme.textPrimary
                horizontalAlignment: TextInput.AlignHCenter
                verticalAlignment: TextInput.AlignVCenter
                selectByMouse: true; clip: true
                validator: input.validator
                // Qt's native live formatting can rewrite text mid-edit. Keep
                // its commit behavior, but update a valid draft as it is typed.
                onTextEdited: if (acceptableInput) field.edited(input.valueFromText(text,input.locale)/input.factor)
            }
            background: Rectangle { radius: 6; color: input.enabled ? Theme.surfaceRaised : Theme.disabledFill; border.color: field.invalid ? Theme.danger : input.activeFocus ? Theme.accent : Theme.borderControl; border.width:input.activeFocus ? 2 : 1 }
            up.indicator: Rectangle {
                x: input.width-width; width: 28; height: input.height; radius: 6
                color: input.up.pressed ? Theme.borderControl : "transparent"
                Text { anchors.centerIn: parent; text: "+"; font.pixelSize: 17; color: input.up.enabled ? Theme.textPrimary : Theme.textSecondary }
            }
            down.indicator: Rectangle {
                width: 28; height: input.height; radius: 6
                color: input.down.pressed ? Theme.borderControl : "transparent"
                Text { anchors.centerIn: parent; text: "−"; font.pixelSize: 17; color: input.down.enabled ? Theme.textPrimary : Theme.textSecondary }
            }
        }
    }
