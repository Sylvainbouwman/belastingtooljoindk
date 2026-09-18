# Wijzigingsrapport — codereview belastingtooljoindk

**Datum:** 17 augustus 2026, bijgewerkt 18 augustus 2026 en 7 september 2026
**Repository:** `belastingtooljoindk` (tot 18-08-2026 `betalingskenmerk-tool`)
**Betreft:** volledige codereview + oplossen van alle gevonden bugs, gevolgd door een
verificatieronde waarin het rekenwerk van álle vier de rekenpagina's is getoetst aan de bron
**Branch:** `master` (gepusht)
**Tests:** van 0 naar 382 (alle groen)

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
| **Waterstofauto's kregen het prijsplafond opgelegd** | € 16.400 in plaats van € 14.400 bijtelling bij een waterstofauto van € 80.000 (2026) |
| **De youngtimerregeling ontbrak volledig** | Auto's ouder dan 16 jaar kregen 22% van de catalogusprijs in plaats van 35% van de waarde in het economisch verkeer |
| Nulemissiepercentage 2025 stond op 16% | Moet 17% zijn — te lage bijtelling |
| De kopieerknop op de Betalingskenmerk-pagina deed niets | Streamlit haalt onclick-attributen weg; een klik leverde geen kopie en geen melding |
| De marge-instelling gold voor alle auto's tegelijk | Bij meerdere auto's in één berekening kreeg er één het verkeerde forfait |
| BTW-correctie rekende naar dagen, de Belastingdienst naar maanden | € 406,11 waar de Belastingdienst € 405 voorrekent |

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

**Deze tabel is niet volledig meer.** Hij is opgesteld op 17 augustus. De verificatieronde
van 18 augustus vond nog vier fouten die net zo goed in de versie van 15-07 zitten:
middelcodes 85 t/m 88 die als vennootschapsbelasting worden gelezen met een verzonnen RSIN
erbij, de ontbrekende nulemissiekorting voor 2026, het plafond dat onterecht op
waterstofauto's wordt toegepast en de ontbrekende youngtimerregeling. Zie §2b. Het volledige
overzicht van wat mogelijk herberekend moet worden staat in §7, actiepunt 4.

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
en kwam op € 406,11. De BTW-correctie rekent nu in maanden, waarbij een gedeeltelijke
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
| `tests/` | van 203 naar 366 tests; `tests/test_ui.py` en `tests/test_kvk.py` zijn nieuw |

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
| Betalingskenmerk | het extern gevalideerde kenmerk | `Afdr. OB Mei 2026` · RSIN, naam en SBI-code correct opgehaald |
| Betalingskenmerk | zelfde kenmerk, laatste cijfer verminkt | geweigerd, met vermelding dat op positie 1 een 2 hoort te staan en niet een 4 |
| Betalingskenmerk | kopieerknop | werkt nu; het onclick-attribuut van de oude knop bleek door Streamlit te worden verwijderd |
| Auto BTW privé | een echt kenteken, heel 2026 | BTW € 634,96 · bijtelling € 5.173,74 (22%) |
| Auto BTW privé | zelfde auto, 1 sep t/m 31 dec | 4,00/12 maanden · € 211,65 (met de oude dagmethode € 212,22) |
| Auto BTW privé | officieel rekenvoorbeeld Belastingdienst | € 405,00 exact |
| VIES | `NL820646660B01` | Geldig · ABN AMRO BANK N.V. · adres · RSIN 8206.46.660 |
| KvK / SBI | een echt KvK-nummer | naam, hoofdactiviteit en twee nevenactiviteiten; de nieuwe URL-controle laat het echte basisprofiel door |
| Alle zes pagina's | na het samenvoegen van de stijlblokken | opmaak ongewijzigd, geen fouten in de serverlog |

En de controles uit ronde 2 (17 augustus):

| Pagina | Testgeval | Uitkomst |
|---|---|---|
| Auto BTW privé | een echt kenteken (VW Up!, eerste toelating 14-01-2020) | BTW-correctie € 380,97 en bijtelling € 3.104,20 — gelijk aan de losse berekening |
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
OB-kenmerk toont "RSIN" en haalt nog gewoon de vennootschap met haar SBI-code op.

