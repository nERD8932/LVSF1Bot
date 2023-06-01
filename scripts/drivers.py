import datetime
import logging
import os
import requests
from unidecode import unidecode
import fastf1 as ff1
import json

try:
    ff1.Cache.enable_cache("/ff1cache")
except NotADirectoryError:
    os.makedirs("/ff1cache", exist_ok=True)


class Driver:
    def __init__(self, fn, ln, number, team, color, rank, points, wins, nationality, podiums):
        self.nationality = nationality
        self.firstname = unidecode(fn)
        self.lastname = unidecode(ln)
        self.full_name = fn + " " + ln
        self.tla = self.lastname[0:3].upper()
        if self.tla == 'LAT':
            self.tla = 'LAF'
        self.team = team
        self.team_color = color
        self.number = number
        self.season_points = points
        self.rank = rank
        self.podiums = podiums
        self.wins = wins
        self.urlnumber = 2 if self.tla == 'SCH' else 1
        self.pf_img_url = f'https://www.formula1.com/content/dam/fom-website/drivers/{self.firstname[0].upper()}/' \
                          f'{self.firstname[0:3].upper()}{self.tla}0{self.urlnumber}_{self.firstname}_' \
                          f'{self.lastname}/{self.firstname[0:3].lower()}{self.tla.lower()}0{self.urlnumber}.png'
        if self.tla == 'SCH':
            self.tla = 'MSC'

    def todict(self):
        return {'nationality': self.nationality,
                'firstname': self.firstname,
                'lastname': self.lastname,
                'full_name': self.full_name,
                'tla': self.tla,
                'team': self.team,
                'team_color': self.team_color,
                'number': self.number,
                'season_points': self.season_points,
                'rank': self.rank,
                'podiums': self.podiums,
                'wins': self.wins,
                'pf_img_url': self.pf_img_url
                }


class drivers_table:
    def __init__(self):
        self.drivers = {}
        self.results = {}
        self.quali_results = {}
        self.teamcolors = {}
        if os.path.exists('drivers/drivers.json'):
            self.loadDriverTable()
        else:
            self.constructDriversFromApi(datetime.datetime.now().year)
            self.updateDriverTable()

    @staticmethod
    def get_drivers_standings():
        url = f"https://ergast.com/api/f1/{datetime.datetime.now().year}/driverStandings.json"
        response = requests.get(url)
        data = response.json()
        drivers_standings = data['MRData']['StandingsTable']['StandingsLists'][0]
        return drivers_standings['DriverStandings']

    def constructDriversFromApi(self, year):
        ergastdata, lr = self.get_drivers_standings()
        for r in range(1, lr + 1):
            event: ff1.events.Event = ff1.get_event(year, r)
            sess: ff1.events.Session = event.get_race()
            sess.load()
            self.results[str(r)] = sess.results['Abbreviation'].tolist()
            if len(self.teamcolors) == 0:
                self.teamcolors = dict(zip(self.results[str(r)], sess.results['TeamColor'].tolist()))
            else:
                for n, m in enumerate(self.results[str(r)]):
                    if self.teamcolors.get(m) is None:
                        self.teamcolors[m] = sess.results['TeamColor'].tolist()[n]

        for d in ergastdata:
            # print(d['Driver']['code'])
            podiums = 0
            for result in self.results.values():
                if d['Driver']['code'] in result[0:3]:
                    podiums += 1
            self.drivers[d['Driver']['code']] = Driver(d['Driver']['givenName'],
                                                       d['Driver']['familyName'],
                                                       d['Driver']['permanentNumber'],
                                                       d['Constructors'][0]['name'],
                                                       self.teamcolors[d['Driver']['code']],
                                                       d['positionText'],
                                                       d['points'],
                                                       d['wins'],
                                                       d['Driver']['nationality'],
                                                       str(podiums)).todict()

    def addDriver(self, fn, ln, number, team, color, rank, points, wins, nationality, podiums):
        self.drivers[self.returnDriverTLA(fn)] = Driver(fn, ln, number, team, color, rank, points, wins, nationality,
                                                        podiums)
        self.updateDriverTable()

    def updateDriverTable(self):
        glp = f'drivers/drivers.json'
        glbp = f'drivers/drivers_backup.json'
        if os.path.exists(glp):
            if os.path.exists(glbp):
                os.remove(glbp)
            os.rename(glp, glbp)
        with open(glp, "w") as outfile:
            json.dump(self.__dict__, outfile)

    def loadDriverTable(self):
        temp = json.load(open(f'drivers/drivers.json', 'r'))
        self.drivers = temp['drivers']
        self.results = temp['results']
        self.quali_results = temp['quali_results']
        # print(self.results)
        self.teamcolors = temp['teamcolors']

    def returnDriverTLA(self, identifier):
        found_dr = 'NaN'
        identifier = identifier.lower()
        dlist = list(self.drivers.values())
        for i in range(len(dlist)):
            if dlist[i]['firstname'].lower() == identifier or \
                    dlist[i]['lastname'].lower() == identifier or \
                    dlist[i]['full_name'].lower() == identifier or \
                    dlist[i]['tla'].lower() == identifier or \
                    dlist[i]['number'] == identifier:
                found_dr = dlist[i]['tla']
                break
        return found_dr


