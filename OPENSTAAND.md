# Openstaande punten

Formaat: per punt

> Dit document is de bron voor de openstaande punten van deze tool. Elk punt heeft een
> status (open of gesloten), een eigenaar (Sylvain of sessie) en een vindplaats. Een
> gesloten punt blijft staan, met datum en reden. Het overzicht in
> `AI_kopgroep/OPEN-PUNTEN.md` leest de regel "Formaat: per punt" hierboven en toont dan
> alleen de open punten met eigenaar Sylvain. Wat een sessie zelf kan doen, staat hier
> wel maar niet in dat overzicht.
>
> De vrijgavenotities, `update-bram.md` en `WIJZIGINGSRAPPORT.md` in deze map zijn
> verslag. Een punt dat daarin nog open staat, hoort hier.
>
> Eerste versie van dit bestand op 29-09-2026; eerder stonden de openstaande punten alleen
> in `WIJZIGINGSRAPPORT.md` (de actielijst per wijziging).
>
> Omgezet naar deze vorm op 04-10-2026 22:46 CEST. De tekst van daarvoor staat in de Git-historie (laatste
> versie in commit 027f7d1). De 16 bestaande punten staan hieronder woordelijk met hun
> bestaande nummer; ze kregen alleen de drie veldregels erbij (Status, Eigenaar,
> Vindplaats), afgeleid uit hun eigen tekst. De punten 17 t/m 30 zijn bij de omzetting
> toegevoegd uit de zeven actiedocumenten van deze map (`OPENSTAAND.md` zelf, `update-bram.md`,
> vier vrijgavenotities en `WIJZIGINGSRAPPORT.md`) en uit `README.md`,
> `UC_belastingtooljoindk.md`, `AGENTS.md` en het concept
> `terugmelding-wolters-kluwer-model-02-04.md`. Waar elk punt uit die documenten is
> gebleven staat in `omzetting-actiedocumenten-2026-10-04.md`. Nummers worden nooit hergebruikt.

**Over eigenaarschap.** De POC is van Sylvain en hij beslist alles wat erin zit. Bram
bouwt de tool daarna op de kantooromgeving en kijkt niet in deze repository. Alle open
punten staan op sessie: er is geen besluit of handeling die alleen Sylvain kan nemen of
doen. Wat de tool bewust niet doet en zelf meldt, staat als achtergrond gemarkeerd. Bij
punt 28 en punt 30 hangt de uitkomst van een meting af die daarna een besluit voor Sylvain
kan opleveren.

## Open

### 17. Gebreken in de specificaties van de Belastingdienst, correctie niet vastgelegd
- **Status:** open, vermoedelijk gemeld en afgehandeld, zonder vastlegging
- **Eigenaar:** sessie
- **Vindplaats:** `update-bram.md`, r.52 en r.151 tot r.159; `WIJZIGINGSRAPPORT.md`, r.191, r.236, r.256 en r.523

In `update-bram.md` staan gebreken in de specificaties die Bram moet corrigeren voordat een ontwikkelaar ze meebouwt. 1. Paragraaf 12 van de specificatie van de rekenmodule telt eerst alle deelbedragen op en rondt daarna één keer af: € 103 waar de Belastingdienst € 102 publiceert. Paragraaf 11 zegt het goed (r.52). 2. Het controlecijfer op positie 1 wordt in de specificatie Betalingskenmerk_bepaling niet beschreven (r.151). 3. Drie van de 27 voorbeelden zijn inconsistent met zichzelf (r.153). 4. Paragraaf 4 zegt "pos 3" waar "pos 13" bedoeld wordt (r.159). Daarnaast geeft de specificatie geen codetabel voor het SOORT-cijfer: de tool labelt alleen 0 en 6 en toont bij een andere waarde niets in plaats van een gok (r.157 en `WIJZIGINGSRAPPORT.md` r.236 en r.523).

Het document draagt het label afgerond (18-09-2026) en paragraaf 7 van het wijzigingsrapport verklaart alle actiepunten gehandeld, maar nergens staat vastgelegd dat de specificaties zijn gecorrigeerd of dat Bram dat heeft bevestigd. Het vermoeden is dat het is gemeld en afgehandeld. Zonder bewijs blijft het punt open.

**Te sluiten wanneer:** vastgelegd is dat Bram de specificaties heeft gecorrigeerd of de terugkoppeling heeft ontvangen, of Sylvain heeft besloten dat het verslag volstaat.

### 19. De automatische tarievencontrole leest de voetnoten niet
- **Status:** bewuste beperking, als achtergrond gemarkeerd op 04-10-2026
- **Eigenaar:** sessie
- **Vindplaats:** `vrijgave-belastingtooljoindk-2026-09-07.md`, r.41 en r.77; `WIJZIGINGSRAPPORT.md`, r.774 en r.784; `README.md`, r.114

De controle die bij elke paginaweergave de tarieventabel op belastingdienst.nl vergelijkt, leest de tabel en niet de voetnoten eronder, en juist daar staan de uitzonderingen. De coronaverlaging voor de inkomstenbelasting per 1 juli 2020 staat in voetnoot ***. De tool meldt dat zelf: de IB-pagina geeft haar niet-gedekte deel mee (`NIET_GEDEKT`) en de voettekst zegt bij elke weergave wat er is gecontroleerd. Gekozen is voor een controle die zegt wat zij niet dekt, in plaats van een tweede parser voor één afgesloten uitzondering uit 2020. De toeslagenpercentages uit de voetnoten * en ** zijn niet gecontroleerd, omdat deze pagina's ze niet gebruiken. Twee tests bewaken de bewuste afwijking en het bestaan van de voetnoot op de bronpagina.

**Te sluiten wanneer:** besloten is of een voetnootcontrole erin komt, of vastgelegd is dat de melding volstaat.