> **Context die dit punt lichter maakt dan het in ronde 2 leek.** Deze Streamlit-versie is
> een testomgeving voor collega's. De versie die in productie gaat, komt in een beveiligde
> omgeving te staan waar de AVG-waarborgen zijn geregeld. Dat neemt de vraag niet weg, maar
> het betekent dat er geen productiegegevens over Streamlit Community Cloud lopen.

---

## 7. Actielijst

Afgerond op 18 augustus 2026. Alle punten zijn gehandeld.

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

---

## 9. Vrijgave 7 september 2026 — de IB-rente van juni 2020, en een controle die het niet kon zien

**Datum:** 7 september 2026
**Aanleiding:** bij het bouwen van het onderwerp revisierente in de repository
`Berekeningen` is dezelfde percentagereeks vanuit de bron opgebouwd en van vindplaatsen
voorzien. Daar kwam één ingangsdatum anders uit dan hier.
**Tests:** van 366 naar 382, alle groen.

### 9.1 De fiscale waarde

In `pages/Belastingrente_IB.py` stond de coronaverlaging van de belastingrente naar
0,01 procent op **1 juni 2020**. Voor de inkomstenbelasting begint die verlaging pas op
**1 juli 2020**. Juni 2020 hoort voor de IB nog op 4,00 procent te staan.

| | |
|---|---|
| Geraakte waarde | ingangsdatum van het percentage 0,01 in de IB-tarieventabel |
| Was | `(date(2020, 6, 1), 0.01)` |
| Wordt | `(date(2020, 7, 1), 0.01)` |
| Vindplaats | Verzamelspoedwet COVID-19, Stb. 2020, 200 — <https://zoek.officielebekendmakingen.nl/stb-2020-200.html> |
| Bevestiging bij de Belastingdienst | voetnoot \*\*\* onder de tabel "Percentages alle belastingen": "Voor de inkomstenbelasting ging de tijdelijke verlaging in vanaf 1-7-2020" |
| Tweede paar ogen | `BELASTINGRENTE_IB_PERIODES` in `Berekeningen/berekeningen.html`, onderbouwd in `Berekeningen/BRONNEN.md` |

De regeling zet het percentage voor de meeste belastingen per 1 juni 2020 op 0,01 procent
en voor de inkomstenbelasting per 1 juli 2020. Voor beide gold de verlaging tot
1 oktober 2020.

### 9.2 Wat het uitmaakte, en voor wie

De renteperiode voor een IB-aanslag begint op 1 juli van het jaar na het belastingjaar
(`STARTMAAND_RENTE = 7` in `_rente.py`). Voor **belastingjaar 2019 en later** valt juni
2020 buiten het tijdvak en verandert er niets. Voor **belastingjaar 2018 en eerder**, met
een dagtekening na juni 2020, loopt het tijdvak wel over die maand.

De richting van het verschil: **de tool rekende te weinig rente**. Voorbeeld, vastgelegd
als test in `tests/test_rente.py` — belastingjaar 2018, dagtekening 1 december 2020,
€ 10.000:

| Deelperiode | Percentage | Dagen | Rente |
|---|---|---|---|
| 01-07-2019 t/m 30-06-2020 | 4,00% | 360 | € 400 |
| 01-07-2020 t/m 30-09-2020 | 0,01% | 90 | € 0 |
| 01-10-2020 t/m 12-01-2021 | 4,00% | 102 | € 113 |
| **Totaal** | | **552** | **€ 513** |

Met de verkeerde datum werd de eerste deelperiode 330 dagen in plaats van 360 en kwam het
totaal op € 479: **€ 34 te weinig** op € 10.000.

### 9.3 Het verschil met de VpB-tabel is bedoeld

