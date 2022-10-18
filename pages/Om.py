import streamlit as st

st.title("💡 Om")
st.markdown(
    """
## Opsætning
Sådan henter du et _refresh token_ fra [eloverblik](https://eloverblik.dk):
1. Gå til eloverblik.dk
2. ...

## Datakilder
Dette værktøj trækker på data fra flere kilder både til udtræk af personligt forbrug, men også til udtræk af tariffer og spotpriser.
- Dit forbrug og oplysninger: https://api.eloverblik.dk/customerapi/index.html
- Elspotpriser: https://www.energidataservice.dk/tso-electricity/elspotprices
- Tariffer: https://www.energidataservice.dk/tso-electricity/datahubpricelist
- AQUAREA Smart Cloud: https://aquarea-smart.panasonic.com/

"""
)