### 20. De nulemissiereeks staat op twee plekken zonder bewaking
- **Status:** open, wacht op de eerstvolgende jaarwisseling
- **Eigenaar:** sessie
- **Vindplaats:** `vrijgave-belastingtooljoindk-2026-09-20.md`, r.35, r.39 en r.108; `WIJZIGINGSRAPPORT.md`, r.330; `_auto_calc.py`, `KORTING_NULEMISSIE`

De tabel `KORTING_NULEMISSIE` in `_auto_calc.py` staat in een andere vorm ook in de zustertool `auto-fiscaal-2027`. Beide vormen zijn op 20-09-2026 naast elkaar gelegd en komen voor alle jaarschijven overeen, maar niets bewaakt dat zij gelijk blijven. Voor de belastingrentereeks is die bewaking wel gebouwd (punt 1); hier is bewust alleen aangevuld.

De reeks verandert vaker dan je zou denken. De Wet fiscale maatregelen Klimaatakkoord liet de korting per 2026 vervallen, terwijl de jaarpagina van de Belastingdienst voor 2026 18 procent tot € 30.000 noemt: voor 2026 is de jaarpagina dus de bron. Voor 2027 staat 20 procent tot € 30.000 in art. 3.20 lid 2 Wet IB 2001 (toestand 01-01-2027). Voor een later regimejaar waarschuwt de tool vanaf 2028. Die vervaldatum is al eens met latere wetgeving opgeschoven, dus de melding blijft staan tot iemand haar opnieuw bij de bron heeft gezien.

**Te sluiten wanneer:** bij de eerstvolgende jaarwisseling beide reeksen naast elkaar zijn gelegd en de grens van 2028 opnieuw bij de bron is gelezen, of er een bewaking is gebouwd.

### 21. Het bewijs tegen model 02-04 dekt niet alles, en uitstel en art. 28c hebben geen model
- **Status:** bewuste beperking, als achtergrond gemarkeerd op 04-10-2026
- **Eigenaar:** sessie
- **Vindplaats:** `vrijgave-belastingtooljoindk-2026-09-29.md`, r.86, r.89 en r.90; `vrijgave-belastingtooljoindk-2026-10-04.md`, r.55; `WIJZIGINGSRAPPORT.md`, r.1024, r.1087 en r.1097

Niet vergeleken bij de gelijkwaardigheidstoets van 29-09-2026: de einddatum van de belastingrente (het model vraagt hem als invoer; die logica is getoetst aan de voorbeelden van de Belastingdienst), art. 28a en 28b (het model rekent ze niet), BTW en naheffing (rekent de tool niet) en 105 VpB-gevallen met het HR-arrest uit (de tool past het arrest altijd toe).

Uitstel en art. 28c zijn op 04-10-2026 gebouwd en hebben geen rekenmodel. Zij zijn getoetst aan de wettekst, door de bron-controleur en met doorgerekende gevallen. Paragraaf L10.6 van het wijzigingsrapport (18-09-2026) zegt dat er geen gepubliceerd rekenvoorbeeld voor de invorderingsrente bestaat en dat het bewijs daardoor zwakker is. Voor art. 28 is dat achterhaald, want sinds 29-09-2026 test de tool het rekenvoorbeeld van de Belastingdienst (240 dagen, 143 euro, L11.3) en is er het model. Voor art. 28a, 28b, 28c en uitstel blijft de wettekst het bewijs.

**Te sluiten wanneer:** besloten is of het bewijs wordt uitgebreid, of vastgelegd is dat de afbakening volstaat.

### 22. Herleving van de rente bij uitstel: 12 of 13 februari
- **Status:** open, aanname zonder bron, vastgelegd bij het sluiten van punt 4 op 04-10-2026
- **Eigenaar:** sessie
- **Vindplaats:** `vrijgave-belastingtooljoindk-2026-10-04.md`, r.49; `OPENSTAAND.md`, punt 4

Bij uitstel op grond van art. 25 lid 5 of 8 neemt de tool "de dag waarop zes weken zijn verstreken na de eerste dag van het jaar" als die dag zelf: 1 januari plus 42 dagen, dus 12 februari, en niet een dag later. Art. 6 lid 1 van het Uitvoeringsbesluit IW 1990 zegt "met ingang van de dag waarop" en lid 2 zegt "de dag volgende op". Geen gelezen bron beslist het, en het verschil is één dag rente. De bron-controleur kon het op 04-10-2026 niet sluiten. De nota van toelichting bij de oorspronkelijke tekst (Stb. 1991, 718) is alleen als scan beschikbaar en niet gelezen.

**Te sluiten wanneer:** de nota van toelichting is gelezen en de dag daarmee vaststaat, of Sylvain de lezing heeft vastgelegd.

### 23. Wat de tool bij uitstel bewust niet rekent
- **Status:** bewuste beperking, als achtergrond gemarkeerd op 04-10-2026
- **Eigenaar:** sessie
- **Vindplaats:** `vrijgave-belastingtooljoindk-2026-10-04.md`, r.24 en r.57; `WIJZIGINGSRAPPORT.md`, r.962 en r.1178; `README.md`, r.173; `OPENSTAAND.md`, punt 4

De tool geeft geen bedrag en wel een melding in twee gevallen. 1. Betaling na afloop van de uitsteltermijn bij de gronden van art. 28 lid 4: de wet legt dat tijdvak niet vast en art. 6 Uitvoeringsbesluit regelt alleen de beëindiging. De Leidraad Invordering 2008 kent beleid voor lid 9, 11 en 17 tot en met 19 (onderdeel 74.5, 74.5a, 74.10 en 74.11). Dat beleid is niet gebouwd en of het ook het gewoon aflopen van de termijn dekt is uitleg. Voor lid 5, 8 en 21 is niets gevonden. 2. Een beëindigd uitstel op grond van art. 25 lid 3: lid 4 en art. 6 Uitvoeringsbesluit noemen die grond niet, dus er is geen herlevingstijdvak aangewezen en de tool doet daarover geen uitspraak.

