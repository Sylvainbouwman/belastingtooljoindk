# Belastingtool JoinDK

Verzameling belastingtools voor Join Administraties en DK Accountants, als één
Streamlit-app. Begonnen als losse betalingskenmerk-tool en daarna uitgebouwd; de
repository heet daarom sinds 18-08-2026 `belastingtooljoindk` en niet meer
`betalingskenmerk-tool`.

**Live:** [belastingtooljoindk.streamlit.app](https://belastingtooljoindk.streamlit.app)
Dit is een testomgeving voor collega's; de productieversie komt in een beveiligde
omgeving te staan.

Deze app hoort **niet** bij de verzameling op bouwman.tools. Dat is een aparte portal
met andere, losse tools. Noem deze app dus niet "Bouwman Tools".

## Omgeving

- Python: `C:\Python314\python.exe`
- `streamlit` staat **niet** in PATH. Altijd starten via:
  ```
  python -m streamlit run app.py
  ```
  Nooit `streamlit run app.py` — dat geeft "not recognized".
- Tests: `python -m pytest -q`

## Structuur

- `app.py` — entrypoint, `st.navigation()`-router over de zes pagina's
- `pages/` — Betalingskenmerk, VIES BTW-controle, KvK/SBI opzoeken, Belastingrente IB,
  Belastingrente VpB, Auto BTW privé
- Rekenlogica, bewust zonder Streamlit-afhankelijkheden zodat het los testbaar is:
  `_kenmerk.py` (betalingskenmerk), `_rente.py` (belastingrente), `_auto_calc.py`
  (BTW-correctie en bijtelling auto), `_vies.py` (BTW-nummers),
  `_tarieven_check.py` (controle op nieuwe tarieven bij de bron)
- `_format.py` — Nederlandse notatie voor bedragen, datums en percentages
- `_ui.py` — gedeeld stijlblok, koptekst, HTML-escaping (`veilig()`) en het KvK-sleutelblok
- `_auto_paste.py` + `_components/auto_paste/` — eigen component dat plakken direct
  doorgeeft, zonder klik
- `tests/` — pytest-suite

De statische HTML-versie is verwijderd in commit `4d4ef5d`; de app draait alleen nog via
Streamlit.

## Werkwijze

- Rekenregels altijd tegen de bron toetsen en de vindplaats in een commentaar bij de
  waarde zetten (jaarpagina, wetsartikel of specificatieparagraaf). Zie `_auto_calc.py`
  en `_kenmerk.py` voor de opzet.
- Bij twijfel over een fiscale waarde: niets aannemen, maar een waarschuwing plaatsen en
  het in `WIJZIGINGSRAPPORT.md` op de actielijst zetten.
- Gegevens die van een API komen gaan via `veilig()` de HTML in.

## KvK API

- KvK blokkeert Cloudflare IP-adressen, daarom werkte de proxy in de oude HTML-versie
  niet. In de Streamlit-versie gaat de call server-side via Python → geen blokkade.
- Endpoint: `https://api.kvk.nl/api/v2/zoeken?rsin={rsin9}`
- API-sleutel: in de zijbalk invoeren (alleen in de sessie) of via
  `st.secrets["kvk_api_key"]` op Streamlit Cloud.
- Een **BSN** gaat nooit naar de KvK; zie `mag_naar_kvk()` in `_kenmerk.py` en de sectie
  Privacy in de README.

## Samenvoegen met WWFT-app

Overweging voor later: deze pagina's onderbrengen in de WWFT multi-page app. Dat is nu
een kwestie van de map `pages/` plus de losse modules meeverhuizen, niet meer van één
bestand kopiëren.
