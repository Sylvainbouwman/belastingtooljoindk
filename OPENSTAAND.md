# Openstaande punten

Laatst bijgewerkt: 20-09-2026 15:45 CEST. Eerste versie van dit bestand; eerder stonden
openstaande punten alleen in `WIJZIGINGSRAPPORT.md` (de actielijst per wijziging) en, voor
dit ene punt, in de nu gearchiveerde berichtenmap `PostbusClaude`.

**Stand:** van de 10 punten staan er 6 open en zijn er 4 gesloten. De zeven fiscale
punten van de pagina Invorderingsrente zijn op 20-09-2026 uit `WIJZIGINGSRAPPORT.md`
hierheen gehaald; twee daarvan zijn diezelfde dag beslist.

## Open

Deze punten stonden tot 20-09-2026 alleen in `WIJZIGINGSRAPPORT.md`, paragraaf L10.7. Zij
raken alle de pagina Invorderingsrente. Ze zijn hierheen gehaald omdat de index over de
repository's heen naar dit bestand kijkt en ze daar dus niet zag; het wijzigingsrapport
verwijst nu hierheen.

### 2. Hoe telt een gedeeltelijke maand die niet de vervalmaand is?

**Status:** open. **Eigenaar:** Sylvain Bouwman. **Vindplaats:** `_invorderingsrente.py`,
`WIJZIGINGSRAPPORT.md` L10.7 punt 2.

Art. 31 URIW noemt de vervalmaand en de volle maand, maar niet met zoveel woorden de
laatste, onvolledige maand van een tijdvak. De module telt die naar rato binnen een
maandlengte van 30, dezelfde systematiek die `dagen_30_360()` gebruikt. Dat volgt uit
onderdeel b maar staat er niet letterlijk.

### 3. Welke formule geldt voor een vergoeding?

**Status:** open. **Eigenaar:** Sylvain Bouwman. **Vindplaats:** `_invorderingsrente.py`,
`WIJZIGINGSRAPPORT.md` L10.7 punt 3.

Art. 30 URIW is naar zijn tekst geschreven voor de in rekening te brengen rente over een
betaling. Voor art. 28a en 28b kent de regeling geen eigen formule. De module gebruikt
dezelfde enkelvoudige formule met het uit te betalen respectievelijk het terug te geven
bedrag als grondslag; de wet noemt die grondslag zelf in art. 28b lid 2, slot.

### 4. Uitstel wordt niet doorgerekend

**Status:** open, als bekende beperking. **Eigenaar:** Sylvain Bouwman.
**Vindplaats:** `WIJZIGINGSRAPPORT.md` L10.7 punt 5.

Dat is een keuze van Sylvain en geen tekort van het onderzoek, maar het blijft een grens:
voor een aanslag waarvoor uitstel is verleend geeft de tool geen bedrag. Staat hier zodat
zichtbaar blijft wat de tool niet doet.

### 5. Art. 28c wordt niet gerekend

**Status:** open, als bekende beperking. **Eigenaar:** Sylvain Bouwman.
**Vindplaats:** `WIJZIGINGSRAPPORT.md` L10.7 punt 6.

Ook een keuze van Sylvain. De pagina signaleert wel de grond en de verzoektermijn van zes
weken, maar rekent het bedrag niet uit.

### 6. De vier tijdvakken zijn niet aan uitvoeringsbeleid of rechtspraak getoetst

**Status:** open. **Eigenaar:** Sylvain Bouwman. **Vindplaats:**
`WIJZIGINGSRAPPORT.md` L10.7 punt 7.

Zij zijn uit de wettekst overgenomen, net als in de onderzoeksnotitie. De Leidraad
Invordering 2008 is wel nagelezen op afwijkingen en gaf er op dit punt geen. Wat ontbreekt
is een toets aan rechtspraak en aan gepubliceerd uitvoeringsbeleid daarbuiten.

### 10. Hoort deze tool in het portaal van bouwman.tools, of niet?

**Status:** open. **Eigenaar:** Sylvain Bouwman. **Gevonden op** 20-09-2026.

`AGENTS.md` van deze repository opent met: "Hoort **niet** bij de portal op bouwman.tools
en heet dus nooit Bouwman Tools." Het toolregister zegt het omgekeerde: `in_portal` staat
op `true`, met een `url` naar `belastingtooljoindk.streamlit.app`. Het portaal bouwt zijn
kaarten uit dat register op, dus de tool wordt daar getoond met een link naar de
Streamlit-app.