**Te sluiten wanneer:** besloten is of het Leidraadbeleid wordt gebouwd, of vastgelegd is dat de melding volstaat.

### 24. Auto BTW privé: twee gevallen die de tool niet toepast
- **Status:** bewuste beperking, als achtergrond gemarkeerd op 04-10-2026
- **Eigenaar:** sessie
- **Vindplaats:** `update-bram.md`, r.132 en r.133; `WIJZIGINGSRAPPORT.md`, r.287; `README.md`, r.199 en r.208

1. Bij een IB-ondernemer is de bijtelling nooit hoger dan de totale autokosten van het jaar. Dat staat in het rekenvoorbeeld van de Belastingdienst, maar de tool kent die kosten niet, past het maximum niet toe en meldt dat. 2. Een auto die volledig op geïntegreerde zonnecellen rijdt valt ook onder de plafondvrijstelling, maar dat is volgens de terugkoppeling aan Bram niet uit de RDW-gegevens af te leiden. De README noemt de zonnecelauto in de regel voor waterstof. Wat de tool in de praktijk doet is bij de omzetting niet in de code nagelezen.

**Te sluiten wanneer:** besloten is of de autokosten als invoer erbij komen en hoe de zonnecelauto wordt herkend, of vastgelegd is dat de melding volstaat.

### 25. De rentereeks eindigt bij december 2026
- **Status:** open, wacht op het vastgestelde percentage voor 2027
- **Eigenaar:** sessie
- **Vindplaats:** `OPENSTAAND.md`, punt 1 (slot); `WIJZIGINGSRAPPORT.md`, r.854; `belastingrente-ib-reeks.txt`

De reeks van de belastingrente eindigt bewust bij december 2026. Het percentage wordt jaarlijks per 1 januari vastgesteld, dus bij de eerstvolgende jaarwisseling moeten `belastingrente-ib-reeks.txt` in beide repositories (hier en in `Berekeningen`) en beide tools worden verlengd nadat het nieuwe percentage is teruggevonden. Tot dan noemt de tool een uitkomst waarvan het rente-einde na vandaag ligt een raming met het laatst opgenomen percentage, want de ingangsdatum van dat percentage garandeert geen geldigheid voor het hele jaar. Of een geplande taak van de portefeuille dit punt dekt is bij de omzetting niet gemeten.

**Te sluiten wanneer:** het percentage voor 2027 is teruggevonden en het bestand en beide tools zijn verlengd.

### 26. Invorderingsrente: uitzonderingen en verrekening waarvan de tool de omvang niet bepaalt
- **Status:** bewuste beperking, als achtergrond gemarkeerd op 04-10-2026
- **Eigenaar:** sessie
- **Vindplaats:** `WIJZIGINGSRAPPORT.md`, r.948, r.952 en r.984; `README.md`, r.176

1. Art. 28 lid 5: de twee aangewezen gevallen (art. 6bis, het aanhoudaanbod bij een in 2022 gedagtekende voorlopige aanslag IB 2022 met box 3, en art. 6ter, de hersteloperatie toeslagen) staan als aanvinkbare regel op de pagina. Aanvinken blokkeert de uitkomst, omdat de tool niet bepaalt over welke dagen de uitzondering precies loopt. 2. De beleidsregel van art. 28.3a Leidraad Invordering 2008 (rente tot nihil over de periode van uitstel op grond van art. 25.4.6 van de Leidraad) staat als derde regel in die lijst en blokkeert op dezelfde manier. 3. Art. 28 lid 1: geen rente voor zover met de aanslag een aanslag wordt verrekend die op dezelfde belasting en hetzelfde tijdvak ziet. De pagina waarschuwt daarvoor en bepaalt dat deel niet.

**Te sluiten wanneer:** besloten is of de dagen of het verrekende deel erin komen, of vastgelegd is dat de blokkade en de waarschuwing volstaan.

### 27. Eén bronhash komt niet overeen met het manifest
- **Status:** open, raakt de uitkomst niet
- **Eigenaar:** sessie
- **Vindplaats:** `WIJZIGINGSRAPPORT.md`, r.1006

Voor de expressie van het Besluit wettelijke rente (BWBR0002744, versie 2015-01-01_0) die 2 procent vaststelt, kwam de zelf berekende hash niet overeen met de hashcode in het manifest van de KOOP-repository. De meting is herhaald na opnieuw downloaden en gaf dezelfde uitkomst. Het raakt de uitkomst niet: dat percentage telt alleen mee via de bodem van 4 procent in art. 2 lid 2 van het Besluit belasting- en invorderingsrente, en elk percentage onder de 4 geeft na die bodem dezelfde 4. Het is wel het enige losse eind in de bronketen van de invorderingsrente.

**Te sluiten wanneer:** de hash opnieuw is gemeten en overeenkomt, of vastgelegd is waar de afwijking vandaan komt.

### 28. Samenvoegen met de WWFT-app
- **Status:** open, mogelijk achterhaald
- **Eigenaar:** sessie
- **Vindplaats:** `AGENTS.md`, r.89; `claude-pos/scripts/open-punten.py`, `GEEN_REGISTERVRAAG`

`AGENTS.md` noemt als open punt dat samenvoegen met de WWFT multi-page app (`pages/` plus losse modules meeverhuizen) een overweging voor later is en niet moet gebeuren zonder opdracht. Volgens het overzichtsscript van de portefeuille is `wwft-check` vervallen per 01-09-2026 en gearchiveerd. Het punt kan daardoor achterhaald zijn. Dat is bij de omzetting niet gemeten.

