# D-Bus contract — Truma D6E integration (v1.14)

**Supersedes** the earlier `dbus-paths.md` in the project (the one describing
`Settings/Truma/OperatingMode`, `RoomSetpoint` and a
`temperature.virtual_truma_d6e_temp01` service). That draft was written
before the two frozen source files existed and invented names the flow and
QML never used. Everything below is derived from `truma-dashboard-flows-v1.13.json`
and `TrumaPageContent-v2.qml` (quoted in `INTERFACE.md`), plus the Venus
`localsettings` convention for **how** a custom setting is registered. No
Venus source was used to look for a built-in Truma service: there is none.

Legend — **custom** = exists only because this integration creates it;
**stock** = shipped by Venus OS.

---

## 1. `com.victronenergy.settings` — `/Settings/Truma/*` (all custom)

### How they are created (stock mechanism, custom paths)

`localsettings` exposes `com.victronenergy.Settings.AddSetting` on object
path `/Settings`, signature `ssvsvv`:

```
AddSetting(group, name, default, itemType, min, max)
  -> creates /Settings/<group>/<name>
  itemType: 'i' (int) | 'f' (float) | 's' (string)   — no bool, no enum
  min == max == 0  -> no range enforced
  path already exists -> type/range re-affirmed, current value kept
```

Consequences that shape the table: booleans and enums are stored as `i`;
`TargetTemperature` is `f` because the flow writes `tenths / 10` (e.g.
`21.5`), and the QML's int property truncates it for display.

Two places create them, same commands:

- automatically: `ensure_settings` → `exec_ensure_settings` on the **Truma
  Bridge** tab, 2 s after every flow start (Venus `dbus` CLI, root)
- by hand: `DEPLOY.md` §3 (identical commands; also the Pi testbench)

```sh
dbus -y com.victronenergy.settings /Settings AddSetting Truma RoomMode 0 i 0 5
dbus -y com.victronenergy.settings /Settings AddSetting Truma TargetTemperature 20.0 f 5.0 30.0
dbus -y com.victronenergy.settings /Settings AddSetting Truma AirMode 1 i 0 1
dbus -y com.victronenergy.settings /Settings AddSetting Truma WaterMode 0 i 0 2
dbus -y com.victronenergy.settings /Settings AddSetting Truma WaterActive 0 i 0 1
dbus -y com.victronenergy.settings /Settings AddSetting Truma Boost 0 i 0 1
dbus -y com.victronenergy.settings /Settings AddSetting Truma EnergyMode 5 i 1 5
dbus -y com.victronenergy.settings /Settings AddSetting Truma FanLevel 0 i 0 10
dbus -y com.victronenergy.settings /Settings AddSetting Truma RoomTemperature 0.0 f 0.0 0.0
dbus -y com.victronenergy.settings /Settings AddSetting Truma BoilerTemperature 0.0 f 0.0 0.0
dbus -y com.victronenergy.settings /Settings AddSetting Truma Online 0 i 0 1
```

### The paths

| Path | Type | Range | Default | QML uid (`TrumaPageContent-v2.qml`) | Flow → D-Bus (`publish_state`) | D-Bus → flow (`qml_in`) | Truma field behind it |
|---|---|---|---|---|---|---|---|
| `/Settings/Truma/RoomMode` | `i` | 0..5 | 0 | `dbus.roomMode` | `st.room.mode` | → `room.mode` | `RoomClimate.Mode` 0 off / 3 heat / 5 vent |
| `/Settings/Truma/TargetTemperature` | `f` | 5..30 °C | 20 | `dbus.targetTemp` | `st.room.tgt / 10` | `× 10` → `room.tgt` | `AirHeating.TgtTemp` (tenths) |
| `/Settings/Truma/AirMode` | `i` | 0..1 | 1 | `dbus.airMode` | `st.room.airMode` | → `room.airMode` | `AirHeating.Mode` 0 fast / 1 comfort |
| `/Settings/Truma/WaterMode` | `i` | 0..2 | 0 | `dbus.waterMode` | `st.water.mode` | → `water.mode` (router adds `water.active=1` after 2 s) | `WaterHeating.Mode` 0=40 / 1=60 / 2=70 °C |
| `/Settings/Truma/WaterActive` | `i` | 0..1 | 0 | `dbus.waterActive` | `st.water.active` | 1 → `water.active`, 0 → `water.off` | `WaterHeating.Active` |
| `/Settings/Truma/Boost` | `i` | 0..1 | 0 | `dbus.boost` | `st.water.boost` | → `water.boost` | `WaterHeating.FasterHeatingMode` |
| `/Settings/Truma/EnergyMode` | `i` | 1..5 | 5 | `dbus.energyMode` | `st.energy.mode` | → `energy.mode` (router expands to Diesel/ElectricLevel) | `EnergySrc.DieselLevel` + `ElectricLevel` |
| `/Settings/Truma/FanLevel` | `i` | 0..10 | 0 | `dbus.fanLevel` | `st.room.fanLevel` | → `vent.level` | `AirCirculation.FanLevel` |
| `/Settings/Truma/RoomTemperature` | `f` | — | 0 | *(not bound)* | `st.room.temp / 10` | *(ignored)* | `RoomClimate.Temp` ?? `AirHeating.Temp` |
| `/Settings/Truma/BoilerTemperature` | `f` | — | 0 | *(not bound)* | `st.water.temp / 10` | *(ignored)* | `WaterHeating.Temp` |
| `/Settings/Truma/Online` | `i` | 0..1 | 0 | *(not bound)* | `st.online ? 1 : 0` (always) | *(ignored)* | BLE read success |

