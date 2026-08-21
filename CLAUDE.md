# Belastingtool JoinDK

Streamlit-app met zes belastingtools voor Join Administraties en DK Accountants:
betalingskenmerk, VIES BTW-controle, KvK/SBI, belastingrente IB en VpB, auto BTW
privé. Begonnen als betalingskenmerk-tool; heet sinds 18-08-2026
`belastingtooljoindk`. Hoort **niet** bij de portal op bouwman.tools en heet dus
nooit "Bouwman Tools".

## Documentatie

`README.md` (werking per tool + sectie Privacy over BSN versus RSIN),
`UC_belastingtooljoindk.md` (doel en scope), `WIJZIGINGSRAPPORT.md` (actielijst;
open fiscale punten horen hier).

## Commando's

```bash
python -m streamlit run app.py
python -m pytest -q
```

## Structuur

- `app.py` — entrypoint met `st.navigation()`-router; `pages/` bevat de zes pagina's.
- Pure reken- en parsermodules, bewust zonder Streamlit-import zodat ze los
  testbaar blijven: `_kenmerk.py`, `_rente.py`, `_auto_calc.py`, `_vies.py`,
  `_tarieven_check.py` (signaleert nieuwe tarieven bij de bron). Houd die grens:
  geen `st.`-aanroepen daarin, geen rekenlogica in `pages/`.
- `_format.py` notatie · `_ui.py` stijl, koptekst, `veilig()`, KvK-sleutelblok ·
  `_auto_paste.py` + `_components/auto_paste/` voor plakken zonder klik.
- De statische HTML-versie is vervallen (commit `4d4ef5d`); alleen Streamlit.

## Externe koppelingen

- Alles wat van een API terugkomt gaat via `veilig()` de HTML in.
- **KvK**: server-side call (`https://api.kvk.nl/api/v2/zoeken?rsin={rsin9}`); de
  oude browserproxy werkte niet omdat KvK Cloudflare-IP's blokkeert. Sleutel via
  de zijbalk (alleen in de sessie) of `st.secrets["kvk_api_key"]`, nooit in code
  of commit. Een **BSN** gaat nooit naar de KvK — `mag_naar_kvk()` in
  `_kenmerk.py`, onderbouwing in de sectie Privacy van de README.
- **VIES** en **RDW**: alleen gevalideerde invoer de querystring in (zie de
  kentekenvalidatie in `pages/Auto_BTW_Prive.py`); storing of leeg antwoord geeft
  een nette melding, geen aanname.

## Fiscale afspraken

Vindplaats in commentaar bij de waarde zelf; `_auto_calc.py` en `_kenmerk.py`
tonen de opzet. Bij twijfel: waarschuwing tonen en het punt op de actielijst in
`WIJZIGINGSRAPPORT.md` zetten, geen gokwaarde.

## Publicatie en gereed

Publieke repo `Sylvainbouwman/belastingtooljoindk`, branch `master`; Streamlit
Cloud publiceert automatisch vanaf `master` naar
[belastingtooljoindk.streamlit.app](https://belastingtooljoindk.streamlit.app),
een testomgeving voor collega's (productie komt in een beveiligde omgeving). Geen
sync naar `bouwman-tools`. Repo is publiek: geen klantgegevens in tests,
voorbeelden of commits — gebruik de voorbeelden uit de officiële specificatie.

Gereed: `python -m pytest -q` groen (nu 366 tests), gewijzigde logica gedekt door
een test, README of WIJZIGINGSRAPPORT bijgewerkt waar dat geldt.

Open punt: samenvoegen met de WWFT multi-page app (`pages/` plus losse modules
meeverhuizen) is een overweging voor later; niet doen zonder opdracht.
