// =============================================================================
//  Main.qml — SDDM greeter theme "inkpaw-encre" (ink & parchment)
// =============================================================================
//  Login screen of the "encre" skin (mockup: .mockups/project/Mew-Login.dc.html):
//    * big brush clock + date, top-left (ochre offset shadow)
//    * login card: ginger cat avatar in an ochre circle, user name, password,
//      ochre "Entrer" button, session/keyboard summary, error line + shake
//    * "Quelle session ?" card on the right (radio list from sessionModel),
//      with the calico cat sitting on it
//    * bottom-right: keyboard layout, Veille, Redémarrer, Éteindre
//  Plain QtQuick + QtQuick.Shapes only (Qt 6, sddm-greeter-qt6). SDDM API used:
//  sddm.login/powerOff/reboot/suspend, signals loginFailed/loginSucceeded,
//  userModel (lastUser), sessionModel (lastIndex), keyboard, config (theme.conf).
//  The layout is drawn on the mockup's 1440×900 grid and scaled by `s`.
//  Every asset (fonts, cats, wallpaper) lives inside this theme folder.
// =============================================================================
import QtQuick
import QtQuick.Shapes

Rectangle {
    id: root
    width: 1440
    height: 900
    color: ink

    // ---- palette & settings (theme.conf, with fallbacks) --------------------
    readonly property color ink:   config.ink   || "#2a2420"
    readonly property color paper: config.paper || "#f1e7cf"
    readonly property color card:  config.card  || "#fffaf0"
    readonly property color muted: config.muted || "#4a4038"
    readonly property color ochre: config.ochre || "#d9a12e"
    readonly property color brick: config.brick || "#c4573e"
    readonly property string bodyFont:    fBody.name    || "sans-serif"
    readonly property string displayFont: fDisplay.name || "cursive"
    readonly property string monoFont:    fMono.name    || "monospace"
    readonly property bool hideUnavailable: config.hideUnavailablePower === "true"

    // scale factor: mockup grid (1440×900) → screen
    readonly property real s: Math.min(width / 1440, height / 900)
    // x of something placed `r` mockup px from the right edge
    function rx(r) { return width - r * s }

    // ---- state ----------------------------------------------------------------
    property int sessionIndex: sessionModel.lastIndex >= 0 ? sessionModel.lastIndex : 0
    property var users: []            // names collected from userModel
    property var userIcons: []
    property int userIdx: 0
    readonly property string userName: users.length > 0 ? users[userIdx] : (userModel.lastUser || "")
    property bool failed: false
    property bool busy: false

    // ---- fonts (from the theme folder) ----------------------------------------
    FontLoader { id: fBody;    source: config.fontBody    || "fonts/ShantellSans-Variable.ttf" }
    FontLoader { id: fDisplay; source: config.fontDisplay || "fonts/CaveatBrush-Regular.ttf" }
    FontLoader { id: fMono;    source: config.fontMono    || "fonts/CourierPrime-Bold.ttf" }

    // ---- collect users, preselect userModel.lastUser --------------------------
    Repeater {
        id: userRep
        model: userModel
        delegate: Item {
            required property string name
            required property string icon
            required property int index
        }
        onItemAdded: root.collectUsers()
        onItemRemoved: root.collectUsers()
    }
    function collectUsers() {
        var n = [], ic = [], sel = 0
        for (var i = 0; i < userRep.count; i++) {
            var it = userRep.itemAt(i)
            if (!it) continue
            n.push(it.name); ic.push(it.icon)
            if (it.name === userModel.lastUser) sel = n.length - 1
        }
        users = n; userIcons = ic; userIdx = sel
    }

    // ---- session / keyboard helpers --------------------------------------------
    property var sessionNames: []     // names collected from sessionModel
    function collectSessions() {
        var n = []
        for (var i = 0; i < sessRep.count; i++) {
            var it = sessRep.itemAt(i)
            n.push(it ? it.sName : "")
        }
        sessionNames = n
    }
    function sessionName(i) { return i >= 0 && i < sessionNames.length ? sessionNames[i] : "" }
    readonly property string layoutName: {
        var l = keyboard && keyboard.layouts ? keyboard.layouts : []
        var i = keyboard ? keyboard.currentLayout : -1
        if (l.length > 0 && i >= 0 && i < l.length && l[i].shortName)
            return String(l[i].shortName).toUpperCase()
        return config.keyboardFallback || "FR"
    }
    function cycleLayout() {
        if (keyboard && keyboard.layouts && keyboard.layouts.length > 1)
            keyboard.currentLayout = (keyboard.currentLayout + 1) % keyboard.layouts.length
    }

    function doLogin() {
        if (busy || userName === "") return
        busy = true
        failed = false
        sddm.login(userName, pw.text, sessionIndex)
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            root.busy = false
            root.failed = true
            pw.text = ""
            pw.forceActiveFocus()
            shake.restart()
        }
        function onLoginSucceeded() { root.busy = false }
    }

    // ---- reusable pieces ---------------------------------------------------------
    // Hand-drawn panel: uneven corners, ink border, hard ink shadow (no blur).
    component Paper: Item {
        id: paperItem
        property color fill: "#f1e7cf"
        property color stroke: "#2a2420"
        property real bw: 3
        property real shadow: 4
        property var radii: [16, 22, 14, 20]   // TL, TR, BR, BL
        Rectangle {
            x: paperItem.shadow; y: paperItem.shadow
            width: parent.width; height: parent.height
            visible: paperItem.shadow > 0
            color: paperItem.stroke
            topLeftRadius: paperItem.radii[0]; topRightRadius: paperItem.radii[1]
            bottomRightRadius: paperItem.radii[2]; bottomLeftRadius: paperItem.radii[3]
            antialiasing: true
        }
        Rectangle {
            anchors.fill: parent
            color: paperItem.fill
            border.color: paperItem.stroke
            border.width: paperItem.bw
            topLeftRadius: paperItem.radii[0]; topRightRadius: paperItem.radii[1]
            bottomRightRadius: paperItem.radii[2]; bottomLeftRadius: paperItem.radii[3]
            antialiasing: true
        }
    }

    // Stroke icon from a 24×24 SVG path (same paths as the mockup).
    component Icon: Item {
        id: iconItem
        property string d: ""
        property color stroke: "#2a2420"
        property real size: 20
        width: size; height: size
        Shape {
            width: 24; height: 24
            scale: iconItem.size / 24
            transformOrigin: Item.TopLeft
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: iconItem.stroke
                strokeWidth: 2.6
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                joinStyle: ShapePath.RoundJoin
                PathSvg { path: iconItem.d }
            }
        }
    }

    // Bottom-right button: icon (or text) over a small bold label.
    component RoundButton: Item {
        id: rbItem
        property real s: 1
        property string label: ""
        property string iconPath: ""
        property string mono: ""          // big mono text instead of an icon
        property string monoFamily: ""
        property string labelFamily: ""
        property color fill: "#f1e7cf"
        property color ink: "#2a2420"
        signal clicked()
        width: Math.max(col.implicitWidth + 20 * s, 46 * s)
        height: col.implicitHeight + 16 * s
        Paper {
            anchors.fill: parent
            fill: rbItem.fill; stroke: rbItem.ink
            bw: 3 * rbItem.s; shadow: (ma.pressed ? 1 : 3) * rbItem.s
            radii: [14 * rbItem.s, 10 * rbItem.s, 16 * rbItem.s, 12 * rbItem.s]
            transform: Translate { x: ma.pressed ? 2 * rbItem.s : 0; y: ma.pressed ? 2 * rbItem.s : 0 }
        }
        Column {
            id: col
            anchors.centerIn: parent
            anchors.horizontalCenterOffset: ma.pressed ? 2 * rbItem.s : 0
            anchors.verticalCenterOffset: ma.pressed ? 2 * rbItem.s : 0
            spacing: 4 * rbItem.s
            Icon {
                visible: rbItem.iconPath !== ""
                anchors.horizontalCenter: parent.horizontalCenter
                d: rbItem.iconPath; stroke: rbItem.ink; size: 20 * rbItem.s
            }
            Text {
                visible: rbItem.label !== ""
                anchors.horizontalCenter: parent.horizontalCenter
                text: rbItem.label
                color: rbItem.ink
                font.family: rbItem.labelFamily
                font.pixelSize: 12 * rbItem.s
                font.weight: Font.Bold
                font.variableAxes: { "wght": 700 }
            }
            Text {
                visible: rbItem.mono !== ""
                anchors.horizontalCenter: parent.horizontalCenter
                text: rbItem.mono
                color: rbItem.ink
                font.family: rbItem.monoFamily
                font.pixelSize: 15 * rbItem.s
                font.weight: Font.Bold
            }
        }
        MouseArea {
            id: ma
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: rbItem.clicked()
        }
    }

    // ---- background ----------------------------------------------------------------
    Image {
        anchors.fill: parent
        source: config.background || "background.jpg"
        fillMode: Image.PreserveAspectCrop
        asynchronous: false
        smooth: true
    }
    Rectangle {
        anchors.fill: parent
        color: root.paper
        opacity: config.veilOpacity !== undefined && config.veilOpacity !== "" ? Number(config.veilOpacity) : 0.2
    }
    // click anywhere: give the focus back to the password field
    MouseArea { anchors.fill: parent; onClicked: pw.forceActiveFocus() }

    // ---- clock, top-left ---------------------------------------------------------------
    Item {
        id: clock
        x: 70 * s; y: 56 * s
        property date now: new Date()
        Timer {
            interval: 1000; running: true; repeat: true; triggeredOnStart: true
            onTriggered: clock.now = new Date()
        }
        readonly property string timeText: Qt.formatTime(now, config.clockFormat || "hh:mm")
        Text {   // ochre offset shadow
            x: 5 * s; y: 5 * s
            text: clock.timeText
            color: root.ochre
            font.family: root.displayFont
            font.pixelSize: 130 * s
        }
        Text {
            id: timeLabel
            text: clock.timeText
            color: root.ink
            font.family: root.displayFont
            font.pixelSize: 130 * s
            lineHeight: 0.9
        }
        Text {
            x: 6 * s
            y: timeLabel.height - 4 * s
            rotation: -1
            text: Qt.locale(config.locale || "fr_FR").toString(clock.now, config.dateFormat || "dddd d MMMM")
            color: root.ink
            font.family: root.bodyFont
            font.pixelSize: 22 * s
            font.weight: Font.Bold
            font.variableAxes: { "wght": 700 }
        }
    }

    // ---- Inkpaw logo, top-right (logo.png = logo/inkpaw-logo.png, copied by install.sh) ----
    Image {
        width: 300 * s; height: 109 * s
        x: rx(70) - width; y: 60 * s
        source: config.logo || "logo.png"
        sourceSize: Qt.size(600 * s, 218 * s)
        fillMode: Image.PreserveAspectFit
        smooth: true
    }

    // ---- login card ------------------------------------------------------------------------
    Item {
        id: loginCard
        x: 150 * s; y: 400 * s
        width: 440 * s
        height: cardCol.implicitHeight + 84 * s
        transform: Translate { id: shakeT; x: 0 }

        SequentialAnimation {
            id: shake
            loops: 1
            NumberAnimation { target: shakeT; property: "x"; to: -14 * root.s; duration: 50 }
            NumberAnimation { target: shakeT; property: "x"; to:  12 * root.s; duration: 70 }
            NumberAnimation { target: shakeT; property: "x"; to:  -8 * root.s; duration: 70 }
            NumberAnimation { target: shakeT; property: "x"; to:   5 * root.s; duration: 60 }
            NumberAnimation { target: shakeT; property: "x"; to:   0; duration: 50 }
        }

        Paper {
            anchors.fill: parent
            fill: root.paper; stroke: root.ink
            bw: 3 * s; shadow: 6 * s
            radii: [16 * s, 22 * s, 14 * s, 20 * s]
        }

        // avatar: ochre circle overlapping the card top
        Item {
            id: avatar
            width: 92 * s; height: 92 * s
            anchors.horizontalCenter: parent.horizontalCenter
            y: -46 * s
            Rectangle {   // hard shadow
                x: 4 * s; y: 4 * s; width: parent.width; height: parent.height
                radius: width / 2; color: root.ink; antialiasing: true
            }
            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: root.ochre
                border.color: root.ink; border.width: 3 * s
                antialiasing: true
                Image {
                    readonly property string userIcon: root.userIcons.length > 0 ? String(root.userIcons[root.userIdx] || "") : ""
                    anchors.centerIn: parent
                    width: 74 * s; height: 74 * s
                    sourceSize: Qt.size(width * 2, height * 2)
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    source: (config.useUserIcon === "true" && userIcon !== "") ? userIcon
                            : (config.avatar || "cats/head-moumoute.png")
                    onStatusChanged: if (status === Image.Error) source = "cats/head-moumoute.png"
                }
            }
        }

        Column {
            id: cardCol
            x: 26 * s; y: 60 * s   // avatar bottom (46) + gap (14)
            width: parent.width - 52 * s
            spacing: 14 * s

            // user name (click = next user when there are several)
            Item {
                width: parent.width
                height: nameText.implicitHeight
                Text {
                    id: nameText
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.userName + (root.users.length > 1 ? " ›" : "")
                    color: root.ink
                    font.family: root.displayFont
                    font.pixelSize: 36 * s
                    lineHeight: 1.0
                }
                MouseArea {
                    anchors.fill: nameText
                    enabled: root.users.length > 1
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: { root.userIdx = (root.userIdx + 1) % root.users.length; root.failed = false; pw.forceActiveFocus() }
                }
            }

            // password field: card color, ink border, lock icon
            Rectangle {
                width: parent.width
                height: 48 * s
                color: root.card
                border.color: root.failed ? root.brick : root.ink
                border.width: 3 * s
                topLeftRadius: 12 * s; topRightRadius: 9 * s; bottomRightRadius: 14 * s; bottomLeftRadius: 10 * s
                antialiasing: true
                Icon {
                    id: lockIcon
                    x: 14 * s
                    anchors.verticalCenter: parent.verticalCenter
                    size: 18 * s; stroke: root.ink
                    d: "M7 11H17A2 2 0 0 1 19 13V19A2 2 0 0 1 17 21H7A2 2 0 0 1 5 19V13A2 2 0 0 1 7 11Z M8 11V8a4 4 0 0 1 8 0v3"
                }
                TextInput {
                    id: pw
                    anchors.left: lockIcon.right; anchors.leftMargin: 10 * s
                    anchors.right: parent.right; anchors.rightMargin: 14 * s
                    anchors.verticalCenter: parent.verticalCenter
                    echoMode: TextInput.Password
                    passwordCharacter: "●"
                    color: root.ink
                    selectionColor: root.ochre
                    selectedTextColor: root.ink
                    font.family: root.bodyFont
                    font.pixelSize: 15 * s
                    font.weight: Font.DemiBold
                    font.variableAxes: { "wght": 600 }
                    focus: true
                    clip: true
                    onTextChanged: if (text.length > 0) root.failed = false
                    onAccepted: root.doLogin()
                    Keys.onEscapePressed: text = ""
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: pw.text.length === 0
                        text: "Mot de passe"
                        color: root.muted
                        opacity: 0.75
                        font: pw.font
                    }
                }
                MouseArea { anchors.fill: parent; cursorShape: Qt.IBeamCursor; onClicked: pw.forceActiveFocus(); z: -1 }
            }

            // error line
            Text {
                width: parent.width
                visible: root.failed
                horizontalAlignment: Text.AlignHCenter
                text: "Mot de passe incorrect"
                color: root.brick
                font.family: root.bodyFont
                font.pixelSize: 14 * s
                font.weight: Font.Bold
                font.variableAxes: { "wght": 700 }
            }

            // "Entrer" button: ochre fill, ink border, hard shadow
            Item {
                width: parent.width
                height: 46 * s
                Paper {
                    anchors.fill: parent
                    fill: root.busy ? Qt.darker(root.ochre, 1.15) : root.ochre
                    stroke: root.ink
                    bw: 3 * s; shadow: (enterMa.pressed ? 1 : 4) * s
                    radii: [14 * s, 10 * s, 16 * s, 12 * s]
                    transform: Translate { x: enterMa.pressed ? 3 * s : 0; y: enterMa.pressed ? 3 * s : 0 }
                }
                Text {
                    anchors.centerIn: parent
                    anchors.horizontalCenterOffset: enterMa.pressed ? 3 * s : 0
                    anchors.verticalCenterOffset: enterMa.pressed ? 3 * s : 0
                    text: root.busy ? "…" : "Entrer"
                    color: root.ink
                    font.family: root.bodyFont
                    font.pixelSize: 16 * s
                    font.weight: Font.Bold
                    font.variableAxes: { "wght": 700 }
                }
                MouseArea {
                    id: enterMa
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.doLogin()
                }
            }

            // summary: session + keyboard
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                textFormat: Text.StyledText
                text: "Session : <b>" + root.sessionName(root.sessionIndex).replace(/\s*\(.*\)\s*$/, "")
                      + "</b> · clavier " + root.layoutName
                color: root.muted
                font.family: root.bodyFont
                font.pixelSize: 13 * s
                font.weight: Font.DemiBold
                font.variableAxes: { "wght": 600 }
            }
        }
    }

    // ---- session chooser, right ---------------------------------------------------------
    Item {
        id: sessCard
        x: rx(70 + 470); y: 390 * s
        width: 470 * s
        height: sessCol.implicitHeight + 36 * s
        rotation: 0.6

        Paper {
            anchors.fill: parent
            fill: root.paper; stroke: root.ink
            bw: 3 * s; shadow: 4 * s
            radii: [16 * s, 22 * s, 14 * s, 20 * s]
        }

        Column {
            id: sessCol
            x: 20 * s; y: 18 * s
            width: parent.width - 40 * s
            spacing: 8 * s

            Text {
                text: "Quelle session ?"
                color: root.ink
                font.family: root.displayFont
                font.pixelSize: 32 * s
                lineHeight: 1.0
                bottomPadding: 4 * s
            }

            Repeater {
                id: sessRep
                model: sessionModel
                onItemAdded: root.collectSessions()
                onItemRemoved: root.collectSessions()
                delegate: Item {
                    id: row
                    required property int index
                    required property string name
                    required property string comment
                    readonly property string sName: name
                    readonly property bool selected: index === root.sessionIndex
                    width: sessCol.width
                    height: rowContent.implicitHeight + 16 * s
                    rotation: selected ? -1 : 0

                    Rectangle {
                        anchors.fill: parent
                        color: row.selected ? root.ochre : (rowMa.containsMouse ? Qt.rgba(0.165, 0.141, 0.125, 0.07) : "transparent")
                        border.color: row.selected ? root.ink : "transparent"
                        border.width: 2.5 * s
                        topLeftRadius: 12 * s; topRightRadius: 9 * s; bottomRightRadius: 14 * s; bottomLeftRadius: 10 * s
                        antialiasing: true
                    }
                    Row {
                        id: rowContent
                        x: 12 * s
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 12 * s
                        // radio dot
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 18 * s; height: 18 * s; radius: width / 2
                            color: root.card
                            border.color: root.ink; border.width: 2.5 * s
                            antialiasing: true
                            Rectangle {
                                anchors.centerIn: parent
                                width: 8 * s; height: 8 * s; radius: width / 2
                                color: root.ink
                                visible: row.selected
                                antialiasing: true
                            }
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            width: row.width - 12 * s - 18 * s - 12 * s - 12 * s
                            Text {
                                width: parent.width
                                elide: Text.ElideRight
                                text: row.name
                                color: root.ink
                                font.family: root.bodyFont
                                font.pixelSize: 15 * s
                                font.weight: Font.Bold
                                font.variableAxes: { "wght": 700 }
                            }
                            Text {
                                width: parent.width
                                visible: row.comment !== ""
                                elide: Text.ElideRight
                                text: row.comment
                                color: root.muted
                                font.family: root.bodyFont
                                font.pixelSize: 12 * s
                                font.weight: Font.DemiBold
                                font.variableAxes: { "wght": 600 }
                            }
                        }
                    }
                    MouseArea {
                        id: rowMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { root.sessionIndex = row.index; pw.forceActiveFocus() }
                    }
                }
            }
        }
    }

    // calico cat sitting on the session card
    Image {
        x: rx(1440 - 1150); y: 300 * s + 4 * s
        width: 110 * s; height: 100 * s
        source: config.sessionCat || "cats/sit-croquette.png"
        sourceSize: Qt.size(220 * s, 200 * s)
        fillMode: Image.PreserveAspectFit
        smooth: true
    }

    // ---- power + layout, bottom-right ------------------------------------------------------
    Row {
        id: powerRow
        x: rx(70) - width
        y: height > 0 ? root.height - 50 * s - height : 0
        spacing: 12 * s

        RoundButton {
            s: root.s; ink: root.ink; fill: root.paper
            monoFamily: root.monoFont; labelFamily: root.bodyFont
            mono: root.layoutName
            height: veille.height
            onClicked: { root.cycleLayout(); pw.forceActiveFocus() }
        }
        RoundButton {
            id: veille
            s: root.s; ink: root.ink; fill: root.paper; labelFamily: root.bodyFont
            visible: !root.hideUnavailable || sddm.canSuspend
            label: "Veille"
            iconPath: "M20 14A8 8 0 1 1 10 4a6 6 0 0 0 10 10z"
            onClicked: sddm.suspend()
        }
        RoundButton {
            s: root.s; ink: root.ink; fill: root.paper; labelFamily: root.bodyFont
            visible: !root.hideUnavailable || sddm.canReboot
            label: "Redémarrer"
            iconPath: "M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5"
            onClicked: sddm.reboot()
        }
        RoundButton {
            s: root.s; ink: root.ink; fill: root.brick; labelFamily: root.bodyFont
            visible: !root.hideUnavailable || sddm.canPowerOff
            label: "Éteindre"
            iconPath: "M12 3v9 M6.4 6.4a8 8 0 1 0 11.2 0"
            onClicked: sddm.powerOff()
        }
    }

    Component.onCompleted: { collectUsers(); pw.forceActiveFocus() }
}
