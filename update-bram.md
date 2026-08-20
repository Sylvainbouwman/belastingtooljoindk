# Belastingtool JoinDK — wat er in de rekenregels is veranderd

**Datum:** 18 augustus 2026
**Repository:** [`Sylvainbouwman/belastingtooljoindk`](https://github.com/Sylvainbouwman/belastingtooljoindk) — heette tot 18-08-2026 `betalingskenmerk-tool`
**Volledig verslag:** [`WIJZIGINGSRAPPORT.md`](WIJZIGINGSRAPPORT.md)

---

Hoi Bram,

Jullie bouwen dit in een andere taal, dus dit document gaat niet over code maar over
**regels**: wat de tool nu doet, wat de versie van 15 juli deed, en waarom. Alles wat
hieronder staat is taalonafhankelijk — percentages, datums, formules en de volgorde waarin
controles moeten gebeuren. De bestandsnamen staan erbij zodat je in de repo kunt nakijken
hoe het is uitgewerkt; je hoeft niets te installeren.

De rekenregels staan bewust los van de schermen. `_kenmerk.py`, `_rente.py`,
`_auto_calc.py`, `_vies.py` en `_kvk.py` bevatten geen Streamlit-code. Bij elke fiscale
waarde staat de vindplaats in een commentaar: een jaarpagina, een wetsartikel of een
paragraaf uit een specificatie. Er zitten 366 tests op, waarvan een deel de gepubliceerde
rekenvoorbeelden van de Belastingdienst letterlijk nabouwt.

**Eén ding vooraf, omdat het door elkaar wordt gehaald.** Deze repository is de
Belastingtool: zes rekentools in één app, en dit is wat bij DK/Join wordt ingebouwd.
*bouwman.tools* is iets anders — een portaal waar Sylvain losse tools bij elkaar zet zodat
collega's ze kunnen uitproberen. Die portal is geen leveringsobject.

---

## 1. Belastingrente IB en VpB — `_rente.py`

De zwaarste bevindingen zitten hier. Twee regels ontbraken volledig.

| Regel | Wat het moet zijn | Wat de versie van 15-07 doet |
|---|---|---|
| **Vrijstelling bij tijdige aangifte** | Aangifte vóór 1 mei (IB) of 1 juni (VpB) én ongewijzigd gevolgd → **geen rente verschuldigd** | rekent gewoon door: € 264 op € 10.000 waar € 0 hoort |
| **Maximering op 19 weken** | Te laat maar ongewijzigd gevolgd → einddatum is 19 weken na ontvangst van de aangifte, of 6 weken na dagtekening, het vroegste | ontbreekt: 198 dagen waar 74 hoort, tot 2,6× te hoog |
| **Dagentelling** | 30 dagen per maand, 360 per jaar | werkelijke dagen, 365 |
| **Einddatum** | telt mee in de periode | telt niet mee |
| **Afronding** | naar beneden op hele euro's, **per tariefperiode** | op centen, over het totaal |
| **Navordering** | rente tot 1 maand na dagtekening; op eigen verzoek maximaal 12 weken na het verzoek | als gewone aanslag: 6 weken |
| **Startdatum VpB** | eerste dag van de 7e maand na het boekjaar | boekjaareinde + 6 maanden + 1 dag → bij boekjaar t/m 30-06 of 28-02 een dag te vroeg |
| **Voorlopige aanslag VpB** | tijdig verzocht en conform opgelegd → geen rente | ontbreekt |
| **Tarieftabel VpB** | boekjaren t/m 2013: 3% | valt terug op 8,25%, tot € 1.295 te veel op € 100.000 |
| **Tarieftabel VpB** | 1-3-2015 t/m 29-2-2016: 8,05% | 8,15% |

Dat de afronding **per tariefperiode** gaat en niet over het totaal blijkt uit hun eigen
voorbeeld: 93 + 9 = 102, terwijl 93,75 + 9,93 zou afronden naar 103.

> **Let op bij jullie specificatie.** §12 van de rekenmodule-specificatie telt eerst alle
> deelbedragen op en rondt daarna één keer af. Dat geeft € 103 waar de Belastingdienst
> € 102 publiceert. §11 zegt het goed. Zolang §12 niet is gecorrigeerd, implementeert een
> ontwikkelaar de fout — dat is het enige punt waar wij iets van jullie nodig hebben.

**Volgorde van de controles** — deze wijkt bewust af van de pseudocode: bij een
navorderingsaanslag zijn de aangiftevragen niet van toepassing, dus de navorderingscheck
gaat **vóór** de vrijstelling. Een navorderingsaanslag volgt per definitie niet de
oorspronkelijke aangifte.

---

## 2. Betalingskenmerk — `_kenmerk.py`

Getoetst aan *Specificatie Betalingskenmerk_bepaling v1.5*. Zes van de 27 voorbeelden in
dat document werden fout gedecodeerd.

| Regel | Wat het moet zijn | Wat de versie van 15-07 doet |
|---|---|---|
| **VpB-middelcodes** | 74, 80–84 en 92–96. Prefix: 74 → `00`, 80–84 → zichzelf, 92–96 → code min 7 | hele reeks 80–96 als VpB |
| **Codes 85–88** | 85/86 = Eurovignet, 87/88 = MOA vrachtwagens | als VpB, met **verzonnen RSIN**: 810360007 waar 036000012 hoort, plus verkeerd jaar |
| **Codes 89–91** | bestaan niet → nette foutmelding | als VpB |
| **Controlecijfer positie 1** | valideren (zie hieronder) | wordt genegeerd |
| **11-proef restwaarde 10** | er bestaat geen geldig nummer → geen nummer tonen | plakt "10" aan: nummer van 10 cijfers, bij 1 op de 11 invoeren |
| **Middelcode 97** | positie 16 bepaalt welke heffing: 1 = landinrichtingsrente, 2 = verontreinigingsheffing | één label met een schuine streep |
| **SOORT-cijfer** | positie 9 (VpB) of 13 (IB, IH, ZVW): 0 = voorlopige, 6 = definitieve aanslag | wordt genegeerd |
| **Jaarreconstructie** | venster van vorig jaar tot en met volgend jaar, want voorlopige aanslagen komen vooruit | cijfer 7 werd in 2026 gelezen als 2017 in plaats van 2027 |

**Het controlecijfer, want dat staat niet in de specificatie.** Daar staat alleen "berekenen
m.b.v. modulus-11 algoritme, zie onderaan", maar onderaan staat uitsluitend de elfproef voor
het BSN/RSIN. De regel die wél klopt is de acceptgiro-elfproef:

1. weeg de posities 2 t/m 16 van **rechts naar links** met 2, 4, 8, 5, 10, 9, 7, 3, 6, 1 en
   herhaal die reeks
2. tel op, neem 11 min de rest bij deling door 11
3. uitkomst 11 → 0, uitkomst 10 → 1

Dat klopt op alle 27 voorbeelden in de specificatie én op een extern gevalideerd kenmerk uit
de praktijk: 28 van de 28. Zonder deze controle levert één verkeerd overgetypt cijfer een
geloofwaardig maar verkeerd BSN/RSIN op.

**Privacy.** Uit een kenmerk van een particulier komt een BSN. Dat wordt getoond, maar gaat
niet naar de KvK. Vooraf te bepalen: bij middelcodes 70, 71, 73, 75 en 23–28 gaat het altijd
om een natuurlijk persoon, en een RSIN begint altijd met 00 of 80–89.

---

## 3. Auto BTW privé — `_auto_calc.py`

| Regel | Wat het moet zijn | Wat de versie van 15-07 doet |
|---|---|---|
| **Laag BTW-forfait** | 1,5% bij een marge-auto, én zodra het privégebruik later valt dan 4 jaar na het jaar van ingebruikname | altijd 2,7%: bijna een verdubbeling, € 1.350 waar € 750 hoort op € 50.000 |
| **Deel van een jaar (BTW)** | naar **maanden**: 4/12 × 2,7% × € 45.000 = € 405, conform het voorbeeld van de Belastingdienst | dagen / 365 → € 406,08 |
| **Schrikkeljaar** | een vol jaar is 1,0 | 366/365 = 100,27% van het forfait |
| **Bijtellingsregime** | staat 60 maanden vast, gerekend vanaf de **eerste dag van de maand ná de eerste toelating** | percentage van het berekeningsjaar |
| **Standaardpercentage** | 25% tot en met 2016, 22% vanaf 2017 | valt voor onbekende jaren stil terug op 22% |
| **Nulemissie** | zie tabel hieronder | 2026 ontbrak → 22% in plaats van 18% |
| **Waterstof en zonnecelauto's** | verlaagd percentage over de **hele** catalogusprijs, geen plafond | plafond toegepast: € 25.400 waar € 14.400 hoort bij € 80.000 |
| **Auto ouder dan 16 jaar** | 35% van de waarde in het economisch verkeer (grens was 15 jaar tot 2026) | 22% van de catalogusprijs |

**Nulemissiereeks**, getoetst aan de jaarpagina's én aan de wettekst. De wet noemt een
verlaging in procentpunten met een maximumbedrag; onderstaande percentages met plafond zeggen
hetzelfde. Boven het plafond geldt het standaardpercentage.

| Regimejaar | Percentage | Plafond | Maximale korting |
|---|---|---|---|
| 2017, 2018 | 4% | geen | n.v.t. |
| 2019 | 4% | € 50.000 | € 9.000 |
| 2020 | 8% | € 45.000 | € 6.300 |
| 2021 | 12% | € 40.000 | € 4.000 |
| 2022 | 16% | € 35.000 | € 2.100 |
| 2023, 2024 | 16% | € 30.000 | € 1.800 |
| 2025 | 17% | € 30.000 | € 1.500 |
| 2026 | 18% | € 30.000 | € 1.200 |

Die maximale korting is plafond × (standaard − percentage). Voor 2019 en 2020 worden de
bedragen € 9.000 en € 6.300 letterlijk in de wetsstukken genoemd, dus daar sluit de tabel
aantoonbaar op aan.

**Twee dingen die de tool niet kan en jullie misschien wel.** De bijtelling is bij een
IB-ondernemer nooit hoger dan de totale autokosten van het jaar; die kosten kent de tool
niet. En een auto die volledig op geïntegreerde zonnecellen rijdt valt ook onder de
plafondvrijstelling, maar dat is niet uit de RDW-gegevens af te leiden.

---

## 4. VIES BTW-controle — `_vies.py`

Eén regel, met gevolgen voor de onderbouwing van het 0%-tarief bij intracommunautaire
prestaties: **een storing is geen ongeldig nummer**. VIES antwoordt bij een storing bij een
lidstaat met HTTP 200 en `isValid: false`. Dat mag niet als "niet geldig" worden getoond,
maar als *niet gecontroleerd*. Er zijn dus drie uitkomsten, geen twee.

---

## 5. Vier gebreken in de specificatie van de Belastingdienst

Relevant omdat jullie er van implementeren. Zie §2b van het wijzigingsrapport.

1. Het **controlecijfer op positie 1** wordt niet beschreven — zie punt 2 hierboven voor de
   regel die wel klopt.
2. **Drie van de 27 voorbeelden zijn inconsistent met zichzelf.** Bij `036000012F0314240`,
   `036000012A0414121` en `036000012N2100030` verschilt het jaartal één cijfer tussen het
   aanslagnummer en het gedrukte kenmerk. De andere 24 zijn exact reproduceerbaar uit de
   regels van het document — dat is nagerekend in beide richtingen.
3. Er is **geen codetabel voor het SOORT-cijfer**. Uit de voorbeelden blijkt alleen
   0 = voorlopige aanslag en 6 = definitieve aanslag.
4. Bij paragraaf 4 staat **"pos 3"** waar "pos 13" wordt bedoeld (B-JAVO bij A-MIDDEL = W).

---

## 6. Waar je het in de repo terugvindt

| Onderwerp | Bestand | Paragraaf in het rapport |
|---|---|---|
| Belastingrente | `_rente.py`, `tests/test_rente.py` | §2a, §3.2 |
| Betalingskenmerk | `_kenmerk.py`, `tests/test_kenmerk.py` | §2b, §3.1 |
| Auto | `_auto_calc.py`, `tests/test_auto_calc.py` | §2b, §2c, §3.3 |
| VIES | `_vies.py`, `tests/test_vies.py` | §3.4 |
| KvK-gegevens | `_kvk.py`, `tests/test_kvk.py` | — |
| Wat er misging in de versie van 15-07 | — | §1a |
| Hoe het is gecontroleerd | — | §5 |

De testbestanden zijn de snelste ingang: daar staan de gepubliceerde rekenvoorbeelden van de
Belastingdienst en de 27 specificatievoorbeelden als verwachte uitkomsten. Wat jullie
implementatie op diezelfde invoer moet opleveren, staat daar dus letterlijk.

Met vriendelijke groet,
Sylvain
