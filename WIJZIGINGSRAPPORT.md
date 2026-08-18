# Wijzigingsrapport — codereview belastingtooljoindk

**Datum:** 17 augustus 2026, bijgewerkt 18 augustus 2026
**Repository:** `belastingtooljoindk` (tot 18-08-2026 `betalingskenmerk-tool`)
**Betreft:** volledige codereview + oplossen van alle gevonden bugs, gevolgd door een
verificatieronde waarin het rekenwerk van álle vier de rekenpagina's is getoetst aan de bron
**Branch:** `master` (gepusht)
**Omvang:** 17 commits, 26 bestanden, +4.200 / −752 regels
**Tests:** van 0 naar 327 (alle groen)

> **Scope.** Dit rapport gaat uitsluitend over de repository `belastingtooljoindk`, die
> tot 18-08-2026 `betalingskenmerk-tool` heette. Die bevat inmiddels zes pagina's —
> Betalingskenmerk, VIES BTW-controle, KvK/SBI opzoeken, Belastingrente IB, Belastingrente
> VpB en Auto BTW privé — die samen als één Streamlit-app draaien.
>
> Deze app hoort **niet** bij de verzameling op **bouwman.tools**; dat is een aparte portal
> met andere, losse tools. De app noemde zichzelf wel zo (in `app.py` en bovenaan de
> README), en dat is met **actiepunt 6** rechtgezet.

---

## 1. Samenvatting in het kort

Het werk bestond uit drie rondes.

**Ronde 1 — codereview.** Tien echte bugs gevonden; negen opgelost, één bewust
ongewijzigd gelaten omdat die een fiscale beslissing vraagt.

**Ronde 2 — verificatie tegen de bron, rentepagina's.** Niet de code doorlezen, maar de
fiscale regels erbij pakken en controleren of de code ze volledig toepast. Dat vond twee
regels die nooit in de tool hebben gezeten — en die het zwaarst wegen van alles in dit
rapport.

**Ronde 3 (18 augustus) — verificatie van de twee resterende pagina's.** Dezelfde methode
op Betalingskenmerk en Auto BTW privé. Die ronde bevestigde de verwachting uit ronde 2:
daar was óók iets te vinden. Zes van de 27 voorbeelden in de officiële specificatie
decodeerde de tool fout, en de bijtelling week op vier punten af van belastingdienst.nl.
In dezelfde ronde zijn de resterende kwetsbaarheden en het opruimwerk afgehandeld.

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
| **Middelcodes 85 t/m 88 werden als VpB gelezen** | Eurovignet en MOA kwamen eruit als vennootschapsbelasting, **met een verzonnen RSIN** — 810360007 waar 036000012 hoort |
| **Nulemissiekorting 2026 ontbrak** | Een EV uit 2026 kreeg 22% in plaats van 18%: € 6.600 in plaats van € 5.400 bij een auto van € 30.000. **Dit is het lopende jaar** |
| **Waterstofauto's kregen het prijsplafond opgelegd** | € 25.400 in plaats van € 14.400 bijtelling bij een waterstofauto van € 80.000 (2026) |
| **De youngtimerregeling ontbrak volledig** | Auto's ouder dan 16 jaar kregen 22% van de catalogusprijs in plaats van 35% van de waarde in het economisch verkeer |
| Nulemissiepercentage 2025 stond op 16% | Moet 17% zijn — te lage bijtelling |
| De kopieerknop op de Betalingskenmerk-pagina deed niets | Streamlit haalt onclick-attributen weg; een klik leverde geen kopie en geen melding |
| De marge-instelling gold voor alle auto's tegelijk | Bij meerdere auto's in één berekening kreeg er één het verkeerde forfait |
| BTW-correctie rekende naar dagen, de Belastingdienst naar maanden | € 406,08 waar de Belastingdienst € 405 voorrekent |

Daarnaast bleek de tool bij ongeveer 1 op de 11 betalingskenmerken een **verzonnen
BSN/RSIN** te tonen, en klopte de kopieerknop-omschrijving alleen voor loonheffing en
omzetbelasting.

De verificatieronde is nu op alle vier de rekenpagina's gedaan. Wat nog open staat, vraagt
een beslissing en geen code — zie de actielijst in paragraaf 7.

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

---

