# Truma iNet X — Node-RED Dashboard 2.0 in Victron-stijl

Volledig dashboard plus flows voor een Truma Combi D6E met iNet X paneel,
draaiend op een Cerbo GX met Venus OS Large. Bediening via GX Touch en via
internet/VRM op telefoon en PC, met dezelfde toestand op beide schermen.

Bestand: `truma-dashboard-flows-v1.13.json` — 161 nodes, 8 tabbladen

## Diff v1.12 naar v1.13 (Timers herbouwd)

Een timer is nu een **tijdelijke override**: bij het starten wordt de huidige
stand bewaard, bij het eindigen exact teruggezet. Stond de kachel uit op 18,0 en
loopt er een timer van 8:00 tot 9:00 op 21,0, dan staat hij om 9:01 weer uit op
18,0.

**Elke instelling zit in de timer zelf**, zodat je nooit eerst iets op Home hoeft
te veranderen:

| Actie | Instellingen |
| --- | --- |
| Room climate | doeltemperatuur, fanprofiel (Fast/Comfort) |
| Hot water | Eco 40 / Comfort 60 / Hot 70, boost aan/uit |
| Ventilator | fanniveau 0-10 |

Energiebron (5 standen) staat los en geldt voor elke actie. **Off is als actie
verdwenen**; het einde van de timer herstelt de vorige stand, en dat kan "uit" zijn.

**Handmatig ingrijpen stopt de timer.** Verander je iets op Home of op de GX
Touch terwijl een timer loopt, dan wordt de rest van de bewaarde stand
teruggezet, blijft jouw wijziging staan, gaat de regel op Off en verschijnt een
melding. Commando's van de timer zelf breken hem niet af; dat gaat op `source`.

**Overlappende timers** delen één bewaarde stand. De eerste die start bewaart,
de laatste die eindigt herstelt.

**Interlocks zijn waarschuwingen, geen blokkades.** De kachel bepaalt. Wat het
dashboard doet is uitleggen wat er gaat gebeuren: boost duurt 40 minuten en zet
room climate uit, de ventilator ook. Niets wordt tegengehouden; de poller leest
terug wat de kachel er werkelijk van maakte.

**Hernoemd:** Heat naar Room climate, Fan only naar Ventilator, "What should
happen" naar Action.

Ongewijzigd: `cmd_router`, MAP, poll-interval, Bluetooth-adres, get-topics,
ui-base path, node-id's.

## 0. Importeren zonder dubbele kaarten

De eerdere screenshots toonden Scenes, Lights en twee keer Ventilator: restanten
van een oudere versie naast de nieuwe. Node-RED laat oude ui-groepen staan als
je een nieuwe versie er overheen importeert. Daarom, elke keer:

1. Verwijder alle acht Truma-tabs (dubbelklik op de tab → Delete).
2. Hamburgermenu → Configuration nodes → tabblad "unused" → alles verwijderen.
3. Deploy. De Dashboard 2.0-zijbalk moet nu alleen "My Dashboard" tonen, leeg.
4. Importeer het nieuwe bestand.
5. BLE-adres invullen in `Truma iNet X`, Deploy.

Sla je stap 1-3 over, dan zie je opnieuw lege dubbele kaarten., importeren via
menu → Import → select a file.

---

## 1. Installatie

### 1.1 Vereiste packages

Via Manage palette:

| Package | Waarvoor |
| --- | --- |
| `@flowfuse/node-red-dashboard` | Dashboard 2.0. Zit **niet** standaard in Venus OS Large. |
| `node-red-contrib-truma-inetx` | BLE-koppeling naar het paneel. |

De MQTT-nodes zitten in de Node-RED core, daar hoef je niets voor te installeren.

### 1.2 Na de import controleren

1. **`Truma iNet X`** (truma-inetx-device) — adres `2C:A7:74:1C:A5:80` staat
   erin. Open de node één keer om te zien of de velden overeenkomen met wat de
   editor toont; `pollOnDeploy` staat uit.
   Pairen doe je eenmalig via de CLI, dat kan niet vanuit de editor:
   ```
   npm run pair -- --bluetooth bluez --debug
   ```
2. **`Venus OS local`** (mqtt-broker) — staat op `127.0.0.1:1883`. Werkt zoals hij
   is, mits MQTT aanstaat onder Settings → Services → MQTT on LAN.
3. **`Read iNet X` / `Write iNet X`** — controleer of de veldnamen in het
   edit-scherm overeenkomen. Ik heb de nodes bedraad op basis van de README van
   het package; wijkt een veldnaam af, dan zie je dat direct in de editor.