**Te sluiten wanneer:** gemeten is of de WWFT multi-page app nog bestaat. Bestaat zij niet meer, dan sluit dit punt met die meting. Bestaat zij wel, dan komt er een besluit van Sylvain.

### 29. Teksten lopen achter op het besluit over het portaal
- **Status:** open, nog niet aangepast
- **Eigenaar:** sessie
- **Vindplaats:** `README.md`, r.9; `WIJZIGINGSRAPPORT.md`, r.15; `UC_belastingtooljoindk.md`, r.35, r.43 en r.44; `update-bram.md`, r.27 (verslag)

Het besluit van 04-10-2026 (punt 10) laat de tegel in het portaal staan en `AGENTS.md` is daarop aangepast. Andere teksten zeggen nog het omgekeerde of lopen achter. `README.md` r.9 en `WIJZIGINGSRAPPORT.md` r.15 zeggen dat de app niet bij bouwman.tools hoort. `UC_belastingtooljoindk.md` noemt zes tools terwijl de app er zeven heeft (r.35) en een statische pagina `betalingskenmerk.html` op bouwman.tools die volgens het document verouderd is en niet meer wordt bijgewerkt (r.43 en r.44). Of die pagina nog bestaat is niet gemeten. `update-bram.md` r.27 draagt dezelfde zin over het portaal, maar is verslag met het label afgerond en blijft zoals het is. Bij de omzetting is alleen OPENSTAAND.md gewijzigd.

**Te sluiten wanneer:** de teksten in lijn zijn met het besluit en gemeten is of `betalingskenmerk.html` nog op bouwman.tools staat.

### 30. Inhoudelijke accordering: stand van `laatst_beoordeeld` niet vastgelegd
- **Status:** open, nog niet gemeten
- **Eigenaar:** sessie
- **Vindplaats:** `vrijgave-belastingtooljoindk-2026-09-07.md`, r.80; `WIJZIGINGSRAPPORT.md`, r.856; `bouwman-tools/tools.json`, `laatst_beoordeeld` van `belastingtool-joindk`

De vrijgavenotitie van 07-09-2026 zegt dat `status` op `beta` blijft en `laatst_beoordeeld` op `null`: die merge publiceert en accordeert niet. Paragraaf L09 van het wijzigingsrapport zegt dat technische review en publicatie afzonderlijk blijven en dat er geen nieuwe fiscale accordering of modelvergelijking was. Sindsdien zijn de gelijkwaardigheidstoets (29-09-2026) en de uitbreiding van 04-10-2026 opgeleverd, maar nergens in deze repository staat of de tool is geaccordeerd. Het register ligt buiten deze repository en is bij de omzetting niet gelezen.

**Te sluiten wanneer:** gemeten is wat `laatst_beoordeeld` voor deze tool in `bouwman-tools/tools.json` zegt. Staat die leeg, dan komt er een punt voor Sylvain over de accordering.

## Gesloten

### 18. Moet er worden herberekend wat met de versie van 15-07-2026 voor klanten is gerekend?
- **Status:** gesloten 04-10-2026 (besluit van 18-08-2026 in de README)
- **Eigenaar:** Sylvain
- **Vindplaats:** `WIJZIGINGSRAPPORT.md`, r.109; `README.md`, r.315

Actiepunt 4 van het wijzigingsrapport (r.109) vroeg na te gaan of er met de oude versie die in DK/Join draait (commit `821b575` van 15-07-2026) voor klanten is gerekend. Die versie rekent aantoonbaar onjuist (paragraaf 1a van het wijzigingsrapport). Het punt stond alleen daar en niet in dit bestand.

Gesloten 04-10-2026. Bewijs: de README legt op r.315 het besluit van 18-08-2026 vast dat herziening van eerdere berekeningen niet nodig is, omdat de tool in de testfase zit. Dat besluit staat daar met datum.

### 13. Fouten in model 02-04, terug te melden aan Wolters Kluwer
- **Status:** gesloten 04-10-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `vrijgave-belastingtooljoindk-2026-09-29.md`, `WIJZIGINGSRAPPORT.md` L11, `terugmelding-wolters-kluwer-model-02-04.md`; lokaal (genegeerd) `.local-testdata/gelijkwaardigheid-02-04/run4-na-broncontrole/vergelijking-02-04.xlsx`

**Gesloten op 04-10-2026.** Sylvain Bouwman heeft het bericht met de drie bevindingen op 04-10-2026 per e-mail aan Wolters Kluwer verstuurd. De tekst is die van `terugmelding-wolters-kluwer-model-02-04.md`. Een antwoord van Wolters Kluwer wordt niet afgewacht; komt er een reactie, dan start die als eigen sessie.

**Status tot 04-10-2026:** open. **Eigenaar:** Sylvain Bouwman. **Gevonden op** 29-09-2026, bij de
gelijkwaardigheidstoets. **Vindplaats:** `vrijgave-belastingtooljoindk-2026-09-29.md`,
`WIJZIGINGSRAPPORT.md` L11, en lokaal (genegeerd) het overzicht
`.local-testdata/gelijkwaardigheid-02-04/run4-na-broncontrole/vergelijking-02-04.xlsx` met
de scripts in `scripts/` ernaast.

Model 02-04, versie v20260117, machinaal doorgerekend met synthetische gevallen. Drie fouten
ten opzichte van de bron, in eigen woorden (het model zelf, zijn formules en teksten komen
niet in Git):

