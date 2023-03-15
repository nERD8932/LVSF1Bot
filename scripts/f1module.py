from datetime import datetime
import logging

logging.getLogger().setLevel(logging.INFO)
logging.getLogger('discord').setLevel(logging.INFO)

dt_fmt = '%Y-%m-%d %H:%M:%S'
logging.basicConfig(format='[{asctime}] [{levelname:<8}] [{name:<15}]: {message}',
                    style='{',
                    datefmt='%Y-%m-%d %H:%M:%S')

dt_format_o = "%Y %Y-%m-%d %H:%M:%S"

import fastf1 as ff1
import os
import drivers
import requests

try:
    ff1.Cache.enable_cache("/ff1cache")
except NotADirectoryError:
    os.makedirs("/ff1cache", exist_ok=True)

drivers_table = drivers.drivers_table()
teams = ["Red Bull", "Ferrari", "Mercedes", "McLaren", "Alpine", "Alfa Romeo", "AlphaTauri", "Haas", "Aston Martin",
         "Williams"]

schedule = [datetime(2023, 3, 4, 20, 29),
            datetime(2023, 3, 18, 22, 29),
            datetime(2023, 4, 1, 10, 29),
            datetime(2023, 4, 29, 18, 59),
            datetime(2023, 5, 7, 1, 29),
            datetime(2023, 5, 20, 19, 29),
            datetime(2023, 5, 27, 19, 29),
            datetime(2023, 6, 3, 19, 29),
            datetime(2023, 6, 18, 1, 29),
            datetime(2023, 7, 1, 19, 59),
            datetime(2023, 7, 8, 19, 29),
            datetime(2023, 7, 22, 19, 29),
            datetime(2023, 7, 29, 19, 59),
            datetime(2023, 8, 26, 18, 29),
            datetime(2023, 9, 2, 19, 29),
            datetime(2023, 9, 16, 18, 29),
            datetime(2023, 9, 23, 11, 29),
            datetime(2023, 10, 7, 19, 59),
            datetime(2023, 10, 22, 3, 29),
            datetime(2023, 10, 29, 2, 29),
            datetime(2023, 11, 3, 23, 59),
            datetime(2023, 11, 18, 13, 29),
            datetime(2023, 11, 25, 19, 29)]


def returnNextEvent():
    next_event: ff1.events.EventSchedule = ff1.get_events_remaining().head(1)
    # logging.info(next_event.to_string())
    ne_round = next_event.iat[0, 0]
    ne_location = next_event.iat[0, 1]
    if ne_location == 'United States':
        ne_location = 'USA'
    ne_date = next_event.iat[0, 4]
    ne_name = next_event.iat[0, 5]
    ne_type = next_event.iat[0, 6]
    ne_session_data = {}

    for i in range(0, 5, 2):
        ne_session_data[next_event.iat[0, 7 + i]] = next_event.iat[0, 7 + i + 1]

    return {'round': ne_round,
            'loc': ne_location,
            'date': ne_date,
            'name': ne_name,
            'type': ne_type,
            'session': ne_session_data
            }


def returnCurrentRoundNum():
    next_event: ff1.events.EventSchedule = ff1.get_events_remaining().head(1)
    ne_round = next_event.iat[0, 0]
    # print(next_event)
    return ne_round


def returnEvent(identifier):
    se: ff1.events.Event = ff1.get_event(datetime.now().year, identifier)
    # print(se)

    ser = se.iat[0]
    sel = se.iat[1]
    sed = se.iat[4]
    sen = se.iat[5]
    sety = se.iat[6]

    if ser < returnCurrentRoundNum():
        return {'round': ser,
                'loc': sel,
                'date': sed,
                'name': sen,
                'type': sety,
                'results': drivers_table.results[str(ser)]
                }
    else:
        return {'round': ser,
                'loc': sel,
                'date': sed,
                'name': sen,
                'type': sety,
                }


def returnRoundsInYear(year=datetime.now().year):
    cal = ff1.events.get_event_schedule(year=year, include_testing=False).tail(1)
    return cal.iat[0, 0]


def returnGPQuali(pgp):
    if returnEvent(pgp)["type"] == "sprint":
        keyword = "sprint"
    else:
        keyword = "qualifying"

    url = f"https://ergast.com/api/f1/{datetime.now().year}/{pgp}/{keyword}.json"
    response = requests.get(url)
    data = response.json()["MRData"]["RaceTable"]["Races"]
    if len(data) == 0:
        return None
    else:
        return [dr["Driver"]["code"] for dr in data[0]["QualifyingResults"]]
        # return ["LEC", "VER", "HAM", "PER", "RUS", "NOR", "ALO", "OCO", "GAS", "ZHO"]


def returnRaceResults(r):
    url = f"https://ergast.com/api/f1/{datetime.now().year}/{r}/results.json"
    response = requests.get(url)
    data = response.json()["MRData"]["RaceTable"]["Races"]
    if len(data) == 0:
        return None
    else:
        return [dr["Driver"]["code"] for dr in data[0]["Results"]]


def verifyTeam(t):
    return t if t in teams else 'NaN'


# print(returnCurrentRoundNum())
