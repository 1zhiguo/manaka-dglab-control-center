import QtQuick
import QtQuick.Controls.Basic as C
C.Dialog {
    id:control; modal:true; padding:20
    property bool unsavedChanges:false
    property string confirmText:""
    font.family:Theme.fontFamily; font.pixelSize:Theme.bodySize
    palette.window:Theme.surface; palette.windowText:Theme.textPrimary
    palette.button:Theme.surfaceRaised; palette.buttonText:Theme.textPrimary
    background:Rectangle { color:Theme.surface; radius:Theme.cardRadius; border.color:Theme.borderControl }
    header:C.Label { visible:text.length>0; text:control.title; padding:20; bottomPadding:12; font.family:Theme.fontFamily; font.pixelSize:Theme.headingSize; font.weight:Font.DemiBold; color:Theme.textPrimary; wrapMode:Text.Wrap }
    footer:DialogButtonBox { visible:count>0; keepEditingOnCancel:control.unsavedChanges; confirmText:control.confirmText }
}