1. **Invorderingsrente, vervalmaand van 31 dagen.** Art. 31 onderdeel a URIW 1990 telt de
   vervalmaand op haar werkelijke aantal dagen. Het model telt een vervalmaand van 31 dagen
   als 30, behalve wanneer de rente precies op de 31e begint. Richting: het model rekent
   één dag te weinig, dus te laag. Speelde in 57 van de 138 gevallen.
2. **Belastingrente, tijdvak dat op de 31e eindigt.** Art. 31 lid 1 Uitvoeringsregeling AWR
   1994 telt de maand op de laatste dag waarvan het tijdvak eindigt op het werkelijke aantal
   dagen. Het model telt ook die maand als 30, terwijl zijn eigen uitleg de regel wel
   noemt. Richting: één dag te weinig. Speelde in 30 van de 202 gevallen.
3. **Belastingrente over één dag.** Valt de einddatum op de begindatum, dan geeft het model
   nul en een foutmelding. Art. 30fc lid 2 AWR kent geen
   minimumduur. Richting: te laag. Drie gevallen.

Wat het model goed doet, en dat hoort bij de terugmelding: beveiligde bladen met
herkenbare invoercellen, een tariefreeks die voor IB en VpB (met het HR-arrest aan)
identiek is aan de bron, de juiste begindatum bij gebroken boekjaren, de juiste eerste
dag van de invorderingsrente en een consequente afronding naar beneden.

**Wat er moet gebeuren:** beslissen of en hoe dit aan Wolters Kluwer wordt teruggemeld.
Niet zelf gedaan: dat is een bericht naar buiten.

### 2. Hoe telt een gedeeltelijke maand die niet de vervalmaand is?
- **Status:** gesloten 04-10-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `_invorderingsrente.py`; `WIJZIGINGSRAPPORT.md` L10.7 punt 2

**Gesloten op 04-10-2026, besluit van Sylvain Bouwman.** De bron-controleur zocht in de
wettekst, de Leidraad Invordering 2008 (art. 28 en 28a/28b), belastingdienst.nl en
rechtspraak naar een regel voor de laatste onvolledige maand en vond niets. De
rekenvoorbeelden van de Belastingdienst gebruiken alleen volle maanden. **Besluit:** de
tool telt die maand naar rato binnen 30 dagen, afgeleid uit art. 31 onderdeel b URIW, en
dat blijft zo.

**Wat onzeker blijft:** belastingdienst.nl zegt "voor een volle maand tellen wij 30 dagen
(voor februari 28 dagen)", ruimer dan art. 31, waar alleen de vervalmaand februari op 28
telt. De tool volgt de wettekst. Heroverwegen zodra beleid of een uitspraak over de
onvolledige maand verschijnt.

**Status tot 04-10-2026:** open. **Eigenaar:** Sylvain Bouwman. **Vindplaats:** `_invorderingsrente.py`,
`WIJZIGINGSRAPPORT.md` L10.7 punt 2.

Art. 31 URIW noemt de vervalmaand en de volle maand, maar niet met zoveel woorden de
laatste, onvolledige maand van een tijdvak. De module telt die naar rato binnen een
maandlengte van 30, dezelfde systematiek die `dagen_30_360()` gebruikt. Dat volgt uit
onderdeel b maar staat er niet letterlijk.

### 3. Welke formule geldt voor een vergoeding?
- **Status:** gesloten 04-10-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `_invorderingsrente.py`; `WIJZIGINGSRAPPORT.md` L10.7 punt 3

**Gesloten op 04-10-2026, besluit van Sylvain Bouwman.** De grondslag (het uit te betalen
respectievelijk terug te geven bedrag) is bevestigd door art. 28b lid 2, slot, en door
KG:207:2022:2, antwoord 3 (Kennisgroep Belastingdienst, 28-03-2023). Voor de formule bij
een vergoeding is niets gevonden: de Leidraad zegt dat er op art. 28a en 28b geen
beleidsregels zijn gemaakt, en art. 30 lid 1 URIW spreekt van de in rekening te brengen
rente. Art. 32 lid 2 URIW (afronding van de "te vergoeden invorderingsrente") wijst er
indirect op dat het hoofdstuk ook voor een vergoeding geldt. **Besluit:** dezelfde
enkelvoudige formule blijft gelden. Heroverwegen bij beleid of een uitspraak.

**Status tot 04-10-2026:** open. **Eigenaar:** Sylvain Bouwman. **Vindplaats:** `_invorderingsrente.py`,
`WIJZIGINGSRAPPORT.md` L10.7 punt 3.

Art. 30 URIW is naar zijn tekst geschreven voor de in rekening te brengen rente over een
betaling. Voor art. 28a en 28b kent de regeling geen eigen formule. De module gebruikt
dezelfde enkelvoudige formule met het uit te betalen respectievelijk het terug te geven
bedrag als grondslag; de wet noemt die grondslag zelf in art. 28b lid 2, slot.

### 4. Uitstel wordt niet doorgerekend
- **Status:** gesloten 04-10-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `_invorderingsrente.uitstel_uitsluiting`, `herlevingsdatum`; `WIJZIGINGSRAPPORT.md` L10.7 punt 5

**Gesloten op 04-10-2026: gebouwd, op besluit van Sylvain Bouwman ("alsnog bouwen").** De
pagina rekent nu de opschorting van art. 28 lid 3 en de herleving van lid 4 met art. 6
Uitvoeringsbesluit IW 1990 (`_invorderingsrente.uitstel_uitsluiting` en
`herlevingsdatum`). De gebruiker vult de grond, de begindatum en eventueel de einddatum
van het uitstel in, en bij een beëindiging de datum van de gebeurtenis. De
bron-controleur toetste de regels op 04-10-2026 aan de wettekst: art. 28, art. 25 en
art. 6 Uitvoeringsbesluit kloppen. Twee doorgerekende gevallen staan in de tests.

