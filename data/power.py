import logging
import datetime as dt
import urllib
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

BASE_URL_CUSTOMERAPI = "https://api.eloverblik.dk/CustomerApi/api/"
BASE_URL_DATASET = "https://api.energidataservice.dk/dataset/"

logger = logging.getLogger(__name__)


def get_data_access_token(refresh_token):

    access_token_url = BASE_URL_CUSTOMERAPI + "token"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        response = requests.get(
            access_token_url,
            headers={"Authorization": f"Bearer {refresh_token}"},
            verify=False,
        )
    response.raise_for_status()
    data_access_token = response.json().get("result")

    return data_access_token


def get_meteringpoint_id(data_access_token):
    metering_points_url = BASE_URL_CUSTOMERAPI + "meteringpoints/meteringpoints"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        response = requests.get(
            metering_points_url,
            headers={"Authorization": f"Bearer {data_access_token}"},
            verify=False,
        )
    response.raise_for_status()
    result = response.json().get("result")
    metering_point_id = result[0].get("meteringPointId")
    return metering_point_id


def get_userinfo_detailed(
    meteringpoint_id=None, data_access_token=None, refresh_token=None
):
    if refresh_token is None and meteringpoint_id is None and data_access_token is None:
        raise Exception("Du som minimum skal give et refresh token")

    if data_access_token is None:
        logger.info("Getting a data access token")
        data_access_token = get_data_access_token(refresh_token)

    if meteringpoint_id is None:
        logger.info("Getting metering points")
        meteringpoint_id = get_meteringpoint_id(data_access_token)
    json_data = {"meteringPoints": {"meteringPoint": [f"{meteringpoint_id}"]}}

    userdetails = BASE_URL_CUSTOMERAPI + "meteringpoints/meteringpoint/getdetails"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        response = requests.post(
            userdetails,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {data_access_token}",
            },
            json=json_data,
            verify=False,
        )
    response.raise_for_status()
    result = response.json().get("result")[0].get("result")
    return result


def get_tarif_prices(userinfo, date_to, date_from):
    charge_owner = userinfo["gridOperatorName"]

    url = BASE_URL_DATASET + "datahubpricelist"

    params = (
        f"start={date_from}&"
        + f"end={date_to}&"
        + 'filter={"ChargeOwner":"'
        + charge_owner
        + '", "ResolutionDuration": "PT1H"}&'
        + "timezone=DK&"
        + "limit=1000"
    )

    payload_str = urllib.parse.quote(params, safe="=&")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        response = requests.get(
            url,
            headers={"Content-Type": "application/json"},
            verify=False,
            params=payload_str,
        )
    response.raise_for_status()
    return parse_tarif_prices_response(response.json())


def parse_tarif_prices_response(results: dict) -> pd.DataFrame:
    records = results["records"]
    df = pd.DataFrame(columns=["ValidFrom", "ValidTo", "Hour", "Tarif"])

    fmt = r"%Y-%m-%dT%X"
    to_datetime = lambda d: dt.datetime.strptime(d, fmt).date()

    dates = pd.date_range(
        to_datetime(records[0]["ValidFrom"]),
        to_datetime(records[0]["ValidTo"]) - dt.timedelta(days=1),
        freq="d",
    )

    index = 0
    for record in records:
        for hour in range(24):
            df2 = pd.DataFrame(
                index=[index],
                data={
                    "ValidFrom": to_datetime(record["ValidFrom"]),
                    "ValidTo": to_datetime(record["ValidTo"]),
                    "Hour": dt.time(hour),
                    "Tarif": record[f"Price{hour+1}"],
                },
            )
            df = pd.concat([df, df2])
            index += 1

    prices = []
    datetimes = []
    valid_groups = df.groupby(["ValidFrom", "ValidTo"])
    for group, idx in valid_groups.groups.items():
        subset = df.iloc[idx].groupby("Hour")["Tarif"].sum()
        dates = pd.date_range(
            group[0],
            group[1] - dt.timedelta(days=1),
            freq="d",
        )
        for date in dates:
            for hour in range(24):
                d = dt.datetime(date.year, date.month, date.day, hour)
                datetimes.append(d)
                prices.append(subset.iloc[hour])

    df_final = pd.DataFrame({"Tarif": prices}, index=datetimes)
    return df_final