## 2b. Verificatieronde deel 2: Betalingskenmerk en Auto BTW privé

Op 18 augustus is dezelfde methode toegepast op de twee pagina's die nog openstonden. De
verwachting was dat daar ook iets te vinden zou zijn. Dat bleek te kloppen.

### Betalingskenmerk tegen de specificatie

De officiële **Specificatie Betalingskenmerk_bepaling v1.5** bevat 27 voorbeelden van een
aanslagnummer met het bijbehorende betalingskenmerk. Die zijn er alle 27 door de tool
gehaald. **Zes decodeerde de tool fout.**

De oorzaak was het openstaande conflict over middelcodes 85 t/m 88 — en de specificatie
beslecht het. Paragraaf 2 leidt de VpB-middelcode af uit de eerste twee posities van het
RSIN: 00 wordt 74, 80 t/m 84 blijven staan, en 85 t/m 89 worden **92 t/m 96**. De
VpB-codes zijn dus 74, 80–84 en 92–96, en niet de hele range 80–96 waar de tool op stond.

De vier labels in de tabel hadden dus gelijk: 85 en 86 zijn Eurovignet, 87 en 88 zijn MOA
vrachtwagens. Wat er misging was ernstiger dan een verkeerd label. Voor het voorbeeld uit
paragraaf 7 van de specificatie gaf de tool:

| | Specificatie | Tool (oud) |
|---|---|---|
| Soort | Naheffingsaanslag MOA | Vennootschapsbelasting |
| BSN/RSIN | 036000012 | **810360007** |
| Jaar | 2023 | 2020 |
| Tijdvak | — | "Boekjaar 3000" |

Dat is een **verzonnen RSIN** dat er geloofwaardig uitziet. De codes 89 t/m 91 vielen ook
in die range en bestaan in de specificatie niet; die geven nu een nette foutmelding.

**Twee dingen die de specificatie oplevert en die de tool nog niet gebruikte:**

- **Middelcode 97 dekt twee heffingen.** De middelherkenning staat op positie 16: 1 is
  landinrichtingsrente, 2 is verontreinigingsheffing rijkswateren. Beide voorbeelden
  bevestigen dat. De tool zette er een label met een schuine streep tussen; nu wordt het
  onderscheiden.
- **Het SOORT-cijfer werd genegeerd** (positie 9 bij VpB, positie 13 bij IB, IH en ZVW).
  Uit de voorbeelden blijkt soort 0 = voorlopige aanslag en soort 6 = definitieve aanslag.
  Alleen die twee waarden worden gelabeld; bij een andere waarde wordt niets beweerd, want
  de specificatie geeft geen codetabel.

**Het controlecijfer op positie 1 kan nu gecontroleerd worden — actiepunt 10 is af.** De
specificatie zegt daarover alleen "berekenen m.b.v. modulus-11 algoritme, zie onderaan",
maar onderaan staat uitsluitend de elfproef voor het BSN/RSIN, niet die voor het kenmerk
zelf. Het algoritme is daarom uit de voorbeelden afgeleid: de gangbare
acceptgiro-elfproef, weging 2-4-8-5-10-9-7-3-6-1 van rechts naar links, 11 min de rest,
waarbij een uitkomst 11 naar 0 gaat en 10 naar 1. Die regel klopt op **alle 27 voorbeelden
in de specificatie én op het extern gevalideerde kenmerk uit de README: 28 van de 28.**
Een verkeerd overgetypt cijfer levert nu een melding op die zegt welk cijfer er hoort te
staan, in plaats van stilzwijgend een verkeerd RSIN.

> **Voor Bram: de specificatie is op drie plekken inconsistent met zichzelf.** Om de
> lezing te controleren is ook de omgekeerde weg nagebouwd: van aanslagnummer naar
> kenmerk volgens de regels van het document. Dat reproduceert **24 van de 27**
> voorbeelden exact, inclusief het controlecijfer. Bij de drie andere verschilt het
> jaartal één cijfer tussen het aanslagnummer en het gedrukte kenmerk: `036000012F0314240`,
> `036000012A0414121` en `036000012N2100030`. Bij de eerste twee klopt het kenmerk en niet
> het aanslagnummer (de omschrijving zegt 2023), bij de derde is het omgekeerd (de
> omschrijving zegt 2021, het kenmerk zegt 2020). Zie **actiepunt 13**.

