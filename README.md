# Bouwman Tools — Belastingtools

Een Streamlit-app met belastingtools voor dagelijks gebruik.

**Live:** [belastingtooljoindk.streamlit.app](https://belastingtooljoindk.streamlit.app)

---

## Tools

### 🏦 Betalingskenmerk
Decodeert 16-cijferige Belastingdienst betalingskenmerken.

- Herkent belastingsoort: LH, OB, VpB, IB en toeslagen
- Reconstrueert het RSIN via de 11-proef (inclusief BTW-nummer)
- Toont jaar en tijdvak (maand of kwartaal)
- Genereert een boekhoudingomschrijving met kopieerknop, per soort passend geformuleerd:
  `Afdr. OB mei 2026` · `Naheff. LH 1e kwartaal 2025` · `Aanslag IB 2025` ·
  `Aanslag VpB boekjaar 2024` · `Zorgtoeslag 2025`
- Zoekt automatisch de bedrijfsnaam **en SBI-code** op via de KvK API (RSIN-lookup)
- **Auto-decode bij plakken** — geen klik nodig

Gevalideerd kenmerk: `4863521721601050` = Aangifte OB, mei 2026, RSIN 863521721
(vastgelegd als regressietest)

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

### 📊 Belastingrente IB
Berekent de belastingrente voor een aanslag inkomstenbelasting.

- Renteperiode: 1 juli volgend op het belastingjaar t/m 6 weken na dagtekening
- Tarieven rechtstreeks van belastingdienst.nl (tabel nagelopen op 17 augustus 2026)
- Altijd zichtbare uitsplitsing per tariefperiode
- Werkt ook als voorcalculatie met verwachte dagtekening
- **Automatische check:** eens per maand wordt de tarieventabel op belastingdienst.nl
  uitgelezen en regel voor regel vergeleken. Signaleert zowel een nieuwe periode als
  een percentage dat met terugwerkende kracht is herzien

### 📊 Belastingrente VpB
Berekent de belastingrente voor een aanslag vennootschapsbelasting.

- Renteperiode: 6 maanden na boekjaar-einde t/m 6 weken na dagtekening
- Ondersteunt **gebroken boekjaren** (elke einddatum)
- Tarieven rechtstreeks van belastingdienst.nl (tabel nagelopen op 17 augustus 2026)
- Altijd zichtbare uitsplitsing per tariefperiode
- Werkt ook als voorcalculatie met verwachte dagtekening
- **Automatische check:** eens per maand wordt de tarieventabel op belastingdienst.nl
  uitgelezen en regel voor regel vergeleken. Signaleert zowel een nieuwe periode als
  een percentage dat met terugwerkende kracht is herzien

### 🚗 Auto BTW privé
Berekent de BTW-correctie en bijtelling voor privégebruik van een zakelijke auto (forfaitmethode).

- Kenteken invoeren → automatische opzoekservice via het **RDW kentekenregister** (gratis, geen API-sleutel)
- Haalt op: merk, model, bouwjaar, brandstof, CO₂-uitstoot en catalogusprijs
- **BTW-correctie** (art. 4 lid 2 Wet OB): 2,7% van de catalogusprijs, of 1,5% bij een
  marge-auto én zodra het jaar van ingebruikname plus de vier jaren daarna voorbij zijn
  (dat laatste wordt afgeleid uit de datum tenaamstelling)
- **Bijtelling**: het percentage ligt vanaf de datum eerste toelating **60 maanden vast**
  en wordt dus niet op het berekeningsjaar bepaald. Loopt die termijn midden in het jaar
  af, dan wordt de periode gesplitst
  - Benzine/diesel: 22% (2017+), 25% (2012–2016)
  - Elektrisch/waterstof: korting met plafond, oplopend van 4% naar 16%; vervalt vanaf 2026
- Keuze volledig jaar of eigen periode
- Catalogusprijs handmatig invullen als RDW geen waarde heeft

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
| `_tarieven_check.py` | Maandelijkse check op nieuwe tarieven (belastingdienst.nl) |
| `tests/` | Pytest-suite (169 tests) |
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

De rekenlogica staat bewust los van Streamlit in `_kenmerk.py`, `_auto_calc.py` en
`_vies.py`, zodat die zonder draaiende app te testen is. Een paar tests gaan over het
netwerk en vergelijken de hardgecodeerde tabellen met de bron (belastingdienst.nl, VIES);
die worden overgeslagen als er geen internet is. Die netwerktests zijn er niet voor niets:
ze hebben twee datafouten in de VpB-tarieventabel aan het licht gebracht.

---

## Openstaande punten

Twee zaken zijn bewust nog niet opgelost omdat ze een fiscaal-inhoudelijke bevestiging
vragen. Beide staan als waarschuwing in de code zelf.

1. **Middelcodes 85 t/m 88.** `MIDDEL2_LABEL` kent deze als Eurovignet en MOA
   vrachtwagens, maar de VpB-tak vangt de hele range 80–96 af en gaat voor. Daardoor
   worden die vier codes nu als Vennootschapsbelasting getoond. Eén van beide klopt niet.
   De [officiële specificatie](https://odb.belastingdienst.nl/wp-content/uploads/2025/07/Specificatie-Betalingskenmerk_bepaling_1.5.pdf)
   zou dit moeten beslechten. Het huidige gedrag is met een test vastgelegd, zodat het
   niet ongemerkt verschuift.

2. **Nulemissiepercentages bijtelling.** De reeks in `_auto_calc.py` is gecorrigeerd naar
   4/4/4/8/12/16 (2017–2025), maar de officiële overzichtspagina gaf een 404 bij het
   naslaan. Controleer deze waarden voordat je er klanten mee bedient.

---

## Deployment (Streamlit Cloud)

1. Push naar `master`
2. Streamlit Cloud deployt automatisch
3. Stel de KvK API-sleutel in via **Settings → Secrets** in het Streamlit Cloud dashboard

---

## Bronnen

- [Specificatie Betalingskenmerk_bepaling v1.5 — Belastingdienst](https://odb.belastingdienst.nl/wp-content/uploads/2025/07/Specificatie-Betalingskenmerk_bepaling_1.5.pdf)
- [Overzicht percentages belastingrente — Belastingdienst](https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/standaard_functies/prive/contact/rechten_en_plichten_bij_de_belastingdienst/belastingrente/overzicht_percentages_belastingrente)
- [KvK Handelsregister API](https://developers.kvk.nl)
- [EU VIES API](https://ec.europa.eu/taxation_customs/vies/)
