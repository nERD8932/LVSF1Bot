import random
import tracemalloc
import jinja2

tracemalloc.start()
#
# for Mem debug purposes, will be commented out in final build
#

import f1module as fom
import logging
from datetime import datetime, timedelta
import os
import discord
from discord.ext import commands
import pandas as pd
from dotenv import load_dotenv
import dbv2 as db
import imgkit
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import itertools

imgk_config = imgkit.config(wkhtmltoimage='wkhtmltopdf/bin/wkhtmltoimage.exe')

imgk_options = {'enable-local-file-access': None}

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

dt_fmt = '%Y-%m-%d %H:%M:%S'

frmt = logging.Formatter('[{asctime}] [{levelname:<8}] [{name:<15}]: {message}',
                         datefmt='%Y-%m-%d %H:%M:%S',
                         style='{')
logging.basicConfig(format='[{asctime}] [{levelname:<8}] [{name:<15}]: {message}',
                    datefmt='%Y-%m-%d %H:%M:%S', style='{', force=True)
handler = logging.FileHandler(
    filename=f'{str(os.getcwd() + "/logs/")}log_{len(os.listdir(str(os.getcwd() + "/logs/"))) + 1}.log',
    encoding='utf-8')

handler.setFormatter(frmt)

disc_logger = logging.getLogger('discord')
disc_logger.setLevel(logging.INFO)
disc_logger.addHandler(handler)

default_logger = logging.getLogger()
default_logger.setLevel(logging.INFO)
default_logger.addHandler(handler)

##############################################################################
#
#   Intents
#
##############################################################################
intents = discord.Intents.none()

intents.messages = True
intents.reactions = True
intents.guilds = True
intents.members = True
intents.message_content = True
intents.emojis_and_stickers = True
intents.guild_scheduled_events = True

##############################################################################
#
#   Utility variables
#
##############################################################################
active_leagues = {}
lfd = str(os.getcwd() + '/guildLeagues/')
bot = commands.Bot(command_prefix='?', intents=intents, help_command=None)
fsel = 5

help_filter = ['close',
               'adduservar',
               'test',
               'registertweetschannel',
               'registerreminderschannel',
               'deregisterchannel',
               'update',
               'sendmessage',
               'sendembed',
               'maintenance']

dt_format_c = "%A, %B %d,  %#I%p"
dt_format_o = "%Y %Y-%m-%d %H:%M:%S"
cyear = datetime.now().year
scheduler = AsyncIOScheduler()

points_seq = [22, 18, 15, 12, 10, 8, 6, 4, 2, 1]
wildcard_qp = 2
wildcard_rp = 3
construct_points = [5, 4, 3, 2, 1]

# print(points_seq)


# tw_follow = ['69008563', '87541152', '1348954901423022082', '1579926101111238658']

optout = []


##############################################################################
#
#   On Ready function, executed when bot establishes a connection to discord
#
##############################################################################
@bot.event
async def on_ready():
    await bot.tree.sync()
    logging.info(f'Bot user {bot.user.name} logged in with ID: ({bot.user.id}).')
    logging.info(f'Available commands: ')
    for command in [str((" " * 10) + c.name + ":" + (" " * (30 - len(c.name))) + c.description) for c in
                    bot.tree.get_commands()]:
        logging.info(command)
    print('')
    os.makedirs(lfd, exist_ok=True)
    await setReminders()
    logging.info(f'Active Leagues: ')
    for league in os.listdir(lfd):
        print('')
        if '_backup' not in league:
            gid = league[0:len(league) - fsel]
            active_leagues[gid] = db.Table(gid, load_from_file=True)
            active_leagues[gid].orderTable()
            logging.info(f'{bot.get_guild(int(gid)).name} '
                         f'with members: {[bot.get_user(int(uid)).name for uid in active_leagues[gid].members.keys()]}')
            if active_leagues[gid].reminder_channel_id != '0':
                try:
                    logging.info(f'Reminder Channel: '
                                 f'{bot.get_channel(int(active_leagues[gid].reminder_channel_id)).name}')
                except AttributeError:
                    active_leagues[gid].reminder_channel_id = '0'
            if active_leagues[gid].twitter_channel_id != '0':
                try:
                    logging.info(f'Twitter Channel: '
                                 f'{bot.get_channel(int(active_leagues[gid].twitter_channel_id)).name}')
                except AttributeError:
                    active_leagues[gid].twitter_channel_id = '0'

    print('-------------------------------------------------------------------------------------------------------'
          '------------------------------------------------------------------------------------------------------\n')


def twitterPrint(tweet):
    em_txt = tweet['text'] + '\n\n'

    if len(tweet['vid_urls']) > 0:
        em_txt = em_txt + '[video]' + '(' + tweet['vid_urls'][0][0] + ')'

    if len(tweet['web_urls']) > 0:
        em_txt = em_txt + '[link]' + '(' + tweet['web_urls'][0] + ')'

    embed = discord.Embed(color=discord.Color.red(),
                          title='\u200b',
                          description=em_txt)
    embed.set_author(name=f'{tweet["name"]} (@{tweet["username"]})')

    if len(tweet['img_urls']) > 0:
        embed.set_image(url=tweet['img_url'][0])

    for league in active_leagues.values():
        if league.twitter_channel_id != '0':
            if bot.get_channel(int(league.twitter_channel_id)) is not None:
                bot.loop.create_task(bot.get_channel(int(league.twitter_channel_id)).send(embed=embed))


##############################################################################
#
#   On Message function, executed when a message is sent to the server, or when DM'ed
#
##############################################################################
@bot.event
async def on_message(message: discord.Message):
    author = message.author
    content = message.content
    if author.id != bot.user.id:
        logging.info(f'Author: {author} ({author.id}), Message: {content}\n')
        await bot.process_commands(message)


##############################################################################
#
#   Register slash command function, executed /register is used
#
##############################################################################
@bot.tree.command(name="register", description="Register yourself for the fantasy league")
async def register(interaction: discord.Interaction):
    await interaction.response.defer()
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if interaction.guild is None:
        await interaction.followup.send("Please perform this command on a server with an active league!")
    else:
        if active_leagues.get(str(interaction.guild.id)) is None:
            logging.info(f'Invalid exec error by {interaction.user} in {interaction.guild.name}.')
            await interaction.followup.send(
                "**There is no active league started on this server!** To start one, "
                "ask an admin to use the **/startleague** command")
        else:
            await init_user(interaction)


async def checkinvalidity(team, usr, cgp):
    invalid = False
    if len(set(team)) != len(team):
        invalid = True
    else:
        if cgp > 1:
            # print(str(cgp - 1))
            qualires = fom.returnGPQuali(cgp - 1)

            if fom.drivers_table.results.get(str(cgp - 1)) is not None and qualires is not None:
                constquali = [result for result in qualires if
                              fom.drivers_table.drivers[usr[cgp - 1][2]]["team"] == fom.drivers_table.drivers[result][
                                  "team"]]
                constrace = [result for result in fom.drivers_table.results[str(cgp - 1)] if
                             fom.drivers_table.drivers[usr[cgp - 1][2]]["team"] == fom.drivers_table.drivers[result][
                                 "team"]]
                if fom.drivers_table.results[str(cgp - 1)][0] in usr[cgp - 1] and \
                        fom.drivers_table.results[str(cgp - 1)][0] in team:
                    invalid = True

                elif len(constrace) > 0 and len(constquali) > 0:
                    if constrace[0] == team[1] or constquali[0] == team[1]:
                        invalid = True

                elif cgp > 2:
                    for dr in team:
                        if dr in usr[cgp - 1] and usr[cgp - 2]:
                            invalid = True
                        break
            else:
                logging.info("Quali or race result not found for invalidity check")

        if team[0] not in [fom.drivers_table.drivers[dr]["team"] for dr in team[1:]]:
            invalid = True

    return invalid


