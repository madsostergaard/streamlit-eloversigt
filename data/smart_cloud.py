import urllib
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

AQUAREA_SERVICE_BASE = "https://aquarea-smart.panasonic.com/"
AQUAREA_SERVICE_LOGIN = "remote/v1/api/auth/login"
AQUAREA_SERVICE_DEVICES = "remote/v1/api/devices"
AQUAREA_SERVICE_CONTRACT = "remote/contract"
AQUAREA_SERVICE_CONSUMPTION = "remote/v1/api/consumption"

_HEADERS = {
    "Cache-Control": "max-age=0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "deflate, br",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:74.0) Gecko/20100101 Firefox/74.0",
}

by_month = False
outputfile = Path("varmepumpedata.csv")


def aquarea_request(
    method: str,
    url: str,
    referer: str = AQUAREA_SERVICE_BASE,
    content_type: str = "application/x-www-form-urlencoded",
    raise_on_error: bool = True,
    **kwargs,
):

    # get the function
    fun = getattr(requests, method)

    headers = _HEADERS.copy()
    request_headers = kwargs.get("headers", {})
    headers.update(request_headers)
    headers["referer"] = referer
    headers["content-type"] = content_type
    kwargs["headers"] = headers

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        response = fun(AQUAREA_SERVICE_BASE + url, **kwargs)
    response.raise_for_status()

    if raise_on_error:
        data = response.json()

        if data["errorCode"] != 0:
            raise Exception(
                (f'{d["errorCode"]}: {d["errorMessage"]}' for d in data["message"])
            )

    return response


def get_heat_data(data_cfg: dict, date: datetime) -> pd.DataFrame:
    if "dateData" not in data_cfg:
        return None

    if isinstance(date, str):
        date = datetime.strptime(date, r"%Y-%m-%d")

    datasets: list = data_cfg["dateData"][0]["dataSets"]

    temp = "Outside"
    temp_data = []
    usage = "Heat"
    usage_data = []

    for dataset in [datasets[0], datasets[-1]]:
        for subset in dataset["data"]:
            if subset["name"] == temp:
                temp_data = subset["values"]
            elif subset["name"] == usage:
                usage_data = subset["values"]

    times = [
        datetime(year=date.year, month=date.month, day=date.day, hour=i)
        for i in range(24)
    ]
    df = pd.DataFrame(
        {"Temperatur": temp_data, "Forbrug": usage_data}, index=pd.DatetimeIndex(times)
    )

    return df


def get_smartcloud_data(
    username: str,
    password: str,
    date_from: str = "2022-01-01",
    date_to: str = pd.Timestamp.now().date(),
) -> pd.DataFrame:
    params = {
        "var.inputOmit": "false",
        "var.loginId": username,
        "var.password": password,
    }

    headers = _HEADERS.copy()
    headers["referer"] = AQUAREA_SERVICE_BASE

    data = urllib.parse.urlencode(params)

    # login
    response = aquarea_request(
        "post",
        AQUAREA_SERVICE_LOGIN,
        referer=AQUAREA_SERVICE_BASE,
        data=urllib.parse.urlencode(params),
        verify=False,
    )

    cookie = response.cookies

    # get device guid
    response = aquarea_request(
        "get", AQUAREA_SERVICE_DEVICES, cookies=cookie, verify=False
    )
    data = response.json()
    device_guid = [d["deviceGuid"] for d in data["device"]][0]

    # get long id
    long_id_cookie = cookie.copy()
    long_id_cookie["selectedGwid"] = device_guid[0]
    response = aquarea_request(
        "post",
        AQUAREA_SERVICE_CONTRACT,
        referer=AQUAREA_SERVICE_BASE,
        cookies=long_id_cookie,
        raise_on_error=False,
        verify=False,
    )
    device_id = response.cookies.get("selectedDeviceId")

    # get consumption
    dates = pd.date_range(date_from, date_to, freq="D")
    dataframes = []

    for date in dates:
        c_cookie = cookie.copy()
        c_cookie["selectedDeviceId"] = device_id
        c_cookie["selectedGwid"] = device_guid
        request_date = str(date.date())
        response = aquarea_request(
            "get",
            f"{AQUAREA_SERVICE_CONSUMPTION}/{device_id}?date={request_date}",
            verify=False,
            cookies=c_cookie,
            referer="https://aquarea-smart.panasonic.com/remote/a2wEnergyConsumption",
            content_type="application/json",
        )
        data = response.json()
        dataframes.append(get_heat_data(data, date))

    return pd.concat(dataframes)