EnergyMode numbering is identical on both sides (no translation):
1 Hybrid 900 W (D1,E1) · 2 Hybrid 1800 W (D1,E2) · 3 Electric 900 W (D0,E1) ·
4 Electric 1800 W (D0,E2) · 5 Diesel (D1,E0).

The QML's `bridgeUp` indicator is `dbus.roomMode.valid`, i.e. *"RoomMode
exists on the bus"*. It is not an online indicator; `Online` is, and the QML
does not bind it (frozen).

### Transport between flow and D-Bus (stock mechanism)

Venus OS `dbus-mqtt` (stock) mirrors D-Bus on `127.0.0.1:1883`:

| Direction | Topic | Payload |
|---|---|---|
| flow → D-Bus (write) | `W/<portalId>/settings/0/Settings/Truma/<Leaf>` | `{"value": v}` |
| D-Bus → flow (change notification, incl. echoes of our own writes) | `N/<portalId>/settings/0/Settings/Truma/<Leaf>` | `{"value": v}` |
| keepalive (N/ stops 60 s after the last one) | `R/<portalId>/keepalive` | `""` first, then `{"keepalive-options":["suppress-republish"]}` |

`W/` to a path that does not exist is dropped silently by Venus. That is why
the `AddSetting` step is not optional.

---

## 2. `com.victronenergy.temperature.trumaroom` / `.trumaboiler` (custom)

| Service | Path | Type | Unit | QML uid | Source |
|---|---|---|---|---|---|
| `com.victronenergy.temperature.trumaroom` | `/Temperature` | double (or invalid until first online read) | °C | `dbus.roomTemp` | mirrors `/Settings/Truma/RoomTemperature` |
| `com.victronenergy.temperature.trumaboiler` | `/Temperature` | double | °C | `dbus.boilerTemp` | mirrors `/Settings/Truma/BoilerTemperature` |
| both | `/TemperatureType` | int | — | — | 3 Room / 5 Water heater (stock enum: 0 Battery, 1 Fridge, 2 Generic, 3 Room, 4 Outdoor, 5 Water heater, 6 Freezer) |
| both | `/Status` | int | — | — | 0 ok, 1 not connected (from `/Settings/Truma/Online`) |
| both | `/DeviceInstance` | int | — | — | claimed via `/Settings/Devices/truma_room|truma_boiler/ClassAndVrmInstance` (stock mechanism, `temperature:30` / `:31` preferred, localsettings resolves clashes) |
| both | `/ProductName`, `/CustomName`, `/Connected`, `/Mgmt/*`, `/ProductId`, `/FirmwareVersion`, `/HardwareVersion` | — | — | — | the standard set every Venus device service carries |

Provider: `venus/dbus-truma-temp/dbus-truma-temp.py`, a ~150-line Python
service on `velib_python` (`VeDbusService`, `VeDbusItemImport`), run by
runit from `/data`. Install in `DEPLOY.md` §6. It is optional: without it
the two QML temperature bindings stay invalid and the page shows "—";
everything else works.

Why not Node-RED's `victron-virtual` node: it names its service
`com.victronenergy.temperature.virtual_<nodeId>` and that cannot be changed,
while the QML names are frozen.

---

## 3. What is stock and merely used

| Thing | Stock? | Used for |
|---|---|---|
| `com.victronenergy.settings` service, `AddSetting` | stock | creating `/Settings/Truma/*` |
| `dbus-mqtt` on `127.0.0.1:1883`, `N/ W/ R/` topics | stock | flow ↔ D-Bus |
| `N/+/system/0/Serial` | stock | learning the portal id (`portal_id`) |
| `N/+/system/0/Dc/Battery/Soc`, `N/+/system/0/Ac/ActiveIn/Connected` | stock | site data for the battery guard |
| `/Settings/Devices/<id>/ClassAndVrmInstance` | stock | DeviceInstance claim for the temperature services |
| `VeQuickItem` (QML) | stock | binding the page to D-Bus (see risk in `INTERFACE.md` §7) |
| `svc -t /service/gui-v2` | stock | restarting the GUI |
| `/data/rc.local` | stock | re-linking the temperature service after a firmware update |
