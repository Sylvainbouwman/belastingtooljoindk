# Wijzigingsrapport — codereview Bouwman Tools

**Datum:** 17 augustus 2026
**Betreft:** volledige codereview van de Streamlit-app + oplossen van alle gevonden bugs
**Branch:** `master` (gepusht)
**Omvang:** 9 commits, 18 bestanden, +1.686 / −329 regels
**Tests:** van 0 naar 169 (alle groen)

---

## 1. Samenvatting in het kort

De volledige codebase is doorgenomen op fouten en kwetsbaarheden. Er zijn **tien echte
bugs** gevonden; negen daarvan zijn opgelost, één is bewust ongewijzigd gelaten omdat
die een fiscale beslissing vraagt.

Vier bugs leidden tot **verkeerde bedragen of verkeerde conclusies** in de tool:

| Wat er misging | Gevolg |
|---|---|
| Bijtellingspercentage werd op het berekeningsjaar bepaald | EV's kregen het verkeerde percentage; een EV uit 2021 werd op het 2025-regime gerekend |
| Het lage BTW-forfait van 1,5% na 4 jaar ontbrak | Oudere auto's rekenden structureel 2,7% — bijna dubbel |
| Twee datafouten in de VpB-rentetabel | Tot €1.295 te veel rente op een aanslag van €100.000 (boekjaar 2012) |
| VIES-storingen werden als "niet geldig" getoond | Risico bij de beoordeling van het 0%-tarief bij ICP-leveringen |

Daarnaast bleek de tool bij ongeveer 1 op de 11 betalingskenmerken een **verzonnen
BSN/RSIN** te tonen, en klopte de kopieerknop-omschrijving alleen voor loonheffing en
omzetbelasting.

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

Naast de 169 tests is de app gestart en met echte data doorlopen:

| Pagina | Testgeval | Uitkomst |
|---|---|---|
| Auto BTW privé | kenteken `H507BX` (VW Up!, eerste toelating 14-01-2020) | BTW-correctie € 380,97 en bijtelling € 3.104,20 — gelijk aan de losse berekening |
| Auto BTW privé | PDF genereren | werkt, met de nieuwe velden eerste toelating en ingebruikname |
| VIES | `NL820646660B01` | ✓ Geldig · ABN AMRO BANK N.V. · adres · afgeleid RSIN 8206.46.660 |
| VIES | `nl<img src=x onerror=alert(1)>` | geweigerd, 0 geïnjecteerde elementen |
| Betalingskenmerk | `0100000061500210` (11-proef gaat niet op) | "Niet af te leiden", rest decodeert door |
| Betalingskenmerk | IB / VpB / toeslag | `Aanslag IB 2025` · `Aanslag VpB boekjaar 2024` · `Zorgtoeslag 2025` |
| Belastingrente VpB | boekjaar 2024, dagtekening vandaag | € 697,53 · tarief toont nu "5% / 6,5%" |

Twee tests draaien over het netwerk en vergelijken de hardgecodeerde tabellen met de bron
(belastingdienst.nl en VIES). Die hebben de twee VpB-datafouten gevonden en blijven
signaleren zodra de bron wijzigt.

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

- [ ] **4. Controleer of eerdere berekeningen herzien moeten worden.**
      Zijn er klanten waarvoor met de oude versie is gerekend?
      - Belastingrente VpB over **boekjaren t/m 2013** — die was aantoonbaar te hoog.
      - Bijtelling van **elektrische auto's** — die kreeg het verkeerde jaarregime.
      - BTW-correctie van auto's die **langer dan 4 jaar in gebruik** zijn — die stond op
        2,7% in plaats van 1,5%.

### Voor de volgende sessie — technisch, geen besluit nodig

- [ ] 5. Kwetsbaarheden K1 t/m K4 oplossen (klein werk, grotendeels mechanisch)
- [ ] 6. Duplicatie opruimen: gedeelde modules voor opmaak, CSS en het KvK-sleutelblok
- [ ] 7. Knoppen die niets doen weghalen of laten werken
- [ ] 8. Controlecijfer van het betalingskenmerk valideren, zodat een typefout wordt
      opgemerkt in plaats van stilzwijgend een verkeerd RSIN op te leveren

### Ter kennisgeving voor Bram

- [ ] 9. De tarievencontrole waarschuwt vanaf nu automatisch als belastingdienst.nl
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

Elke commitmelding beschrijft wat er misging, wat het gevolg was en hoe is gecontroleerd
dat er niets anders is gewijzigd.