@bot.tree.command(name="draft_phone",
                  description="Android/iOS draft command; Note: (pick order: Pick1, Pick2, Pick3, Wildcard, Constructor)")
async def draft_phone(interaction: discord.Interaction, picks: str):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    team = picks.split(",")
    if len(team) != 5:
        interaction.response.send_message("Invalid team length, try again.")
    else:
        await draftbase(interaction, team[0], team[1], team[2], team[3], team[4])


@bot.tree.command(name="draft", description="Pick your team for the current GP")
async def draft(interaction: discord.Interaction, pick_1: str, pick_2: str, pick_3: str, wildcard: str,
                constructor: str):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    await draftbase(interaction, pick_1, pick_2, pick_3, wildcard, constructor)


async def draftbase(interaction: discord.Interaction, pick_1: str, pick_2: str, pick_3: str, wildcard: str,
                    constructor: str):
    if interaction.guild is None:
        await interaction.response.send_message("Please perform this command on a server with an active league!")
    else:
        if active_leagues.get(str(interaction.guild.id)) is None:
            logging.info(f'Invalid exec error by {interaction.user} in {interaction.guild.name}.')
            await interaction.response.send_message(
                "**There is no active league started on this server!** To start one, "
                "ask an admin to use the **/startleague** command", ephemeral=True)
        elif active_leagues.get(str(interaction.guild.id)).table.get(str(interaction.user.id)) is None:
            await interaction.response.send_message(
                "**You have not yet registered for the league!**, use /register first",
                ephemeral=True)
        # elif active_leagues[str(interaction.guild.id)].table[str(interaction.user.id)][1][2] != 'NaN':
        #     print('NotNaN')
        #     await interaction.response.send_message("**You've already selected your team!!**", ephemeral=True)
        else:
            await interaction.response.defer(ephemeral=True)

            cgp = fom.returnCurrentRoundNum()

            if cgp > 1:
                qualiresults = fom.returnGPQuali(cgp - 1)
            else:
                qualiresults = None

            # print(cgp)
            if cgp > 1 and fom.schedule[cgp - 2] < datetime.now() < (fom.schedule[cgp - 2] + timedelta(days=3)):
                ne = fom.returnNextEvent()
                window = fom.schedule[cgp - 2] + timedelta(days=3)
                await interaction.followup.send(f"The pick window is currently closed; it will re-open on "
                                                f"{await returnFormattedTime(window)}"
                                                f" for the {ne['name']}.")
            else:
                team = [fom.verifyTeam(constructor),
                        fom.drivers_table.returnDriverTLA(wildcard),
                        fom.drivers_table.returnDriverTLA(pick_1),
                        fom.drivers_table.returnDriverTLA(pick_2),
                        fom.drivers_table.returnDriverTLA(pick_3)]

                if 'NaN' in team:
                    await interaction.followup.send("One or more driver or constructor was not detected by the "
                                                    "database. (try using the driver TLA instead)")
                elif len(set(team)) != len(team):
                    embed = discord.Embed(title='...you little sh-',
                                          description="You can't pick the same driver twice; but "
                                                      "you already knew that didn't you? Do you "
                                                      "realise I have to add an if-else statement "
                                                      "somewhere or the "
                                                      "other for every dumb-ass cases like this? "
                                                      "Congratulations, you increased the number of "
                                                      "lines of code "
                                                      "I had to write by ten lines; are you proud of "
                                                      "yourself?  Now, unless you want to clone { "
                                                      "insert_driver_name} and convince the FiA to "
                                                      "let them race this season under the same name, "
                                                      "team, "
                                                      "number and TLA, I suggest you pick another "
                                                      "driver. Punk.",
                                          color=discord.Color.red())
                    await interaction.followup.send(embed=embed, ephemeral=True)

                else:
                    # if active_leagues[str(interaction.guild.id)].table[str(interaction.user.id)][cgp][1] != 'NaN':
                    # await interaction.response.send_message("You have already picked your team for this GP!", ephemeral=True)
                    invalid = False
                    if cgp > 1:

                        raceconst = list(result for result in fom.drivers_table.results[str(cgp - 1)] if
                                         fom.drivers_table.drivers[
                                             active_leagues[str(interaction.guild.id)].table[str(interaction.user.id)][
                                                 cgp - 1][2]]["team"] == fom.drivers_table.drivers[result]["team"])

                        if fom.drivers_table.results[str(cgp - 1)][0] in \
                                active_leagues[str(interaction.guild.id)].table[str(interaction.user.id)][cgp - 1] and \
                                fom.drivers_table.results[str(cgp - 1)][0] in team:
                            invalid = True
                            await interaction.followup.send(
                                "The winner of the last GP was in your previous team; you cannot pick that driver for this GP!",
                                ephemeral=True)

                        elif len(raceconst) > 0:
                            if raceconst[0] == team[1]:
                                invalid = True
                                await interaction.response.send_message(
                                    "Your wildcard's exhausted! Pick a different driver!",
                                    ephemeral=True)

                        elif qualiresults is not None:
                            qualiconst = list(result for result in qualiresults if fom.drivers_table.drivers[
                                active_leagues[str(interaction.guild.id)].table[str(interaction.user.id)][
                                    cgp - 1][2]]["team"] == fom.drivers_table.drivers[result]["team"])
                            if len(qualiconst) > 0:
                                if qualiconst[0] == team[1]:
                                    invalid = True
                                    await interaction.followup.send(
                                        "Your wildcard's exhausted! Pick a different driver!")

                        elif cgp > 2:
                            for dr in team:
                                if dr in active_leagues[str(interaction.guild.id)].table[str(interaction.user.id)][
                                    cgp - 1] and \
                                        active_leagues[str(interaction.guild.id)].table[str(interaction.user.id)][
                                            cgp - 2]:
                                    invalid = True
                                    await interaction.followup.send(
                                        "You can't pick exhausted drivers/constructors! Use /team to check what in "
                                        "your team is exhausted.")
                                break

                    if team[0] not in [fom.drivers_table.drivers[dr]["team"] for dr in team[1:]]:
                        invalid = True
                        await interaction.followup.send("You need to have atleast one driver from your "
                                                        "chosen constructor in your team!")

                    # print(invalid)
                    if not invalid:
                        # print("lmao")
                        tempv = active_leagues[str(interaction.guild.id)].table[str(interaction.user.id)][cgp]
                        for i in range(5):
                            # print(tempv, team[i])
                            tempv[1 + i] = team[i]
                        active_leagues[str(interaction.guild.id)].orderTable()
                        await interaction.followup.send("Picks saved!")