### Auto BTW privé tegen belastingdienst.nl

De jaarpagina's van belastingdienst.nl zijn per jaar nagelopen. Vier afwijkingen, waarvan
twee die vandaag spelen:

| Wat | Bron | Was |
|---|---|---|
| Nulemissie 2025 | 17% t/m € 30.000 | 16% |
| Nulemissie 2026 | 18% t/m € 30.000 | géén korting, dus 22% |
| Waterstof en zonnecelauto's | verlaagd percentage **zonder plafond** | plafond werd toegepast |
| Auto ouder dan 16 jaar | 35% van de waarde in het economisch verkeer | 22% van de catalogusprijs |

De youngtimergrens ging **per 2026 van 15 naar 16 jaar**. De pagina herkent dit nu aan de
datum eerste toelating uit het RDW en vraagt de waarde in het economisch verkeer; zonder
die waarde wordt geen bedrag getoond in plaats van een verkeerd bedrag.

**En opnieuw een methodeverschil, net als bij de rente.** Het rekenvoorbeeld op "Btw en
privégebruik auto van de zaak" gaat over een auto die op 1 september tot het bedrijf gaat
horen en komt uit op `4/12 × 2,7% × € 45.000 = € 405`. De tool rekende met dagen door 365
en kwam op € 406,08. De BTW-correctie rekent nu in maanden, waarbij een gedeeltelijke
maand naar rato van de dagen binnen die maand telt. De bijtelling blijft naar dagen
rekenen, omdat de 60-maandstermijn midden in een maand kan aflopen en de periode dan op de
dag wordt gesplitst. Beide methodes staan nu in de voettekst en in de PDF.

**Wat wél klopte:** het lage BTW-forfait vanaf het vijfde jaar na ingebruikname, de
60-maandstermijn die begint op de eerste dag van de maand ná de eerste toelating, de
percentages van 2021 t/m 2024, en het standaardpercentage van 22% (2017 en later) en 25%
(tot en met 2016).

**Eén regel die de tool niet kan toepassen:** bij een IB-ondernemer is de bijtelling nooit
hoger dan de totale autokosten van het jaar. Dat staat in het rekenvoorbeeld van de
Belastingdienst, maar de tool kent die kosten niet. De pagina meldt dat nu expliciet.

---

## 2c. De bijtellingsreeks tegen de wet zelf

De jaarpagina's van belastingdienst.nl noemen het plafond van 2020 niet, en zeggen niets
over 2017 en 2018. Die drie gegevens stonden daarom eerst als onbevestigd in de code.
Sylvain heeft daarna de primaire bronnen aangeleverd: het Staatsblad en de memories van
toelichting. Daarmee sluit de reeks, en er zit een controle in die de tabel aan de wet
vastlegt.

De wet formuleert de korting namelijk anders dan de tool. In artikel 3.20 Wet IB staat een
**verlaging in procentpunten met een maximumbedrag**; de tool noteert het **resulterende
percentage met een plafond op de catalogusprijs**. Dat is dezelfde regel, en dat is nu na te
rekenen: plafond × (standaard − percentage) hoort precies het maximale kortingsbedrag uit
de wet te zijn. Twee van die bedragen staan letterlijk in de stukken:

| Jaar | Wettelijke korting | Plafond | Maximale korting | Bron |
|---|---|---|---|---|
| 2017, 2018 | 18%-punt → 4% | geen | n.v.t. | Stb. 2016, 275, art. 3.20 lid 2 |
| 2019 | 18%-punt → 4% | € 50.000 | **€ 9.000** | Stb. 2016, 275, art. III |
| 2020 | 14%-punt → 8% | € 45.000 | **€ 6.300** | Kst. 35 304, nr. 3 |

€ 50.000 × 18% = € 9.000 en € 45.000 × 14% = € 6.300 — beide bedragen worden in de bron
genoemd en komen exact uit. Dat staat nu als test vast, samen met een controle dat de
korting bij een prijs boven het plafond nooit boven dat wettelijke maximum uitkomt.

Twee dingen die ik gisteren alleen via de jaarpagina's had, blijken ook rechtstreeks in de
wet te staan:

