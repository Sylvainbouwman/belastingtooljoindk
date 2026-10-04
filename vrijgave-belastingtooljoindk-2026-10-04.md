# Vrijgavenotitie Belastingtool JoinDK, 4 oktober 2026

Status: klaar voor de poort. De stand van de punten staat in `OPENSTAAND.md`; er is er één
open (punt 13, het bericht aan Wolters Kluwer, dat Sylvain zelf verstuurt).

## Waarover gaat het

Tool: Belastingtool JoinDK, pagina Invorderingsrente. Draait op
[belastingtooljoindk.streamlit.app](https://belastingtooljoindk.streamlit.app), een
testomgeving voor collega's. Eigenaar: Sylvain Bouwman. Onderbouwing in
`WIJZIGINGSRAPPORT.md`, paragraaf L12.

## Wat er verandert voor de gebruiker

1. **Uitstel wordt doorgerekend.** Bij uitstel vraagt de pagina de grond, de periode en
   eventueel de beëindiging, en laat de rente over de uitsteltijd weg (art. 28 lid 3). Na een
   beëindiging herleeft de rente op de dag van art. 6 Uitvoeringsbesluit IW 1990. Voorheen gaf de
   tool bij uitstel geen bedrag.
2. **Art. 28c is een eigen grondslag.** Vergoeding op verzoek bij heffing in strijd met het
   Unierecht, van de dag na de betaling tot de dag vóór de terugbetaling. Voorheen alleen een
   signalering.
3. **Art. 28b begint een dag eerder**, op de dag na de vervaldag, zoals de Belastingdienst het
   uitvoert. Een vergoeding wordt daardoor een dag hoger.
4. **Geen bedrag meer** bij betaling na afloop van de uitsteltermijn voor de gronden van
   art. 28 lid 4: de wet legt dat tijdvak niet vast. De melding noemt het Leidraadbeleid.

Wat níet verandert: de tariefreeksen, de dagentelling, de afronding en de andere pagina's.

## Vindplaats van elke geraakte fiscale regel

| Regel | Vindplaats | Waar in de code |
|---|---|---|
| Geen rente over de tijd van uitstel krachtens art. 25 lid 3, 5, 8, 9, 11, 17, 18, 19 en 21 | art. 28 lid 3 IW 1990 (BWBR0004770, versie 01-07-2026, geraadpleegd 04-10-2026) | `_invorderingsrente.uitstel_uitsluiting` |
| Herleving na beëindiging van uitstel | art. 28 lid 4 IW 1990; art. 6 Uitvoeringsbesluit IW 1990 (BWBR0004772, versie 12-12-2025) | `_invorderingsrente.herlevingsdatum` |
| Art. 28c: tijdvak, grondslag, uitsluiting en verzoektermijn | art. 28c lid 1 tot en met 3 IW 1990 | `_invorderingsrente.periode_art28c`, `pages/Invorderingsrente.py` |
| Art. 28b: begin op de dag na de vervaldag | KG:207:2022:2 (Kennisgroep Belastingdienst, 28-03-2023); belastingdienst.nl, Invorderingsrente, geraadpleegd 04-10-2026 | `_invorderingsrente.periode_art28b` |

## Getest

`python -m pytest -q`: 516 geslaagd, 0 mislukt (was 492).

## Tweede paar ogen

- **Bron-controleur**, 04-10-2026, eerste ronde: tijdvakken, formule en percentages van de
  invorderingsrente. Klopt, met één afwijking (de eerste dag van art. 28b, hersteld volgens
  besluit van Sylvain).
- **Bron-controleur**, 04-10-2026, tweede ronde over de nieuwe code: tien regels kloppen. Eén
  melding klopte niet (er bleek wel Leidraadbeleid voor betaling na afloop van het uitstel;
  hersteld). Eén punt is niet met een bron te sluiten: of de rente bij art. 25 lid 5 en 8 op 12
  of 13 februari herleeft. De tool kiest de letterlijke lezing, 12 februari; vastgelegd in
  `OPENSTAAND.md` punt 4.

## Wat de toets niet dekt

- Er is geen model dat uitstel of art. 28c rekent; de berekening is getoetst aan de wettekst
  en met doorgerekende gevallen, niet aan een bestaand rekenmodel.
- Het Leidraadbeleid voor betaling na afloop van het uitstel is niet gebouwd.