Zet MQTT aan op de Cerbo voordat je deployt, anders blijft de Bridge-tab in
"no portal id yet" hangen.

### 1.3 Persistente context (aanbevolen)

Zonder dit verlies je historie, schema en logboek bij elke herstart. In
`/data/home/nodered/.node-red/settings.js`:

```js
contextStorage: {
  default: { module: "memory" },
  file:    { module: "localfilesystem", config: { dir: "/data/nodered-context" } }
}
```

De flows proberen eerst de `file` store en vallen stil terug op geheugen als die
er niet is. Je hoeft dus niets aan te passen als je dit overslaat, je raakt
alleen data kwijt bij een reboot.

### 1.4 D-Bus settings-paden aanmaken

De Bridge-tab schrijft naar `/Settings/Truma/*`. Die paden moeten één keer
bestaan voordat er iets in kan. Op de Cerbo, via SSH:

```
dbus -y com.victronenergy.settings /Settings AddSettings \
'%[{"path":"/Settings/Truma/RoomMode","default":0,"min":0,"max":5},
   {"path":"/Settings/Truma/TargetTemperature","default":20,"min":5,"max":30},
   {"path":"/Settings/Truma/AirMode","default":1,"min":0,"max":1},
   {"path":"/Settings/Truma/WaterMode","default":0,"min":0,"max":2},
   {"path":"/Settings/Truma/EnergyMode","default":2,"min":0,"max":5},
   {"path":"/Settings/Truma/RoomTemperature","default":0,"min":-50,"max":100},
   {"path":"/Settings/Truma/BoilerTemperature","default":0,"min":0,"max":100},
   {"path":"/Settings/Truma/Online","default":0,"min":0,"max":1}]'
```

Deze namen komen uit de bestaande `truma-victron GUIv2` flow en zijn dus precies
wat `PageTruma.qml` verwacht. **Let op de eenheid:** `TargetTemperature` staat op
D-Bus in hele graden (20), terwijl het BLE-protocol tienden gebruikt (200). De
Bridge-tab rekent in beide richtingen om.

Wil je cabinetemperatuur als grafiek in VRM, dan moeten
`com.victronenergy.temperature.trumaroom` en `.trumaboiler` als virtual devices
bestaan. Dat kan alleen met `node-red-contrib-victron`, niet via MQTT.

Controleer daarna met `dbus -y com.victronenergy.settings /Settings/Truma GetValue`.
Deze namen zijn precies wat `PageTruma.qml` via VeQuickItem moet binden.

Zonder deze stap werkt het web-dashboard gewoon; alleen de synchronisatie met de
GX Touch valt weg.

---

## 2. Hoe de flows werken

Zeven tabbladen, elk met één verantwoordelijkheid. Ze praten uitsluitend via
link-nodes, dus je kunt een tab uitschakelen zonder de rest te breken.

### Truma Poller
Elke 2 minuten een volledige uitlezing, plus een gerichte uitlezing van alleen
de aangeraakte topics zodra een write bevestigd is. `Poll guard` laat de tik vallen als de
circuit breaker openstaat, als we in een backoff-venster zitten, of als Bluetooth
tijdelijk is vrijgegeven voor je telefoon. `Normalise` verwerkt zowel de geneste
vorm (`topics.RoomClimate.parameters.Mode.value`) als de platte vorm, omdat het
package beide kan opleveren. Temperaturen blijven in tienden van een graad,
precies zoals het protocol ze levert; pas in de UI wordt er gedeeld door tien.

`Read failed` doet exponential backoff van 30 seconden tot 15 minuten. Vijf
opeenvolgende fouten openen de breaker; één geslaagde lezing sluit hem weer.

### Truma Commands
Het schrijfpad is de plek waar BLE-flakiness wordt opgevangen.

`Command map + guards` is het enige punt waar een UI-sleutel een protocol-write
wordt. De mapping staat bovenaan die node als één tabel. Deze node breidt scènes
uit naar losse commando's, controleert bereik, en blokkeert elektrisch verwarmen
bij lage accu zonder walstroom.

`Queue (single flight)` staat maximaal één BLE-write toe. Herhaalde writes naar
dezelfde sleutel vervangen elkaar in plaats van zich op te stapelen, dus
sliderverkeer kan de verbinding niet platleggen. Bij het uitsturen wordt de
gewenste waarde als `pending` in de state gezet met een token. De UI toont die
direct, en de poller haalt hem weg zodra het apparaat bevestigt. Bevestigt het
apparaat binnen 45 seconden niet, dan rolt de waarde terug en krijg je een melding.