- **De waterstofuitzondering.** Het plafond is ingevoerd "met dien verstande dat het bedrag
  van de verlaging ten hoogste € 9.000 bedraagt indien de auto **niet** wordt aangedreven
  door een motor die kan worden gevoed met waterstof" (Stb. 2016, 275, art. III). De
  memorie van toelichting bij de Klimaatakkoordwet herhaalt het: "De cap is niet van
  toepassing op auto's met een motor die kan worden gevoed met waterstof."
- **De 60-maandstermijn.** Artikel 3.20, elfde lid: de verlaging blijft van toepassing
  "voor een periode van 60 maanden te rekenen vanaf de eerste dag van de maand volgend op
  de datum van eerste toelating van de auto". Dat is letterlijk wat
  `vervaldatum_vaste_termijn()` doet.

> **Eén punt om in de gaten te houden.** De Wet fiscale maatregelen Klimaatakkoord liet de
> korting **per 2026 geheel vervallen**. De jaarpagina 2026 en de overzichtstabel voor
> werknemers noemen wel degelijk 18% tot en met € 30.000, dus dat is met latere wetgeving
> aangepast. Voor 2026 is de jaarpagina daarom de bron, en dat staat zo in de code. Het
> laat ook zien waarom de melding bij een regimejaar voorbij de gecontroleerde tabel
> nuttig is: deze reeks verandert vaker dan je zou denken.

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

### 3.5 Ronde 3 — wat er in de code is veranderd

De bevindingen staan in paragraaf 2b; hier staat waar ze terechtkwamen.

| Bestand | Wijziging |
|---|---|
| `_kenmerk.py` | VpB-middelcodes teruggebracht tot 74, 80–84 en 92–96; controlecijferfunctie erbij; middelcode 97 gesplitst in LIR en VHR; SOORT-cijfer gelezen; boekjaar als maandbereik; de handgeschreven lijsten met zestien booleans voor de positieweergave vervangen door `actieve_posities()`, die nu ook werkelijk de gedecodeerde velden markeert |
| `_auto_calc.py` | percentages 2025 en 2026 gecorrigeerd; `is_plafondvrij()` voor waterstof; `maandfractie()` voor de BTW-correctie; youngtimerfuncties; `standaardpercentage()` in plaats van een stille terugval op 22%; `waarschuwing_regimejaar()` |
| `pages/Betalingskenmerk.py` | kopieerknop vervangen door een codeblok; extra rerun weg; escaping; KvK-URL-controle |
| `pages/Auto_BTW_Prive.py` | marge per auto; youngtimerblok; maandweergave; kentekenvalidatie; escaping van de RDW-velden |
| `pages/VIES_BTW_Controle.py`, `pages/KvK_SBI_Opzoeken.py` | dode knop weg; gedeeld stijlblok; escaping; KvK-sleutelblok en URL-controle |
| `_format.py`, `_ui.py` | nieuw — zie paragraaf 6 |
| `tests/` | van 203 naar 327 tests; `tests/test_ui.py` is nieuw |

---

## 4. Wat is bewust NIET aangepast

**Middelcodes 85 t/m 88 — dit punt is opgelost.** In ronde 2 was het bewust laten staan,
omdat het een fiscale vraag leek. De specificatie beslecht het: het zijn Eurovignet en MOA,
de VpB-range was fout. Zie paragraaf 2b.

**De drie gegevens van vóór 2021 zijn inmiddels ook bevestigd.** Ze stonden hier eerst als
onbevestigd, omdat de jaarpagina's van belastingdienst.nl ze niet noemen. Sylvain heeft de
primaire bronnen aangeleverd en daarmee sluit de reeks: zie paragraaf 2c.

Wat nu nog bewust níet is aangepast:

**Het SOORT-cijfer buiten de waarden 0 en 6.** Alleen die twee komen in de voorbeelden van
de specificatie voor. Bij een andere waarde toont de tool niets in plaats van een gok.

**De youngtimerwaarde.** De waarde in het economisch verkeer is geen RDW-gegeven en kan de
tool niet zelf bepalen; die wordt gevraagd.

---

## 5. Hoe het is gecontroleerd

Naast de 327 tests is de app gestart en met echte data doorlopen. Eerst de controles uit
ronde 3 (18 augustus):