Dat is geen fout in het register: er staan drie tools zo in, naast deze ook `auditfile-app`
en `dba-risicoscan`. Maar een van de twee teksten klopt niet, en dat maakt uit voor wie de
tool ziet en welke status-tag daarbij hoort.

**Wat er moet gebeuren:** vaststellen welke van de twee de bedoeling is. Hoort hij in het
portaal, dan moet die zin uit `AGENTS.md`. Hoort hij er niet in, dan moet `in_portal` naar
`false` en verdwijnt de kaart. Niet zelf gekozen, want het raakt wie de tool te zien krijgt.

## Gesloten

### 7. Geldt art. 31 onderdeel a ook bij art. 28a?

**Status:** gesloten op 20-09-2026. **Eigenaar:** Sylvain Bouwman. **Herkomst:**
`WIJZIGINGSRAPPORT.md` L10.7 punt 1.

Onderdeel a hangt aan "de maand waarin de enige of laatste betalingstermijn van de aanslag
vervalt". Bij art. 28 en art. 28b bestaat die maand, want beide tijdvakken haken aan bij de
invorderbaarheid van art. 9. Bij art. 28a vangt het tijdvak aan na de dagtekening van een
uitbetaling en vervalt er niets. De module past daar alleen onderdeel b toe, dus 30 dagen
per maand. Over 26-02-2026 tot en met 09-04-2026 geeft dat 44 dagen in plaats van 42.

**Besluit van Sylvain op 20-09-2026: dat blijft zo.** De grond is de tekst zelf: onderdeel a
knoopt aan bij een vervallende betalingstermijn van een aanslag, en bij art. 28a is er geen
aanslag en vervalt er geen termijn. Dat aanknopingspunt ontbreekt dus, en dan geldt
onderdeel b voor alle maanden van het tijdvak.

**Wat onzeker blijft:** de wet zegt niet met zoveel woorden dat onderdeel a bij art. 28a
buiten toepassing blijft; dat volgt uit het ontbreken van het aanknopingspunt. Er is geen
rechtspraak of gepubliceerd beleid over gevonden. De melding bij de uitkomst blijft daarom
staan. Heroverwegen zodra beleid of een uitspraak hierover verschijnt.

### 8. Deelbetalingen worden niet toegerekend

**Status:** gesloten op 20-09-2026. **Eigenaar:** Sylvain Bouwman. **Herkomst:**
`WIJZIGINGSRAPPORT.md` L10.7 punt 4.

Art. 29 URIW rekent per betaling afzonderlijk. De pagina rekent één betaling per keer door;
bij meerdere betalingen voert de gebruiker ze los in. De tool verdeelt een openstaand saldo
niet zelf en past de splitsingsformule van art. 30 lid 2 niet automatisch toe.
`splits_betaling()` staat wel in de module en is getest, maar wordt door de pagina niet
aangeboden.

**Besluit van Sylvain op 20-09-2026: dat blijft zo, en de functie blijft staan.** Eén
betaling per keer is te overzien, en meerdere betalingen in één scherm maakt de invoer fors
ingewikkelder voor een geval dat zich weinig voordoet. De melding die zegt dat de gebruiker
ze los moet invoeren blijft. Overwogen en niet gekozen: de functie weghalen, omdat het werk
dan opnieuw moet als de testgroep haar toch mist. Komt die vraag uit het testen, dan is dit
het punt om te heropenen.

### 9. De verwijzing naar "openstaand punt A" wees nergens heen

**Status:** gesloten op 20-09-2026, opgeruimd.

`WIJZIGINGSRAPPORT.md` verwees bij de Auto BTW privé-pagina naar "openstaand punt A
hieronder". Dat punt is nooit uitgewerkt: in de allereerste versie van het rapport
(commit `869ceff`) stond de verwijzing er al zonder doel. Er is dus niets verdwenen bij een
opruiming, maar de tekst beloofde wel een punt dat er niet was. De verwijzing is vervangen
door wat er feitelijk over de nulemissietabel te zeggen valt.

### 1. Waar hoort de belastingrente te worden gerekend: `belastingtooljoindk` of `Berekeningen`

**Status:** gesloten op 20-09-2026. **Eigenaar:** Sylvain Bouwman.

