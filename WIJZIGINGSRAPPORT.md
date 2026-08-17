# Wijzigingsrapport — codereview betalingskenmerk-tool

**Datum:** 17 augustus 2026
**Repository:** `betalingskenmerk-tool`
**Betreft:** volledige codereview + oplossen van alle gevonden bugs, gevolgd door een
verificatieronde waarin het rekenwerk is getoetst aan de bron
**Branch:** `master` (gepusht)
**Omvang:** 14 commits, 21 bestanden, +2.884 / −433 regels
**Tests:** van 0 naar 203 (alle groen)

> **Scope.** Dit rapport gaat uitsluitend over de repository `betalingskenmerk-tool`.
> Die bevat inmiddels zes pagina's — Betalingskenmerk, VIES BTW-controle, KvK/SBI
> opzoeken, Belastingrente IB, Belastingrente VpB en Auto BTW privé — die samen als
> één Streamlit-app draaien. Andere tools uit de Bouwman Tools-verzameling zijn
> **niet** bekeken.
>
> Let op de naamgeving: de app presenteert zichzelf intern als "Bouwman Tools"
> (in `app.py` en bovenaan de README), terwijl dat de naam van de héle verzameling is.
> Zie **actiepunt 6**.

---

## 1. Samenvatting in het kort

Het werk bestond uit twee rondes.

**Ronde 1 — codereview.** Tien echte bugs gevonden; negen opgelost, één bewust
ongewijzigd gelaten omdat die een fiscale beslissing vraagt.

**Ronde 2 — verificatie tegen de bron.** Niet de code doorlezen, maar de fiscale regels
erbij pakken en controleren of de code ze volledig toepast. Dat vond twee regels die
nooit in de tool hebben gezeten — en die het zwaarst wegen van alles in dit rapport.

De gevolgen voor de uitkomsten, van zwaar naar licht:

| Wat er misging | Gevolg |
|---|---|
| Vrijstelling bij tijdige aangifte ontbrak volledig | **De tool toonde rente waar niets verschuldigd is** — € 264 op € 10.000 |
| Maximering op 19 weken ontbrak | **tot 2,6× te hoge** renteberekening |
| Het lage BTW-forfait van 1,5% na 4 jaar ontbrak | Oudere auto's rekenden 2,7% — **bijna dubbel** |
| Bijtellingspercentage werd op het berekeningsjaar bepaald | EV's kregen structureel het verkeerde regime |
| Twee datafouten in de VpB-rentetabel | Tot € 1.295 te veel rente op € 100.000 (boekjaar 2012) |
| Rekenmethode week af van de Belastingdienst (dagentelling, afronding) | enkele euro's per aanslag |
| VIES-storingen werden als "niet geldig" getoond | Risico bij de beoordeling van het 0%-tarief bij ICP |

Daarnaast bleek de tool bij ongeveer 1 op de 11 betalingskenmerken een **verzonnen
BSN/RSIN** te tonen, en klopte de kopieerknop-omschrijving alleen voor loonheffing en
omzetbelasting.

De verificatieronde is alleen op de rentepagina's gedaan. Auto BTW privé en
Betalingskenmerk staan nog open — zie actiepunt 9.

---

## 1a. Voor Bram: de versie in DK/Join rekent fout

De code die rond 17 juli 2026 uit GitHub is opgehaald, is commit **`821b575` van
15-07-2026**. Sindsdien is er niets bijgewerkt. In die versie is geverifieerd aanwezig:

```python
(date(2016, 3, 1),  8.05)                          # moet 1-3-2015 zijn; rijen vóór 2014 ontbreken
def _btw_correctie(catalogusprijs, marge, dagen)   # geen ingebruikname → 1,5%-regel ontbreekt
def _bijtelling(..., jaar, dagen)                  # berekeningsjaar i.p.v. datum eerste toelating
```

**De volgende berekeningen zijn in die versie aantoonbaar onjuist:**