| Pagina | Testgeval | Uitkomst |
|---|---|---|
| Betalingskenmerk | alle 27 voorbeelden uit specificatie v1.5 | alle 27 juist, inclusief het BSN/RSIN uit het aanslagnummer |
| Betalingskenmerk | omgekeerde weg: aanslagnummer naar kenmerk | 24 van 27 exact gelijk; 3 zijn in het document zelf inconsistent |
| Betalingskenmerk | `4863521721601050` | `Afdr. OB Mei 2026` · RSIN 8635.21.721 · naam Onesti B.V. · SBI 69204 |
| Betalingskenmerk | zelfde kenmerk, laatste cijfer verminkt | geweigerd, met vermelding dat op positie 1 een 2 hoort te staan en niet een 4 |
| Betalingskenmerk | kopieerknop | werkt nu; het onclick-attribuut van de oude knop bleek door Streamlit te worden verwijderd |
| Auto BTW privé | kenteken `TH992G`, heel 2026 | BTW € 634,96 · bijtelling € 5.173,74 (22%) |
| Auto BTW privé | zelfde auto, 1 sep t/m 31 dec | 4,00/12 maanden · € 211,65 (met de oude dagmethode € 212,22) |
| Auto BTW privé | officieel rekenvoorbeeld Belastingdienst | € 405,00 exact |
| VIES | `NL820646660B01` | Geldig · ABN AMRO BANK N.V. · adres · RSIN 8206.46.660 |
| KvK / SBI | KvK-nummer `68750110` | naam, hoofdactiviteit en twee nevenactiviteiten; de nieuwe URL-controle laat het echte basisprofiel door |
| Alle zes pagina's | na het samenvoegen van de stijlblokken | opmaak ongewijzigd, geen fouten in de serverlog |

En de controles uit ronde 2 (17 augustus):

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

## 6. Kwetsbaarheden en opruimwerk — afgehandeld

Deze punten stonden in ronde 2 nog open en zijn op 18 augustus opgelost (commit `6cda4d0`).

### Kwetsbaarheden

| Nr | Punt | Opgelost met |
|---|---|---|
| K1 | Externe API-data (KvK-namen, SBI-omschrijvingen, RDW-velden) ging ongeéscaped de HTML in | `veilig()` in `_ui.py`; alle pagina's gaan daar nu langs |
| K2 | Het kenteken werd server-side niet gevalideerd; willekeurige tekens kwamen in de RDW-querystring | normaliseren en tegen een patroon toetsen vóór de aanroep |
| K3 | De KvK-API-sleutel ging naar een URL uit het antwoord zonder controle op de host | `is_kvk_url()` eist https en hostnaam `api.kvk.nl` |
| K4 | De devcontainer startte Streamlit met CORS en XSRF-bescherming uit | die twee vlaggen zijn weg |
| K5 | **Privacy/AVG:** uit een kenmerk van een particulier rolt een BSN. Die werd getoond, een uur gecachet en als zoekterm naar de KvK gestuurd — terwijl de KvK particulieren niet kent | opgelost, zie paragraaf 6a |

### Opruimwerk

- **Duplicatie opgeruimd.** Twee nieuwe modules: `_format.py` voor de Nederlandse notatie
  (zonder Streamlit, zodat de rekenmodules en de tests er los bij kunnen) en `_ui.py` voor
  het stijlblok, de koptekst, `veilig()` en het KvK-sleutelblok. Het stijlblok stond vijf
  keer gekopieerd, het KvK-sleutelblok twee keer en `nl_euro`/`nl_date` zowel in `_rente.py`
  als in de autopagina. De opmerking uit ronde 2 dat ook `tarief_op` en `bereken` dubbel
  stonden was achterhaald: die waren al naar `_rente.py` verhuisd.
- **Knoppen die niets deden.** "Controleer" (VIES) en "Zoeken" (KvK) zijn weg; beide
  pagina's reageren direct op de invoer. Daarbij kwam een **derde, ernstiger geval** boven:
  de kopieerknop op de Betalingskenmerk-pagina was opgebouwd met een `onclick`-attribuut in
  meegegeven HTML, en Streamlit verwijdert gebeurtenisattributen daaruit. In de browser
  nagelopen: dat attribuut stond niet in de opgebouwde pagina. De knop toonde een
  kopieersymbool en deed bij een klik niets — geen kopie, geen terugkoppeling. De
  omschrijving staat nu in een codeblok met de eigen kopieerknop van Streamlit.