**Herkomst:** `PostbusClaude/archief/2026-09/VRAGEN-07-09-2026.md`, vraag 1 ("Waar hoort de
belastingrente te worden gerekend? (klus 3c, en daarmee ook 3b)"), met de aanvulling van de
tweede sessie diezelfde dag ("Bij vraag 1 — waar de belastingrente hoort: correctie op mijn
eigen aanvulling"). Overgezet op 19-09-2026 bij het opruimen van `PostbusClaude`.
`WIJZIGINGSRAPPORT.md`, paragraaf 9.7, verwees al naar dit punt maar wees naar het
brondocument in `PostbusClaude` zelf; die verwijzing is bijgewerkt naar dit bestand. Dit punt
speelt in twee repository's tegelijk; dezelfde tekst staat ook in
`Berekeningen/OPENSTAAND.md`.

Woordelijk uit het brondocument:

> **Wat de vraag daarmee wordt.** Niet "komen er twee plekken", want die zijn er nu. De vraag
> is welke van de twee de bron wordt en wat er met de andere gebeurt:
>
> - **Consolideren in `belastingtooljoindk`** heeft de rijkere renteberekening (dagen,
>   dagtekening, aanslagtermijnen, maximering van 19 weken) en de bestaande tests. De prijs:
>   het onderwerp revisierente dat vandaag in `Berekeningen` is gepubliceerd moet daar dan
>   weer uit, en de revisierente verhuist naar een Streamlit-app buiten het portaal.
> - **Consolideren in `Berekeningen`** heeft de gecontroleerde reeks met vindplaats en
>   controledatum, de melding bij een onbekend jaar en de eindige reeks. De prijs: de
>   dagtelling en het bepalen van begin- en einddatum per aanslagsoort moeten daar nog bij, en
>   dat is precies het zware deel van model 02-04.
>
> **Mijn voorkeur, en die is verschoven door wat ik hierboven vond:** consolideren in
> `belastingtooljoindk` voor het aanslagdeel, en de percentagereeks daar overnemen uit
> `Berekeningen`, inclusief de vindplaatsen, de controledatum, de eindigheid en de juiste
> juli-datum. Het onderwerp revisierente laat ik dan staan waar het staat, want dat rekent
> geen aanslag maar past één wettelijk voorschrift toe (art. 30i lid 3) en heeft de
> dagtelling niet nodig. Dat is geen dubbele bron van waarheid maar één reeks met twee
> gebruikers — en dán is het wel nodig dat de reeks op één plek staat en de andere hem
> invoert in plaats van overtypt.
>
> **Dat laatste is werk dat nog niemand heeft gedaan** en het is de kern van uw besluit:
> zolang de reeks op twee plekken met de hand wordt bijgewerkt, loopt hij uiteen. Dat is
> vandaag al aantoonbaar gebeurd, want de ene plek heeft juni 2020 fout en de andere niet.
>
> ### En hier zat een gat in mijn eigen advies
>
> "De tweede voert de reeks in in plaats van hem over te typen" klinkt sluitend, maar er zit
> geen mechanisme onder, en de eerste sessie wees mij daarop. `Berekeningen` is één
> HTML-bestand dat offline moet werken, `belastingtooljoindk` is Python: die kunnen geen
> bestand delen. Wat overblijft is onvolmaakt, en het is eerlijker om dat te laten zien dan
> om "consolideren" als opgelost te presenteren:
>
> | Mechanisme | Wat het kost | Waar het knelt |
> | --- | --- | --- |
> | Eén bronbestand, met een bouwstap die in beide repository's een reeks genereert | een
>   bouwstap in twee talen, en `Berekeningen` heeft er nu geen | `berekeningen.html`
>   verliest zijn eigenschap dat het bestand zelf de bron is; een bouwproduct in een
>   single-file tool is een nieuwe klasse fouten |
> | Een derde repository als bron van de reeks | een repository, een versie en een
>   publicatieroute erbij | zwaar voor twaalf regels, en het onderhoud verschuift naar een
>   plek waar niemand kijkt |
> | Een controle die de twee reeksen tegen elkaar toetst en luid faalt bij verschil | één
>   test of één script, in één van de twee repository's | lost de duplicatie niet op, maar
>   maakt afwijken onmogelijk zonder dat iemand het ziet |
>
> **De derde is de goedkoopste en zou deze fout gevonden hebben.** Dat is ook waar de eerste
> sessie op uitkomt, en daar sluit ik mij bij aan zodat u niet twee adviezen krijgt.
> Consolideren blijft de richting; de controle is wat er als eerste moet komen, want die
> werkt ook zolang er niet geconsolideerd is.

**Wat hier al wel is gebeurd, ter toelichting en niet ter afdoening van de vraag zelf:** de
IB-datumfout (1 juni tegenover 1 juli 2020) waar de aanvulling naar verwijst, is inmiddels in
`pages/Belastingrente_IB.py` gecorrigeerd naar 1 juli, met de vindplaats en de uitleg van het
verschil in het commentaar erboven. Ook de VpB-tarieventabel in
`pages/Belastingrente_VpB.py` is inmiddels bijgewerkt met de na het arrest van de Hoge Raad
van 16 januari 2026 gecorrigeerde percentages voor 2022 tot en met 2026, zonder dat daarvoor
een schakelaar (het bronmodel 02-04 kent `hrArrestToepassen`) is gebouwd; de tool toont één
uitkomst op basis van de gecorrigeerde reeks. Dat lost de onderliggende datafout en het
arrest-punt van vraag 4 in het brondocument op, maar beantwoordt niet welke repository de
bron wordt voor de percentagereeks zelf en hoe de andere repository haar voortaan overneemt
in plaats van overtypt. Dat besluit is op 20-09-2026 genomen; zie hieronder.

---

**Gesloten op 20-09-2026.** Besluit van Sylvain Bouwman.

**De vraag zelf berustte op een aanname die niet klopt.** De brondocumenten van
07-09-2026 gingen ervan uit dat twee tools hetzelfde doen en dat een van beide de bron
moet worden. Nagemeten op 20-09-2026: dat is niet zo. `Berekeningen` gebruikt de
percentagereeks uitsluitend voor de tegenbewijsregeling van art. 30i lid 3 AWR en telt
daarbij in hele maanden met een gemiddeld percentage; er zit geen dagtelling,
dagtekening of aanslagtermijn in. `belastingtooljoindk` rekent een aanslag met precies
die onderdelen. Er is dus geen dubbele implementatie om te consolideren, maar een
gedeeld gegeven met twee gebruikers die er iets anders mee doen. Consolideren van de
berekening zou een van beide tools iets opleggen wat zij niet nodig heeft.

**Wat er wel te bewaken viel is gebouwd.** De twaalf percentages zijn op 20-09-2026
naast elkaar gelegd: zij zijn identiek over alle 180 maanden van januari 2012 tot en met
december 2026. De fout waar het punt op wees, 1 juni tegenover 1 juli 2020 voor de
inkomstenbelasting, is hersteld. Om te voorkomen dat zij opnieuw uiteenlopen is de
bewaking in drie schakels gelegd:

1. `belastingrente-ib-reeks.txt` staat woordelijk gelijk in beide repository's: de
   reeks als leesbare tekst, met de bron en de reden van de juli-uitzondering erbij.
2. Elke repository heeft een test die haar eigen constante tegen dat bestand legt en
   faalt zodra de code en het bestand uiteenlopen. In `Berekeningen` is dat
   `tests/rentereeks-gedeeld.test.mjs`, hier `tests/test_rentereeks_gedeeld.py`. Beide
   zijn op 20-09-2026 getoetst door de reeks te verstoren; zij worden dan rood, en de
   Python-kant vangt de historische juni-fout met drie afzonderlijke toetsen.
3. `PostbusClaude/controle_rentereeks.py` vergelijkt de twee bestanden. Dat kan geen
   test doen, want de repository's zien elkaar niet; dit script draait op een machine
   waar beide staan.

**Waarom de bewaking zo is verdeeld en niet anders.** Twee repository's die elkaar niet
zien kunnen in hun eigen CI niet bewijzen dat zij gelijk zijn. Wat elke kant wel kan is
zich binden aan een leesbaar bestand. Het vorige controlescript,
`PostbusClaude/controle_rentetabellen.py`, probeerde de code van beide tools
rechtstreeks te lezen met een bewust smal contract. Gemeten op 20-09-2026 weigerde het
met "Aanvullend of onbekend gebruik van Python-TARIEVEN": de IB-pagina had er twee
leesplekken bij gekregen. Het heeft dus maanden niets gemeten terwijl het bestond, en
juist in die periode liepen de reeksen uiteen. Het is vervangen en blijft in de
Git-historie van die map terugvindbaar.

**Wat hiermee niet is beslist.** Of de percentages zelf nog kloppen met de bron is een
andere vraag; die bewaakt de netwerkcontrole `_tarieven_check.py` in deze repository.
En de reeks eindigt bewust bij december 2026. Het percentage wordt jaarlijks per
1 januari vastgesteld, dus bij de eerstvolgende jaarwisseling moeten beide bestanden en
beide tools worden verlengd nadat het nieuwe percentage is teruggevonden.
