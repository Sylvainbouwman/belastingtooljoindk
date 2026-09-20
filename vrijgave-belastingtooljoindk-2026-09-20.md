# Vrijgavenotitie Belastingtool JoinDK, 20 september 2026

Status: afgerond. De punten uit deze notitie staan met hun stand in `OPENSTAAND.md`.

## Waarover gaat het

Tool: Belastingtool JoinDK. Draait op
[belastingtooljoindk.streamlit.app](https://belastingtooljoindk.streamlit.app), een
testomgeving voor collega's; productie komt in een beveiligde omgeving en is een eigen
overdracht. Datum: 20 september 2026. Eigenaar: Sylvain Bouwman.

Dit is een beoordelingsronde. Eén bevinding leidt tot een gewijzigd bedrag, de rest is
vastlegging: punten die op de verkeerde plek stonden zijn overgezet en twee daarvan zijn
beslist.

## 1. De nulemissiekorting voor 2027 ontbrak, en dat scheelde € 600 per jaar

De tabel `KORTING_NULEMISSIE` in `_auto_calc.py` liep tot en met 2026. Voor een later
regimejaar rekende de tool met het standaardpercentage van 22 procent en waarschuwde zij
daarbij, netjes en zichtbaar. Maar het cijfer voor 2027 was allang bekend.

**Teruggelezen op 20 september 2026** in art. 3.20 lid 2 Wet IB 2001, geldende tekst met
toestand 1 januari 2027: de onttrekking wordt *"op jaarbasis verlaagd met 2% van de waarde
van de auto indien uit het kentekenregister blijkt dat de CO2-uitstoot 0 gram per kilometer
is, met dien verstande dat het bedrag van de verlaging ten hoogste € 600 bedraagt"*. Dat is
22 − 2 = 20 procent over de eerste € 30.000, want € 600 gedeeld door 2 procent is € 30.000.

Voor een nieuwe elektrische auto met een catalogusprijs vanaf € 30.000 rekende de tool dus
€ 600 bijtelling per jaar te hoog. Door de 60-maandenregel raakt dat alleen auto's die in
2027 voor het eerst worden toegelaten, maar die komen er wel.

**Dezelfde reeks stond al met 2027 in de zustertool `auto-fiscaal-2027`**, in een andere
vorm: daar als verlaging in procentpunten met een maximumbedrag, hier als resulterend
percentage met een plafond van de catalogusprijs. Beide vormen zeggen hetzelfde en zijn
naast elkaar gelegd; zij komen voor alle jaarschijven overeen. Dat de twee uiteen konden
lopen zonder dat iemand het merkte is dezelfde constatering als bij de belastingrentereeks
diezelfde ochtend. Voor die reeks is een bewaking gebouwd; hier is bewust alleen aangevuld.

**Wat de waarschuwing nu doet:** zij schuift op naar 2028. De korting vervalt dan volgens
de geldende tekst, maar die vervaldatum is al een keer met latere wetgeving opgeschoven,
dus de melding blijft staan tot iemand haar opnieuw bij de bron heeft gezien.

## 2. Zeven fiscale punten stonden op de verkeerde plek

Zij stonden alleen in `WIJZIGINGSRAPPORT.md`, paragraaf L10.7, en raken alle de pagina
Invorderingsrente. `OPENSTAAND.md` meldde tegelijk "nul open". Dat is precies hoe punten
blijven liggen: de index over alle repository's heen herkent actiedocumenten op
bestandsnaam en keek dus naar het verkeerde bestand.

Alle zeven staan nu in `OPENSTAAND.md`, met status, eigenaar en vindplaats. Het
wijzigingsrapport houdt zijn tekst als vindplaats van de oorspronkelijke formulering en
verwijst hierheen. `AGENTS.md` zei tot vandaag het omgekeerde en is gecorrigeerd.

Twee van de zeven zijn diezelfde dag beslist.

**Geldt art. 31 onderdeel a ook bij art. 28a?** Nee, besloot Sylvain. Onderdeel a knoopt aan
bij "de maand waarin de enige of laatste betalingstermijn van de aanslag vervalt". Bij art.
28a vangt het tijdvak aan na de dagtekening van een uitbetaling en is er geen aanslag en
geen vervallende termijn; dat aanknopingspunt ontbreekt dus en onderdeel b geldt voor alle
maanden. Over 26-02-2026 tot en met 09-04-2026 geeft dat 44 dagen in plaats van 42. Wat
onzeker blijft: de wet zegt niet met zoveel woorden dat onderdeel a hier buiten toepassing
blijft, en er is geen rechtspraak of gepubliceerd beleid over gevonden. De melding bij de
uitkomst blijft daarom staan.

**Deelbetalingen.** De pagina rekent één betaling per keer door; `splits_betaling()` staat
wel in de module en is getest maar wordt niet aangeboden. Besluit: dat blijft zo, en de
functie blijft staan. Meerdere betalingen in één scherm maakt de invoer fors ingewikkelder
voor een geval dat zich weinig voordoet. Komt die vraag uit het testen, dan is dit het punt
om te heropenen.

## 3. Een verwijzing die nergens heen wees

`WIJZIGINGSRAPPORT.md` verwees bij de Auto BTW privé-pagina naar "openstaand punt A
hieronder". Dat punt is nooit uitgewerkt: in de allereerste versie van het rapport
(`869ceff`) stond de verwijzing er al zonder doel. Er is dus niets verdwenen bij een
opruiming, maar de tekst beloofde wel iets wat er niet was. Vervangen door wat er feitelijk
over de nulemissietabel te zeggen valt.

## Geraakte fiscale waarden

| Waarde | Was | Wordt | Vindplaats |
|---|---|---|---|
| Nulemissiekorting regimejaar 2027 | ontbrak, viel terug op 22% | 20% tot € 30.000 | art. 3.20 lid 2 Wet IB 2001, toestand 2027-01-01 |
| Laatste geverifieerde jaar | 2026 | 2027 | idem |

Geen andere waarde is gewijzigd.

## Wat is er getest

```
python -m pytest -q        473 tests groen (was 470)
```

Drie bestaande tests bewaken de reeks jaar voor jaar en wezen bij het invoeren precies aan
wat er mee moest; zij zijn bijgewerkt met de bron van 2027 erbij. Drie nieuwe tests toetsen
dat regimejaar 2027 de korting krijgt en geen waarschuwing meer, dat het voordeel op een
dure auto begrensd is op de € 600 uit de wet, en dat een waterstofauto het plafond ook in
2027 ontloopt.

## Wat er niet in zit

Vijf van de zeven fiscale punten bij de invorderingsrente blijven open en staan in
`OPENSTAAND.md`: de telling van een gedeeltelijke maand die niet de vervalmaand is, de
formule bij een vergoeding, dat uitstel niet wordt doorgerekend, dat art. 28c niet wordt
gerekend, en dat de vier tijdvakken niet aan uitvoeringsbeleid of rechtspraak zijn getoetst.
De laatste twee zijn keuzes van Sylvain en staan er als bekende grens.

De nulemissiereeks staat nog steeds op twee plekken, hier en in `auto-fiscaal-2027`, zonder
bewaking die meet of zij gelijk blijven. Dat is een bewuste keuze van vandaag; bij de
eerstvolgende jaarwisseling hoort iemand ze naast elkaar te leggen.
