# Vrijgavenotitie Belastingtool JoinDK, 29 september 2026

Status: klaar voor de poort. De open punten staan met hun stand in `OPENSTAAND.md`.

## Waarover gaat het

Tool: Belastingtool JoinDK, pagina's Belastingrente IB, Belastingrente VpB en
Invorderingsrente. Draait op
[belastingtooljoindk.streamlit.app](https://belastingtooljoindk.streamlit.app), een
testomgeving voor collega's. Eigenaar: Sylvain Bouwman.

Dit is de gelijkwaardigheidstoets tegen model 02-04 (Wolters Kluwer, versie v20260117). De
onderbouwing staat in `WIJZIGINGSRAPPORT.md`, paragraaf L11.

## Uitkomst

Nul onverklaarde verschillen. Belastingrente: 202 synthetische gevallen, 864 velden gelijk
en 146 verklaard. Invorderingsrente: 138 gevallen, 395 velden gelijk en 157 verklaard. Het
model is in Excel zelf doorgerekend; de tool is niet tegen een nabouw van het model gelegd.

## Wat er verandert voor de gebruiker

1. **Invorderingsrente begint een dag later**, op de dag na de uiterste betaaldatum, zoals
   de Belastingdienst en het model rekenen. Tot nu toe rekende de tool een dag te veel. Bij
   art. 28b schuift het begin ook een dag op. Op de pagina heet de datum nu "vervaldag
   (uiterste betaaldatum)", met "invorderbaar vanaf" de dag erna.
2. **Belastingrente telt de laatste maand volgens art. 31 lid 1 Uitvoeringsregeling AWR
   1994.** Eindigt de rente op de 31e, dan telt die maand 31 dagen: één dag meer rente dan
   tot nu toe. En een VpB-berekening over de tariefwissel van 1 maart 2015 telt februari nu
   als volle maand van 30 dagen: twee dagen meer dan tot nu toe.
3. **Een VpB-boekjaar dat vóór 2012 eindigt geeft een melding in plaats van een bedrag**,
   omdat daar de oude heffingsrente gold.

Wat níet verandert: de tariefreeksen, de afronding per tariefperiode van de belastingrente
(besluit 29-09-2026, OPENSTAAND.md punt 12) en de rekenvoorbeelden van de Belastingdienst,
die de tests nog steeds tot op de euro reproduceren.

## Vindplaats van elke geraakte fiscale regel

| Regel | Vindplaats | Waar in de code |
|---|---|---|
| Einde belastingrentetijdvak: dag vóór de invorderbaarheid | art. 30fc lid 2 AWR (BWBR0002320, versie 01-01-2026) | `_rente.py`, kop |
| Termijn van zes weken vervalt op dagtekening + 42 dagen | art. 9 lid 1 IW 1990; onderdeel 9.5 Leidraad Invordering 2008 | `_invorderingsrente.vervaldag_op` |
| Invorderingsrente vanaf de invorderbaarheid, dag na de vervaldag | art. 28 lid 2 IW 1990; belastingdienst.nl, Invorderingsrente, geraadpleegd 29-09-2026 | `_invorderingsrente.invorderbaar_op`, `periode_art28` |
| Art. 28b vanaf de dag na de invorderbaarheid | art. 28b lid 2 IW 1990 | `_invorderingsrente.periode_art28b` |
| Volle maand 30 dagen, laatste maand van het tijdvak werkelijk | art. 31 lid 1 Uitvoeringsregeling AWR 1994 (BWBR0006736, versie 01-01-2026) | `_rente.dagen_belastingrente` |
| Afronding belastingrente naar beneden | art. 31 lid 2 Uitvoeringsregeling AWR 1994; belastingdienst.nl, voorbeeld 93 + 9 = 102 | `_rente.bereken` |
| Belastingrente vanaf belastingjaar 2012 | Kamerstukken II 2012/13, 33403, nr. 3, par. 14 (overgangsbepaling zelf nog niet nagelezen, punt 14) | `pages/Belastingrente_VpB.py` |

## Getest

`python -m pytest -q`: 488 geslaagd, 0 mislukt (was 473). Nieuw: het rekenvoorbeeld
invorderingsrente van de Belastingdienst, de telling van art. 31 lid 1 URAWR aan het einde
van het tijdvak en bij een tariefwissel, de vervalmaand van 31 dagen, de schrikkeldag, het
tijdvak van één dag en de weigering van een boekjaar vóór 2012. Elke nieuwe test is rood
gezien tegen de oude code.

## Wat de toets niet dekt

- De einddatum van de belastingrente (6 weken, 19 weken, navordering, vrijstelling): het
  model vraagt die als invoer. Die logica staat getoetst tegen de voorbeelden van de
  Belastingdienst. Eén daarvan spreekt de andere tegen; zie OPENSTAAND.md punt 12.
- Art. 28a en 28b: het model rekent ze niet.
- VpB met het HR-arrest uit: de tool past het arrest van 16-01-2026 altijd toe.

## Open na deze vrijgave

- Punt 13: drie fouten in model 02-04, terug te melden aan Wolters Kluwer.
- Punt 14: de precieze overgangsgrens tussen heffingsrente en belastingrente.