@bot.tree.command(name="sendmessage", description="Send Message")
async def sendmessage(interaction: discord.Interaction, message: str):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if not await bot.is_owner(interaction.user):
        logging.info(f'Invalid exec error by {interaction.user} in {interaction.guild.name}.')
        await interaction.response.send_message("You are not authorized to run this command.", ephemeral=True)
    else:
        await bot.get_channel(interaction.channel_id).send(content=message)
        await interaction.response.send_message("Sent!", ephemeral=True)


@bot.tree.command(name="sendembed", description="Send Embed")
async def sendembed(interaction: discord.Interaction, em_title: str, em_message: str, text: str):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if not await bot.is_owner(interaction.user):
        logging.info(f'Invalid exec error by {interaction.user} in {interaction.guild.name}.')
        await interaction.response.send_message("You are not authorized to run this command.", ephemeral=True)
    else:
        embed = discord.Embed(title=em_title,
                              description=em_message,
                              color=discord.Color.red())
        await bot.get_channel(interaction.channel_id).send(content=text, embed=embed)
        await interaction.response.send_message("Sent!", ephemeral=True)


@bot.tree.command(name="update", description="Update the season round and scores")
async def update(interaction: discord.Interaction, txtresult: str = "parse", txtquali: str = "parse",
                 podiums: bool = True):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    await interaction.response.defer()
    if interaction.guild is None:
        await interaction.followup.send("Please perform this command on a server with an active league!")
    else:
        if active_leagues.get(str(interaction.guild.id)) is None:
            logging.info(f'Invalid exec error by {interaction.user} in {interaction.guild.name}.')
            await interaction.followup.send(
                "**There is no active league started on this server!** To start one, "
                "ask an admin to use the **/startleague** command")

        elif not await bot.is_owner(interaction.user):
            logging.info(f'Invalid exec error by {interaction.user} in {interaction.guild.name}.')
            await interaction.followup.send("You are not authorized to run this command.", ephemeral=True)
        else:

            pgp = fom.returnCurrentRoundNum() - 1
            embed = discord.Embed(title="[Points Breakdown]", description="", color=discord.Color.red())
            try:
                dvrpoints = {dr['Driver']['code']: dr['points'] for dr in fom.drivers_table.get_drivers_standings()}
                # print(dvrpoints)
                dvrwins = {dr['Driver']['code']: dr['wins'] for dr in fom.drivers_table.get_drivers_standings()}
                dvrrank = {dr['Driver']['code']: dr['position'] for dr in fom.drivers_table.get_drivers_standings()}

                for dr in dvrpoints.keys():
                    if fom.drivers_table.drivers.get(dr) is not None:
                        fom.drivers_table.drivers[dr]['season_points'] = dvrpoints[dr]
                        fom.drivers_table.drivers[dr]['wins'] = dvrwins[dr]
                        fom.drivers_table.drivers[dr]['rank'] = dvrrank[dr]

                if podiums:
                    for i in range(3):
                        fom.drivers_table.drivers[fom.drivers_table.results[str(pgp)][i]]['podiums'] = str(
                            int(fom.drivers_table.drivers[fom.drivers_table.results[str(pgp)][i]]['podiums']) + 1)

                await fom.drivers_table.updateDriverTable()

            except Exception:
                logging.info("Something went wrong with the driver point assignment.")

            # print(pgp)
            if pgp > 0:
                # Grabbing race and quali results
                if txtresult == "parse":
                    prr = fom.returnRaceResults(pgp)
                else:
                    prr = txtresult.split(" ")
                if txtquali == "parse":
                    prq = fom.returnGPQuali(pgp)
                else:
                    prq = txtresult.split(" ")


                # prr = ["LEC", "VER", "HAM", "PER", "RUS", "NOR", "ALO", "OCO", "GAS", "ZHO"]
                # prq = ["LEC", "VER", "HAM", "PER", "RUS", "NOR", "ALO", "OCO", "GAS", "ZHO"]

                # Calculating constructor winner based off our points allcoation
                constructors = {}
                for index, dr in enumerate(itertools.islice(prr, 10)):
                    try:
                        if constructors.get(fom.drivers_table.drivers[dr]['team']) is None:
                            constructors[fom.drivers_table.drivers[dr]['team']] = points_seq[index]
                        else:
                            constructors[fom.drivers_table.drivers[dr]['team']] += points_seq[index]
                    except ValueError:
                        logging.info("Driver not found in driver database while calculating constructor!")

                constructors = dict(sorted(constructors.items(), key=lambda x: x[1], reverse=True))
                for index, val in enumerate(itertools.islice(constructors, 5)):
                    constructors[val] = 5 - index

                if prr is not None and prq is not None:
                    if fom.drivers_table.results.get(str(pgp)) is None:
                        fom.drivers_table.results[str(pgp)] = prr
                    if fom.drivers_table.quali_results.get(str(pgp)) is None:
                        fom.drivers_table.quali_results[str(pgp)] = prq

                    breakdown = {}

                    # just restting the member points values for this gp to 0, and adding constructor points
                    for mem in active_leagues[str(interaction.guild.id)].members:
                        active_leagues[str(interaction.guild.id)].table[mem][pgp][0] = 0

                        # randomizing picks for people who didn't draft in time
                        if active_leagues[str(interaction.guild.id)].table[mem][pgp][1] == 'NaN':
                            randteam = random.sample(list(fom.drivers_table.drivers.keys()), 4)
                            randteam.insert(0, fom.drivers_table.drivers[random.choice(randteam)]['team'])
                            # print(randteam, active_leagues[str(interaction.guild.id)].table[mem], pgp)
                            while not await checkinvalidity(randteam,
                                                            active_leagues[str(interaction.guild.id)].table[mem], pgp):
                                randteam = random.sample(list(fom.drivers_table.drivers.keys()), 4)
                                randteam.insert(0, fom.drivers_table.drivers[random.choice(randteam[1:])]['team'])
                            for i in range(1, 6):
                                active_leagues[str(interaction.guild.id)].table[mem][pgp][i] = randteam[i - 1]

                        if constructors.get(active_leagues[str(interaction.guild.id)].table[mem][pgp][1]) is not None:
                            active_leagues[str(interaction.guild.id)].table[mem][pgp][0] += constructors[
                                active_leagues[str(interaction.guild.id)].table[mem][pgp][1]]
                        breakdown[bot.get_user(int(mem)).name] = str(
                            constructors[active_leagues[str(interaction.guild.id)].table[mem][pgp][1]]) + "C "
                        # print(mem, constructors[active_leagues[str(interaction.guild.id)].table[mem][pgp][1]])

                    for i in range(20):
                        for mem in active_leagues[str(interaction.guild.id)].members:
                            if i < 10 and prr[i] in active_leagues[str(interaction.guild.id)].table[mem][pgp][3:]:
                                active_leagues[str(interaction.guild.id)].table[mem][pgp][0] += points_seq[i]
                                breakdown[bot.get_user(int(mem)).name] = breakdown[
                                                                             bot.get_user(int(mem)).name] + "+" + str(
                                    points_seq[i]) + "P "
                                # print(bot.get_user(int(mem)).name + ": +" + str(points_seq[i]))

                            if prr[i] == active_leagues[str(interaction.guild.id)].table[mem][pgp][2]:
                                constrace = [dr for dr in prr if fom.drivers_table.drivers[dr]['team'] ==
                                             fom.drivers_table.drivers[
                                                 active_leagues[str(interaction.guild.id)].table[mem][pgp][2]]['team']]
                                if len(constrace) > 0:
                                    if constrace[0] == active_leagues[str(interaction.guild.id)].table[mem][pgp][2]:
                                        active_leagues[str(interaction.guild.id)].table[mem][pgp][0] += wildcard_rp
                                        breakdown[bot.get_user(int(mem)).name] = breakdown[
                                                                                     bot.get_user(
                                                                                         int(mem)).name] + "+" + str(
                                            wildcard_rp) + "WR "

                            if prq[i] == active_leagues[str(interaction.guild.id)].table[mem][pgp][2]:
                                constquali = [dr for dr in prq if
                                              fom.drivers_table.drivers[dr]['team'] == fom.drivers_table.drivers[
                                                  active_leagues[str(interaction.guild.id)].table[mem][pgp][2]]['team']]
                                if len(constquali) > 0:
                                    if constquali[0] == active_leagues[str(interaction.guild.id)].table[mem][pgp][2]:
                                        active_leagues[str(interaction.guild.id)].table[mem][pgp][0] += wildcard_qp
                                        breakdown[bot.get_user(int(mem)).name] = breakdown[
                                                                                     bot.get_user(
                                                                                         int(mem)).name] + "+" + str(
                                            wildcard_qp) + "WQ "

                    for user in breakdown:
                        embed.add_field(name=user, value=breakdown[user], inline=False)
                    active_leagues[str(interaction.guild.id)].orderTable()
                    fom.drivers_table.updateDriverTable()
                    await setReminders()
                else:
                    logging.log(level=3, msg="Race results not found during update sequence! try re-running the bot")
                    exit()
            await interaction.followup.send("Updated.", embed=embed, ephemeral=True)