**Wat de tool bewust niet rekent, en daarvoor een melding geeft in plaats van een
bedrag:**

- Betaling na afloop van de uitsteltermijn bij de gronden van art. 28 lid 4. De wet laat
  het tijdvak aan een algemene maatregel van bestuur en art. 6 Uitvoeringsbesluit regelt
  alleen de beëindiging. De Leidraad kent beleid voor lid 9, 11 en 17 tot en met 19
  (onderdeel 74.5, 74.5a, 74.10 en 74.11), maar of dat ook het gewoon aflopen van de
  termijn dekt is uitleg. Voor lid 5, 8 en 21 is niets gevonden.
- Een beëindigd uitstel op grond van art. 25 lid 3: lid 4 noemt die grond niet.

**Aanname die blijft:** bij uitstel op grond van art. 25 lid 5 of 8 neemt de tool "de dag
waarop zes weken zijn verstreken na de eerste dag van het jaar" als die dag zelf (1 januari
plus 42 dagen, dus 12 februari) en niet een dag later. Art. 6 lid 1 zegt "met ingang van de
dag waarop", lid 2 zegt "de dag volgende op". Geen gelezen bron beslist het; het verschil is
één dag rente. De nota van toelichting bij de oorspronkelijke tekst (Stb. 1991, 718) is
alleen als scan beschikbaar en niet gelezen.

**Status tot 04-10-2026:** open, als bekende beperking. **Eigenaar:** Sylvain Bouwman.
**Vindplaats:** `WIJZIGINGSRAPPORT.md` L10.7 punt 5.

Dat is een keuze van Sylvain en geen tekort van het onderzoek, maar het blijft een grens:
voor een aanslag waarvoor uitstel is verleend geeft de tool geen bedrag. Staat hier zodat
zichtbaar blijft wat de tool niet doet.

### 5. Art. 28c wordt niet gerekend
- **Status:** gesloten 04-10-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `_invorderingsrente.periode_art28c`; `WIJZIGINGSRAPPORT.md` L10.7 punt 6

**Gesloten op 04-10-2026: gebouwd, op besluit van Sylvain Bouwman.** Art. 28c staat nu in de
keuzelijst (`_invorderingsrente.periode_art28c`). Het tijdvak loopt van de dag na de betaling
tot de dag vóór de terugbetaling, met het terug te geven bedrag als grondslag en de te
vergoeden tariefreeks, zonder vervalmaand (30 dagen per maand). De gebruiker geeft aan of het
verzoek tijdig is ingediend (uiterlijk zes weken na de beschikking) en kan de dagen opgeven
waarover belastingrente of invorderingsrente op grond van art. 28b wordt vergoed; die tellen
niet mee. Bron-controleur 04-10-2026: tijdvak, grondslag, uitsluiting en verzoektermijn
kloppen. Wat de tool niet toetst: of de heffing werkelijk in strijd met het Unierecht is en of
er een beschikking ligt; dat vult de gebruiker in.

**Status tot 04-10-2026:** open, als bekende beperking. **Eigenaar:** Sylvain Bouwman.
**Vindplaats:** `WIJZIGINGSRAPPORT.md` L10.7 punt 6.

Ook een keuze van Sylvain. De pagina signaleert wel de grond en de verzoektermijn van zes
weken, maar rekent het bedrag niet uit.

### 6. De vier tijdvakken zijn niet aan uitvoeringsbeleid of rechtspraak getoetst
- **Status:** gesloten 04-10-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `_invorderingsrente.periode_art28b`; `WIJZIGINGSRAPPORT.md` L10.7 punt 7

**Gesloten op 04-10-2026.** Beoordeeld als de vier tijdvakken van art. 28, 28a, 28b en 28c.
De bron-controleur toetste ze aan de wet, de Leidraad, KG:207:2022:2 (Kennisgroep
Belastingdienst, 28-03-2023), belastingdienst.nl (Invorderingsrente) en rechtspraak (HR
2024:756, HR 2024:853, RBNHO 2020:7456 en RBNNE 2020:1995). Bevestigd: het tijdvak van art.
28 en 28a, het einde van 28b, art. 28c en alle percentages. Afwijkend: de eerste dag van art.
28b lag een dag later dan de uitvoering. **Besluit van Sylvain op 04-10-2026: de uitvoering
volgen.** Het tijdvak begint nu de dag na de vervaldag (`periode_art28b`); een vergoeding
wordt daardoor een dag hoger. Dit vervangt wat bij punt 12 over art. 28b stond. Geen
uitspraak gevonden over de dagentelling of de formule. De database van rechtspraak.nl is niet
rechtstreeks doorzocht, alleen via een zoekmachine.

**Status tot 04-10-2026:** open. **Eigenaar:** Sylvain Bouwman. **Vindplaats:**
`WIJZIGINGSRAPPORT.md` L10.7 punt 7.

Zij zijn uit de wettekst overgenomen, net als in de onderzoeksnotitie. De Leidraad
Invordering 2008 is wel nagelezen op afwijkingen en gaf er op dit punt geen. Wat ontbreekt
is een toets aan rechtspraak en aan gepubliceerd uitvoeringsbeleid daarbuiten.

### 10. Hoort deze tool in het portaal van bouwman.tools, of niet?
- **Status:** gesloten 04-10-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `AGENTS.md`; `bouwman-tools/tools.json`, `in_portal`

**Gesloten op 04-10-2026, besluit van Sylvain Bouwman: de tegel blijft in het portaal.** Het
register (`in_portal: true`, met een link naar de Streamlit-app) klopt dus. De zin in
`AGENTS.md` is aangepast: de tool staat als tegel in het portaal maar valt niet onder
Cloudflare Access en heet nooit "Bouwman Tools". Voor de gebruiker verandert niets.

