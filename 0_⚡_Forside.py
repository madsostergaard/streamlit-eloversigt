import datetime as dt
from pathlib import Path
from typing import Dict, List, Literal, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from data import get_power_usage, get_smartcloud_data, get_userinfo_detailed

TOKEN_PATH = Path("token.txt")
LOCAL_DATA_PATH = Path("data.csv")
MONTH_NAMES = [
    "",
    "januar",
    "februar",
    "marts",
    "april",
    "maj",
    "juni",
    "juli",
    "august",
    "september",
    "oktober",
    "november",
    "december",
]
DAY_NAMES = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
USER_INFO_TEMPLATE = """Adresse: {} {}, {} {}\n\nBruger(e): {} {}"""


@st.cache(show_spinner=False)
def get_userinfo_cached(*args, **kwargs):
    return get_userinfo_detailed(*args, **kwargs)


@st.cache(show_spinner=False)
def get_smartcloud_data_cached(*args, **kwargs):
    return get_smartcloud_data(*args, **kwargs)


@st.cache(show_spinner=False)
def get_power_usage_cached(*args, **kwargs):
    return get_power_usage(*args, **kwargs)


def display_plotly_chart(
    df: pd.DataFrame,
    y: List[str],
    labels: Optional[dict] = None,
    plot_kwargs: Dict = {},
    kind: Literal["bar", "line"] = "bar",
    show_rangeslider: bool = False,
    x_range: List = None,
) -> None:
    px_fun = getattr(px, kind)
    fig = px_fun(df, y=y, labels=labels, **plot_kwargs)
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    if show_rangeslider:
        fig.update_xaxes(rangeslider_visible=True)

    if x_range is not None:
        fig.update_layout(xaxis_range=x_range)

    st.plotly_chart(fig, use_container_width=True)


def display_multiaxes_plotly_chart(
    df: pd.DataFrame,
    y1: str,
    y2: str,
    y1_axis: str,
    y2_axis: str,
    y1_name: Optional[str] = None,
    y2_name: Optional[str] = None,
    kind: Literal["bar", "line"] = "line",
):
    barchart = kind == "bar"
    kw = {"offsetgroup": 1} if barchart else {}
    kind = "Bar" if barchart else "Scatter"
    chart_fun = getattr(go, kind)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        chart_fun(x=df.index, y=df[y1], name=y1_name or y1, **kw),
        secondary_y=False,
    )

    if barchart:
        kw["offsetgroup"] = 2

    fig.add_trace(
        chart_fun(x=df.index, y=df[y2], name=y2_name or y2, **kw),
        secondary_y=True,
    )
    # Set x-axis title
    fig.update_xaxes(title_text="Tid")

    # Set y-axes titles
    fig.update_yaxes(title_text=y1_axis, secondary_y=False)
    fig.update_yaxes(title_text=y2_axis, secondary_y=True)

    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode="group" if kind == "Bar" else None,
    )
    st.plotly_chart(fig, use_container_width=True)


def display_average_daily_use(
    in_df: pd.DataFrame, year: int, select_columns: List[str]
) -> None:
    df = in_df[in_df.index.year == year].groupby(pd.Grouper(freq="MS")).sum()
    df = df[select_columns].divide(df.index.days_in_month, axis=0)

    df.index = map(lambda x: MONTH_NAMES[x.month] + f" {x.year}", df.index)
    st.dataframe(df.T)


def get_daily_use(in_df: pd.DataFrame, year: int) -> pd.DataFrame:
    df = in_df.groupby((in_df.index.floor("d"))).sum()
    df = df[df.index.year == year]
    return df


def get_monthly_sum(in_df: pd.DataFrame) -> pd.DataFrame:
    df = in_df.groupby([pd.Grouper(freq="MS")]).sum()
    df = df.assign(
        year=df.index.year,
        months=pd.Categorical(
            values=map(lambda x: MONTH_NAMES[x.month], df.index),
            categories=MONTH_NAMES,
        ),
    )
    return df


def get_weekday_average(
    in_df: pd.DataFrame, year: int, select_columns: List[str]
) -> pd.DataFrame:
    df = in_df.groupby((in_df.index.floor("d"))).sum()

    mask = df.index.year == year
    df = df[mask].groupby((df[mask].index.dayofweek))[select_columns]
    df = df.mean()
    df["Ugedag"] = list(map(lambda d: DAY_NAMES[d], df.index))
    return df


def get_hourly_average(in_df: pd.DataFrame, year: int) -> pd.DataFrame:
    mask = in_df.index.year == year
    df = in_df[mask].groupby((in_df[mask].index.hour)).mean()
    df["Timer"] = df.index
    return df


