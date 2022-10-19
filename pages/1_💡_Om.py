import streamlit as st

st.set_page_config(page_title="Om", page_icon="💡")

st.title("💡 Om")
st.markdown(
    """
## Streamlit-eloversigt
Værktøj til at vise elforbrug og -priser. 
Det er også muligt at hente data fra AQUAREA Smart-Cloud hvis man har en Panasonic varmepumpe, som jeg har. 

## Opsætning
Du har brug for et token fra [eloverblik](https://eloverblik.dk) for at kunne hente dit eldata. 
Se altid [nuværende vejledninger her](https://energinet.dk/Energidata/DataHub/Eloverblik).
Et refreshtoken er gyldig i et år, men du kan til enhver tid deaktivere eller slette dit token

Sådan danner du et token:
1. Gå til eloverblik.dk.
2. Log ind med nem-id (eller MitID når det bliver implementeret). Bemærk: du skal logge ind som den, der har oprettet jeres elaftale.
3. Klik på profilikonet i højre hjørne og klik derefter på "Datadeling".
4. Klik på "Opret Token".
5. Navngiv dit token og klik på "Opret Token".
6. Kopier dit token og noter det et sikkert sted. Du ser det kun én gang.
7. Du kan nu bruge token her i app'en.

## Datakilder
Dette værktøj trækker på data fra flere kilder både til udtræk af personligt forbrug, men også til udtræk af tariffer og spotpriser.
- Dit forbrug og oplysninger: https://api.eloverblik.dk/customerapi/index.html
- Elspotpriser: https://www.energidataservice.dk/tso-electricity/elspotprices
- Tariffer: https://www.energidataservice.dk/tso-electricity/datahubpricelist
- AQUAREA Smart Cloud: https://aquarea-smart.panasonic.com/

"""
)
