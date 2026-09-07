# Vrijgavenotitie belastingtooljoindk — 7 september 2026

Eerste vrijgavenotitie van deze repository; eerdere wijzigingen zijn vastgelegd in
`WIJZIGINGSRAPPORT.md`. De uitgebreide onderbouwing van deze vrijgave staat daar in
paragraaf 9. Deze notitie is de korte versie plus de verantwoording van de poort.

**Betreft:** de ingangsdatum van de coronaverlaging van de belastingrente voor de
inkomstenbelasting, en de controle die de fout niet kon zien.
**Opdracht:** `PostbusClaude/belastingtool-joindk/OPDRACHT-07-09-2026.md`.

## De fiscale wijziging: één waarde

| | |
|---|---|
| Geraakte waarde | ingangsdatum van het percentage 0,01 in de IB-tarieventabel |
| Was | `(date(2020, 6, 1), 0.01)` in `pages/Belastingrente_IB.py` |
| Wordt | `(date(2020, 7, 1), 0.01)` |
| Vindplaats | Verzamelspoedwet COVID-19, Stb. 2020, 200 — <https://zoek.officielebekendmakingen.nl/stb-2020-200.html> |
| Bevestiging | voetnoot \*\*\* onder de tabel "Percentages alle belastingen" op belastingdienst.nl: "Voor de inkomstenbelasting ging de tijdelijke verlaging in vanaf 1-7-2020" |

Juni 2020 valt voor de inkomstenbelasting nog onder 4,00%. De VpB-tabel houdt op dezelfde
plek wél 1 juni 2020 aan en dat is daar juist; dat verschil tussen de twee tabellen is
bedoeld en mag niet worden gelijkgetrokken. Aan de VpB-reeks is niets gewijzigd.

**Wie het merkt.** De renteperiode voor een IB-aanslag begint op 1 juli van het jaar na het
belastingjaar. Voor belastingjaar 2019 en later valt juni 2020 buiten het tijdvak en
verandert er niets. Voor belastingjaar 2018 en eerder rekende de tool te weinig rente.
Nagemeten met `_rente.bereken` op belastingjaar 2018, dagtekening 1 december 2020 en
€ 10.000: € 513 waar de tool € 479 gaf, dus € 34 te laag. Het verschil valt naar één kant.

## De eigenlijke bevinding: de controle was verkeerd gedefinieerd

De automatische controle bij elke paginaweergave parseert de *tabel* onder de kop
"Percentages alle belastingen". De IB-uitzondering staat op de bron in een voetnoot *ónder*
die tabel. De controle kon de afwijking dus structureel niet zien en keurde haar bij elke
paginaweergave opnieuw goed, onder het kopje "1-op-1 nagelopen tegen de bron".

Van de twee uitwegen die de opdracht noemt, is de tweede gekozen: **een controle die zegt
welk deel zij niet kan toetsen**, en niet een tweede parser voor voetnoottekst. Grond: het
gaat om één afgesloten historische uitzondering uit 2020 die niet meer verandert, en een
voetnootparser zou daar een nieuwe stille faalmodus voor terugbrengen. De IB-pagina geeft
haar niet-gedekte deel mee als `NIET_GEDEKT` en dat staat onder de berekening in beeld; de
VpB-pagina leunt niet op een voetnoot en geeft niets mee. Daarnaast kent de netwerktest de
bewuste afwijking nu als gegeven, zodat elke andere rij nog wél 1-op-1 wordt getoetst, en
een aparte test valt om zodra de rij of de voetnoot op de bronpagina verandert.

## Het stille `None`

`controleer_nieuwe_tarieven()` gaf `None` terug zowel wanneer de reeks klopte als wanneer
er niets was gecontroleerd. Zij geeft nu een `Controle` met vier statussen: `gelijk`,
`afwijking`, `onbereikbaar` en `onleesbaar`. Een afwijking blijft een waarschuwing; de twee
toestanden waarin niets is vergeleken worden zichtbaar gemeld, en de voettekst zegt bij
elke weergave wát er is gecontroleerd.

`_haal_pagina_op()` is ongemoeid gebleven, zoals de opdracht voorschrijft: die functie is
gecached en gooit met opzet, zodat Streamlit het mislukte antwoord niet vasthoudt en de
volgende weergave het opnieuw probeert. Het herstel zit volledig in de aanroeper. Dat staat
nu ook in de docstring, zodat een volgende sessie er niet aan begint.

## De poort van vier

1. **Tests groen vóór de kopieerstap.** `python -m pytest -q` geeft 382 passed, 0 failed
   (was 366). Gedraaid in de worktree vóór de merge naar `master`. De vijf netwerktests
   hebben werkelijk gedraaid en zijn niet overgeslagen: nagelopen met `-v`, ze halen de
   bronpagina op en bevestigen dat de voetnoot en de bedoelde afwijking er nog staan.
2. **Vrijgavenotitie.** Dit stuk, met paragraaf 9 van `WIJZIGINGSRAPPORT.md` als
   onderbouwing.
3. **Gelijkwaardigheidstoets.** Niet van toepassing: deze tool vervangt geen rekenmodel van
   een derde. Er is dus ook geen onverklaard verschil. Wat er wél is: een tweede,
   onafhankelijk opgebouwde IB-percentagereeks in `Berekeningen`, en juist het verschil
   daartussen bracht deze fout aan het licht. Beide reeksen zijn nu gelijk op deze rij.
4. **Vindplaats bij de waarde.** De enige geraakte fiscale waarde heeft haar vindplaats in
   het commentaar boven de tabel: Stb. 2020, 200, met de voetnoot op belastingdienst.nl als
   bevestiging en de controledatum 7 september 2026 erbij. Ook is opgeschreven wat buiten
   de controle is gebleven: de toeslagenpercentages uit de voetnoten \* en \*\*, die deze
   rekenpagina's niet gebruiken.

`status` blijft `beta` en `laatst_beoordeeld` blijft `null`: deze merge publiceert en
accordeert niet.

## Wat hierbuiten is gebleven

Niets geconsolideerd, niets verplaatst, geen koppeling tussen repository's gebouwd. Waar de
belastingrente hoort te worden gerekend is vraag 1 in
`PostbusClaude/VRAGEN-07-09-2026.md` en een besluit van Sylvain. De drie punten hierboven
zijn fout welk besluit er ook valt.
