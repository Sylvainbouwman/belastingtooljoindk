# Openstaande punten

Laatst bijgewerkt: 19-09-2026 15:00 CEST. Eerste versie van dit bestand; eerder stonden
openstaande punten alleen in `WIJZIGINGSRAPPORT.md` (de actielijst per wijziging) en, voor
dit ene punt, in de nu gearchiveerde berichtenmap `PostbusClaude`.

**Stand:** van het ene punt staat er 1 open.

## Open

### 1. Waar hoort de belastingrente te worden gerekend: `belastingtooljoindk` of `Berekeningen`

**Status:** open. **Eigenaar:** Sylvain Bouwman.

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
in plaats van overtypt. Dat besluit staat nog open.
