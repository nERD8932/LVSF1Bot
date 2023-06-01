import json
import copy
import logging
from collections import OrderedDict
import os


class Table:
    def __init__(self, guild_id, rounds=23, load_from_file=False):

        self.guild_id = str(guild_id)
        self.reminder_channel_id = '0'
        self.twitter_channel_id = '0'
        self.table = {'tags': ['UserID']}
        self.members = {}
        self.print_table = []
        self.rounds = rounds
        self.user_values = 5
        self.mottos = {}

        if load_from_file:
            self.loadTable(guild_id)
        else:
            for i in range(rounds):
                self.table['tags'].append(f'R{i + 1}')
            self.print_table = self.returnPrintableTable()

    def addUser(self, uid):
        uid = str(uid)
        user_val_init = [0]
        self.members[uid] = 0
        self.mottos[uid] = "The one and only!"
        for i in range(self.user_values):
            user_val_init.append('NaN')
        append_list = [uid]
        for i in range(self.rounds):
            append_list.append(copy.deepcopy(user_val_init))
        self.table[uid] = append_list
        self.print_table = self.returnPrintableTable()
        self.updateLocalTable()

    def updateTableVals(self):
        for mb in self.members.keys():
            self.members[str(mb)] = self.returnUserPoints(mb)
        self.members = dict(sorted(self.members.items(), key=lambda x: x[1], reverse=True))

    def updateLocalTable(self):
        glp = f'guildLeagues/{self.guild_id}.json'
        glbp = f'guildLeagues/{self.guild_id}_backup.json'
        if os.path.exists(glp):
            if os.path.exists(glbp):
                os.remove(glbp)
            os.rename(glp, glbp)
        with open(glp, "w") as outfile:
            json.dump(self.__dict__, outfile, indent=4)

    def loadTable(self, gid):
        temp = json.load(open(f'guildLeagues/{self.guild_id}.json', 'r'))
        self.guild_id = temp['guild_id']
        self.reminder_channel_id = temp['reminder_channel_id']
        self.twitter_channel_id = temp['twitter_channel_id']
        self.members = temp['members']
        self.table = temp['table']
        self.print_table = temp['print_table']
        self.rounds = temp['rounds']
        self.user_values = temp['user_values']
        self.mottos = temp['mottos']

    def returnUserPoints(self, uid):
        uid = str(uid)
        # if uid == "244873578175004672":
        #     return -420
        psum = 0
        for j in self.table[uid][1:]:
            psum += j[0]
        return psum

    def orderTable(self):
        self.updateTableVals()
        tempt = copy.deepcopy(self.table)
        for mb in self.members:
            self.table.pop(mb)

        for mb in self.members:
            self.table[mb] = tempt[mb]

        self.updateLocalTable()

    def returnUserRank(self, uid):
        i = 0
        uid = str(uid)
        for user in self.members.items():
            if uid == user[0]:
                return i + 1
            i += 1

    def returnPrintableTable(self):
        # Truncating driver vals
        tt = list(self.table.values())
        pt = [['Round#/Squad Manager'] + copy.deepcopy(tt[0][1:]) + ['Total Tally', 'Squad Manager']]
        # print(pt)
        for i in range(1, len(tt)):
            pt.append(copy.deepcopy(tt[i]))
            for j in range(1, len(pt[i])):
                pt[i][j] = pt[i][j][0]

            pt[i] = pt[i] + [self.members[pt[i][0]], pt[i][0]]

        return pt

    def printVals(self):
        logging.info("Table Vals: \n")
        print("Guild ID: ", self.guild_id)
        print("Reminder")
        print("Members: ", self.members.values())
        print("Table: ", self.table)
        print("Rounds: ", self.rounds)
        print("UVals: ", self.user_values)

# table = Table(123, 4, 5, False)
# table.addUser(456)
# table.printVals()
# table.updateLocalTable()
#
# table2 = Table(123, load_from_file=True)
# table2.printVals()
