# Bouwman Tools — Belastingtools

Een Streamlit-app met belastingtools voor dagelijks gebruik.

**Live:** [belastingtooljoindk.streamlit.app](https://belastingtooljoindk.streamlit.app)

---

## Tools

### 🏦 Betalingskenmerk
Decodeert 16-cijferige Belastingdienst betalingskenmerken.

- Herkent belastingsoort: LH, OB, VpB, IB, ZVW, HSB, MOA, Eurovignet, LIR/VHR en toeslagen
- **Controleert het controlecijfer op positie 1** en weigert een kenmerk dat de proef niet
  haalt, met vermelding van het cijfer dat er hoort te staan — een typefout levert dus geen
  geloofwaardig ogend maar verkeerd RSIN meer op
- Reconstrueert het RSIN via de 11-proef (inclusief BTW-nummer)
- Toont jaar, tijdvak (maand of kwartaal) en bij een aanslag of het een **voorlopige of
  definitieve** aanslag is
- Genereert een boekhoudingomschrijving met kopieerknop, per soort passend geformuleerd:
  `Afdr. OB mei 2026` · `Naheff. LH 1e kwartaal 2025` · `Aanslag IB 2025` ·
  `Voorl. aanslag VpB boekjaar 0112` · `Zorgtoeslag 2025` · `Naheff. MOA 2023`
- Zoekt automatisch de bedrijfsnaam **en SBI-code** op via de KvK API (RSIN-lookup)
- **Auto-decode bij plakken** — geen klik nodig

Gevalideerd kenmerk: `4863521721601050` = Aangifte OB, mei 2026, RSIN 863521721
(vastgelegd als regressietest)

Alle **27 voorbeelden** uit de officiële Specificatie Betalingskenmerk_bepaling v1.5 staan
als regressietest in `tests/test_kenmerk.py`, met het BSN/RSIN uit het bijbehorende
aanslagnummer als verwachte uitkomst.

> Gaat de 11-proef niet op, dan wordt geen RSIN getoond maar een melding dat het
> kenmerk waarschijnlijk verkeerd is overgenomen. Soort, jaar en tijdvak blijven
> gewoon leesbaar.

### 🇪🇺 VIES BTW-controle
Valideert Europese BTW-nummers via de officiële EU VIES-database.

- Ondersteunt alle EU-landen (NL, DE, BE, FR, ...); `GR`, `UK` en `GB` worden
  herkend als `EL` respectievelijk `XI`
- Toont geldigheid, bedrijfsnaam en adres
- Leidt voor NL-nummers automatisch het RSIN af
- Onderscheidt **drie** uitkomsten: geldig, niet geldig en *niet gecontroleerd*.
  VIES antwoordt bij een storing namelijk met HTTP 200 en `isValid: false`; die
  gevallen worden expliciet als storing gemeld en niet als ongeldig nummer
- Gratis, geen API-sleutel vereist

### 🔍 KvK / SBI opzoeken
Zoek bedrijfsgegevens op via de KvK Handelsregister API.

- Zoeken op bedrijfsnaam, KvK-nummer (8 cijfers) of RSIN (9 cijfers)
- Toont naam, KvK-nummer, RSIN en SBI-activiteitscode(s)
- Onderscheid hoofd- en nevenactiviteiten
- Tot 10 resultaten per zoekopdracht

### 📊 Belastingrente IB en VpB
Berekent de belastingrente voor een aanslag inkomstenbelasting of vennootschapsbelasting,
volgens de rekenmethode van de Belastingdienst.

**Rekenmethode** — de testsuite reproduceert de gepubliceerde rekenvoorbeelden van de
Belastingdienst tot op de euro:

- **30 dagen per maand, 360 dagen per jaar** (niet: werkelijke dagen / 365)
- Renteperiode **inclusief** begin- en einddatum
- Per tariefperiode **naar beneden afgerond op hele euro's** — niet over het totaal;
  hun eigen voorbeeld geeft 93 + 9 = 102, terwijl 93,75 + 9,93 naar 103 zou afronden
- Splitst automatisch bij elke tariefwijziging binnen de periode

**Situaties die worden herkend** — de pagina toont welke regel is toegepast:

| Situatie | Einddatum rente |
|---|---|
| Aangifte op tijd (vóór 1 mei IB / 1 juni VpB) én ongewijzigd gevolgd | **geen rente verschuldigd** |
| VpB: tijdig om een voorlopige aanslag verzocht, conform opgelegd | **geen rente verschuldigd** |
| Te laat, maar ongewijzigd gevolgd | 19 weken na ontvangst aangifte, of 6 weken na dagtekening — het vroegste |
| Afgeweken van de aangifte | 6 weken na dagtekening |
| Navorderingsaanslag | 1 maand na dagtekening |
| Navordering op eigen verzoek | 12 weken na het verzoek, of 1 maand na dagtekening — het vroegste |

**Verder:**

- Startdatum: 1 juli volgend op het belastingjaar; bij VpB de 7e maand na het boekjaar,
  zodat ook **gebroken boekjaren** kloppen
- Uitklapblok met alle uitgangspunten en de reden van de einddatum, zodat een fiscalist
  de berekening kan narekenen
- Werkt ook als voorcalculatie met een verwachte dagtekening
- **Automatische check:** eens per maand wordt de tarieventabel op belastingdienst.nl
  uitgelezen en regel voor regel vergeleken. Signaleert zowel een nieuwe periode als
  een percentage dat met terugwerkende kracht is herzien
- Nog niet ondersteund: navordering bij een gebroken boekjaar is niet apart getoetst

### 🚗 Auto BTW privé
Berekent de BTW-correctie en bijtelling voor privégebruik van een zakelijke auto (forfaitmethode).

- Kenteken invoeren → automatische opzoekservice via het **RDW kentekenregister** (gratis, geen API-sleutel)
- Haalt op: merk, model, bouwjaar, brandstof, CO₂-uitstoot en catalogusprijs
- **BTW-correctie** (art. 4 lid 2 Wet OB): 2,7% van de catalogusprijs inclusief BTW en BPM,
  of 1,5% bij een marge-auto én zodra het jaar van ingebruikname plus de vier jaren daarna
  voorbij zijn (dat laatste wordt afgeleid uit de datum tenaamstelling). De correctie wordt
  **naar maanden** berekend, conform het rekenvoorbeeld van de Belastingdienst
  (`4/12 × 2,7% × € 45.000 = € 405`); een gedeeltelijke maand telt naar rato van de dagen
  binnen die maand
- **Bijtelling**: het percentage ligt vanaf de datum eerste toelating **60 maanden vast**
  en wordt dus niet op het berekeningsjaar bepaald. Loopt die termijn midden in het jaar
  af, dan wordt de periode gesplitst
  - Benzine/diesel: 22% (2017 en later), 25% (tot en met 2016)
  - Nulemissie: korting met plafond — 4% (2017–2019), 8% (2020), 12% (2021), 16% (2022–2024),
    17% (2025), 18% (2026), telkens tot het plafond van dat jaar en daarboven 22%
  - **Waterstof** (en auto's volledig op geïntegreerde zonnecellen): het verlaagde percentage
    geldt over de hele catalogusprijs, zonder plafond
  - **Youngtimer**: is de auto op 1 januari ouder dan 16 jaar (tot 2026: 15 jaar), dan is de
    bijtelling 35% van de waarde in het economisch verkeer. De pagina herkent dat aan de datum
    eerste toelating en vraagt die waarde; zonder waarde wordt géén bedrag getoond
- Marge-auto per auto in te stellen, dus ook goed bij meerdere auto's in één berekening
- Keuze volledig jaar of eigen periode
- Catalogusprijs handmatig invullen als RDW geen waarde heeft

> De bijtelling is bij een IB-ondernemer nooit hoger dan de totale autokosten van het jaar.
> Die kosten kent de tool niet, dus dat maximum wordt niet toegepast; de pagina meldt dat.

---

## Structuur

| Bestand | Beschrijving |
|---------|-------------|
| `app.py` | Entrypoint — `st.navigation()` router |
| `pages/Betalingskenmerk.py` | Betalingskenmerk decoder + KvK naam/SBI |
| `pages/VIES_BTW_Controle.py` | EU BTW-nummer validatie via VIES |
| `pages/KvK_SBI_Opzoeken.py` | KvK / SBI opzoeken op naam, KvK-nr of RSIN |
| `pages/Belastingrente_IB.py` | Belastingrente IB calculator |
| `pages/Belastingrente_VpB.py` | Belastingrente VpB calculator |
| `pages/Auto_BTW_Prive.py` | Auto BTW privé calculator (RDW-koppeling) |
| `_auto_paste.py` | Streamlit custom component declaratie (paste-detectie) |
| `_components/auto_paste/` | HTML/JS voor de paste-component |
| `_kenmerk.py` | Decodeerlogica betalingskenmerk (zonder Streamlit, los testbaar) |
| `_auto_calc.py` | BTW-correctie en bijtelling zakelijke auto (zonder Streamlit) |
| `_vies.py` | BTW-nummerlogica en duiding van VIES-antwoorden (zonder Streamlit) |
| `_rente.py` | Belastingrenteberekening: 30/360, renteperiode, afronding (zonder Streamlit) |
| `_tarieven_check.py` | Maandelijkse check op nieuwe tarieven (belastingdienst.nl) |
| `_format.py` | Nederlandse notatie voor bedragen, datums en percentages (zonder Streamlit) |
| `_ui.py` | Gedeeld stijlblok, koptekst, HTML-escaping en het KvK-sleutelblok |
| `tests/` | Pytest-suite (293 tests) |
| `requirements.txt` | Python dependencies |
| `requirements-dev.txt` | Alleen voor de tests (pytest) |

---

## API-sleutels

| API | Gebruikt door | Kosten | Sleutel vereist |
|-----|--------------|--------|-----------------|
| KvK Handelsregister | Betalingskenmerk, KvK/SBI | ~€0,02–0,04 per aanroep | Ja — via `.streamlit/secrets.toml` |
| RDW Open Data | Auto BTW privé | Gratis | Nee |
| EU VIES | VIES BTW-controle | Gratis | Nee |

---

## Lokaal draaien

```bash
python -m streamlit run app.py
```

> Let op: `streamlit` staat niet in PATH op dit systeem — gebruik altijd `python -m streamlit`.

Maak een `.streamlit/secrets.toml` aan met:

```toml
kvk_api_key = "jouw-kvk-api-sleutel"
```

---

## Tests

```bash
python -m pytest tests/ -q
```

De rekenlogica staat bewust los van Streamlit in `_kenmerk.py`, `_auto_calc.py`,
`_vies.py`, `_rente.py` en `_format.py`, zodat die zonder draaiende app te testen is.

Twee testbestanden zijn tegen een officiële bron gelegd. `tests/test_kenmerk.py` bevat alle
27 voorbeelden uit de Specificatie Betalingskenmerk_bepaling v1.5; `tests/test_auto_calc.py`
bevat het rekenvoorbeeld van de Belastingdienst voor de BTW-correctie (€ 405).

De belangrijkste tests staan in `tests/test_rente.py`: die reproduceren de
rekenvoorbeelden die de Belastingdienst zelf publiceert, tot op de euro. Zolang die
groen zijn, is de rekenmethode aantoonbaar gelijk aan de bron — niet aan een
interpretatie ervan.

Een paar tests gaan over het netwerk en vergelijken de hardgecodeerde tabellen en het
antwoordformaat met de bron (belastingdienst.nl, VIES); die worden overgeslagen als er
geen internet is. Ze zijn er niet voor niets: ze hebben twee datafouten in de
VpB-tarieventabel aan het licht gebracht.

---

## Openstaande punten

De verificatieronde is afgerond: alle vier de rekenpagina's zijn tegen de bron getoetst.
Zie [WIJZIGINGSRAPPORT.md](WIJZIGINGSRAPPORT.md) voor wat dat opleverde en voor de
actielijst.

Wat nu nog open staat, vraagt een beslissing en geen code:

1. **Drie gegevens van vóór 2021 zijn niet bij de bron bevestigd.** Het plafond van 2020
   (€ 45.000) en het ontbreken van een plafond in 2017 en 2018 staan niet op de
   jaarpagina's van belastingdienst.nl. Ze spelen alleen bij een herberekening van een oud
   jaar: de 60-maandstermijn van elke auto met eerste toelating tot en met 2020 is
   uiterlijk in 2025 verlopen. Staat als waarschuwing in `_auto_calc.py`.

2. **BSN-verwerking (punt K5).** Uit het kenmerk van een particulier rolt een BSN. Die
   wordt getoond, een uur gecachet en als zoekterm naar de KvK gestuurd — terwijl de KvK
   particulieren niet kent. Op Streamlit Community Cloud loopt dat over infrastructuur van
   derden. Dit is een verwerkersvraag.

3. **De naam van deze app.** De repository heet `betalingskenmerk-tool`, maar de app bevat
   zes pagina's en presenteert zichzelf als "Bouwman Tools". Zie de actielijst in het
   wijzigingsrapport.

4. **Zijn er eerdere berekeningen die herzien moeten worden?** De verificatierondes hebben
   fouten opgeleverd die verkeerde bedragen en verkeerde nummers gaven. Het overzicht van
   wat wanneer fout was, staat in het wijzigingsrapport.

---

## Deployment (Streamlit Cloud)

1. Push naar `master`
2. Streamlit Cloud deployt automatisch
3. Stel de KvK API-sleutel in via **Settings → Secrets** in het Streamlit Cloud dashboard

---

## Bronnen

- [Specificatie Betalingskenmerk_bepaling v1.5 — Belastingdienst](https://odb.belastingdienst.nl/wp-content/uploads/2025/07/Specificatie-Betalingskenmerk_bepaling_1.5.pdf)
- [Overzicht percentages belastingrente — Belastingdienst](https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/standaard_functies/prive/contact/rechten_en_plichten_bij_de_belastingdienst/belastingrente/overzicht_percentages_belastingrente)
- [Belastingrente betalen bij inkomstenbelasting — Belastingdienst](https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/standaard_functies/prive/contact/rechten_en_plichten_bij_de_belastingdienst/belastingrente/belastingrente_betalen_bij_inkomstenbelasting)
- [Belastingrente betalen bij vennootschapsbelasting — Belastingdienst](https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/standaard_functies/prive/contact/rechten_en_plichten_bij_de_belastingdienst/belastingrente/belastingrente_betalen_bij_vennootschapsbelasting)
- [KvK Handelsregister API](https://developers.kvk.nl)
- [EU VIES API](https://ec.europa.eu/taxation_customs/vies/)