async def reminder(timeleft):
    ne = fom.returnNextEvent()
    cr = fom.returnCurrentRoundNum()
    qualitime = fom.schedule[cr - 1]

    if timeleft == "windowopen":
        embed = discord.Embed(title='Reminder!', description=f'The pick window for the **{ne["name"]}** is now open!\n'
                                                             f'Remember to draft your team before the '
                                                             f'qualifying starts!', color=discord.Color.red())
        msg_embed = discord.Embed(title='Reminder!',
                                  description=f"The pick window for the **{ne['name']}** is now open! Draft your picks using"
                                              f"/draft at the earliest.",
                                  color=discord.Color.red())
    elif timeleft == "notdrafted":
        embed = None
        msg_embed = discord.Embed(title='Reminder!',
                                  description=f"Since you had forgotten to draft your picks for the **{ne['name']}**"
                                              f", you will be assigned a random team. (if you wish to stop recieving "
                                              f"these reminders, message the developer @nERD)",
                                  color=discord.Color.red())
    else:
        if datetime.now() > qualitime:
            embed = discord.Embed(title='Reminder!', description=f'The {ne["name"]} race starts in '
                                                                 f'{timeleft}! Best of luck!',
                                  color=discord.Color.red())
            msg_embed = None
        else:

            embed = discord.Embed(title='Reminder!', description=f'The {ne["name"]} qualifying session starts in '
                                                                 f'{timeleft}!\nRemember to draft your team before '
                                                                 f'it starts!', color=discord.Color.red())
            embed.add_field(name=f'',
                            value='',
                            inline=False)

            msg_embed = discord.Embed(title='Reminder!',
                                      description=f"The **{ne['name']}** qualifying session starts in "
                                                  f"{timeleft}. You haven't drafted your picks for the "
                                                  f"upcoming event. Do so by using the /draft command at the earliest."
                                                  f" (if you wish to stop recieving these reminders, contact the "
                                                  f"developer @nERD)",
                                      color=discord.Color.red())

    for league in active_leagues.values():
        if league.reminder_channel_id != '0':
            if bot.get_channel(int(league.reminder_channel_id)) is not None and embed is not None:
                bot.loop.create_task(bot.get_channel(int(league.reminder_channel_id)).send(embed=embed))
        for member in league.members:
            if league.table[member][cr][1] == 'NaN' and msg_embed is not None:
                await bot.get_user(int(member)).send(embed=msg_embed)


async def setReminders():
    scheduler.remove_all_jobs()
    cr = fom.returnCurrentRoundNum()
    # cr = 2
    qualitime = fom.schedule[cr - 1]

    reminders = [[qualitime - timedelta(minutes=5), "5 minutes"],
                 [qualitime - timedelta(minutes=30), "30 minutes"],
                 [qualitime - timedelta(hours=1), "1 hour"],
                 [qualitime - timedelta(hours=3), "3 hours"],
                 [qualitime - timedelta(hours=5), "5 hours"],
                 [qualitime - timedelta(hours=12), "12 hours"],
                 [qualitime - timedelta(hours=24), "1 day"],
                 [qualitime - timedelta(hours=48), "2 days"],
                 [qualitime - timedelta(hours=96), "4 days"],
                 [qualitime + timedelta(hours=22), "notdrafted"]]
    if cr > 1:
        reminders.append([fom.schedule[cr - 2] + timedelta(days=3), "windowopen"])

    for r in reminders:
        if datetime.now() < r[0]:
            scheduler.add_job(reminder,
                              'cron',
                              year=cyear,
                              month=r[0].month,
                              day=r[0].day,
                              hour=r[0].hour,
                              minute=r[0].minute,
                              second=r[0].second,
                              args=[r[1]],
                              name=r[1],
                              )
    if scheduler.state == 0:
        scheduler.start()


##############################################################################
#
#   New user init function, executed when a new user needs to be registered to a database table
#
##############################################################################
async def init_user(interaction):
    await interaction.response.defer()
    temp_league = active_leagues[str(interaction.guild.id)]
    if temp_league.members.get(str(interaction.user.id)) is None:
        temp_league.addUser(str(interaction.user.id))
        await interaction.followup.send(f'Registered user {interaction.user.mention}!')
    else:
        logging.info(f'Invalid exec error by {interaction.user} in {interaction.guild.name}.')
        await interaction.followup.send("You're already Registered!")


##############################################################################
#
#   Close slash command (admin only), saves tables, and closes bot instance when triggered
#
##############################################################################
@bot.tree.command(name="close", description="Closes the current bot instance")
async def close(interaction: discord.Interaction, backup: bool = False):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if interaction.guild is None:
        await interaction.response.send_message("Please perform this command on a server with an active league!")
    else:
        logging.info(f'Close command triggered by {interaction.user} in {interaction.guild.name}.')
        if not await bot.is_owner(interaction.user):
            logging.info(f'Invalid exec error by {interaction.user} in {interaction.guild.name}.')
            await interaction.response.send_message("You are not authorized to run this command.", ephemeral=True)
        else:
            if backup:
                for league in active_leagues:
                    league.orderTable()
            await interaction.response.send_message(f'Closing...')
            await exit(0)


