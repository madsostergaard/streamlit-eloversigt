# 📦 Streamlit eloversigt

This is a Streamlit app for visualizing power usage. 
The app can fetch power usage and price information for any households in Denmark. 
It can also fetch power consumption from a Panasonic heat pump through the AQUAREA Smart-Cloud API, but this is only optional. 

I use it to monitor our energy consumption at home :-)

## Demo App

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://madsostergaard-streamlit-eloversigt-forside-bxa5px.streamlitapp.com//)

## Tips and tricks when running local

When running the streamlit app locally you can do the following:
1) add a file called `token.txt` which contains - you guessed it - your token. It will be read before rendering the app.
2) download your data to csv and store it in the root of the project. Call it `data.csv` and it will be read into the app. In this way, you can build a local database of past measurements, as you can "only" get the past ~2 years worth of data from eloverblik. 

## TODOs

This is a short list of stuff I might look at next
- [ ] adding trendlines to power usage 
- [ ] adding temperature measurements from the heatpump when present
- [ ] forecasting of e.g. power usage
