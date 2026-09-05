# Notes for anyone testing or changing this

**Please report back even if it just works.** The single most useful thing
right now is confirmation (or not) on hardware other than the author's:
which GX device, which Venus OS version, which D6E/iNet X, and whether the
GX Touch page appeared in the swipe view.

Things worth knowing before you change the flow:

- **Node-RED flow context is per tab.** State cached on one tab is invisible
  on another. The D-Bus bridge depends on this: it keeps its own copy of the
  heater state, because comparing against another tab's copy would silently
  fail and turn every mirror write back into a heater command (an endless
  BLE loop).
- **Every write is echoed back.** The bridge writes `/Settings/Truma/*` and
  also listens to it. Only a value that differs both from the heater's last
  reported state and from any in-flight write is a real user action.
- **One command queue.** Everything that writes to the heater goes through
  it, single flight. Don't wire a new path straight to the set node.
- **Units.** The protocol uses tenths of a degree; the D-Bus settings and
  both UIs use whole degrees. The bridge converts.
- **Sliders commit on release**, not per tick — the GX Touch CPU is modest.

`docs/INTERFACE.md` lists every key, path, unit and mapping. If you change a
name, change it there too.