##############################################################################
#
#   Start league slash command (admin only), triggered when /startleague is executed by an admin,
#
##############################################################################
@bot.tree.command(name="startleague", description="Start a league. Rounds = number of races.")
async def startleague(interaction: discord.Interaction, rounds: int = int(fom.returnRoundsInYear(cyear))):
    await interaction.response.defer()
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if interaction.guild is None:
        await interaction.followup.send("Please perform this command on a server with an active league!")
    else:
        if not interaction.user.guild_permissions.administrator:
            logging.info(f'Invalid exec error by {interaction.user} in {interaction.guild.name}.')
            await interaction.followup.send("You are not authorized to run this command.", ephemeral=True)
        else:
            if active_leagues.get(str(interaction.guild.id)) is not None:
                await interaction.followup.send("__**A league already exists for this server!**__ "
                                                "If you wish to override it, press the conformation button bellow",
                                                view=ConformationButton(rounds=rounds))
            else:
                await init_league(interaction=interaction, rounds=rounds)


##############################################################################
#
#   Add user var A,ads an extra user variable (executable by admins)
#
##############################################################################
@bot.tree.command(name="adduservar", description="Add an extra user variable (executable by admins)")
async def adduservar(interaction: discord.Interaction, num: int):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if interaction.guild is None:
        await interaction.response.send_message("Please perform this command on a server with an active league!")
    else:
        if num <= 0 or num >= 10:
            await interaction.response.send_message("Invalid value, try adding a number between 1 and 10.",
                                                    ephemeral=True)
        else:
            if active_leagues.get(str(interaction.guild_id)) is None:
                await interaction.response.send_message(
                    "No active league exists on this server! Use /startleage first.",
                    ephemeral=True)
            else:
                active_leagues[str(interaction.guild_id)].user_values += num
                tt = active_leagues[str(interaction.guild_id)].table
                for i in range(1, len(tt)):
                    for j in range(1, active_leagues[str(interaction.guild_id)].rounds + 1):
                        for k in range(num):
                            tt[list(tt)[i]][j].append('NaN')


# @bot.tree.command(name="pick", description="Pick your drivers for the upcoming race")
# async def pick(interaction: discord.Interaction, pick_1: str, pick_2: str, pick_3: str):
#     templ = active_leagues.get(str(interaction.guild.id))
#     if templ is None:
#         await interaction.response.send_message("No active league exists on this server! "
#                                                 "Use /startleage first.", ephemeral=True)
#     else:
#         if templ.table.get(str(interaction.user.id)) is None:
#             await interaction.response.send_message("You have not registered for the league yet; use /register first.",
#                                                     ephemeral=True)
#
#         elif templ.table[str(interaction.user.id)][1][2] == 'NaN':
#             await interaction.response.send_message("You have not set your team yet! Use /draft first.",
#                                                     ephemeral=True)
#         else:
#             picks = [fom.drivers_table.returnDriverTLA(pick_1),
#                      fom.drivers_table.returnDriverTLA(pick_2),
#                      fom.drivers_table.returnDriverTLA(pick_3)]
#             if 'NaN' in picks:
#                 await interaction.response.send_message(f'The following picks were not identified by the system; '
#                                                         f'{[x for x in picks if x != pick_1 or x != pick_2 or x != pick_3]}'
#                                                         f'use the drivers TLA for best results', ephemeral=True)
#             elif len(set(picks)) != len(picks):
#                 embed = discord.Embed(title='...you little sh-', description="You can't pick the same driver twice; but"
#                                                                              " you already knew that didn't you? Do you "
#                                                                              "realise I have to add an if-else statement "
#                                                                              "somewhere or the "
#                                                                              "other for every dumb-ass cases like this? "
#                                                                              "Congratulations, you increased the number of "
#                                                                              "lines of code "
#                                                                              "I had to write by ten lines; are you proud of "
#                                                                              "yourself?  Now, unless you want to clone { "
#                                                                              "insert_driver_name} and convince the FiA to "
#                                                                              "let them race this season under the same name, "
#                                                                              "team, "
#                                                                              "number and TLA, I suggest you pick another "
#                                                                              "driver. Punk.")
#                 await interaction.response.send_message(embed=embed,
#                                                         ephemeral=True)
#
#             else:
#                 currentRound = fom.returnCurrentRoundNum()
#                 deadline = fom.returnPicksEnded()
#                 if deadline[0]:
#                     await interaction.response.send_message(f'You have missed the pick deadline '
#                                                             f'{returnFormattedTime(deadline[1])}, try '
#                                                             f'entering them earlier next race.', ephemeral=True)
#                 else:
#                     global invalid
#                     invalid = False
#                     for pick in picks:
#                         if pick not in templ.table[str(interaction.user.id)][currentRound - 1][2:]:
#                             await interaction.response.send_message(f'Invalid picks! Use /checkteam to check your '
#                                                                     f'current team, and /swap to swap teamamtes',
#                                                                     ephemeral=True)
#                             invalid = True
#                             break
#
#                         elif currentRound >= 2 and pick in templ.table[str(interaction.user.id)][currentRound - 1][
#                             1] and \
#                                 pick in templ.table[str(interaction.user.id)][currentRound - 2][1]:
#                             await interaction.response.send_message(f'Invalid picks! Use /team to check your '
#                                                                     f'current team, and /swap to swap teamamtes',
#                                                                     ephemeral=True)
#                             invalid = True
#                             break
#                     if not invalid:
#                         templ.table[str(interaction.user.id)][currentRound][1] = picks
#                         templ.updateLocalTable()
#                         await interaction.response.send_message(f'Picks registered!', ephemeral=True)