**Status tot 04-10-2026:** open. **Eigenaar:** Sylvain Bouwman. **Gevonden op** 20-09-2026.

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

### 11. Krijgt deze tool (of zijn zes onderdelen) een dossierstuk, Excel-export of dossierbestand?
- **Status:** gesloten 04-10-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `bouwman-tools/tools.json`, uitgangen van `belastingtool-joindk`

**Gesloten op 04-10-2026, besluit van Sylvain Bouwman.** Punt 10 is beslist: de tool blijft
in het portaal. De Streamlit-app krijgt in deze testomgeving geen dossierstuk, Excel-export
of dossierbestand. Dat hoort bij de overdracht aan de platformbouw, waar de productieversie
in een beveiligde omgeving komt. De drie uitgangen blijven in `tools.json` op `false`.
Komt de vraag uit de collega-test, dan start die als eigen sessie.

**Status tot 04-10-2026:** open, bewust niet nu opgepakt. **Eigenaar:** Sylvain Bouwman. **Gevonden op**
27-09-2026, bij de portefeuillebrede inventarisatie van de uitgangen.

`tools.json` in `bouwman-tools` heeft voor `belastingtool-joindk` alle drie de
uitgangen op `false` staan. Besloten op 27-09-2026: nu geen bouwsessie hiervoor. Twee
redenen. Ten eerste raakt dit een Streamlit-app en niet de single-file HTML-opzet
waarvoor de skill `tool-uitgangen` is geschreven; de standaardaanpak (een `@media
print`-blok, een bevroren werkblad, een JSON-dossierbestand) veronderstelt een
losstaand HTML-bestand en moet voor Streamlit eerst worden vertaald. Ten tweede is er
overlap met `Berekeningen` (zie punt 1 hierboven, en de open vraag in punt 10 of deze
tool zelfs in het portaal hoort): eerst bouwen op een plek die mogelijk verdwijnt of
van eigenaar wisselt, is voorbarig werk.

**Wat er moet gebeuren, ná punt 10:** zodra vaststaat of deze tool blijft en waar de
belastingrente/revisierente-onderdelen definitief wonen, opnieuw beoordelen of een
uitgang per onderdeel zinvol is, en zo ja, hoe dat in Streamlit vorm krijgt.

### 15. Twee rekenvoorbeelden van de Belastingdienst spreken elkaar tegen
- **Status:** gesloten 04-10-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** belastingdienst.nl, "Belastingrente betalen bij inkomstenbelasting", geraadpleegd 29-09-2026

**Gesloten op 04-10-2026, besluit van Sylvain Bouwman.** Er verandert niets in de tool: die
volgt de wet (art. 30fc lid 2 AWR met art. 9 IW 1990 en onderdeel 9.5 Leidraad) en het
eerste voorbeeld. Het tweede voorbeeld op belastingdienst.nl rekent een dag verder, en dat
blijft een afwijking van de Belastingdienst zelf. Heroverwegen als de Belastingdienst het
voorbeeld aanpast of uitlegt.

**Status tot 04-10-2026:** open. **Eigenaar:** Sylvain Bouwman. **Gevonden op** 29-09-2026.
**Vindplaats:** belastingdienst.nl, "Belastingrente betalen bij inkomstenbelasting",
geraadpleegd 29-09-2026.

Bij een aanslag van 11 december 2024 loopt de belastingrente tot en met 22 januari 2025,
dagtekening plus 42 dagen; zo rekenen de wet (art. 30fc lid 2 AWR met art. 9 IW 1990 en
onderdeel 9.5 Leidraad) en de tool. Bij een aanslag van 27 juni 2024 loopt zij volgens de
pagina tot en met 9 augustus 2024, dagtekening plus 43 dagen; de tool komt op 8 augustus en
7 euro in plaats van 8. De tool volgt de wet en het eerste voorbeeld.

**Wat er moet gebeuren:** niets in de tool. Heroverwegen als de Belastingdienst het voorbeeld
aanpast of uitlegt; eventueel melden bij de Belastingdienst.

### 16. Een naam uit model 02-04 stond in punt 1 van dit bestand
- **Status:** gesloten 29-09-2026
- **Eigenaar:** sessie
- **Vindplaats:** `OPENSTAAND.md`, punt 1; zoektocht over de hele repository op 29-09-2026

**Status:** gesloten op 29-09-2026, op verzoek van Sylvain Bouwman. **Gevonden** diezelfde dag
door de publicatiepoort.

Punt 1 noemde sinds 20-09-2026 letterlijk de naam van de schakelaar voor het HR-arrest uit het
model. De afspraak is dat teksten, formules en celadressen van het model niet in Git komen, en
deze repository is publiek. De naam is vervangen door een omschrijving; een zoektocht over de
hele repository vond geen andere vermelding.

**Wat blijft:** de naam staat nog in de Git-historie, in de commit die OPENSTAAND.md op
20-09-2026 aanmaakte. Die historie herschrijven vraagt een force-push op de publieke
hoofdbranch. **Besluit van Sylvain op 29-09-2026: de historie blijft zoals zij is.** Het gaat
om één woord en geen rekenmateriaal, en een herschreven publieke historie wist het niet
gegarandeerd uit kopieën en caches.

### 14. Vanaf welk boekjaar geldt belastingrente in plaats van heffingsrente?
- **Status:** gesloten 29-09-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `pages/Belastingrente_VpB.py`

**Status:** gesloten op 29-09-2026. **Eigenaar:** Sylvain Bouwman. **Vindplaats:**
`pages/Belastingrente_VpB.py`.

Het model laat de rente voor boekjaren tot en met 2011 bij het einde van het boekjaar
beginnen (heffingsrente) en vanaf 2012 zes maanden later. De tool rekende een ouder boekjaar
stil met het nieuwe stelsel door. De eerste herstelversie weigerde een boekjaar dat vóór
2012 eindigde; de bron-controleur wees erop dat dat de verkeerde grens is.