`Unstick the queue` is de vangnetlaag: mocht een write nooit terugkomen én nooit
falen, dan wordt de wachtrij na 60 seconden vrijgegeven.

### Truma Failsafe
Elke minuut drie onafhankelijke controles:

- **Vorstbeveiliging** zet de kachel aan als de cabine onder 6,0 °C zakt terwijl
  hij uit staat.
- **Accubewaking** schakelt terug naar diesel bij SOC onder 35% zonder walstroom.
  Staat standaard **uit**; inschakelen met `flow.set('batteryGuard', true, 'file')`.
- **Stale-data watchdog** markeert de verbinding als down na drie minuten zonder
  verse data, zodat de UI nooit oude waarden toont alsof ze actueel zijn.

Alle drie respecteren een handmatige actie van de afgelopen tien minuten. Zet jij
de kachel bewust uit in de vrieskou, dan zet de vorstbeveiliging hem niet meteen
weer aan; je ziet in plaats daarvan een uitleg in de banner bovenaan.

### Truma Schedule
Regels staan in één array. `Evaluate rules` draait elke minuut en is
edge-triggered: een regel vuurt één keer bij het openen van zijn venster en één
keer bij het sluiten. Daardoor kun je na het startmoment gewoon handmatig
bijstellen zonder dat de volgende minuut je correctie ongedaan maakt.
Vensters over middernacht worden correct afgehandeld.

### Truma Log
Ringbuffer van 200 regels, historie-buffer van 48 uur met één monster per twee
minuten, dagstatistieken en de verbindingsgezondheid. `Replay buffer` tekent de
grafiek na een herstart opnieuw, zodat de Historie-pagina nooit leeg is.

### Truma Bridge (uitgeschakeld bij levering)
Zet deze tab aan zodra MQTT on LAN aanstaat op de Cerbo en je de GX Touch
gesynchroniseerd wilt hebben. Zonder MQTT blijven de nodes "disconnected", wat
verder niets breekt, maar het is rommel in de editor.

Venus OS spiegelt de volledige D-Bus-boom op de lokale MQTT-broker. Dat is
dezelfde data die de GX Touch toont, alleen bereikbaar zonder afhankelijk te zijn
van node-internals die ik hier niet kan verifiëren.

`Learn portal id` haalt het VRM portal-id uit het tweede segment van elk
Venus-topic, dus er staat niets installatiespecifieks hardcoded. De keepalive
elke 25 seconden is verplicht: Venus stopt met publiceren op `N/` topics zestig
seconden na de laatste keepalive.

`GX Touch to command` luistert op de settings-boom en zet een wijziging van het
QML-scherm om in een commando. Het vergelijkt eerst met de laatst gelezen waarde
en negeert alles wat gelijk is, zodat onze eigen spiegelwrites niet als commando
terugkaatsen.

### Truma Debug
Zes taps op de belangrijkste punten in de keten. **Alle debug-nodes staan
uitgeschakeld**, zodat er niets draait tot je er een aanzet met het vierkantje
rechts op de node. Dat scheelt CPU op de Cerbo, wat op dit apparaat merkbaar is.

Elke tap is een pass-through: uitgang 1 draagt het echte bericht ongewijzigd
verder, uitgang 2 voedt alleen de debug-node. Je kunt dus niets breken door er
een aan te zetten.

Volgorde bij het in bedrijf nemen:

| Tap | Wat het je vertelt |
| --- | --- |
| 1. Raw device read | Of BLE en het pairen werken, en welke topics je paneel echt heeft |
| 2. Normalised state | Of de parser jouw topics vindt |
| 3. Outgoing command | Of een knopdruk als `AirHeating.TgtTemp = 220` de deur uit gaat |
| 4. Errors | Alleen warn en error, niet elke logregel |
| 5. MQTT to Venus | Wat er naar de settings-boom gaat, als de GX Touch niet meeloopt |
| 6. Uncaught errors | Vangnet over alle tabbladen, gaat ook naar het logboek |

Tap 1 en 2 zijn wat je nodig hebt bij de eerste verbinding. Tap 3 is wat je nodig
hebt als een knop niets lijkt te doen. Zet ze weer uit zodra het draait.

---

## 3. Hoe de UI is opgebouwd