@bot.tree.command(name="team", description="Look at your team for a given GP, and their exhaustion status")
async def team(interaction: discord.Interaction, hidden: bool = True, gp: int = int(fom.returnCurrentRoundNum())):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    await interaction.response.defer(ephemeral=bool(hidden))
    if interaction.guild is None:
        await interaction.followup.send("Please perform this command on a server with an active league!")
    else:
        templ = active_leagues.get(str(interaction.guild.id))
        if templ is None:
            await interaction.followup.send("No active league exists on this server! "
                                            "Use /startleage first.", ephemeral=True)
        else:
            if templ.table.get(str(interaction.user.id)) is None:
                await interaction.followup.send(
                    "You have not registered for the league yet; use /register first.",
                    ephemeral=True)
            # elif templ.table[str(interaction.user.id)][1][0] == 'NaN':
            #     await interaction.response.send_message("You have not registered for the league yet; use /register first.",
            #                                             ephemeral=True)
            else:
                cr = gp
                cgp = fom.returnCurrentRoundNum()
                if cr < 1 or cr > cgp:
                    await interaction.followup.send("Invalid GP number")
                else:
                    embed = discord.Embed(title=f"{interaction.user.name}'s Team",
                                          description='\u200b',
                                          color=discord.Color.red())

                    drafted = False
                    for r in templ.table[str(interaction.user.id)][1:]:
                        if r[1] != 'NaN':
                            drafted = True

                    if not drafted:
                        await interaction.followup.send("You haven't picked a team yet!", ephemeral=True)
                    else:
                        exhausted = [False, False, False, False, False]
                        if templ.table[str(interaction.user.id)][cr][1] == 'NaN' and cr == cgp:
                            cr -= 1
                            embed.add_field(name='\u200b',
                                            value="Note: You haven't set your team\n for the upcoming round; "
                                                  "showing previous rounds roster.",
                                            inline=False)
                            drs = templ.table[str(interaction.user.id)][cr]
                            qualires = fom.returnGPQuali(cr)

                            if qualires is not None:
                                constquali = [dr for dr in qualires if fom.drivers_table.drivers[dr]['team'] == fom.drivers_table.drivers[drs[2]]['team']]
                            else:
                                constquali = None

                            raceres = fom.returnRaceResults(cr)
                            if raceres is not None:
                                constrace = [dr for dr in raceres if fom.drivers_table.drivers[dr]['team'] == fom.drivers_table.drivers[drs[2]]['team']]
                            else:
                                constrace = None

                            if raceres is not None:
                                for i in range(1, 6):
                                    if cr - 1 >= 1:
                                        if drs[i] in templ.table[str(interaction.user.id)][cr - 1]:
                                            exhausted[i - 1] = True
                                    if fom.drivers_table.results[str(cr)][0] == drs[i]:
                                        exhausted[i - 1] = True
                                if constrace is not None and constquali is not None:
                                    if constrace[0] == drs[2] or constquali[0] == drs[2]:
                                        exhausted[1] = True
                                else:
                                    logging.log("Quali or Race results seem to be inccomplete for /team exec.")
                            # print(exhausted)
                        elif cr != cgp:
                            drs = templ.table[str(interaction.user.id)][cr]
                            if templ.table[str(interaction.user.id)][cr][1] == 'NaN':
                                embed.add_field(name='\u200b',
                                                value="Note: You haven't set your team\n for the upcoming round; "
                                                      "showing previous rounds roster.",
                                                inline=False)
                            else:
                                qualires = fom.returnGPQuali(cr)
                                if qualires is not None:
                                    constquali = []
                                else:
                                    constquali = None
                                if fom.drivers_table.results.get(str(cr)) is not None:
                                    constrace = [dr for dr in fom.drivers_table.results[str(cr)] if
                                                 fom.drivers_table.drivers[dr]['team'] ==
                                                 fom.drivers_table.drivers[drs[2]][
                                                     'team']]
                                else:
                                    constrace = None

                                if fom.drivers_table.results.get(str(cr)) is not None:
                                    for i in range(1, 6):
                                        if cr - 1 >= 1:
                                            if drs[i] in templ.table[str(interaction.user.id)][cr - 1]:
                                                exhausted[i - 1] = True
                                        if fom.drivers_table.results[str(cr)][0] == drs[i]:
                                            exhausted[i - 1] = True
                                    if constrace is not None and constquali is not None:
                                        if constrace[0] == drs[2] or constquali[0] == drs[2]:
                                            exhausted[1] = True
                                    else:
                                        logging.log("Quali or Race results seem to be inccomplete for /team exec.")
                        else:
                            drs = templ.table[str(interaction.user.id)][cr]
                        if drs[1] != 'NaN':
                            embed.add_field(name='Top-3\n',
                                            value=f'{str(fom.drivers_table.drivers[drs[3]]["full_name"] + " ⠀") if not exhausted[2] else str(fom.drivers_table.drivers[drs[3]]["full_name"] + "  🔻")}\n '
                                                  f'{str(fom.drivers_table.drivers[drs[4]]["full_name"] + " ⠀󠀠") if not exhausted[3] else str(fom.drivers_table.drivers[drs[4]]["full_name"] + "  🔻")}\n '
                                                  f'{str(fom.drivers_table.drivers[drs[5]]["full_name"] + " ⠀") if not exhausted[4] else str(fom.drivers_table.drivers[drs[5]]["full_name"] + "  🔻")}',
                                            inline=True)

                            embed.add_field(name='Wildcard\n',
                                            value=f'{str(fom.drivers_table.drivers[drs[2]]["full_name"] + " ⠀") if not exhausted[1] else str(fom.drivers_table.drivers[drs[2]]["full_name"] + "  🔻")}',
                                            inline=True)

                            embed.add_field(name='Constructor\n',
                                            value=f'{str(drs[1] + " ⠀󠀠") if not exhausted[0] else str(drs[1] + "  🔻")}',
                                            inline=True)
                            embed.set_thumbnail(url=interaction.user.avatar.url)

                        await interaction.followup.send(embed=embed, ephemeral=bool(hidden))


@bot.tree.command(name="maintenance", description="Perform server maintenance")
async def maintenance(interaction: discord.Interaction, hours: int = 2):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if await bot.is_owner(interaction.user):
        to = datetime.now() + timedelta(hours=hours)
        embed = discord.Embed(title="Maintenance Alert!",
                              description=f"The league bot will go down after 10 minutes for maintainance and updating "
                                          f"till {await returnFormattedTime(to)}.",
                              color=discord.Color.red())
        await bot.get_channel(interaction.channel_id).send(embed=embed)
        await interaction.response.send_message("Done!", ephemeral=True)

        scheduler.add_job(exit,
                          'cron',
                          year=cyear,
                          month=to.month,
                          day=to.day,
                          hour=to.hour,
                          minute=to.minute,
                          second=to.second,
                          args=[0],
                          name="close")
    else:
        await interaction.response.send_message("No.", ephemeral=True)


##############################################################################
#
# DeRegisters a channel
#
##############################################################################
@bot.tree.command(name="deregisterchannel", description="De-registers the invoked channel.")
async def deregchannel(interaction: discord.Interaction):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if interaction.guild is None:
        await interaction.response.send_message("Please perform this command on a server with an active league!")
    else:
        if active_leagues.get(str(interaction.guild.id)) is None:
            await interaction.response.send_message("No active league exists on this server! "
                                                    "Use /startleage first.", ephemeral=True)
        elif not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have the permission to execute this command",
                                                    ephemeral=True)
        else:
            temp = active_leagues[str(interaction.guild.id)]
            if temp.twitter_channel_id == str(interaction.channel_id) == temp.reminder_channel_id:
                temp.twitter_channel_id = '0'
                temp.reminder_channel_id = '0'
                await interaction.response.send_message("Done! De-registered this channel for both tweets and updates.",
                                                        ephemeral=True)
                temp.updateLocalTable()
            elif str(interaction.channel_id) == temp.reminder_channel_id:
                temp.reminder_channel_id = '0'
                await interaction.response.send_message("Done! De-registered this channel for driver pick updates",
                                                        ephemeral=True)
                temp.updateLocalTable()
            elif temp.twitter_channel_id == str(interaction.channel_id):
                temp.twitter_channel_id = '0'
                await interaction.response.send_message("Done! De-registered this channel for twitter updates",
                                                        ephemeral=True)
                temp.updateLocalTable()


##############################################################################
#
# Register a channel for all pick updates
#
##############################################################################
@bot.tree.command(name="registerreminderschannel",
                  description="Registers the invoked channel as the default for reminders")
async def reminderchannel(interaction: discord.Interaction):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if interaction.guild is None:
        await interaction.response.send_message("Please perform this command on a server with an active league!")
    else:
        if active_leagues.get(str(interaction.guild.id)) is None:
            await interaction.response.send_message("No active league exists on this server! "
                                                    "Use /startleage first.", ephemeral=True)
        elif not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have the permission to execute this command",
                                                    ephemeral=True)
        else:
            temp = active_leagues[str(interaction.guild.id)]
            temp.reminder_channel_id = str(interaction.channel_id)
            temp.updateLocalTable()
            await interaction.response.send_message("Done!", ephemeral=True)