- **Overbodige rerun weg.** De Betalingskenmerk-pagina deed eerst een volledige
  herberekening om een laadtekst te tonen en haalde de KvK-gegevens pas in de tweede ronde
  op. Dat is nu een spinner om de opzoeking heen.
- **Fragiele veldtoegang.** De links uit het KvK-antwoord werden met een harde index
  gelezen, waardoor een link zonder die velden de pagina liet omvallen; nu met `.get()`.
- **Controle op het kenmerk zelf.** Positie 1 wordt nu gevalideerd — zie paragraaf 2b.

---

## 6a. K5: het BSN gaat niet meer naar de KvK

Besloten op 18 augustus: het nummer mag worden getoond — een medewerker moet kunnen zien
dat het om een natuurlijk persoon gaat — maar als het niet nodig is om het naar de KvK te
sturen, dan gebeurt dat niet.

Dat blijkt scherper te kunnen dan het leek. De tool weet namelijk vooraf of een opzoeking
zin heeft, op twee gronden:

1. **Het middel.** Inkomstenbelasting, de conserverende aanslag IH, de Zorgverzekeringswet
   en de zes toeslagen worden uitsluitend aan natuurlijke personen opgelegd. Bij die
   middelcodes staat vast dat het nummer een BSN is.
2. **De beginposities.** Bij loonheffing, omzetbelasting, houderschapsbelasting, MOA,
   Eurovignet en middelcode 97 kan het beide zijn: een eenmanszaak draagt omzetbelasting af
   onder een nummer dat op het BSN is gebaseerd. Daar geldt de regel die in paragraaf 2 van
   de specificatie staat: "RSIN-s beginnen altijd met 00, of 80 t/m 89". Begint het nummer
   daar niet mee, dan is het geen RSIN en levert een opzoeking bij de KvK toch niets op.

Bij vennootschapsbelasting is het altijd een RSIN — de specificatie stelt uitdrukkelijk dat
een VpB-aanslagnummer nooit een BSN bevat.

De privacywinst en de functionele winst lopen hier gelijk op: elk nummer dat nu niet meer
wordt verstuurd, is een nummer waarvoor de KvK per definitie geen antwoord had. En omdat de
KvK-opzoeking de enige plek was waar het nummer een uur werd gecachet, verdwijnt daarmee
ook de caching van BSN's.

In de app nagelopen: een voorlopige aanslag IB toont "BSN (natuurlijk persoon)" met een
uitleg dat er niet is opgezocht en zonder netwerkverkeer naar de KvK; het gevalideerde
OB-kenmerk toont "RSIN" en haalt nog gewoon Onesti B.V. met SBI-code 69204 op.

> **Context die dit punt lichter maakt dan het in ronde 2 leek.** Deze Streamlit-versie is
> een testomgeving voor collega's. De versie die in productie gaat, komt in een beveiligde
> omgeving te staan waar de AVG-waarborgen zijn geregeld. Dat neemt de vraag niet weg, maar
> het betekent dat er geen productiegegevens over Streamlit Community Cloud lopen.

---

## 7. Actielijst

Bijgewerkt op 18 augustus, na de terugkoppeling van Sylvain. Er staat nog één punt open.

### Nog te doen

Niets meer aan de code. Wat resteert is werk buiten de repository:

- [ ] **De repository omdopen op GitHub** naar `belastingtooljoindk`, en daarna de app in
      Streamlit Cloud opnieuw uitrollen. Let op de volgorde: eerst de oude app in Streamlit
      Cloud verwijderen zodat het subdomein `belastingtooljoindk` vrijkomt, dan opnieuw
      deployen vanaf de nieuwe reponaam en de KvK-sleutel opnieuw in Settings → Secrets
      zetten. Alle verwijzingen ín de repository zijn al omgezet.

### Afgehandeld met een beslissing

- [x] **0. Bram laat de huidige `master` ophalen.** Bram pullt later. Zolang dat niet is
      gebeurd, draait in DK/Join de versie van 15-07-2026 — zie §1a voor wat daar fout aan
      is.