### Kleur
Alle kleur komt uit tien CSS-variabelen in één site-scoped template
(`Victron theme CSS`). Zodra je `Victron.VenusOS/Theme.qml` erbij kunt pakken,
vervang je die tien waarden en volgt het hele dashboard. Nergens anders staat een
hex-waarde. De Vuetify-tokens worden in dezelfde block overschreven, zodat
ingebouwde widgets zoals notificaties meelopen met het palet.

De defaults die er nu in staan zijn de gui-v2 dark waarden: paginakleur `#0E0E0E`,
panelen `#1B1B1B`, rijen `#262626`, lijnwerk `#333333`, accent `#4790D3`, en de
Victron statuskleuren groen, amber en rood.

### Waarom v1.3 anders is opgebouwd dan v1.2
In v1.2 stond alle opmaak in één site-scoped stylesheet met CSS-variabelen.
Die bereikte de widgets niet, waardoor alles ongestyled rendrede en elke groep
een eigen scrollbalk kreeg. In v1.3 draagt **elke widget zijn eigen `<style>`
met letterlijke kleurwaarden**. Dat is minder elegant maar het werkt gegarandeerd,
ongeacht hoe Dashboard 2.0 zijn CSS afschermt. De kleuren staan nog steeds op één
plek in de generator; in het geëxporteerde JSON staan ze per widget.

Alle groepen zijn volle breedte, want dit dashboard is voor je telefoon. Op een
PC-scherm wordt het één kolom in plaats van uitgesmeerde halve blokken.

### Component-stijl
De GX Touch werkt met platte panelen, hairline randen, geen slagschaduw en een
kleine radius. Dat is in de CSS afgedwongen op `.nrdb-ui-group`. De bediening
gebeurt met segmented controls in plaats van dropdowns, omdat je op een
touchscreen in een camper met één tik wilt kunnen schakelen. Elke knop is
minimaal 46 pixels hoog.

Een knop kent drie toestanden: rust, actief (accent gevuld), en pending
(accent-omlijnd met een langzame puls). Die derde toestand is het verschil tussen
een dashboard dat traag aanvoelt en één dat reageert. Bij `prefers-reduced-motion`
wordt de puls een stippellijn.

### Pagina's
- **Home** — vijf kaarten in één kolom: Status (één regel), Kamer, Energie,
  Water, Ventilator. Hoogtes 2 / 6 / 6 / 5 / 4. Alle knoppen zijn altijd
  klikbaar; of de kachel de parameter rapporteert bepaalt alleen welke knop
  blauw oplicht, nooit of je mag drukken.
- **Schedule** — de regellijst met per regel een aan/uit en verwijderen, plus één
  hoofdschakelaar om het hele schema te pauzeren. Daaronder het formulier.
- **History** — grafiek van cabine, setpoint en boiler over 48 uur, met
  dagstatistieken eronder.
- **Diagnostics** — verbindingsgezondheid, vijf actieknoppen, logvenster en de
  ruwe payload van de laatste uitlezing.

### Responsief
Groepen staan op halve breedte in een grid van twaalf. Onder 600 pixels vallen ze
onder elkaar, krimpt de grote uitlezing en wordt het schemaformulier één kolom.
De temperatuurslider heeft plus- en minknoppen naast zich, omdat een slider op
een telefoon in een rijdende camper onbruikbaar precies is.

### Teksten
Geen technische termen in de interface. "Fan only" in plaats van "Ventilating
mode 5", "Reset the connection" in plaats van "Force reconnect". Foutmeldingen
zeggen wat er gebeurde en wat je eraan kunt doen, zonder excuses.

---

## 4. VRM-integratie

### Toegang
Venus OS Large biedt Node-RED remote aan via VRM. Het dashboard zit op het pad
`/truma`, dus achter de VRM-proxy wordt dat de proxy-URL plus `/truma`.

**Let op, dit is het meest waarschijnlijke struikelblok:** Dashboard 2.0 gebruikt
een websocket-verbinding, en die kan breken achter een pad-prefix. Werkt het
dashboard lokaal wel en via VRM niet, controleer dan in de browserconsole of de
websocket een 404 of 502 geeft. In dat geval is `httpNodeRoot` in `settings.js`
de knop waaraan je draait. Een tunnel via Tailscale of Cloudflare omzeilt het
probleem volledig, omdat er dan geen pad-herschrijving plaatsvindt.

### Data richting VRM
Twee routes, en ze doen iets anders:

1. **Settings-boom** (`/Settings/Truma/*`) — synchroniseert GX Touch en
   web-dashboard. Verschijnt niet als grafiek in VRM.
2. **Retained topic** `truma/state` — het volledige state-object, bruikbaar voor
   elke andere consument aan boord.