##############################################################################
#
# Register a channel for all twitter updates
#
##############################################################################
@bot.tree.command(name="registertweetschannel", description="Registers the invoked channel as the default for tweets")
async def twitterchannel(interaction: discord.Interaction):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if interaction.guild is None:
        await interaction.response.send_message("Please perform this command on a server with an active league!")
    else:
        if active_leagues.get(str(interaction.guild.id)) is None:
            await interaction.response.send_message("No active league exists on this server! "
                                                    "Use /startleage first.", ephemeral=True)
        elif not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have the permission to execute this command",
                                                    ephemeral=True)
        else:
            temp = active_leagues[str(interaction.guild.id)]
            temp.twitter_channel_id = str(interaction.channel_id)
            temp.updateLocalTable()
            await interaction.response.send_message("Done!", ephemeral=True)


##############################################################################
#
# Test, test.
#
##############################################################################
# @bot.tree.command(name="test", description="test")
# async def test(interaction: discord.Interaction):
#     await interaction.response.send_message("No DMs necessary, see?", ephemeral=True)


##############################################################################
#
#   Init league function, initializes the tables and other variables necessary
#
##############################################################################
async def init_league(interaction, rounds=int(fom.returnRoundsInYear(cyear)), uvars=5):
    active_leagues[str(interaction.guild.id)] = db.Table(guild_id=str(interaction.guild.id),
                                                         rounds=rounds,
                                                         load_from_file=False)

    active_leagues[str(interaction.guild.id)].reminder_channel_id = str(interaction.channel.id)
    active_leagues[str(interaction.guild.id)].orderTable()
    next_event = fom.returnNextEvent()
    embed = discord.Embed(title=f'Starting the LVS F1 Fantasy League {cyear}!',
                          description="Press the button below, or use the /register command to register "
                                      "yourself!",
                          color=discord.Color.red())
    embed.add_field(name=f'The next event, the **{next_event["name"]}** is on '
                         f'{await returnFormattedTime(next_event["date"])}!',
                    value=f'Be sure to register and submit your picks before the deadline', inline=False)

    embed.add_field(name='\u200b',
                    value=f'**Note**: This channel has been assigned as the default reminders channel; if you wish to'
                          f'change that, use the /deregisterchannel command, and /registerreminderschannel to register'
                          f'a different channel.', inline=False)

    await interaction.response.send_message(embed=embed, view=RegisterButton())


##############################################################################
#
#   Returns a  formatted version of a given datetime
#
##############################################################################
async def returnFormattedTime(date):
    if isinstance(date, str):
        date = datetime.strptime(date, dt_format_o)
        return str(date.strftime(dt_format_c))
    elif isinstance(date, datetime):
        return str(date.strftime(dt_format_c))
    else:
        print("Invalid format sent")


##############################################################################
#
#   Prints leaderboard
#
##############################################################################
@bot.tree.command(name="leaderboard", description="Display leaderboard of current league")
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()
    if interaction.guild is None:
        await interaction.followup.send("Please perform this command on a server with an active league!")
    else:
        if active_leagues.get(str(interaction.guild.id)) is not None:
            embed = discord.Embed(title=f'League Leaderboard',
                                  description="\u200b",
                                  color=discord.Color.red())
            lb = list(active_leagues[str(interaction.guild.id)].members.items())
            for i in range(len(lb)):
                embed.add_field(name=f'#{i + 1}. **{bot.get_user(int(lb[i][0])).display_name}**',
                                value=f'{lb[i][1]}pts',
                                inline=False)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f'**No active league on this server!** '
                                            f'Ask an admin to use **/startleague** first.')


##############################################################################
#
#   Shows a specified events information, datetime and track. Image is fetched
#   directly from formula1.com
#
##############################################################################
@bot.tree.command(name="grandprix", description="Displays the specified event's info.")
async def seasonevent(interaction: discord.Interaction, gp: str):
    await interaction.response.defer()
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if gp.isnumeric():
        gp = int(gp)
    try:
        se = fom.returnEvent(gp)
        embed = discord.Embed(color=discord.Color.red())
        if se.get('results') is not None:

            embed.title = f'**{se["name"]}** '
            embed.description = f'The GP took place on {await returnFormattedTime(se["date"])}, ' \
                                f'and had a {se["type"]} round format, (round {se["round"]} ' \
                                f'of {fom.returnRoundsInYear(cyear)})\n\n'

            embed.add_field(name='**Race Results**', value='-----------------------', inline=False)

            for count, d in enumerate(se['results']):
                embed.add_field(name=f'#{count + 1}', value=f'{fom.drivers_table.drivers[d]["full_name"]}', inline=True)
            embed.add_field(name=f'\u200b', value=f'\u200b', inline=True)

        else:
            embed.title = f'**{se["name"]}** is on {await returnFormattedTime(se["date"])}!'
            embed.description = f'with a {se["type"]} round format, (round {se["round"]} ' \
                                f'of {fom.returnRoundsInYear(cyear)})'
        embed.set_image(url=await returnTrackLink(se["loc"], se["name"]))
        embed.set_footer(text="For more info, use the /help command to see what all you can do.")
        await interaction.followup.send(embed=embed)
    except ValueError:
        await interaction.followup.send("Invalid GP identifier!")

    #
    # print(next_event["loc"])
    # embed.set_image(url=await returnTrackLink(next_event["loc"]))
    # embed.set_footer(text="For more info, use the /help command to see what all you can do.")
    # await interaction.response.send_message(embed=embed)


##############################################################################
#
#   Shows next events name, datetime and track. Image is fetched
#   directly from formula1.com
#
##############################################################################
@bot.tree.command(name="nextevent", description="Displays the next event's info.")
async def nextevent(interaction: discord.Interaction):
    await interaction.response.defer()
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    next_event = fom.returnNextEvent()
    embed = discord.Embed(
        title=f'The next event, the **{next_event["name"]}** is on {await returnFormattedTime(next_event["date"])}!',
        description=f'with a {next_event["type"]} round format, (round {next_event["round"]} '
                    f'of {fom.returnRoundsInYear(cyear)})',
        color=discord.Color.red())

    embed.set_image(url=await returnTrackLink(next_event["loc"], next_event["name"]))
    embed.set_footer(text="For more info, use the /help command to see what all you can do.")
    await interaction.followup.send(embed=embed)


async def returnTrackLink(track_loc, track_name):
    gpid = track_loc
    # print(track_loc+", "+track_name)
    if track_loc == 'United States':
        gpid = 'USA'
    elif track_name == 'Emilia Romagna Grand Prix':
        gpid = 'Emilia_Romagna'
    elif track_name == 'Miami Grand Prix':
        gpid = 'Miami'
    elif track_name == 'Monaco Grand Prix':
        gpid = 'Monoco'
    elif track_name == 'Azerbaijan Grand Prix':
        gpid = 'Baku'
    elif track_name == 'British Grand Prix':
        gpid = 'Great_Britain'
    elif track_loc == 'Saudi Arabia':
        gpid = 'Saudi_Arabia'
    elif track_loc == 'Great Britain':
        gpid = 'Great_Britain'
    elif track_loc == 'UAE':
        gpid = 'Abu_Dhabi'
    return f'https://www.formula1.com/content/dam/fom-' \
           f'website/2018-redesign-assets/Circuit%20maps%2016x9/{gpid}_Circuit.png '


