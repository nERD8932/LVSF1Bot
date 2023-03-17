[![Logo](https://cdn.discordapp.com/attachments/1006201726069641268/1086157444557844521/githubbanner.png)]()
# LVS F1 Fantasy League Bot
A discord bot created by and for the LVS team.

#### Features
- Create an F1 league for the specified year, with 'n' number of rounds.
- Allow players to register for the league and draft their teams for upcoming races
- Allow owner to control point updates and other parameters
- League rules and points are customizable through the bots' python script.
- Uses fastf1 and eargast to update race information, driver season points and rank, etc. (future versions will remove fastf1 dependancy)
- Currently only supported on Windows machines

#
#### Installation
###### Default Rules and points:
- Extract the latest package into a suitable directory. Assuming your discord bot is already set up, create a new file called .env in the same directory as the bots exe. Open this file with a text editor of your choice, and add the entry: DISCORD_TOKEN=(discord bot token)

###### Custom Rules:
- Copy the files in the /scripts folder into the main director.
- Install python, if you haven't already.
- Open a terminal in the main directory, and use 'pip' to install the packages in requirements.txt.
- Edit the league rules in 'bot. py' using your preferred IDE (I recommend PyCharm). Most of the points logic is in the update and draft functions, however be sure to check the comments on all the functions to make sure your custom rules are applied to all of them.
- Once you are done editing the relavent rules, run 'bot. py' through your IDE or directly through a terminal.
- If you wish to compile the project into a singular exe, use the 'pyinstaller -F bot.py' command in the terminal.
- If you need any further help; feel free to contact me and I'll help to whatever extent I can.

#

#### Dependancies
- Ergast API 
- FastF1 
- wkhtmltopdf
- NumPy 
- Pandas 
- Python 

**Huge thanks to the teams and creators of the aforementioned packages, you guys rock!**


#### License
MIT
**Free Software, Hell Yeah!**
#
#### Created by [nERD]

[//]: # ()

   [nERD]: <https://github.com/nERD8932/>