- [x] **3. BSN-verwerking (K5).** Besloten: tonen mag, versturen naar de KvK niet.
      Uitgevoerd, zie paragraaf 6a.
- [x] **4. Eerdere berekeningen herzien.** Niet nodig: de tool is nog in testfase, er is
      nog niet met een oude versie voor klanten gerekend.
- [x] **5. §12 van de rekenmodule-specificatie.** Wordt aangepast.
- [x] **6. De naam van de app.** De repository gaat `belastingtooljoindk` heten, gelijk aan
      de URL, omdat het feitelijk een verzameling is: begonnen met het betalingskenmerk en
      daarna uitgebouwd. De browsertabtitel en de README-titel staan nu op "Belastingtool
      JoinDK" in plaats van "Bouwman Tools", want die laatste is een andere verzameling
      waar deze app niet op staat. Het bestand `UC_betalingskenmerk-tool.md` heet nu
      `UC_belastingtooljoindk.md`.

### Afgerond in de derde ronde

- [x] **1. Nulemissiepercentages en plafonds** — de hele reeks 2017 t/m 2026 is bij de bron
      bevestigd; zie paragraaf 2c.
- [x] **2. Middelcodes 85 t/m 88** — beslecht door specificatie v1.5: Eurovignet en MOA.
- [x] **7. Kwetsbaarheden K1 t/m K4** — opgelost, zie paragraaf 6. Met K5 erbij is de hele
      kwetsbaarhedenlijst afgehandeld.
- [x] **8. Knoppen die niets doen** — weg, inclusief de kopieerknop die helemaal niets deed.
- [x] **9. Verificatieronde afmaken** — gedaan voor Betalingskenmerk en Auto BTW privé.
- [x] **10. Controlecijfer valideren** — gedaan, klopt op 28 van de 28 bekende gevallen.
- [x] **11. Duplicatie opruimen** — gedaan; `_format.py` en `_ui.py` zijn nieuw.
- [x] **Navordering bij een gebroken boekjaar** — stond als voorbehoud in de README en is nu
      als combinatie getoetst.

### Ter kennisgeving voor Bram

- [ ] 12. De tarievencontrole waarschuwt vanaf nu automatisch als belastingdienst.nl
      afwijkt van de tabellen in de code — zowel bij een nieuwe periode als bij een met
      terugwerkende kracht herzien percentage. Er hoeft dus niet meer handmatig te worden
      nagelopen, maar de melding moet wél worden opgevolgd.

- [ ] 13. **De Specificatie Betalingskenmerk_bepaling v1.5 is op vier punten onvolledig of
      inconsistent.** Relevant, omdat jullie team ervan implementeert.
      - Het **controlecijfer op positie 1** wordt niet beschreven. Er staat "berekenen
        m.b.v. modulus-11 algoritme, zie onderaan", maar onderaan staat alleen de elfproef
        voor het BSN/RSIN. De regel die op alle 27 voorbeelden klopt, staat gedocumenteerd in
        `controlecijfer()` in `_kenmerk.py`.
      - **Drie voorbeelden zijn inconsistent met zichzelf**: bij `036000012F0314240`,
        `036000012A0414121` en `036000012N2100030` verschilt het jaartal één cijfer tussen
        het aanslagnummer en het gedrukte kenmerk. De overige 24 zijn exact reproduceerbaar
        uit de regels van het document.
      - Er is **geen codetabel voor het SOORT-cijfer**. Uit de voorbeelden blijkt alleen
        0 = voorlopige aanslag en 6 = definitieve aanslag.
      - Bij paragraaf 4 staat **"pos 3"** waar "pos 13" wordt bedoeld (B-JAVO bij
        A-MIDDEL = W).

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
| `300f8a0` | Wijzigingsrapport en README bijgewerkt na ronde 2 |
| `2c63b05` | **Verificatieronde betalingskenmerk** — specificatie v1.5 volledig verwerkt, controlecijfer erbij |
| `ee85894` | **Verificatieronde auto** — vier rekenfouten tegen belastingdienst.nl |
| `6cda4d0` | Kwetsbaarheden K1 t/m K4, dode knoppen en de gekopieerde stijlblokken |

Elke commitmelding beschrijft wat er misging, wat het gevolg was en hoe is gecontroleerd
dat er niets anders is gewijzigd.
