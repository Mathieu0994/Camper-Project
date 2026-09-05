#!/usr/bin/env python3
"""
dbus-truma-temp — provides the two temperature services the GX Touch page
already binds to:

    com.victronenergy.temperature.trumaroom    /Temperature  (room air, °C)
    com.victronenergy.temperature.trumaboiler  /Temperature  (boiler water, °C)

by mirroring two settings paths that the Node-RED bridge (v1.14,
"Publish to D-Bus mirror") keeps up to date:

    /Settings/Truma/RoomTemperature
    /Settings/Truma/BoilerTemperature
    /Settings/Truma/Online            -> /Status (0 ok, 1 not connected)

Why a separate service: Node-RED's victron-virtual node can only create
services named com.victronenergy.temperature.virtual_<nodeid>, and the QML
names are frozen. This is the platform-native way to own an arbitrary
service name on Venus (velib_python's VeDbusService, the same library
Victron's own drivers use).

Install: see DEPLOY.md §6. Runs as a runit service from /data so it
survives firmware updates. NOT tested on a device in the session that
wrote it — Venus was not reachable; see DEPLOY.md.
"""
import logging
import sys
import time

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

sys.path.insert(1, '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python')
from vedbus import VeDbusService, VeDbusItemImport  # noqa: E402

VERSION = '1.14.0'
SETTINGS = 'com.victronenergy.settings'
BUSITEM = 'com.victronenergy.BusItem'

# suffix, settings leaf, TemperatureType (3 Room, 5 Water heater), product name, unique id, preferred instance
SERVICES = [
    ('trumaroom',   'RoomTemperature',   3, 'Truma D6E room',   'truma_room',   30),
    ('trumaboiler', 'BoilerTemperature', 5, 'Truma D6E boiler', 'truma_boiler', 31),
]

log = logging.getLogger('dbus-truma-temp')


def claim_instance(bus, unique, preferred):
    """Venus convention: ask localsettings for /Settings/Devices/<unique>/
    ClassAndVrmInstance = 'temperature:<n>'. localsettings hands back the
    instance actually granted (it resolves clashes itself)."""
    settings = bus.get_object(SETTINGS, '/Settings')
    settings.AddSetting('Devices/' + unique, 'ClassAndVrmInstance',
                        'temperature:%d' % preferred, 's', 0, 0,
                        dbus_interface='com.victronenergy.Settings')
    item = bus.get_object(SETTINGS, '/Settings/Devices/%s/ClassAndVrmInstance' % unique)
    value = str(item.GetValue(dbus_interface=BUSITEM))
    return int(value.split(':')[1])


def settings_path_exists(bus, path):
    try:
        bus.get_object(SETTINGS, path).GetValue(dbus_interface=BUSITEM)
        return True
    except dbus.DBusException:
        return False


class TrumaTemperature:
    def __init__(self, bus, suffix, leaf, ttype, product, unique, preferred):
        self.leaf = leaf
        self.seen_online = False
        self.last = None
        name = 'com.victronenergy.temperature.' + suffix
        instance = claim_instance(bus, unique, preferred)
        try:
            self.svc = VeDbusService(name, bus=bus, register=False)   # velib_python >= 2023
            deferred = True
        except TypeError:
            self.svc = VeDbusService(name, bus=bus)                   # older velib_python
            deferred = False
        s = self.svc
        s.add_path('/Mgmt/ProcessName', 'dbus-truma-temp')
        s.add_path('/Mgmt/ProcessVersion', VERSION)
        s.add_path('/Mgmt/Connection', 'Node-RED bridge via /Settings/Truma')
        s.add_path('/DeviceInstance', instance)
        s.add_path('/ProductId', 0xFFFF)
        s.add_path('/ProductName', product)
        s.add_path('/FirmwareVersion', VERSION)
        s.add_path('/HardwareVersion', 'Truma iNet X (BLE)')
        s.add_path('/Connected', 1)
        s.add_path('/CustomName', product, writeable=True)
        s.add_path('/Temperature', None, gettextcallback=lambda p, v: '%.1f C' % v if v is not None else '--')
        s.add_path('/TemperatureType', ttype, writeable=True)
        s.add_path('/Status', 1)   # 1 = not connected until the bridge says otherwise
        if deferred:
            s.register()
        log.info('%s registered, DeviceInstance %d', name, instance)

        path = '/Settings/Truma/' + leaf
        self.src = VeDbusItemImport(bus, SETTINGS, path, eventCallback=self._on_value, createsignal=True)
        self._apply(self.src.get_value())

    def _on_value(self, service, path, changes):
        self._apply(changes.get('Value'))

    def _apply(self, value):
        if value is None:
            return
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        self.last = value
        # 0.0 is the setting's default before the bridge's first successful
        # read; hide it until the heater has been online at least once.
        self.svc['/Temperature'] = value if self.seen_online else None

    def set_online(self, online):
        self.seen_online = self.seen_online or online
        self.svc['/Status'] = 0 if online else 1
        if self.seen_online and self.last is not None:
            self.svc['/Temperature'] = self.last


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # The settings paths are created by the Node-RED flow at its start
    # ("Ensure Truma settings"). Wait for them rather than fail.
    needed = ['/Settings/Truma/' + s[1] for s in SERVICES] + ['/Settings/Truma/Online']
    while not all(settings_path_exists(bus, p) for p in needed):
        log.info('waiting for /Settings/Truma/* (Node-RED flow not started yet?)')
        time.sleep(10)

    services = [TrumaTemperature(bus, *s) for s in SERVICES]

    def on_online(service, path, changes):
        v = changes.get('Value')
        if v is not None:
            for t in services:
                t.set_online(int(v) == 1)

    online = VeDbusItemImport(bus, SETTINGS, '/Settings/Truma/Online', eventCallback=on_online, createsignal=True)
    v = online.get_value()
    if v is not None:
        for t in services:
            t.set_online(int(v) == 1)

    GLib.MainLoop().run()


if __name__ == '__main__':
    main()
