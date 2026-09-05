// SwipePageModel.snippet.qml — the entry to add to gui-v2's
// components/SwipePageModel.qml so "Truma" appears as a real top-level page:
//
//     Brief — Overview — (Boat) — (Levels) — Truma — Notifications — Settings
//
// This is a SNIPPET, not a full-file replacement. gui-v2 is a moving target
// and the stock file on your Cerbo must be read first (docs/swipe-page.md,
// steps 1-3). Insert this block directly before the Notifications entry,
// and copy the exact property set that the Levels (or Boat) Loader entry in
// the same file passes to its page — that set is what `setSource` must
// supply, because SwipeViewPage declares them as required properties.

    // ---- Truma D6E (custom page, loaded from /data so it survives firmware updates) ----
    Loader {
        id: trumaPageLoader
        asynchronous: false
        Component.onCompleted: {
            // Property names below must match what the Levels/Boat entry passes.
            // `view` is mandatory; add iconSource / url only if that entry does.
            setSource("file:///data/truma/qml/TrumaPage.qml", {
                "view": /* the same expression the Levels/Boat entry uses for its view, e.g. */ root.view,
                "iconSource": /* reuse the Levels icon until you pick one */ "qrc:/images/icon_levels_24.svg",
                "url": "/truma"
            })
        }
        onStatusChanged: {
            // A missing or broken TrumaPage.qml must degrade to "no Truma page",
            // never to "no GUI". Loader.Error is logged and the slot stays empty.
            if (status === Loader.Error)
                console.warn("SwipePageModel: Truma page failed to load")
        }
    }