| Tool | Wat er misgaat | Omvang |
|---|---|---|
| Belastingrente IB + VpB | **Rekent rente waar niets verschuldigd is.** De vrijstelling bij tijdige aangifte (vóór 1 mei / 1 juni) die ongewijzigd wordt gevolgd, ontbreekt volledig | **€ 264 waar € 0 hoort** op € 10.000 |
| Belastingrente IB + VpB | **De maximering op 19 weken** na ontvangst van de aangifte ontbreekt | **tot 2,6× te hoog** |
| Belastingrente IB + VpB | Rekent met werkelijke dagen / 365; de Belastingdienst rekent 30 dagen per maand / 360 | enkele euro's |
| Belastingrente IB + VpB | Einddatum telt niet mee; rondt niet af op hele euro's | < € 2 |
| Belastingrente IB + VpB | Navorderingsaanslagen worden als gewone aanslag gerekend (6 weken i.p.v. 1 maand) | ~2 weken te veel rente |
| Belastingrente VpB | Boekjaren t/m 2013 vallen terug op 8,25% waar 3% geldt | tot **€ 1.295** te veel op € 100.000 |
| Belastingrente VpB | Periode 1-3-2015 t/m 29-2-2016 rekent 8,15% i.p.v. 8,05% | ~€ 37 op € 100.000 |
| Belastingrente VpB | Startdatum een dag te vroeg bij boekjaren t/m 30-06 of 28-02 | 1 dag rente |
| Auto BTW privé | Bijtelling gebruikt het verkeerde jaarregime | EV's structureel fout, kan honderden euro's per auto zijn |
| Auto BTW privé | BTW-correctie mist de 1,5%-regel na 4 jaar | **bijna dubbel**: € 1.350 i.p.v. € 750 op € 50.000 |
| Auto BTW privé | Schrikkeljaar rekent 100,27% van het forfait | ~0,27% te hoog in 2024, 2028 |
| Betalingskenmerk | Ongeveer 1 op de 11 kenmerken toont een **verzonnen** BSN/RSIN | fout nummer, geen foutmelding |
| VIES | Een storing bij een lidstaat wordt getoond als "niet geldig" | risico bij 0%-tarief ICP |

De twee bovenste regels zijn het ernstigst: die zijn pas bij de verificatieronde
gevonden (§2a) en betreffen regels die nooit in de tool hebben gezeten.

**Wat er moet gebeuren:** de huidige `master` ophalen. Het is dezelfde repository, dus
een `git pull` volstaat — er is geen aparte levering nodig. Daarna geldt actiepunt 4:
nagaan of er met de oude versie voor klanten is gerekend.

---

## 2. Hoe is voorkomen dat er werkende code sneuvelde

Dit was expliciet een randvoorwaarde, dus in deze volgorde gewerkt:

1. **Golden baseline eerst.** De huidige uitvoer van de decoder is over **4.227 invoeren**
   vastgelegd (alle middelcode-combinaties, alle jaarcijfers, alle tijdvakcodes en 4.000
   willekeurige kenmerken).
2. **Daarna pas verplaatsen.** De rekenlogica is uit de Streamlit-pagina's gehaald naar
   losse modules. De extractie is bewezen gedragsidentiek: alle 4.227 invoeren gaven
   dezelfde uitvoer.
3. **Pas toen fixen.** Bij elke fix is opnieuw tegen de baseline vergeleken, met de eis
   dat *alleen* de bedoelde velden veranderen. Bij bug 1 wijzigden 238 invoeren,
   uitsluitend in de velden `rsin`/`rsin9`; bij bug 10 wijzigde precies één
   jaartoewijzing (2017 → 2027).
4. **Eén commit per bug**, zodat elke wijziging los terug te lezen of terug te draaien is.
5. **Naspelen in de draaiende app.** Niet alleen tests: de app is gestart en elke
   gewijzigde pagina is met echte data doorlopen (zie §5).

---

## 2a. Verificatieronde: het rekenwerk tegen de bron

De eerste ronde ging over fouten die je vindt door naar de *code* te kijken. Daarna is
de omgekeerde beweging gemaakt: de fiscale regels erbij pakken en controleren of de code
ze volledig en juist toepast. Dat vindt een ander soort fout — namelijk regels die er
nooit in hebben gezeten, en die je dus ook niet als bug tegenkomt.

**De toetssteen.** De Belastingdienst publiceert rekenvoorbeelden. De nieuwe module
reproduceert die exact: 73 dagen → € 15, en 180 + 22 dagen → € 93 + € 9 = € 102. Daarmee
is de rekenmethode niet langer een interpretatie maar aantoonbaar gelijk aan de bron.