##############################################################################
#
#   Shows a drivers info, the information is fetched from a database. Image is fetched
#   directly from formula1.com
#
##############################################################################
@bot.tree.command(name="driverinfo", description="Displays the queried driver's info.")
async def driver(interaction: discord.Interaction, identifier: str):
    await interaction.response.defer()
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if fom.drivers_table.returnDriverTLA(identifier) == 'NaN':
        await interaction.followup.send("No driver found with identification you specified!")
    else:
        dr = fom.drivers_table.drivers[fom.drivers_table.returnDriverTLA(identifier)]
        embed = discord.Embed(
            title=f'**{dr["full_name"]}**',
            description=f'{dr["team"]}',
            color=discord.Color.from_str(f'0x{dr["team_color"]}'))
        embed.add_field(name=f'**#{dr["rank"]}**', value="Season Rank", inline=True)
        embed.add_field(name=f'**{dr["season_points"]}pts**', value="Season Points", inline=True)
        embed.add_field(name=f'**#{dr["number"]}**', value="Permanent Number", inline=True)
        embed.add_field(name=f'**{dr["podiums"]}**', value="Season Podiums", inline=True)
        embed.add_field(name=f'**{dr["wins"]}**', value="Season Wins", inline=True)
        embed.add_field(name=f'Nationality', value=f'**{dr["nationality"]}**', inline=True)
        embed.set_image(url=dr['pf_img_url'])
        embed.set_footer(text=f'For more info, visit the https://www.grandprixstats.org/f1/seasons/{cyear}/')
        await interaction.followup.send(embed=embed)


##############################################################################
#
#   Profile; fetches data from active league, if there is one;
#   otherwise simply shows ones discord name and pfp
#
##############################################################################
@bot.tree.command(name="profile", description="Displays a users profile in current server")
async def profile(interaction: discord.Interaction, user: discord.User):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if interaction.guild is None:
        await interaction.response.send_message("Please perform this command on a server with an active league!")
    else:
        await interaction.response.defer()
        pfp = user.avatar.url
        embed = discord.Embed(
            title=f'{user.name}',
            description="The one and only!",
            color=discord.Color.red())
        embed.set_thumbnail(url=pfp)
        if active_leagues.get(str(interaction.guild.id)) is not None:
            temp_league_check: db.Table = active_leagues[str(interaction.guild.id)]
            if temp_league_check.members.get(str(user.id)) is not None:
                embed.add_field(name="Current League Rank",
                                value=f'Rank #{temp_league_check.returnUserRank(str(user.id))} !',
                                inline=True)
                embed.add_field(name="Current Points", value=f'{temp_league_check.members[str(user.id)]}',
                                inline=True)
            else:
                embed.add_field(name="Current League Standing", value="Not participating in current league.",
                                inline=False)

        else:
            embed.set_footer(text='The server does not have any active leagues.')
        await interaction.followup.send(embed=embed)


##############################################################################
#
#   PointsTable; prints the points table till current round
#
##############################################################################
@bot.tree.command(name="pointstable", description="Displays the table of points for active league, "
                                                  "till the defined round")
async def pointstable(interaction: discord.Interaction):
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    if interaction.guild is None:
        await interaction.response.send_message("Please perform this command on a server with an active league!")
    else:
        if active_leagues.get(str(interaction.guild.id)) is None:
            await interaction.response.send_message("**There is no active league started on this server!** To start one"
                                                    ", ask an admin to use the **/startleague** command")
        else:
            await interaction.response.defer()
            pt = active_leagues[str(interaction.guild.id)].returnPrintableTable()
            # converting user id to name, and adding sum column
            for i in range(1, len(pt)):
                n = str(bot.get_user(int(pt[i][0])).name)
                pt[i][0] = n
                pt[i][-1] = n
            pt_df = pd.DataFrame(pt[1:], columns=pt[0])
            pt_df.style.hide(axis="index")
            pd.set_option('colheader_justify', 'center')

            table = '{table}'

            html_string = f'''
            <html>
                <head><title>LVS F1 Fantasy League</title></head>
                <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
                <link rel="stylesheet" type="text/css" href="file:///{os.getcwd()}/table/tablestyle.css" />
                <body style="background-color: #313338">
                    {table}
                </body>
            </html>
            '''
            # 4C4C4C

            imgkit.from_string(html_string.format(table=pt_df.to_html(classes='tablestyle', index=False)),
                               output_path='table/table.png',
                               config=imgk_config,
                               options=imgk_options,
                               css=f'{os.getcwd()}/table/tablestyle.css')

            await interaction.followup.send(file=discord.File('table/table.png'))
            # pt_df.style.apply(dfstyle)
            # print(pt)
            # print(pt_df)


##############################################################################
#
#   Custom help embed function
#
##############################################################################
@bot.tree.command(name="help", description="Displays a list of commands")
async def help_custom(interaction: discord.Interaction):
    await interaction.response.defer()
    logging.info(
        f"{interaction.user.name} ({interaction.user.id}) triggered {interaction.command.name} at {datetime.now()}")
    embed = discord.Embed(
        title="Command List",
        description="List of available commands with brief descriptions",
        color=discord.Color.red())
    for c in bot.tree.get_commands():
        if c.name not in help_filter:
            embed.add_field(name=f'**/{c.name}**', value=c.description, inline=False)
    embed.set_footer(text=f"For more help, contact the lazy dev who made me (@nERD).")
    await interaction.followup.send(embed=embed)


##############################################################################
#
#   Button classes, creates a discord.ui.view class that's
#   used in message embeds
#
##############################################################################

class ConformationButton(discord.ui.View):
    def __init__(self, *, timeout=30, rounds, uvars=5):
        self.rounds = rounds
        self.uvars = uvars
        self.disabled = False
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red)
    async def create_delete_b(self, interaction: discord.Interaction, button1: discord.ui.Button):
        if not self.disabled:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You are not authorized to run this command.")
            else:
                await interaction.message.add_reaction(u"\U0001F44D")
                self.disabled = True
                await init_league(interaction, rounds=self.rounds, uvars=self.uvars)
                await interaction.response.defer()
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Keep Current", style=discord.ButtonStyle.red)
    async def create_preserve_b(self, interaction: discord.Interaction, button2: discord.ui.Button):
        if not self.disabled:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You are not authorized to run this command.")
            else:
                await interaction.message.add_reaction(u"\U0001F44D")
                self.disabled = True
                await interaction.response.defer()
        else:
            await interaction.response.defer()


class RegisterButton(discord.ui.View):
    def __init__(self, *, timeout=None):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Register", style=discord.ButtonStyle.red)
    async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await init_user(interaction)


def startdisc():
    bot.run(DISCORD_TOKEN, log_handler=None)


# def starttwt():
#     twbot = twitterbot.twBot(pfunc=twitterPrint)


if __name__ == '__main__':
    startdisc()
# if __name__ == '__main__':
#     t1 = threading.Thread(target=startdisc)
#     t2 = threading.Thread(target=starttwt)
#     t1.start()
#     t2.start()
#     t1.join()