def combine_data() -> pd.DataFrame:
    power_df = st.session_state.get("power_df", None)
    smartcloud_df = st.session_state.get("smartcloud_df", None)

    local_df = None
    if LOCAL_DATA_PATH.exists():
        with LOCAL_DATA_PATH.open("r") as f:
            local_df = pd.read_csv(f, parse_dates=True, index_col=[0])

        if smartcloud_df is None and power_df is None:
            return local_df
        elif smartcloud_df is None:
            power_df = (
                pd.concat([local_df, power_df], ignore_index=False)
                .reset_index()
                .drop_duplicates(subset="index")
            )
            power_df = power_df.set_index("index")
            return power_df

    if smartcloud_df is None:
        return power_df

    c_df = pd.merge(
        power_df,
        smartcloud_df,
        how="outer",
        left_index=True,
        right_index=True,
    )

    c_df["Ren el"] = c_df["Elforbrug"].fillna(0) - c_df["Forbrug"].fillna(0)
    c_df = c_df.rename(columns={"Forbrug": "Varmepumpe"})

    if local_df is not None:
        c_df = (
            pd.concat([local_df, c_df], ignore_index=False)
            .reset_index()
            .drop_duplicates(subset="index")
        )
        c_df = c_df.set_index("index")

    return c_df


@st.cache
def df_to_csv(df):
    return df.to_csv().encode("utf-8")