`pages/Belastingrente_VpB.py` houdt op precies dezelfde plek **wél 1 juni 2020** aan. Dat
is daar juist: in de VpB-tabel op de bronpagina staat bij die rij geen voetnoot, en de
verlaging ging voor de VpB werkelijk op 1 juni 2020 in. De hele VpB-tabel is op
7 september 2026 rij voor rij tegen de bron gelegd; alle zestien rijen kloppen en er is
niets gewijzigd.

Het verschil tussen de twee tabellen ziet eruit als een fout en is het niet. Het is nu op
drie plaatsen vastgelegd, zodat het niet wordt "rechtgetrokken": in het commentaar boven
beide tabellen, in `AFWIJKINGEN_IB` in `tests/test_tarieven_check.py` en in de tests
`test_ib_en_vpb_verschillen_in_juni_2020` en
`test_vpb_verlaging_begint_wel_op_1_juni_2020`.

### 9.4 Waarom de fout een jaar kon blijven staan

Boven de IB-tabel stond "Laatste controle: 17 augustus 2026 (tabel 1-op-1 nagelopen tegen
de bron)", en de pagina liet een automatische controle draaien tegen de kop
`"Percentages alle belastingen"`. Beide gingen langs de fout heen, en niet doordat er
slordig is gewerkt:

- **De automatische controle was verkeerd gedefinieerd.** Zij parseert de *tabel* onder
  die kop. De IB-uitzondering staat op de bronpagina in lopende tekst — voetnoot \*\*\* —
  *ónder* die tabel. De afwijking was daarmee structureel onvindbaar, en de controle
  keurde haar bij elke paginaweergave opnieuw goed.
- **"1-op-1 nagelopen" is niet navolgbaar.** Er stond niet welke bron, welke rijen en
  welke uitzonderingen waren nagelopen, dus een volgende controleur kon niet zien dat de
  voetnoot buiten beeld was gebleven.

Wat er is gedaan:

1. De kop `KOP_ALGEMEEN` blijft voor de IB-pagina staan. Zij is de juiste: de algemene
   tabel is de enige plek op de bron waar de IB-percentages staan. Wat niet kan, is de
   voetnoot meenemen — dat zou een tweede parser vragen voor één afgesloten historische
   uitzondering uit 2020 die niet meer verandert, en die parser zou zelf een stille
   faalmodus toevoegen. Gekozen is daarom voor het alternatief: **de controle meldt nu
   zelf welk deel zij niet dekt.** De IB-pagina geeft dat als `NIET_GEDEKT` mee, en het
   staat onder de berekening in beeld. De VpB-pagina leunt niet op een voetnoot en geeft
   niets mee.