### Twee regels die volledig ontbraken

**Geen rente bij tijdige aangifte.** *"U betaalt geen belastingrente als u voor 1 mei
aangifte doet en wij uw gegevens ongewijzigd overnemen"* — bij VpB is de grens 1 juni.
De tool rekende gewoon door: op € 10.000 verscheen € 264 waar niets verschuldigd is.

**Maximering op 19 weken** na ontvangst van de aangifte, als er niet van wordt afgeweken.
In het voorbeeld van de Belastingdienst rekende de tool 198 dagen waar er 74 hoorden —
**2,6× te hoog**.

Beide vragen informatie die de tool niet had. Er zijn daarom invoervelden bijgekomen:
*datum ontvangst aangifte* (mag leeg blijven) en *aangifte ongewijzigd gevolgd*.

### Drie rekentechnische afwijkingen

| | Belastingdienst | Was |
|---|---|---|
| Dagentelling | 30 dagen per maand, 360 per jaar | werkelijke dagen, 365 |
| Einddatum | telt mee | telde niet mee |
| Afronding | naar beneden op hele euro's, per tariefperiode | centen |

Dat de afronding **per tariefperiode** gebeurt en niet over het totaal blijkt uit hun
eigen voorbeeld: 93 + 9 = 102, terwijl 93,75 + 9,93 zou afronden naar 103.

### Naar aanleiding van de rekenmodule-specificatie

Op de specificatie die tijdens dit traject is aangeleverd, zijn drie zaken doorgevoerd:

- **Navorderingsaanslag** — rente tot 1 maand na de dagtekening in plaats van 6 weken.
  Bij navordering op eigen verzoek geldt daarnaast een maximum van 12 weken na het
  verzoek. Beide pagina's hebben nu een keuze *definitieve aanslag / navorderingsaanslag*.
- **VpB voorlopige aanslag** — rente kan ook worden voorkomen door tijdig om een
  voorlopige aanslag te verzoeken die conform wordt opgelegd.