def main():
    if TOKEN_PATH.exists():
        with TOKEN_PATH.open("r") as f:
            token = f.read()
    else:
        token = None

    st.set_page_config(page_title="Elforbrug", layout="centered", page_icon="⚡")
    st.title("⚡ Elforbrug ⚡")

    power_df = st.session_state.get("power_df", None)
    smartcloud_df = st.session_state.get("smartcloud_df", None)
    userinfo = st.session_state.get("userinfo", None)

    with st.expander("Data", expanded=True):
        st.subheader("Hent data")
        st.markdown(
            "Det er muligt at hente de sidste 720 dages data fra eloverblik.dk. Se fanen 'Om' for mere info"
        )
        col1, col2 = st.columns((0.5, 0.5), gap="medium")
        with col1:
            form = st.form(key="power_form")
            date_from = form.date_input("Startdato for data-træk")
            date_to = form.date_input("Slutdato på data-træk")
            token_input = (
                form.text_input("Indtast dit refresh-token fra eloverblik.dk her")
                if token is None
                else token
            )
            dk_area = form.selectbox(
                "Vælg dit område",
                ("Vest for storebælt", "Øst for storebælt"),
                index=1,
            )
            do_get_power_data = form.form_submit_button("⚡ Hent el-data!")

            if do_get_power_data:
                if date_to < date_from:
                    st.warning("Fra-datoen skal være før til-datoen!")
                    return

                with st.spinner(
                    f"Trækker eldata fra {str(date_from)} til {str(date_to)}"
                ):
                    power_df = get_power_usage_cached(
                        refresh_token=token_input,
                        date_from=date_from,
                        date_to=date_to,
                        dk_west=dk_area == "Vest for storebælt",
                    )
                    userinfo = get_userinfo_cached(refresh_token=token_input)

                    st.session_state["power_df"] = power_df
                    st.session_state["userinfo"] = userinfo

        with col2:
            form = st.form(key="smartcloud_form")
            date_from = form.date_input("Startdato for data-træk")
            date_to = form.date_input("Slutdato på data-træk")
            username = form.text_input("Indast smart-cloud brugernavn")
            password = form.text_input("Indtast smart-cloud kodeord", type="password")
            do_get_smartcloud_data = form.form_submit_button(
                "☁ Hent data fra AQUAREA Smart Cloud!"
            )

            if do_get_smartcloud_data:
                with st.spinner(
                    f"Henter varmepumpedata fra {str(date_from)} til {str(date_to)}..."
                ):
                    smartcloud_df = get_smartcloud_data_cached(
                        username=username,
                        password=password,
                        date_from=date_from,
                        date_to=date_to,
                    )
                    st.session_state["smartcloud_df"] = smartcloud_df

    c_df = combine_data()
    if c_df is None:
        st.warning("Du skal hente data ovenfor for at komme videre.")
        return

    with st.sidebar:
        # We only get userinfo with a token, so this might be empty
        if userinfo is not None:
            st.info(
                USER_INFO_TEMPLATE.format(
                    userinfo["contactAddresses"][0]["streetName"],
                    userinfo["contactAddresses"][0]["buildingNumber"],
                    userinfo["contactAddresses"][0]["postcode"],
                    userinfo["contactAddresses"][0]["cityName"],
                    userinfo["firstConsumerPartyName"],
                    f""" og {userinfo.get("secondConsumerPartyName")}"""
                    if userinfo.get("secondConsumerPartyName") is not None
                    else "",
                ),
                icon="ℹ",
            )

        csv = df_to_csv(c_df)
        st.download_button(
            "👇 Download dine data som .csv-fil",
            csv,
            "data.csv",
            "text/csv",
            key="download-csv",
        )

    total_use = c_df.groupby(c_df.index.year).sum()
    year = st.selectbox(
        "Vælg et år",
        options=total_use.index.unique(),
        index=len(total_use.index.unique()) - 1,
    )

    heatpump_present: bool = c_df.get("Varmepumpe", None) is not None
    ys = ["Ren el", "Varmepumpe"] if heatpump_present else ["Elforbrug"]

    tab1, tab2 = st.tabs(("💡 Forbrug", "💰 Priser"))
    with tab1:
        st.success(f"Årlig totale forbrug t.d.: {total_use['Elforbrug'][year]} kWh")

        st.subheader("Elforbrug")
        resolution = st.selectbox("Tidsopløsning", ("Måned", "Dag", "Timer"))
        if resolution == "Måned":
            df = get_monthly_sum(c_df)
            display_plotly_chart(
                df[df.index.year == year], ys, {"value": "kWh"}, kind="bar"
            )
        elif resolution == "Dag":
            display_plotly_chart(
                get_daily_use(c_df, year), ys, {"value": "kWh"}, kind="bar"
            )
        else:
            st.info("Viser seneste måned")
            x_range = [c_df.index[-1] - dt.timedelta(hours=24), c_df.index[-1]]
            display_mask = c_df.index > (c_df.index[-1] - dt.timedelta(days=31))
            ds = c_df[display_mask]
            display_plotly_chart(
                ds,
                ys,
                {"value": "kWh"},
                kind="bar",
                show_rangeslider=True,
                x_range=x_range,
            )

        st.subheader("Gennemsnitligt dagligt elforbrug i kWh")
        display_average_daily_use(c_df, year, ys)

        st.subheader("Gennemsnitsdage og - timer")

        col1, col2 = st.columns([0.5, 0.6])
        with col1:
            display_plotly_chart(
                df=get_weekday_average(c_df, year, ys),
                y="Ugedag",
                labels={"value": "kWh"},
                plot_kwargs=dict(x=ys, barmode="group", orientation="h"),
                kind="bar",
            )

        with col2:
            display_plotly_chart(
                get_hourly_average(c_df, year),
                y=ys,
                labels={"value": "kWh"},
                plot_kwargs=dict(x="Timer", barmode="group"),
                kind="bar",
            )

    with tab2:
        c_df = c_df.assign(
            totalforbrug=c_df["Elforbrug"] * (c_df["SpotPrice"] + c_df["Tarif"])
        )

        st.success(
            f"Årlig totale forbrug t.d.: {c_df.groupby(c_df.index.year).sum()['totalforbrug'][year]:.2f} DKK"
        )
        st.info(
            "Bemærk at de viste priser kun er elpris og tarif. Derudover kommer desuden både abonnement og transportgebyr ",
            icon="ℹ",
        )

        st.subheader("Månedlig elpris")
        day_basis = st.checkbox("Data på dagsbasis", key="")
        if not day_basis:
            df = get_monthly_sum(c_df)
            display_multiaxes_plotly_chart(
                df[df.index.year == year],
                "Elforbrug",
                "totalforbrug",
                "Elforrbug (kWh)",
                "Pris (DKK)",
                y2_name="Pris",
                kind="bar",
            )
        else:
            df = get_daily_use(c_df, year)
            display_multiaxes_plotly_chart(
                df,
                "Elforbrug",
                "totalforbrug",
                "Elforbrug (kWh)",
                "Pris (DKK)",
                y2_name="Pris",
                kind="bar",
            )

        st.subheader("Gennemsnitsdage og -timer")
        col1, col2 = st.columns([0.5, 0.6])
        with col1:
            df = get_weekday_average(c_df, year, ["SpotPrice", "Tarif"])
            df[["SpotPrice", "Tarif"]] = df[["SpotPrice", "Tarif"]].divide(24)

            display_plotly_chart(
                df,
                y="Ugedag",
                labels={"value": "DKK/h"},
                plot_kwargs=dict(
                    orientation="h", barmode="group", x=["SpotPrice", "Tarif"]
                ),
                kind="bar",
            )

        with col2:
            df = get_hourly_average(c_df, year)
            display_plotly_chart(
                df,
                y=["SpotPrice", "Tarif"],
                labels={"value": "DKK/h"},
                plot_kwargs=dict(barmode="group", x="Timer"),
                kind="bar",
            )

    st.subheader("❓ Bruger du strøm på de rigtige tidspunkter?")

    label = "Vælg periode"
    col1, col2 = st.columns((0.5, 0.5), gap="large")

    df = c_df[c_df.index.year == year].assign(pris=c_df["SpotPrice"] + c_df["Tarif"])

    with col1:
        resolution = st.selectbox("Tidsopløsning", ("År", "Måned", "Uge"), index=0)
    with col2:
        if resolution == "Måned":
            time = st.select_slider(
                label, map(lambda x: MONTH_NAMES[x.month], df.index)
            )
            time_idx = MONTH_NAMES.index(time)
            sub_df = df[df.index.month == time_idx]
        elif resolution == "Uge":
            df["weeknum"] = df.index.isocalendar().week
            time = st.select_slider(label, df["weeknum"].unique())
            sub_df = df[df["weeknum"] == time]
        else:
            sub_df = df

    df = px.data.tips()
    fig = px.histogram(
        sub_df[["pris", "Elforbrug"]],
        x="pris",
        labels={"pris": "Pris (DKK)", "y": "kWh"},
    )
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