2. De bronvermelding boven beide tabellen noemt nu de werkelijke grondslag, de
   IB-uitzondering met vindplaats en per onderdeel wat wel en niet is gecontroleerd —
   inclusief wat er buiten is gebleven (de toeslagenpercentages uit de voetnoten \* en
   \*\*, die deze pagina's niet gebruiken). Controledatum: 7 september 2026.
3. De netwerktest die de tabellen rij voor rij met de bron vergelijkt, kent de bewuste
   afwijking nu als gegeven (`AFWIJKINGEN_IB`), zodat elke *andere* rij nog 1-op-1 wordt
   getoetst. Een extra test controleert of die afwijking nog op de bronpagina bestaat: als
   de Belastingdienst de rij van 1-6-2020 ooit wijzigt, dekt de uitzondering stil niets
   meer af en moet zij opnieuw worden beoordeeld. Een derde test kijkt of de voetnoot zelf
   nog op de pagina staat.

### 9.5 "Geen waarschuwing" betekende twee dingen

`controleer_nieuwe_tarieven()` gaf `None` terug zowel wanneer de reeks klopte als wanneer
de bronpagina niet bereikbaar was. De gebruiker kon die twee niet onderscheiden, en de
afwezigheid van een waarschuwing las als "gecontroleerd en in orde". Hetzelfde gold bij
een gewijzigde opmaak van de bron: dan werd de tabel niet herkend en gebeurde er evenmin
iets.

De functie geeft nu een `Controle` terug met vier statussen: `gelijk`, `afwijking`,
`onbereikbaar` en `onleesbaar`. Een afwijking blijft een `st.warning`; de twee toestanden
waarin niets is vergeleken worden een `st.info` boven de invoer, en de voettekst zegt bij
elke paginaweergave wát er is gecontroleerd. Dat de tool niet stukloopt op een netwerkfout
blijft zo.

**Bewust ongemoeid gelaten:** het gooien van een uitzondering in `_haal_pagina_op()`. Die
functie draagt `@st.cache_data` en gooit met opzet in plaats van `None` terug te geven,
zodat Streamlit het mislukte antwoord niet cachet en de volgende paginaweergave het
opnieuw probeert. De uitzondering verlaat de gecachete functie vóórdat
`controleer_nieuwe_tarieven()` haar vangt; daar was dus niets ongedaan gemaakt, er
ontbrak alleen een onderscheid in de aanroeper. Wie hier aan `_haal_pagina_op` gaat
sleutelen, breekt de retry zonder iets op te lossen. Dat staat nu ook in de docstring.

De reparatie is beperkt gebleven tot de twee aanroepers. Met een grep is vastgesteld dat
`controleer_nieuwe_tarieven` nergens anders wordt gebruikt en `_haal_pagina_op` niet
buiten de module.

### 9.6 Gewijzigde bestanden

| Bestand | Wat |
|---|---|
| `pages/Belastingrente_IB.py` | ingangsdatum 1 juli 2020; bronvermelding met vindplaats en uitzondering; `NIET_GEDEKT`; melding bij niet-gecontroleerd |
| `pages/Belastingrente_VpB.py` | rij 1 juni 2020 expliciet als bedoeld verschil vastgelegd; bronvermelding en controledatum; zelfde melding. **Geen waardewijziging** |
| `_tarieven_check.py` | `Controle` met vier statussen; `controleregel()` voor de voettekst; docstrings die zeggen wat de controle wél en niet ziet |
| `tests/_tarieventabellen.py` | nieuw: leest de TARIEVEN uit de pagina's, zodat tests de werkelijk gebruikte reeks toetsen |
| `tests/test_rente.py` | juni 2020 voor IB en VpB; een berekening over een tijdvak dat juni 2020 omvat |
| `tests/test_tarieven_check.py` | bewuste afwijking als gegeven; tests voor de vier statussen en voor de voetnoot op de bron |

### 9.7 Wat hierbuiten is gebleven

De reeks staat sinds 7 september 2026 op twee plekken: hier en in `Berekeningen`. Welke
van de twee de bron wordt en hoe de andere hem overneemt in plaats van overtypt, is een
openstaand besluit — zie `PostbusClaude/VRAGEN-07-09-2026.md`, punt 1. Er is hier niets
verhuisd en geen koppeling tussen de repository's gebouwd; de drie punten hierboven zijn
fout welk besluit er ook valt.


## L09 — invoergrenzen rentepagina's, 8 september 2026

De pagina's blokkeren navordering op eigen verzoek zolang de verzoekdatum ontbreekt. Voorheen viel die invoer stil terug op gewone navordering. Een renteperiode die begint vóór de oudste tariefingang wordt geblokkeerd, zodat geen tarief van2012 op oudere perioden wordt toegepast. Dit begrenst de dekking van deze tool; er is geen nieuwe historische fiscale regel of tarief toegevoegd.

Zodra het berekende rente-einde na vandaag ligt, wordt de uitkomst expliciet een raming met het laatst opgenomen percentage genoemd. De ingangsdatum van dat percentage garandeert geen geldigheid gedurende een heel kalenderjaar. Het voorlopige-aanslagvinkje op de VpB-pagina vermeldt dat de vrijstellingsuitkomst op een gebruikersverklaring berust.

De pure rekenmodule en tariefreeksen zijn ongewijzigd. Elf nieuwe tests voeren de echte berekeningssecties van beide pagina's uit met synthetische invoer en een vaste klok. Geen Streamlit-app gestart en geen live bron of klantbestand nodig voor deze controles. Volledige testset:393geslaagd. Technische review en publicatie via de bestaande route blijven afzonderlijk; geen nieuwe fiscale accordering of modelvergelijking.


---

## L10 — invorderingsrente: een nieuwe module, en een dagentelling die anders bleek, 18-09-2026 11:53 CEST

**Aanleiding:** de onderzoeksnotitie
`PostbusClaude/belastingtool-joindk/AAN-CODEX-20260910-invorderingsrente-functionele-eisen.md`
van 10 september 2026. Die notitie noemde vier punten die vóór de eerste regel code moesten
worden nagezocht en liet twee keuzes aan Sylvain.
**Keuzes van Sylvain, verwerkt in deze module:** bouw art. 28, 28a en 28b; art. 28c alleen
als signalering. En: reken de opschorting tijdens uitstel niet door maar vraag haar uit, met
een blokkade op de uitkomst zolang zij niet is ingevuld.
**Tests:** van 393 naar 465, alle groen.

### L10.1 Het onderzoek sprak de verwachting tegen

Dit is de belangrijkste uitkomst van deze ronde, en zij raakt de rekenkern.

De notitie schreef dat hoofdstuk V IW 1990 op het eerste gezicht een telling in werkelijke
dagen lijkt voor te schrijven, en waarschuwde dat `dagen_30_360()` uit `_rente.py` daarom niet
mocht worden hergebruikt. Die waarschuwing was terecht, maar om een andere reden dan gedacht.
**Artikel 31 van de Uitvoeringsregeling Invorderingswet 1990 schrijft geen telling in
werkelijke dagen voor, en ook geen zuivere 30/360-telling, maar een mengvorm:**

> "Bij de bepaling van het aantal dagen waarover invorderingsrente wordt berekend, wordt:
> a. de maand waarin de enige of laatste betalingstermijn van de aanslag vervalt, tot het
> werkelijke aantal dagen in aanmerking genomen met dien verstande dat de maand februari
> altijd op 28 dagen wordt gesteld; b. een volle maand gesteld op 30 dagen en een jaar op
> 360 dagen."

Er kwamen in dezelfde regeling nog drie afwijkingen bij die de notitie niet had voorzien:

| Regel | Wat er staat | Waar het van afwijkt |
|---|---|---|
| art. 32 URIW | in rekening te brengen rente naar beneden afgerond op hele euro's, te vergoeden rente **naar boven** | belastingrente rondt in beide gevallen naar beneden af |
| art. 30 lid 1 URIW | `(A x P + A x P enz.) x betaling / 36000` — de deelperioden worden eerst opgeteld | belastingrente rondt **per tariefperiode** af |
| art. 33 URIW | bij de enige of laatste betaling blijft € 49 of minder buiten invordering (€ 23 tot en met 2025) | belastingrente kent geen drempelbedrag |

En één die de grondslag raakt: art. 29 URIW rekent de in rekening te brengen rente **over
iedere betaling afzonderlijk**, en art. 30 lid 1 rekent haar over het betaalde bedrag en niet
over het openstaande saldo. Art. 30 lid 2 geeft de formule om een ontvangen betaling te
splitsen in hoofdsom en rente. Beide formules staan in de regeling als afbeelding en niet als
tekst; zij zijn overgenomen uit illustratie `123954.png` en `123955.png` bij art. 30 in de
KOOP-versie 2026-01-01_0.

Gevolg voor de bouw: er staat een eigen `dagen_invorderingsrente()` in
`_invorderingsrente.py` en `dagen_30_360()` is niet hergebruikt. Er staat een test
(`test_dagentelling_is_niet_die_van_de_belastingrente`) die vastlegt dat de twee tellingen
aantoonbaar uiteenlopen, zodat het verschil niet later wordt "rechtgetrokken".

### L10.2 De tariefreeks: het zijn er twee, niet één

De notitie schreef dat het besluit geen onderscheid maakt tussen rente die in rekening wordt
gebracht en rente die wordt vergoed. **Dat klopt pas vanaf 1 januari 2024.** Tot en met
31 december 2023 kende artikel 2 van het Besluit belasting- en invorderingsrente twee leden:
lid 1 gaf een vast percentage voor de in rekening te brengen rente, lid 2 koppelde de te
vergoeden rente aan de wettelijke rente van art. 6:119 BW, "met dien verstande dat het
eerstgenoemde percentage ten minste 4 bedraagt".

| Periode | In rekening | Te vergoeden | Grondslag van de vergoeding |
|---|---|---|---|
| 01-06-2020 t/m 30-06-2022 | 0,01% | 4% | wettelijke rente 2%, bodem 4 |
| 01-07-2022 t/m 31-12-2022 | 1% | 4% | wettelijke rente 2%, bodem 4 |
| 01-01-2023 t/m 30-06-2023 | 2% | 4% | wettelijke rente 4%, bodem 4 |
| 01-07-2023 t/m 31-12-2023 | 3% | **6%** | wettelijke rente 6% |
| 01-01-2024 t/m 31-12-2025 | 4% | 4% | één percentage (art. 2, Stb. 2023, 511) |
| vanaf 01-01-2026 | 4,3% | 4,3% | één percentage (art. 2, Stb. 2025, 383) |

In de tweede helft van 2023 is het verschil dus een factor twee. Wie daar één reeks gebruikt,
rekent een vergoeding op de helft uit. De twee reeksen staan als `TARIEVEN_IN_REKENING` en
`TARIEVEN_TE_VERGOEDEN` in de module, met een test die vastlegt dat zij in die periode
uiteenlopen en vanaf 2024 weer samenvallen.

Nog een verschil met de notitie: die telde dertien expressies met een eigen ingangsdatum. Het
zijn er veertien; **23 juni 2020** ontbrak in dat rijtje. Op de percentages maakt dat niets
uit, want die versie wijzigde art. 2 niet.

Een onbekende datum geeft geen stille terugval. `tarief_op()` in deze module geeft `None`
terug vóór 1 juni 2020, waar `_rente.tarief_op()` juist terugvalt op het oudste percentage.
De pagina blokkeert dan met een melding.

### L10.3 De aanwijzing van art. 28 lid 5, en het tijdvak van art. 28 lid 4

Beide staan in hoofdstuk II van het Uitvoeringsbesluit Invorderingswet 1990, dat blijkens
art. 1 lid 1 uitvoering geeft aan onder meer art. 28 van de wet.

**Art. 28 lid 5 — geen rente wegens uitzonderlijke omstandigheden.** Er zijn twee aangewezen
gevallen: art. 6bis (het aanhoudaanbod van de ontvanger bij een in 2022 gedagtekende
voorlopige aanslag IB 2022 met box 3) en art. 6ter (de hersteloperatie toeslagen, zolang de
invordering is gepauzeerd). Beide staan als aanvinkbare regel op de pagina; aanvinken
blokkeert de uitkomst, omdat de tool niet bepaalt over welke dagen de uitzondering precies
loopt.

Daarnaast is de Leidraad Invordering 2008 nagelezen. Die bevat één beleidsmatige regel die
hetzelfde effect heeft maar een andere status: art. 28.3a vermindert de rente tot nihil over
de periode van uitstel op grond van art. 25.4.6 van de Leidraad. Die staat als derde regel in
de lijst, uitdrukkelijk gemerkt als beleid en niet als AMvB. De Leidraad bevat géén nadere
regel over de dagentelling; art. 31 URIW is daarvoor de enige bron.

**Art. 28 lid 4 — herleving na beëindigd uitstel.** Art. 6 van het Uitvoeringsbesluit wijst
twee tijdvakken aan: voor uitstel op grond van art. 25 lid 5 of 8 loopt de rente vanaf de dag
waarop zes weken zijn verstreken na de eerste dag van het jaar volgend op het jaar van de
gebeurtenis, en voor de overige gronden vanaf de dag volgend op de dag waarop de omstandigheid
zich voordoet. De tool rekent dat niet uit maar toont het wel, zodat zichtbaar is wat er
geldt. Let op: **art. 25 lid 3 staat wel in art. 28 lid 3 maar niet in lid 4 en niet in
art. 6 van het Uitvoeringsbesluit.** Voor die grond is geen herlevingstijdvak aangewezen en
doet de tool daarover geen uitspraak.

### L10.4 Samenloop met de belastingrentemodule

De opdracht vroeg dit in de wettekst zelf na te lezen en niet op gezag van de notitie aan te
nemen. Dat is gedaan, en het levert een scherper beeld op dan "art. 28a en 28c":

| Grondslag | Uitsluiting van dagen waarover al belastingrente is vergoed? |
|---|---|
| art. 28 lid 2 | nee |
| art. 28a lid 2, tweede volzin | **ja** |
| art. 28b lid 2 | nee |
| art. 28c lid 2, tweede volzin | ja, maar deze grondslag wordt niet gerekend |

Van de drie gebouwde grondslagen kent dus **alleen art. 28a** die uitsluiting. Zij is als
gedeelde invoer gebouwd en niet als gedeelde rekenkern: de pagina vraagt bij art. 28a de
periode waarover al belastingrente is vergoed, en die dagen tellen niet mee. Zonder beide
datums geeft de pagina geen uitkomst. De vastlegging staat als `UITSLUITING_BELASTINGRENTE`
in de module, met een test per grondslag.

Art. 28 lid 1 kent wel een eigen, andere beperking: geen rente voor zover met de aanslag een
aanslag wordt verrekend die op dezelfde belasting en hetzelfde tijdvak ziet. Dat is geen
dagenuitsluiting maar een beperking van de grondslag. De pagina waarschuwt daarvoor en bepaalt
dat deel niet.

### L10.5 De bronnen, met hash

Alle teksten komen uit de KOOP-repository en niet uit een samenvatting. Van elke versie is de
SHA-512 van het opgehaalde bestand vergeleken met de `hashcode` in het bijbehorende manifest.

| Bron | BWB | Versie | SHA-256 (eerste 16) | Manifesthash |
|---|---|---|---|---|
| Invorderingswet 1990 | BWBR0004770 | 2026-07-01_0 | `4ea1c83fdf3c3c49` | komt overeen |
| Uitvoeringsregeling IW 1990 | BWBR0004766 | 2026-01-01_0 | `69b596a6fc43dd5a` | komt overeen |
| Uitvoeringsbesluit IW 1990 | BWBR0004772 | 2025-12-12_0 | `2209bcf0a5237fc4` | komt overeen |
| Besluit belasting- en invorderingsrente | BWBR0043680 | 2026-02-13_0 | `1d7ccd565188dbc0` | komt overeen |
| Leidraad Invordering 2008 | BWBR0024096 | 2026-07-01_0 | `dad80912c9c7d310` | komt overeen |
| Besluit vaststelling wettelijke rente | BWBR0047640 | per ingangsdatum | zie module | komt overeen |
| Besluit wettelijke rente | BWBR0002744 | 2015-01-01_0 | `694dc8019c5409b5` | **wijkt af** |

De twee eerste hashes bevestigen de meting uit de onderzoeksnotitie van 10 september.

Die laatste regel is het enige losse eind in de bronketen. Voor de expressie van het Besluit
wettelijke rente die 2 procent vaststelt, kwam de zelf berekende SHA-512 niet overeen met de
hashcode in het manifest; de meting is herhaald na opnieuw downloaden en gaf dezelfde
uitkomst. **Het raakt de uitkomst niet:** dat percentage telt alleen mee via de bodem van
4 procent in art. 2 lid 2 van het Besluit belasting- en invorderingsrente, en elk percentage
onder de 4 geeft na toepassing van die bodem dezelfde 4.

### L10.6 Wat er is gebouwd

| Bestand | Wat |
|---|---|
| `_invorderingsrente.py` | nieuw. Tarieven, drempels, dagentelling art. 31, afronding art. 32, de formules van art. 30, de drie tijdvakken, de uitstelgronden, de uitzonderingen en de signalering van art. 28c |
| `pages/Invorderingsrente.py` | nieuw. Uitvraag per grondslag, alle blokkades, uitvoer met de deelperioden en een uitklapblok met de uitgangspunten |
| `app.py` | de pagina toegevoegd aan de router |
| `tests/test_invorderingsrente.py` | nieuw, 51 tests. Elke test die een fiscale regel vastlegt noemt het artikel in zijn docstring |
| `tests/test_invorderingsrentepagina.py` | nieuw, 21 tests. Draait de pagina met een nagebouwde Streamlit en bewaakt de blokkades |
| `README.md` | de zevende pagina beschreven, structuurtabel en testaantal bijgewerkt |

**Er is geen toetssteen zoals bij belastingrente.** De Belastingdienst publiceert voor
invorderingsrente geen rekenvoorbeeld waarmee de methode tot op de euro kan worden
gereproduceerd; de pagina met rentepercentages bevat ook geen invorderingsrentetabel. De
tests leggen daarom de wettelijke regels vast met de vindplaats erbij, en niet een
gepubliceerde uitkomst. Dat is een zwakkere vorm van bewijs dan bij `_rente.py`, en dat hoort
bij de beoordeling te worden meegewogen.

### L10.7 Openstaande fiscale punten

Deze punten zijn bewust niet zelfstandig beslist. Zij staan hier omdat een verkeerde keuze
tot een verkeerd bedrag leidt.

1. **Geldt art. 31 onderdeel a ook bij art. 28a?** Onderdeel a hangt aan "de maand waarin de
   enige of laatste betalingstermijn van de aanslag vervalt". Bij art. 28 en art. 28b bestaat
   die maand, want beide tijdvakken haken aan bij de invorderbaarheid van art. 9. Bij art. 28a
   vangt het tijdvak aan na de dagtekening van een uitbetaling en vervalt er niets. De module
   past daar alleen onderdeel b toe, dus 30 dagen per maand. Dat scheelt: over dezelfde
   periode 26-02-2026 tot en met 09-04-2026 geeft dat 44 dagen in plaats van 42.
2. **Hoe telt een gedeeltelijke maand die niet de vervalmaand is?** Art. 31 noemt de
   vervalmaand en de volle maand, maar niet met zoveel woorden de laatste, onvolledige maand
   van een tijdvak. De module telt die naar rato binnen een maandlengte van 30, dezelfde
   systematiek die `dagen_30_360()` gebruikt. Dat volgt uit onderdeel b maar staat er niet
   letterlijk.
3. **Welke formule geldt voor een vergoeding?** Art. 30 URIW is naar zijn tekst geschreven
   voor de in rekening te brengen rente over een betaling. Voor art. 28a en 28b kent de
   regeling geen eigen formule. De module gebruikt dezelfde enkelvoudige formule met het uit
   te betalen respectievelijk het terug te geven bedrag als grondslag; de wet noemt die
   grondslag zelf in art. 28b lid 2, slot.
4. **Deelbetalingen worden niet toegerekend.** Art. 29 URIW rekent per betaling afzonderlijk.
   De pagina rekent één betaling per keer door. Bij meerdere betalingen moet de gebruiker elke
   betaling apart invoeren; de tool verdeelt een openstaand saldo niet zelf en past de
   splitsingsformule van art. 30 lid 2 niet automatisch toe. `splits_betaling()` staat wel in
   de module en is getest, maar wordt door de pagina nog niet aangeboden.
5. **Uitstel wordt niet doorgerekend.** Dat is de keuze van Sylvain en geen tekort van het
   onderzoek, maar het blijft een beperking: voor een aanslag waarvoor uitstel is verleend
   geeft de tool geen bedrag.
6. **Art. 28c wordt niet gerekend.** Ook een keuze van Sylvain. De pagina signaleert de grond
   en de verzoektermijn van zes weken.
7. **De vier tijdvakken zijn niet aan uitvoeringsbeleid of rechtspraak getoetst.** Zij zijn
   uit de wettekst overgenomen, net als in de onderzoeksnotitie. De Leidraad Invordering 2008
   is wel nagelezen op afwijkingen en gaf er op dit punt geen.
