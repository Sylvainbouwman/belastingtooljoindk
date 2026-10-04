# Concept: terugmelding aan Wolters Kluwer, model 02-04

Concept van 04-10-2026, bedoeld om door Sylvain Bouwman zelf te worden verstuurd. Het
bevat alleen gedrag en wetsartikelen in eigen woorden, geen formules, celadressen of
teksten uit het model en geen klantgegevens. Voor de achtergrond zie `OPENSTAAND.md`
punt 13 en `WIJZIGINGSRAPPORT.md` L11.

Hieronder de tekst om te kopiëren.

```
Onderwerp: Drie bevindingen bij het rekenmodel belastingrente en invorderingsrente (model 02-04, versie v20260117)

Beste mensen van de helpdesk,

Wij gebruiken het rekenmodel belastingrente en invorderingsrente (model 02-04, versie v20260117) en hebben het machinaal doorgerekend met synthetische gevallen, naast een eigen berekening. Daarbij vonden wij drie punten waarop de uitkomst afwijkt van de wet. Wij melden ze graag zodat u ze kunt beoordelen.

1. Invorderingsrente, vervalmaand van 31 dagen. Artikel 31 onderdeel a van de Uitvoeringsregeling Invorderingswet 1990 laat de maand waarin de enige of laatste betalingstermijn vervalt meetellen met haar werkelijke aantal dagen. Telt de rente een maand van 31 dagen, dan telt het model die maand als 30 dagen, behalve wanneer de rente precies op de 31e begint. De uitkomst is daardoor één dag rente te laag. Het speelde in 57 van de 138 gevallen die wij doorrekenden.

2. Belastingrente, tijdvak dat op de 31e van een maand eindigt. Artikel 31 lid 1 van de Uitvoeringsregeling AWR 1994 telt de maand van de laatste dag waarop het tijdvak eindigt met het werkelijke aantal dagen. Het model telt ook die maand als 30 dagen, terwijl de uitleg in het model de regel wel noemt. De uitkomst is één dag rente te laag. Het speelde in 30 van de 202 gevallen.

3. Belastingrente over één dag. Valt de einddatum op de begindatum, dan geeft het model nul en de melding dat de einddatum groter moet zijn. Artikel 30fc lid 2 AWR kent geen minimumduur, dus een tijdvak van één dag geeft rente. De uitkomst is te laag. Dit speelde in drie gevallen.

Wat het model goed doet: beveiligde bladen met herkenbare invoercellen, een tariefreeks die voor IB en VpB (met het arrest van de Hoge Raad aan) gelijk is aan de bron, de juiste begindatum bij gebroken boekjaren, de juiste eerste dag van de invorderingsrente en een consequente afronding naar beneden.

Wij sturen op verzoek graag de synthetische gevallen waarmee wij de afwijkingen vonden.

Met vriendelijke groet,
Sylvain Bouwman
Join Administraties
```