**De bron:** art. XXXIV lid 1 onderdeel b Belastingplan 2012 (Stb. 2011, 639; BWBR0030999,
geraadpleegd 29-09-2026) laat hoofdstuk VA AWR zoals het luidde op 31 december 2012 van
toepassing op "belastingaanslagen vennootschapsbelasting die betrekking hebben op
tijdvakken die zijn aangevangen vóór 1 januari 2012". Voor de IB (onderdeel a) telt een
tijdvak dat vóór 1 januari 2012 is geëindigd; de IB-pagina biedt die jaren niet aan.

**Wat er is gedaan:** bij een boekjaar dat vóór 2014 eindigt vraagt de VpB-pagina ook de
begindatum, en een boekjaar dat vóór 1 januari 2012 is begonnen geeft een melding in plaats
van een bedrag. Getest met een gebroken boekjaar 01-07-2011 t/m 30-06-2012.

**Aanname die blijft:** de begindatum wordt alleen gevraagd als het boekjaar vóór 2014
eindigt, dus de tool gaat ervan uit dat een boekjaar niet langer dan 24 maanden duurt. Art. 7
lid 4 Wet Vpb 1969 noemt geen maximum. Een verlengd eerste boekjaar dat vóór 2012 begon en na
2013 eindigde, rekent de tool dus met belastingrente. Zeldzaam en vijftien jaar oud; bewust
niet verder uitgebouwd. Opgemerkt door de bron-controleur bij de herkeuring.

### 12. Vier rekenkeuzes uit de gelijkwaardigheidstoets tegen model 02-04
- **Status:** gesloten 29-09-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `_rente.py`; `_invorderingsrente.py`; `vrijgave-belastingtooljoindk-2026-09-29.md`

**Status:** gesloten op 29-09-2026, besluit van Sylvain Bouwman. **Vindplaats:**
`_rente.py`, `_invorderingsrente.py`, `vrijgave-belastingtooljoindk-2026-09-29.md`.

Bij de toets bleken vier punten waar model, tool en Belastingdienst uiteenliepen en de bron
een keuze liet. Voorgelegd met advies; alle vier volgens advies beslist.

1. **Eerste dag van de invorderingsrente: de dag na de uiterste betaaldatum.** De tool
   begon op de uiterste betaaldatum zelf en rekende daardoor een dag meer dan het model en
   de Belastingdienst ("vanaf de dag na de uiterste betaaldatum"), en telde die dag ook in
   de belastingrente mee. Hersteld. Gevolg voor art. 28b: dat tijdvak begint "de dag na" de
   invorderbaarheid en schuift dus ook een dag op. **Bijgewerkt op 04-10-2026:** art. 28b
   begint toch de dag na de vervaldag, zoals de Belastingdienst het uitvoert; zie punt 6.
2. **Afronding van de belastingrente blijft per tariefperiode**, zoals het rekenvoorbeeld
   van de Belastingdienst (93 + 9 = 102). Het model en de letterlijke tekst van art. 31
   lid 2 Uitvoeringsregeling AWR ronden één keer af (103). Verklaard verschil; de tool komt
   hooguit 1 euro per extra tariefperiode lager uit.
3. **Tijdvak dat op de 31e eindigt telt die maand als 31**, volgens art. 31 lid 1
   Uitvoeringsregeling AWR. Hersteld; model en tool telden 30.
4. **Schrikkeldag in de vervalmaand telt als één dag** als de invorderingsrente op 29
   februari begint. "Februari altijd op 28 dagen" begrenst de volle maand. Zo gebleven; het
   model slaat 29 februari over. De bron-controleur noemt dit onzeker: art. 31 onderdeel a
   URIW legt de lengte van de maand vast, niet hoe een dag na de 28e meetelt, en een telling
   van nul is ook te lezen. Het besluit blijft staan; heroverwegen als er beleid of
   rechtspraak over verschijnt.

**Wat verder openstaat:** het tegenstrijdige rekenvoorbeeld van de Belastingdienst staat
als punt 15.

### 7. Geldt art. 31 onderdeel a ook bij art. 28a?
- **Status:** gesloten 20-09-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `WIJZIGINGSRAPPORT.md` L10.7 punt 1

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
- **Status:** gesloten 20-09-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `WIJZIGINGSRAPPORT.md` L10.7 punt 4

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
- **Status:** gesloten 20-09-2026
- **Eigenaar:** sessie
- **Vindplaats:** `WIJZIGINGSRAPPORT.md`, Auto BTW privé

**Status:** gesloten op 20-09-2026, opgeruimd.

`WIJZIGINGSRAPPORT.md` verwees bij de Auto BTW privé-pagina naar "openstaand punt A
hieronder". Dat punt is nooit uitgewerkt: in de allereerste versie van het rapport
(commit `869ceff`) stond de verwijzing er al zonder doel. Er is dus niets verdwenen bij een
opruiming, maar de tekst beloofde wel een punt dat er niet was. De verwijzing is vervangen
door wat er feitelijk over de nulemissietabel te zeggen valt.

### 1. Waar hoort de belastingrente te worden gerekend: `belastingtooljoindk` of `Berekeningen`
- **Status:** gesloten 20-09-2026
- **Eigenaar:** Sylvain
- **Vindplaats:** `PostbusClaude/archief/2026-09/VRAGEN-07-09-2026.md`; `WIJZIGINGSRAPPORT.md` paragraaf 9.7; `Berekeningen/OPENSTAAND.md`

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
een schakelaar (het bronmodel 02-04 kent er een voor het HR-arrest) is gebouwd; de tool toont één
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