Wil je cabinetemperatuur als grafiek in VRM, dan moet die als echt D-Bus
temperature-device geregistreerd worden, niet als setting. Dat is de virtual
device-functionaliteit van `node-red-contrib-victron`. Ik heb dat bewust niet
ingebouwd omdat ik de exacte node-eigenschappen hier niet kon verifiëren, en een
gok die stil faalt is erger dan een ontbrekende feature.

### Beveiliging
Achter VRM zit je login, maar VRM-toegang wordt vaak breder gedeeld dan bedoeld.
Overweeg Node-RED-authenticatie via `adminAuth` en `httpNodeAuth` in
`settings.js`. Een PIN-slot op de scèneknoppen kan ik toevoegen als je dat wilt.

---

## 5. De twee open punten

Ik heb deze bewust niet ingevuld met iets plausibels.

### Alle bedieningen zijn nu gemapt

De discovery-fase is voorbij. De volledige mapping staat in
`Command map + guards` op de tab Truma Commands:

| UI | Schrijft |
| --- | --- |
| Verwarming aan/uit | `RoomClimate.Mode` 3 / 0 |
| Doeltemperatuur | `AirHeating.TgtTemp` (tienden) |
| Fast / Comfort | `AirHeating.Mode` 0 / 1 |
| Ventilator aan | `RoomClimate.Mode` 5, dan `AirCirculation.FanLevel` 0-10 |
| Water 40/60/70 | `WaterHeating.Mode` 0/1/2, dan `WaterHeating.Active` 1 |
| Water uit | `WaterHeating.Active` 0 |
| Boost | `WaterHeating.FasterHeatingMode` 0 / 1 |
| Energiebron | `EnergySrc.DieselLevel` en `EnergySrc.ElectricLevel` |

### Energie is een transactie, geen enkele write

De vijf UI-standen zijn combinaties van twee parameters:

| Stand | Diesel | Elektrisch |
| --- | --- | --- |
| Diesel | 1 | 0 |
| Elektrisch 900 W | 0 | 1 |
| Elektrisch 1800 W | 0 | 2 |
| Diesel + 900 W | 1 | 1 |
| Diesel + 1800 W | 1 | 2 |

De volgorde is conditioneel, niet vast:

1. Gaat elektrisch omlaag, schrijf dat eerst
2. Verandert diesel, schrijf dat daarna
3. Gaat elektrisch omhoog, schrijf dat als laatste

Daarmee kom je nooit boven `max(start, doel)` uit en passeer je nooit een
onbedoelde hybride stand. Van diesel naar elektrisch 1800 gaat de kachel dus
kort helemaal uit in plaats van even op hybride 1800.

De wachtrij behandelt zo'n paar als één transactie: de stappen worden niet
gecoalesceerd, de tweede vertrekt pas als de eerste bevestigd is, en de
pending-state van de UI hangt aan de gecombineerde stand. Faalt een stap, dan
worden de resterende stappen verworpen in plaats van half toegepast.

Water aanzetten werkt hetzelfde, met een minimum van 2 seconden tussen `Mode` en
`Active`.

---

## 6. Wat later verandert bij persistente BLE

De pollinterval van 20 seconden is de enige plek waar het huidige
connect-per-operatie model doorwerkt. Stap je later over op een blijvende
verbinding met GATT-notifications, dan vervalt `inj_poll` en voed je `Normalise`
rechtstreeks vanuit de notification-stroom. De rest van de flows,
de hele UI en het optimistic-UI mechanisme blijven ongewijzigd. Het
correlatie-token dat nu al in elk commando zit is precies wat je dan nodig hebt
om je eigen echo van een paneelwijziging te onderscheiden.

---

## 7. Getest

De logica is buiten Node-RED gesimuleerd met 33 assertions: normalisatie van
beide payload-vormen, commandomapping, bereikbewaking, scène-expansie,
single-flight wachtrij met coalescing, optimistic rollback, backoff en circuit
breaker, alle drie de failsafes inclusief het respecteren van handmatige acties,
edge-triggering van het schema, portal-id detectie, de MQTT-spiegel en het
negeren van eigen echo's. Alle 24 function-nodes en 16 Vue-templates zijn
syntactisch gecontroleerd, plus elf controles op de debug-tab die aantonen dat
de taps de echte berichtenstroom niet onderbreken.

Wat niet getest is en niet getest kán worden zonder de camper: de daadwerkelijke
BLE-communicatie en de veldnamen van de truma-inetx nodes.