- **Bug in de startdatum** — die werd berekend als boekjaar-einde + 6 maanden + 1 dag.
  Bij een boekjaar t/m 30-06 of 28-02 kwam dat een dag te vroeg uit, omdat 30 juni op
  30 december wordt afgebeeld. De specificatie formuleert het in hele maanden ("vanaf
  de 7e maand na het boekjaar"); die formulering is overgenomen en lost meteen het
  randgeval op van een boekjaar dat midden in een maand eindigt.

Beide pagina's tonen nu een uitklapblok met alle uitgangspunten en de reden van de
einddatum (`vrijstelling` / `19-wekenregel` / `6-wekenregel` / `navordering` /
`bovengrens`), zodat een fiscalist de berekening kan narekenen.

> **De specificatie spreekt zichzelf tegen.** §11 zegt: per tariefperiode afronden. De
> pseudocode in §12 telt eerst op en rondt daarna één keer af. Dat geeft € 103 waar de
> Belastingdienst € 102 publiceert. §11 heeft gelijk en is gevolgd; §12 moet worden
> gecorrigeerd voordat de specificatie wordt uitgeleverd — een ontwikkelaar pakt de
> pseudocode. Zie **actiepunt 5**.

**Wat wél klopte:** de VpB-startdatum voor reguliere boekjaren, en de drie
regressiecontroles uit §9 van de specificatie (73, 77 en 202 dagen) komen exact uit.

**Nog niet gedekt:** de verificatieronde is alleen op de rentepagina's uitgevoerd. Auto
BTW privé en Betalingskenmerk staan nog open — zie **actiepunt 9**.

---

## 3. Wat is aangepast

### 3.1 Betalingskenmerk

**Bug 1 — 11-proef met restwaarde 10 gaf een RSIN van 10 cijfers** · commit `412788f`

Bij de 11-proef kan de uitkomst 10 zijn. Dat betekent dat er géén geldig BSN/RSIN bestaat.
De oude code plakte letterlijk "10" achter de acht cijfers, wat een verzonnen nummer van
10 cijfers opleverde. Dat werd getoond als bijvoorbeeld `1000.00.0610` en ging ook naar de
KvK-API. Dit trof ongeveer 1 op de 11 invoeren.

Nu: geen RSIN, maar de melding dat het kenmerk waarschijnlijk verkeerd is overgenomen.
Soort, jaar en tijdvak blijven gewoon leesbaar en de KvK-opzoeking wordt overgeslagen.

**Bug 3 — de boekhoudomschrijving klopte alleen voor LH en OB** · commit `4116c69`

De omschrijving op de kopieerknop — de kernfunctie van de tool — werd voor élke soort
volgens hetzelfde sjabloon opgebouwd:

| | Vóór | Nu |
|---|---|---|
| Omzetbelasting | `Afdr. OB 1e kwartaal 2025` | *ongewijzigd* |
| Inkomstenbelasting | `Afdr. IB — 2025` | `Aanslag IB 2025` |
| Vennootschapsbelasting | `Afdr. VpB Boekjaar 2024 2025` | `Aanslag VpB boekjaar 2024` |
| Zorgtoeslag | `Afdr. ZT — 2025` | `Zorgtoeslag 2025` |

Alle 1.526 bestaande LH/OB-omschrijvingen zijn byte-identiek gebleven.

**Bug 10 — het jaar kon niet vooruit kijken** · commit `cf5d04e`

Het jaarvenster liep tot en met het huidige jaar. Een voorlopige aanslag voor volgend jaar
— die in het najaar al de deur uit gaat — kwam daardoor tien jaar te vroeg uit: in 2026
werd jaarcijfer 7 gelezen als 2017 in plaats van 2027. Het venster is nu
`[peiljaar−8, peiljaar+1]` en werkt ook over decenniumgrenzen (in 2029 hoort cijfer 0 bij
2030, niet bij 2020 — daar ging de oude opzet ook de mist in).

### 3.2 Belastingrente IB en VpB

**Bug 4 — de tarievencontrole las álle datums op de pagina** · commit `d3b3326`

De automatische check verzamelde met een reguliere expressie elke datum op
belastingdienst.nl, inclusief einddatums (`31-12-2025`) en datums buiten de tabel. De
waarschuwing vuurt op dit moment nog niet, maar zou voorspelbaar vals alarm geven zodra de
Belastingdienst een einddatum bij de 2026-regel zet. Een waarschuwing die vals alarm geeft,
wordt genegeerd.

De check leest nu per tabelrij de ingangsdatum en het percentage, en kent de twee tabellen
apart (algemeen versus vennootschapsbelasting). Nieuw: hij signaleert nu ook een
**percentage dat met terugwerkende kracht is herzien** — dat gebeurt bij belastingrente
regelmatig en werd voorheen helemaal niet opgemerkt.

**Bijvangst: twee datafouten in de VpB-tarieventabel** · zelfde commit

Deze kwamen pas aan het licht toen de nieuwe check de tabel regel voor regel tegen de bron
legde. Beide geverifieerd bij de Belastingdienst:

| In de code stond | Officieel | Gevolg |
|---|---|---|
| ingang 8,05% op **1-3-2016** | 1-3-**2015** t/m 31-8-2016 | periode 1-3-2015 t/m 29-2-2016 rekende 8,15% i.p.v. 8,05% |
| alle rijen vóór 1-4-2014 **ontbraken** | 1-1-2013 t/m 31-3-2014 → **3%** | viel terug op 8,25% — bijna drie keer te hoog |

Effect op een aanslag van €100.000:

| Boekjaar | Dagtekening | Vóór | Na | Verschil |
|---|---|---|---|---|
| 2012 | 01-06-2014 | € 4.362,33 | € 3.067,81 | **− € 1.294,52** |
| 2013 | 01-06-2015 | € 4.309,45 | € 4.272,74 | − € 36,71 |
| 2014 | 01-09-2016 | € 6.318,36 | € 6.301,92 | − € 16,44 |
| 2023 | 01-06-2025 | € 3.436,99 | € 3.436,99 | € 0,00 |

**Recente jaren wijzigen dus niet.** Alleen berekeningen over oudere boekjaren waren fout.

**Bijvangst: rentepercentages werden verkeerd weergegeven** · commit `0f55c2c`

Gevonden bij het naspelen in de draaiende app. De samenvattingstegel rondde af op hele
procenten: 6,5% werd getoond als "6%", 7,5% door bankiersafronding als "8%" en 0,01% als
"0%". De detailregels eronder toonden wél de juiste waarde, dus de tegel sprak zichzelf
tegen. De berekening zelf was altijd goed — dit was puur weergave.

**Rekenmethode en ontbrekende regels** · commits `faae4e3` en `e026c8e`

De zwaarste bevindingen op deze pagina's komen uit de verificatieronde en staan
uitgewerkt in **§2a**: de ontbrekende vrijstelling bij tijdige aangifte, de ontbrekende
maximering op 19 weken, de afwijkende dagentelling en afronding, de navorderingsaanslag
en de dagfout in de startdatum bij bepaalde gebroken boekjaren.

De rekenlogica staat nu in `_rente.py`, los van Streamlit, met 42 tests waarvan drie de
rekenvoorbeelden van de Belastingdienst tot op de euro reproduceren.

### 3.3 Auto BTW privé

**Bug 5 — het bijtellingspercentage werd op het verkeerde jaar bepaald** · commit `34fefe3`

Het bijtellingspercentage ligt vanaf de eerste toelating **60 maanden vast**. De code
bepaalde het op het *berekeningsjaar*. Een EV uit 2021 (12% tot €40.000) kreeg daardoor het
2025-regime opgelegd (16% tot €30.000). De datum eerste toelating werd al bij het RDW
opgehaald, maar werd alleen voor het bouwjaar-label gebruikt.

Nu wordt die datum volledig gebruikt. Loopt de 60-maandstermijn midden in het jaar af, dan
wordt de periode gesplitst en krijgt elk deel zijn eigen regime. In de app is nu zichtbaar
tot wanneer het regime vastligt.

Ook is de nulemissietabel gecorrigeerd — zie **openstaand punt A** hieronder.

**Bug 6 — het lage BTW-forfait van 1,5% ontbrak volledig** · zelfde commit

1,5% geldt niet alleen voor marge-auto's, maar ook zodra het jaar van ingebruikname plus de
vier jaren daarna voorbij zijn. Die regel zat er niet in, waardoor oudere auto's
structureel op 2,7% bleven staan. Op een catalogusprijs van €50.000 scheelt dat
€1.350 versus €750 per jaar.

De datum tenaamstelling wordt nu als ingebruikname gebruikt. Is die onbekend, dan blijft
2,7% gelden — bewust niet gokken in het voordeel van de klant.

**Bug 7 — schrikkeljaar leverde meer dan een vol jaar op** · zelfde commit

`dagen / 365` gaf bij 366 dagen 100,27% van het forfait. Nu gekapt op 1,0.

### 3.4 VIES BTW-controle

**Bug 8 — een storing werd getoond als "niet geldig"** · commit `5cbcc54`

De VIES-API antwoordt **altijd** met HTTP 200, ook als een lidstaat onbereikbaar is. Het
veld `isValid` staat dan op false en `userError` bevat de reden. De code keek alleen naar
`isValid`, waardoor `MS_UNAVAILABLE`, `SERVICE_UNAVAILABLE`, `TIMEOUT`, `VAT_BLOCKED` en
`IP_BLOCKED` allemaal als een rood **"✗ Niet geldig"** verschenen.

Voor de beoordeling van het 0%-tarief bij intracommunautaire leveringen is *"de Duitse
dienst is tijdelijk plat"* iets heel anders dan *"dit nummer bestaat niet"*. Er is nu een
derde status: **"⚠ Niet gecontroleerd"**, met uitleg en het advies later opnieuw te
proberen.

Het antwoordformaat is bij de dienst zelf nagelopen en wordt door een test bewaakt.

**Bug 9 — foutresultaten werden een uur bewaard** · zelfde commit

Netwerkfouten werden als resultaat gecachet. Eén hik maakte een BTW-nummer daarmee een uur
lang oncontroleerbaar, ook na herladen. Geldt nu ook voor de KvK- en
belastingdienst-aanroepen.

**Meegenomen: invoervalidatie** · zelfde commit

Omdat deze functie toch herschreven werd: de invoer wordt nu gevalideerd. Tekens als
`< > = /` bleven voorheen staan en belandden zowel in de opgevraagde URL als in de HTML van
de resultaatpagina. In de draaiende app gecontroleerd dat `nl<img src=x onerror=alert(1)>`
nu wordt geweigerd. Ook worden `GR`, `UK` en `GB` nu herkend als `EL` respectievelijk `XI`.

---

## 4. Wat is bewust NIET aangepast

**Middelcodes 85 t/m 88** — `MIDDEL2_LABEL` kent deze als Eurovignet en MOA vrachtwagens,
maar de VpB-tak vangt de hele range 80–96 af en gaat vóór de tabel. Daardoor worden die
vier codes nu als Vennootschapsbelasting getoond. Eén van beide klopt niet.

Dit is een fiscaal-inhoudelijke vraag, geen technische. Het gedrag is daarom **exact
gelaten zoals het was**, het conflict is uitgebreid in de code gedocumenteerd, en er is een
test die bewaakt dat het niet ongemerkt verschuift. Zie **actiepunt 2**.

---

## 5. Hoe het is gecontroleerd

Naast de 203 tests is de app gestart en met echte data doorlopen:

| Pagina | Testgeval | Uitkomst |
|---|---|---|
| Auto BTW privé | kenteken `H507BX` (VW Up!, eerste toelating 14-01-2020) | BTW-correctie € 380,97 en bijtelling € 3.104,20 — gelijk aan de losse berekening |
| Auto BTW privé | PDF genereren | werkt, met de nieuwe velden eerste toelating en ingebruikname |
| VIES | `NL820646660B01` | ✓ Geldig · ABN AMRO BANK N.V. · adres · afgeleid RSIN 8206.46.660 |
| VIES | `nl<img src=x onerror=alert(1)>` | geweigerd, 0 geïnjecteerde elementen |
| Betalingskenmerk | `0100000061500210` (11-proef gaat niet op) | "Niet af te leiden", rest decodeert door |
| Betalingskenmerk | IB / VpB / toeslag | `Aanslag IB 2025` · `Aanslag VpB boekjaar 2024` · `Zorgtoeslag 2025` |
| Belastingrente | aangiftedatum onbekend | € 697 + "dit is een bovengrens" |
| Belastingrente | aangifte 20-04-2025, ongewijzigd gevolgd | **Geen belastingrente verschuldigd** |
| Belastingrente | afgeweken van de aangifte | € 697 (180 d × 6,5% = € 325 + 268 d × 5% = € 372) |
| Belastingrente VpB | navorderingsaanslag | € 681 — einddatum 1 maand i.p.v. 6 weken |
| Belastingrente VpB | tijdig verzochte voorlopige aanslag | **Geen belastingrente verschuldigd** |

De belangrijkste controle staat in de testsuite: `tests/test_rente.py` reproduceert de
rekenvoorbeelden die de Belastingdienst zelf publiceert, tot op de euro. Zolang die
tests groen zijn, is de rekenmethode aantoonbaar gelijk aan de bron.

Drie tests draaien over het netwerk en vergelijken de hardgecodeerde tabellen en het
antwoordformaat met de bron (belastingdienst.nl en VIES). Die hebben de twee
VpB-datafouten gevonden en blijven signaleren zodra de bron wijzigt.

Zelf controleren:

```bash
python -m pytest tests/ -q
```

---

## 6. Wat we hierna nog gaan doen

Uit de review kwamen ook punten die **nog niet zijn opgepakt**. Geen van deze veroorzaakt
verkeerde bedragen; het gaat om robuustheid, privacy en onderhoudbaarheid.

### Kwetsbaarheden (nog te doen)

| Nr | Punt | Ernst |
|---|---|---|
| K1 | Externe API-data (KvK-namen, SBI-omschrijvingen, RDW-velden) gaat ongeëscaped de HTML in | Laag — bronnen zijn betrouwbaar, maar het patroon deugt niet |
| K2 | Het kenteken wordt server-side niet gevalideerd; alleen de lengte wordt gecontroleerd. Willekeurige tekens komen in de RDW-querystring | Middel |
| K3 | De KvK-API-sleutel wordt naar een URL uit het antwoord gestuurd zonder te controleren dat die van `api.kvk.nl` komt | Laag |
| K4 | De devcontainer start Streamlit met XSRF-bescherming uit (standaard Codespaces-sjabloon) | Laag, alleen lokaal |
| K5 | **Privacy/AVG:** uit een kenmerk van een particulier rolt een BSN. Die wordt getoond, een uur gecachet en als zoekterm naar de KvK gestuurd — terwijl de KvK particulieren niet kent. Op Streamlit Community Cloud loopt dat over infrastructuur van derden | **Bespreken** |

### Opruimwerk (nog te doen)

- **Duplicatie:** `nl_euro`, `nl_date`, `tarief_op` en `bereken` staan identiek in beide
  rentepagina's; het CSS-blok is vijf keer gekopieerd; het KvK-sleutelblok twee keer.
  Scheelt zo'n 200 regels.
- **Overbodige rerun:** de Betalingskenmerk-pagina doet een extra volledige herberekening
  bij elke interactie om een laadtekst te tonen.
- **Knoppen die niets doen:** "Controleer →" (VIES) en "Zoeken →" (KvK) worden nooit
  uitgelezen; die pagina's reageren direct op de invoer.
- **Fragiele veldtoegang:** enkele plekken crashen bij een onverwacht antwoordformaat.
- **Geen controle op het kenmerk zelf:** positie 1 is een controlecijfer over de rest en
  wordt genegeerd. Wie één cijfer verkeerd overtypt, krijgt nu een geloofwaardig ogend maar
  verkeerd resultaat zonder waarschuwing.

---

## 7. Actielijst

### Voor Sylvain — vraagt jouw fiscale oordeel

- [ ] **1. Controleer de nulemissiepercentages voor de bijtelling.**
      De reeks in `_auto_calc.py` is gecorrigeerd naar 4% (2017/2018, geen plafond),
      4% tot €50.000 (2019), 8% tot €45.000 (2020), 12% tot €40.000 (2021),
      16% tot €35.000 (2022) en 16% tot €30.000 (2023–2025).
      **De officiële overzichtspagina gaf een 404, dus deze waarden zijn níet bij de bron
      nageslagen.** Dit staat als waarschuwing in de code. Controleer ze voordat je de tool
      hiermee bij klanten inzet.

- [ ] **2. Zoek uit wat middelcodes 85 t/m 88 werkelijk zijn.**
      Eurovignet/MOA vrachtwagens, of toch Vennootschapsbelasting? De
      [Specificatie Betalingskenmerk_bepaling v1.5](https://odb.belastingdienst.nl/wp-content/uploads/2025/07/Specificatie-Betalingskenmerk_bepaling_1.5.pdf)
      zou dit moeten beslechten. Laat het antwoord weten, dan is het in vijf minuten
      aangepast.

- [ ] **3. Neem een besluit over de BSN-verwerking (punt K5).**
      Wil je dat de tool BSN's toont, cachet en naar de KvK stuurt? En is Streamlit
      Community Cloud daarvoor de juiste plek? Dit is een verwerkersvraag, geen
      technische.

- [ ] **0. Laat Bram de huidige `master` ophalen. Dit gaat vóór al het andere.**
      De versie in DK/Join is van 15-07-2026 en rekent aantoonbaar fout — zie §1a.
      Zolang die draait, worden er verkeerde bedragen geproduceerd in de beveiligde
      omgeving.

- [ ] **4. Controleer of eerdere berekeningen herzien moeten worden.**
      Zijn er klanten waarvoor met de oude versie is gerekend? Let op: dat kan zowel via
      jouw lokale versie als via DK/Join zijn gebeurd.
      - Belastingrente VpB over **boekjaren t/m 2013** — die was aantoonbaar te hoog.
      - Bijtelling van **elektrische auto's** — die kreeg het verkeerde jaarregime.
      - BTW-correctie van auto's die **langer dan 4 jaar in gebruik** zijn — die stond op
        2,7% in plaats van 1,5%.

- [ ] **5. Corrigeer §12 van de rekenmodule-specificatie vóór die wordt uitgeleverd.**
      De pseudocode telt eerst alle deelbedragen op en rondt daarna één keer af
      (`total_interest += interest` … `return floor(total_interest)`). Dat geeft € 103
      waar de Belastingdienst € 102 publiceert. §11 zegt het goed — per tariefperiode
      afronden — maar een ontwikkelaar implementeert de pseudocode. Zolang §12 niet is
      aangepast, bouwt Bram's team de fout in.

- [ ] **6. Besluit hoe deze app moet heten.**
      De repository heet `betalingskenmerk-tool`, maar bevat inmiddels zes pagina's en
      presenteert zichzelf als "Bouwman Tools" — de naam van de héle verzameling, waarvan
      dit er één is. Dat leidt tot verwarring over wat waar zit. Het speelt op twee plekken:
      - `app.py` regel 4: `page_title="Bouwman Tools"` (bepaalt de browsertabtitel)
      - `README.md` regel 1: `# Bouwman Tools — Belastingtools`

      Denk ook aan wat er in `CLAUDE.md` staat: het plan is deze pagina's later onder te
      brengen in de WWFT multi-page app. Dan wordt de naamgeving nóg relevanter. Geef aan
      welke naam je wilt, dan pas ik beide plekken aan.

### Voor de volgende sessie — technisch, geen besluit nodig

- [ ] 7. Kwetsbaarheden K1 t/m K4 oplossen (klein werk, grotendeels mechanisch)
- [ ] 8. Knoppen die niets doen weghalen of laten werken
- [ ] 9. **Verificatieronde afmaken.** Alleen de rentepagina's zijn tegen de bron
      getoetst. Auto BTW privé en Betalingskenmerk staan nog open. Gezien wat die ronde
      bij de rente opleverde — twee volledig ontbrekende regels — is de verwachting dat
      daar ook iets te vinden is. Dit is het punt met de hoogste te verwachten opbrengst.
- [ ] 10. Controlecijfer van het betalingskenmerk valideren, zodat een typefout wordt
      opgemerkt in plaats van stilzwijgend een verkeerd RSIN op te leveren. Vraagt
      specificatie v1.5, net als actiepunt 2.
- [ ] 11. Duplicatie opruimen (CSS, opmaak, KvK-sleutelblok). **Bewust achteraan gezet:**
      het gaat vrijwel volledig om opmaak, en dat is juist het deel dat door de UI van
      DK/Join wordt vervangen. Loont pas als besloten is waar de code uiteindelijk woont.

### Ter kennisgeving voor Bram

- [ ] 12. De tarievencontrole waarschuwt vanaf nu automatisch als belastingdienst.nl
      afwijkt van de tabellen in de code — zowel bij een nieuwe periode als bij een
      met terugwerkende kracht herzien percentage. Er hoeft dus niet meer handmatig te
      worden nagelopen, maar de melding moet wél worden opgevolgd.

---

## 8. Commitoverzicht

| Commit | Onderwerp |
|---|---|
| `d5763e8` | Testvangnet: decodeerlogica geëxtraheerd + 32 regressietests (geen gedragswijziging) |
| `412788f` | Bug 1 — 11-proef restwaarde 10 |
| `4116c69` | Bug 3 — boekhoudomschrijving per soort |
| `cf5d04e` | Bug 10 — jaarreconstructie |
| `d3b3326` | Bug 4 — tarievencontrole + twee datafouten VpB-tabel |
| `34fefe3` | Bugs 5, 6, 7 — bijtelling en BTW-correctie auto |
| `5cbcc54` | Bugs 8, 9 — VIES-storingen en caching |
| `0f55c2c` | Percentageweergave 6,5% / 7,5% |
| `19edb8e` | README bijgewerkt |
| `eca4039` | Wijzigingsrapport toegevoegd |
| `e500b3d` | Rapporttitel gecorrigeerd (scope) |
| `11541fc` | Vastgelegd dat de versie in DK/Join fout rekent |
| `faae4e3` | **Verificatieronde** — belastingrente rekende volgens een andere methode dan de Belastingdienst |
| `e026c8e` | **Specificatie verwerkt** — navordering, voorlopige aanslag, maandtelling boekjaar |

Elke commitmelding beschrijft wat er misging, wat het gevolg was en hoe is gecontroleerd
dat er niets anders is gewijzigd.