def get_spot_prices(date_to, date_from, dk_west: bool = False) -> pd.DataFrame:
    url = BASE_URL_DATASET + "Elspotprices"
    area = "DK1" if dk_west else "DK2"

    params = (
        f"start={date_from}&"
        + f"end={date_to}&"
        + 'filter={"PriceArea":"'
        + area
        + '"}&'
        + "columns=HourDK,SpotPriceDKK&"
        + "timezone=DK&"
        + "limit=0"
    )

    payload_str = urllib.parse.quote(params, safe="=&")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        response = requests.get(
            url,
            headers={"Content-Type": "application/json"},
            verify=False,
            params=payload_str,
        )
    response.raise_for_status()
    return parse_spot_prices_response(response.json())


def parse_spot_prices_response(result: dict) -> pd.DataFrame:
    fmt = r"%Y-%m-%dT%X"
    datetimes = []
    prices = []
    for record in result["records"]:
        datetimes.append(dt.datetime.strptime(record["HourDK"], fmt))
        prices.append(record["SpotPriceDKK"] / 1000)

    df_prices = pd.DataFrame({"SpotPrice": prices}, index=datetimes)
    return df_prices


def get_power_usage(
    date_from: str = "2022-01-01",
    date_to: str = str(datetime.now().date()),
    dk_west: bool = False,
    refresh_token: str = None,
) -> pd.DataFrame:

    logger.info("Getting a data access token")
    data_access_token = get_data_access_token(refresh_token)

    logger.info("Getting metering points")
    metering_point_id = get_meteringpoint_id(data_access_token)

    json_data = {"meteringPoints": {"meteringPoint": [f"{metering_point_id}"]}}
    resolution = "Hour"  # "Hour" or "Day" or "Month"

    meter_data_url = (
        BASE_URL_CUSTOMERAPI
        + f"meterdata/gettimeseries/{date_from}/{date_to}/{resolution}"
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {data_access_token}",
    }

    logger.info(f"Getting meterdata using url {meter_data_url}")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        response = requests.post(
            meter_data_url, json=json_data, headers=headers, verify=False
        )
    response.raise_for_status()
    measurements = response.json().get("result")[0]

    timeseries = measurements["MyEnergyData_MarketDocument"]["TimeSeries"][0]
    period = timeseries["Period"]

    fmt = r"%Y-%m-%dT%XZ"

    dfs = []
    for point in period:
        quantities = [float(p["out_Quantity.quantity"]) for p in point["Point"]]
        date = datetime.strptime(point["timeInterval"]["end"], fmt)
        n_examples = min(24, len(quantities))
        times = [
            datetime(year=date.year, month=date.month, day=date.day, hour=i)
            for i in range(n_examples)
        ]
        dfs.append(
            pd.DataFrame(
                {"Elforbrug": quantities[:n_examples]}, index=pd.DatetimeIndex(times)
            )
        )
    df = pd.concat(dfs)

    logger.info("Getting prices")
    userinfo = get_userinfo_detailed(
        data_access_token=data_access_token, meteringpoint_id=metering_point_id
    )
    tarif_df = get_tarif_prices(userinfo, date_to=date_to, date_from=date_from)
    spotprice_df = get_spot_prices(
        date_to=date_to,
        date_from=date_from,
        dk_west=dk_west,
    )

    df = pd.merge(df, tarif_df, "left", left_index=True, right_index=True)
    df = pd.merge(df, spotprice_df, "left", left_index=True, right_index=True)
    # TODO: Figure out why tarif prices could be duplicated
    df = (
        df.reset_index().drop_duplicates(subset="index", keep="last").set_index("index")
    )

    return df
