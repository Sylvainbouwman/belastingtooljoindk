# Belastingtool JoinDK — overzicht voor Bram

**Datum:** 18 augustus 2026
**Repository:** `Sylvainbouwman/belastingtooljoindk` (heette tot 18-08-2026 `betalingskenmerk-tool`)
**Live testomgeving:** [belastingtooljoindk.streamlit.app](https://belastingtooljoindk.streamlit.app)

---

Hoi Bram,

Hieronder staat wat er in deze repository zit, wat er sinds jullie ophaalmoment is
veranderd, en wat er van jou of je team nodig is. De details staan in
[`WIJZIGINGSRAPPORT.md`](WIJZIGINGSRAPPORT.md); ik verwijs per punt naar de paragraaf.

## Eerst het onderscheid, want dat wordt door elkaar gehaald

**Deze repository is de Belastingtool.** Eén Streamlit-app met zes rekentools erin. Dit is
de code die bij DK/Join in de beveiligde omgeving wordt ingebouwd.

**bouwman.tools is iets anders.** Dat is een portaal waar Sylvain allerlei losse tools bij
elkaar zet, achter een login, zodat collega's ze kunnen uitproberen. De Belastingtool is
daar sinds 18-08-2026 als tegel te vinden, maar die portal is alleen een verzamelplek voor
intern testen — geen onderdeel van deze code en geen leveringsobject. Kijk je naar wat er
naar DK/Join gaat, dan is deze repository het enige dat telt.

De naam "Bouwman Tools" stond eerder ook in deze app zelf. Dat was onjuist en is
rechtgezet: de app heet **Belastingtool JoinDK**.

---

## De zes tools in deze repository

**1. Betalingskenmerk** — `pages/Betalingskenmerk.py`
Decodeert een 16-cijferig betalingskenmerk naar belastingmiddel, jaar, tijdvak en
BSN/RSIN, en levert een omschrijving voor de boekhouding. Getoetst aan de officiële
*Specificatie Betalingskenmerk_bepaling v1.5*: alle 27 voorbeelden uit dat document staan
als test vastgelegd. Het controlecijfer op positie 1 wordt gevalideerd, dus een verkeerd
overgetypt cijfer wordt geweigerd in plaats van stilzwijgend tot een verkeerd RSIN te
leiden. Zie §2b.

**2. VIES BTW-controle** — `pages/VIES_BTW_Controle.py`
Controleert een Europees BTW-nummer bij de EU-database en leidt bij NL-nummers het RSIN af.
Onderscheidt drie uitkomsten: geldig, niet geldig, en *niet gecontroleerd*. Dat laatste is
wezenlijk: VIES antwoordt bij een storing met HTTP 200 en `isValid: false`, wat eerder als
"ongeldig nummer" werd getoond. Zie §3.4.

**3. KvK / SBI opzoeken** — `pages/KvK_SBI_Opzoeken.py`
Zoekt een bedrijf op naam, KvK-nummer of RSIN en toont rechtsvorm, handelsnamen,
registratiedatum, werkzame personen, adres en SBI-activiteiten. Let op de kosten: zoeken is
gratis, elk opgevraagd basisprofiel kost € 0,02. De pagina haalt een profiel daarom alleen
op voor het bedrijf dat je aanklikt.

**4. Belastingrente IB** — `pages/Belastingrente_IB.py`
**5. Belastingrente VpB** — `pages/Belastingrente_VpB.py`
Berekenen de belastingrente volgens de methode van de Belastingdienst: 30 dagen per maand,
360 dagen per jaar, per tariefperiode naar beneden afgerond. De testsuite reproduceert de
rekenvoorbeelden die de Belastingdienst zelf publiceert, tot op de euro. Herkennen de
vrijstelling bij tijdige aangifte, de maximering op 19 weken, navordering, en bij VpB het
tijdig verzoek om een voorlopige aanslag en gebroken boekjaren. Zie §2a en §3.2.

**6. Auto BTW privé** — `pages/Auto_BTW_Prive.py`
BTW-correctie privégebruik en bijtelling van een zakelijke auto, met kentekenlookup via het
RDW. De BTW-correctie rekent naar maanden, conform het rekenvoorbeeld van de
Belastingdienst. Het bijtellingspercentage ligt 60 maanden vast vanaf de eerste toelating.
De nulemissiereeks 2017 t/m 2026 is getoetst aan de jaarpagina's én aan de wettekst.
Inclusief de youngtimerregeling en de waterstofuitzondering. Zie §2b en §2c.

**Rekenlogica staat los van de UI.** `_kenmerk.py`, `_rente.py`, `_auto_calc.py`,
`_vies.py`, `_kvk.py` en `_format.py` bevatten geen Streamlit-code en zijn dus los testbaar
en los overneembaar. Bij elke fiscale waarde staat de vindplaats in een commentaar: een
jaarpagina, een wetsartikel of een paragraaf uit een specificatie. Op dit moment 366 tests,
alle groen.

---

## Wat er van jou nodig is

### 1. Haal de huidige `master` op. Dit gaat vóór al het andere.

De code die rond 17 juli is opgehaald is commit `821b575` van 15-07-2026. **Die versie
rekent aantoonbaar fout.** §1a somt dertien punten op met de bedragen erbij; de
verificatieronde van 18 augustus vond daar nog vier bij, die in §2b staan en in diezelfde
oude versie zitten. De zwaarste:

- de vrijstelling bij tijdige aangifte ontbreekt volledig, waardoor er rente wordt berekend
  waar niets verschuldigd is (€ 264 waar € 0 hoort, op € 10.000)
- de maximering op 19 weken ontbreekt, wat tot 2,6× te hoge rente geeft
- middelcodes 85 t/m 88 worden als vennootschapsbelasting gelezen, met een verzonnen RSIN
  erbij: 810360007 waar 036000012 hoort
- de nulemissiekorting voor 2026 ontbreekt, dus een te hoge bijtelling in het lopende jaar
- de BTW-correctie mist de 1,5%-regel na vier jaar, wat bijna een verdubbeling geeft

**De repository is omgedopt**: `betalingskenmerk-tool` heet nu `belastingtooljoindk`. Je
bestaande clone blijft werken via de doorverwijzing van GitHub, maar werk de remote bij:

```
git remote set-url origin https://github.com/Sylvainbouwman/belastingtooljoindk.git
```

### 2. Corrigeer §12 van de rekenmodule-specificatie vóór uitlevering

De pseudocode telt alle deelbedragen op en rondt daarna één keer af. Dat geeft € 103 waar de
Belastingdienst € 102 publiceert. §11 van dezelfde specificatie zegt het goed — per
tariefperiode afronden — maar een ontwikkelaar implementeert de pseudocode. Zolang §12 niet
is aangepast, bouwt je team de afrondingsfout in.

---

## Ter kennisgeving

**De tarievencontrole waarschuwt vanaf nu automatisch.** Eens per maand wordt de
tarieventabel op belastingdienst.nl uitgelezen en regel voor regel vergeleken met de
tabellen in de code. Dat signaleert zowel een nieuwe periode als een percentage dat met
terugwerkende kracht is herzien. Er hoeft dus niet meer handmatig te worden nagelopen, maar
**de melding moet wél worden opgevolgd**.

**De Specificatie Betalingskenmerk_bepaling v1.5 is op vier punten onvolledig of
inconsistent.** Relevant omdat jullie er van implementeren:

1. Het **controlecijfer op positie 1** wordt niet beschreven. Er staat "berekenen m.b.v.
   modulus-11 algoritme, zie onderaan", maar onderaan staat alleen de elfproef voor het
   BSN/RSIN. De regel die op alle 27 voorbeelden klopt staat gedocumenteerd in
   `controlecijfer()` in `_kenmerk.py`.
2. **Drie voorbeelden zijn inconsistent met zichzelf**: bij `036000012F0314240`,
   `036000012A0414121` en `036000012N2100030` verschilt het jaartal één cijfer tussen het
   aanslagnummer en het gedrukte kenmerk. De overige 24 zijn exact reproduceerbaar uit de
   regels van het document.
3. Er is **geen codetabel voor het SOORT-cijfer**. Uit de voorbeelden blijkt alleen
   0 = voorlopige aanslag en 6 = definitieve aanslag.
4. Bij paragraaf 4 staat **"pos 3"** waar "pos 13" wordt bedoeld (B-JAVO bij A-MIDDEL = W).

**Privacy.** Uit een betalingskenmerk van een particulier rolt een BSN. Dat nummer wordt
getoond met een label erbij, maar gaat **niet** naar de KvK — die kent geen particulieren.
De tool bepaalt dat vooraf op het middel en op de beginposities van het nummer. De
Streamlit-omgeving is een testomgeving; er horen geen productiegegevens in.

---

## Waar je de details vindt

| Wat | Waar |
|---|---|
| Wat er misging in de versie van 15-07 | §1a |
| Verificatie van de rentepagina's | §2a |
| Verificatie van betalingskenmerk en auto | §2b |
| De bijtellingsreeks tegen de wettekst | §2c |
| Alle wijzigingen per pagina | §3 |
| Wat bewust niet is aangepast | §4 |
| Hoe het is gecontroleerd | §5 |
| Kwetsbaarheden K1 t/m K5 | §6 en §6a |
| Actielijst | §7 |

Alles in [`WIJZIGINGSRAPPORT.md`](WIJZIGINGSRAPPORT.md). Elke commitmelding beschrijft
daarnaast wat er misging, wat het gevolg was en hoe is gecontroleerd dat er niets anders is
gewijzigd.

Met vriendelijke groet,
Sylvain
