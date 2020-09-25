import discord
from discord.ext.commands import Bot

import asyncio

from random import sample

import os.path

from requests import get
from json import loads

import aiohttp

import nest_asyncio
nest_asyncio.apply()

client = Bot('')

verified_server_ids_set = {730755297831813180}  # bot will only work in these servers. It will record everything it can read from any unauthorized servers to logs2.txt
bot_channel_ids_set = {757842201207242822}  # while the bot will try to convert links to embeds in all channels of verified servers, only in these channels will it actively look for commands and try to respond to them
admin_user_ids_set = {387961214011047937}  # only admins can do the toggle command
mm = 1

greetings = {"Hello", "Nice to see you", "Beautiful day,", "How have you been,", "Yes I'm alive,", "REEEEEEEEEEEEEEEEEE WHY WAS I PINGED!", "Always a pleasure", "What is thy bidding", "wut", "lol"}

local_files = {
    "base": "",
    "help": "help.txt",
    "user_config": "users.txt",
    "token": "token.txt",
    "log": "logs.txt",
    "log2": "logs2.txt"
}

web_links = {
    "map_api": "https://api.krunker.io/search?type=map&val=",
    "matchmaker": "https://matchmaker.krunker.io/game-list?hostname=krunker.io",
    "link_info": "https://matchmaker.krunker.io/game-info?game=",
    "map_social": "https://krunker.io/social.html?p=map&q=",
    "game_link": "https://krunker.io/?game="
}

bot_strings = {
    "help": "```fix\nSee .help```",
    "no_settings": "```diff\n-No regions or modes set```",
    "add_modes": "```diff\n-Please add modes```",
    "add_regions": "```diff\n-Please add regions```",
    "wrong_input": "```diff\n-Wrong input```",
    "updated_regions": "```diff\n+Updated your regions. Your regions are now```",
    "updated_modes": "```diff\n+Updated your modes. Your modes are now```",
    "cleared_settings": "```diff\n-Cleared your regions and modes```",
    "cleared_regions": "```diff\n-Cleared regions```",
    "cleared_modes": "```diff\n-Cleared modes```",
    "no_suitable": "```diff\n-Couldn't find any suitable lobbies for user settings. Try adding more modes or regions```"
}

matchmaker_dict = {
    "players_online": 0,
    "players_maximum": 0,
    "servers_online": 0,
    "regions": set(),
    "modes": set(),
    "names": set(),
    "sp_games": {}  # is a dict cs->region->mode->->name->list of dicts which look like {"po": p_online, "pm": p_max, "l": link}
}


@client.event
@asyncio.coroutine
async def on_message(message):
    if message.author == client.user:  # ignore what the bot itself says
        return

    if message.guild.id not in verified_server_ids_set:
        bot_log_2(message)  # log everything from unauthorized servers that the bot can read to logs2.txt
        return

    if message.content.startswith(".") and message.channel.id in bot_channel_ids_set:
        bot_log(message)
        message_string = message.content[1:].lower()

        if message_string in {"hello", "hi"}:
            await message.channel.send("{} {}".format(sample(greetings, 1)[0], message.author.mention))  # not an embed- we want the user to get pinged!
            return

        elif message_string == "toggle" and message.author.id in admin_user_ids_set:
            global mm

            if mm == 0:
                mm = 1
                x = await message.channel.send("Started {}".format(message.author.mention))
            else:
                mm = 0
                x = await message.channel.send("Stopped {}".format(message.author.mention))

            await asyncio.sleep(2)
            await message.delete()
            await x.delete()
            await mm_run()
            return

        elif message_string in {"help", "h"}:
            await send_embed(read_file(local_files["help"]), message.channel)
            return

        elif message_string == "i":
            mm_temp_dict = dict(matchmaker_dict)
            mm_temp_dict.pop("sp_games")
            mm_temp_dict.pop("names")
            await send_embed("```bash\n\"Server Information\"``` ```Players online: {}\nMaximum player capacity: {}\nServers online: {}```\n```Regions:``` ```fix\n{}```\n```Modes:``` ```fix\n{}```".format(mm_temp_dict["players_online"], mm_temp_dict["players_maximum"], mm_temp_dict["servers_online"], read_set_return_pretty_string(mm_temp_dict["regions"]), read_set_return_pretty_string(mm_temp_dict["modes"])), message.channel)
            return

        elif message_string.startswith("r"):
            uc_data = eval(read_file(local_files["user_config"]))

            if str(message.author.id) not in uc_data:
                uc_data[str(message.author.id)] = {"r": set(), "m": set()}

            if message_string == "r all":
                uc_data[str(message.author.id)]["r"] = matchmaker_dict["regions"]

            else:
                r_set_edit = set(message_string[2:].upper().split(" "))

                new_r = (set(uc_data[str(message.author.id)]["r"]) ^ r_set_edit) & matchmaker_dict["regions"]
                uc_data[str(message.author.id)]["r"] = new_r

                if len(r_set_edit & matchmaker_dict["regions"]) == 0:
                    await send_embed("{} {} {}".format(message.author.mention, bot_strings["wrong_input"], bot_strings["help"]), message.channel)
                    return

            write_file(local_files["user_config"], str(uc_data))

            await send_embed("{}{} ```fix\n{}```".format(message.author.mention, bot_strings["updated_regions"], read_set_return_pretty_string(uc_data[str(message.author.id)]["r"])), message.channel)
            return

        elif message_string.startswith("m"):
            uc_data = eval(read_file(local_files["user_config"]))

            if str(message.author.id) not in uc_data:
                uc_data[str(message.author.id)] = {"r": set(), "m": set()}

            if message_string == "m all":
                uc_data[str(message.author.id)]["m"] = matchmaker_dict["modes"]

            else:
                m_set_edit = set(message_string[2:].lower().split(" "))

                new_m = (set(uc_data[str(message.author.id)]["m"]) ^ m_set_edit) & matchmaker_dict["modes"]
                uc_data[str(message.author.id)]["m"] = new_m

                if len(m_set_edit & matchmaker_dict["modes"]) == 0:
                    await send_embed("{} {} {}".format(message.author.mention, bot_strings["wrong_input"], bot_strings["help"]), message.channel)
                    return

            write_file(local_files["user_config"], str(uc_data))

            await send_embed("{}{} ```fix\n{}```".format(message.author.mention, bot_strings["updated_modes"], read_set_return_pretty_string(uc_data[str(message.author.id)]["m"])), message.channel)
            return

        elif message_string == "v":
            uc_data = eval(read_file(local_files["user_config"]))

            if str(message.author.id) not in uc_data:
                await send_embed("{} {} {}".format(message.author.mention, bot_strings["no_settings"], bot_strings["help"]), message.channel)
                return

            await send_embed("{}```Your region settings are``` ```fix\n{}```\n```Your mode settings are``` ```fix\n{}```".format(message.author.mention, read_set_return_pretty_string(uc_data[str(message.author.id)]["r"]), read_set_return_pretty_string(uc_data[str(message.author.id)]["m"])), message.channel)
            return

        elif message_string == "c":
            uc_data = eval(read_file(local_files["user_config"]))

            if str(message.author.id) not in uc_data:
                await send_embed("{} {} {}".format(message.author.mention, bot_strings["no_settings"], bot_strings["help"]), message.channel)
                return

            uc_data.pop(str(message.author.id))

            write_file(local_files["user_config"], str(uc_data))

            await send_embed("{} {}".format(message.author.mention, bot_strings["cleared_settings"]), message.channel)
            return

        elif message_string == "cr":
            uc_data = eval(read_file(local_files["user_config"]))

            if str(message.author.id) not in uc_data:
                await send_embed("{} {} {}".format(message.author.mention, bot_strings["no_settings"], bot_strings["help"]), message.channel)
                return

            uc_data[str(message.author.id)]["r"] = set()

            write_file(local_files["user_config"], str(uc_data))

            await send_embed("{} {}".format(message.author.mention, bot_strings["cleared_regions"]), message.channel)
            return

        elif message_string == "cm":
            uc_data = eval(read_file(local_files["user_config"]))

            if str(message.author.id) not in uc_data:
                await send_embed("{} {} {}".format(message.author.mention, bot_strings["no_settings"], bot_strings["help"]), message.channel)
                return

            uc_data[str(message.author.id)]["m"] = set()

            write_file(local_files["user_config"], str(uc_data))

            await send_embed("{} {}".format(message.author.mention, bot_strings["cleared_modes"]), message.channel)
            return

        elif message_string.startswith("."):
            player_spec = [5, 1]
            if len(message_string) > 1:
                player_spec = message_string[2:].split(" ")
                for k in range (0, len(player_spec)):
                   player_spec[k] = int(player_spec[k])

                if (len(player_spec) != 2) or (not isinstance(player_spec[0], int)) or (not isinstance(player_spec[1], int)):
                    return

            uc_data = eval(read_file(local_files["user_config"]))

            if str(message.author.id) not in uc_data:
                await send_embed("{} {} {}".format(message.author.mention, bot_strings["no_settings"], bot_strings["help"]), message.channel)
                return

            if len(uc_data[str(message.author.id)]["r"]) == 0:
                await send_embed("{} {} {}".format(message.author.mention, bot_strings["add_regions"], bot_strings["help"]), message.channel)
                return

            if len(uc_data[str(message.author.id)]["m"]) == 0:
                await send_embed("{} {} {}".format(message.author.mention, bot_strings["add_modes"], bot_strings["help"]), message.channel)
                return

            await send_embed("{} ```fix\nThe following lobbies match your settings and have at least {} player(s) and at least {} empty spot(s)```".format(message.author.mention, player_spec[0], player_spec[1]), message.channel)

            user_mm = {}  # developer dictionary containing all lobbies that satisfy settings in uc_data
            total_lobby_count = 0
            for region_temp in uc_data[str(message.author.id)]["r"]:

                if region_temp not in matchmaker_dict["sp_games"]["1"]:
                    continue

                if region_temp not in user_mm:
                    user_mm[region_temp] = {}

                user_str = ""
                region_lobby_count = 0

                for mode_temp in uc_data[str(message.author.id)]["m"]:

                    if mode_temp not in matchmaker_dict["sp_games"]["1"][region_temp]:
                        continue

                    name_count = 0

                    user_mm[region_temp][mode_temp] = matchmaker_dict["sp_games"]["1"][region_temp][mode_temp]

                    if len(user_str) > 1900:
                        break

                    for name_temp in matchmaker_dict["sp_games"]["1"][region_temp][mode_temp]:
                        lobby_count = 0

                        for lobby_temp in matchmaker_dict["sp_games"]["1"][region_temp][mode_temp][name_temp]:

                            if lobby_count > 2:
                                break

                            po_temp = lobby_temp["po"]
                            pm_temp = lobby_temp["pm"]

                            if (po_temp >= player_spec[0]) and (pm_temp - po_temp >= player_spec[1]) and (len(user_str) < 1900):

                                if name_count == 0:
                                    user_str += '```fix\n{}```'.format(mode_temp)

                                if lobby_count == 0:
                                    if name_count != 0:
                                        user_str += "\n"  # formatting lol. There was an extra newline between the mode and first name
                                    user_str += "`{}`: ".format(name_temp)
                                    name_count += 1

                                user_str += "[{}/{}]({}) | ".format(lobby_temp["po"], lobby_temp["pm"], lobby_temp["l"])
                                lobby_count += 1
                                region_lobby_count += 1
                                total_lobby_count += 1
                                # print("added lobby")

                if region_lobby_count > 0:
                    await send_embed("{} ```bash\n\"{} region\"```".format(message.author.mention, region_temp) + user_str, message.channel)
                    await asyncio.sleep(1)

            if total_lobby_count == 0:
                await send_embed("{} {} {}".format(message.author.mention, bot_strings["no_suitable"], bot_strings["help"]), message.channel)
            return


    elif message.content.startswith(web_links["game_link"]):
        bot_log(message)

        link_arr = get_decode_load(web_links["link_info"] + message.content.replace(web_links["game_link"], ""))

        if "error" in link_arr:  # wrong link
            return

        v_embed = discord.Embed(color=0x000000, url=message.content, title="{}/{} players on {} ({} region)".format(link_arr[2], link_arr[3], link_arr[4]['i'], link_arr[1]), description="\n{}\nLink posted by {}".format(message.content, message.author.mention))
        await message.channel.send(embed=v_embed)
        await message.delete()
        return


@client.event
async def on_ready():
    print("Logged in as {} ({})".format(client.user.name, client.user.id))
    await client.change_presence(status=discord.Status.dnd)
    # await client.change_presence(status=discord.Status.online, activity=discord.Game("Looking out for .help"))
    print("Changed presence")
    print("Now ready")
    await mm_run()

async def mm_run():
    while mm:
        await update_matchmaker_dict()
        await asyncio.sleep(5)
    return


def local_files_init():
    x = 0
    if not os.path.isfile(local_files["help"]):
        write_file(local_files["help"], "-")
        x += 1
    if not os.path.isfile(local_files["token"]):
        write_file(local_files["token"], "-")
        x += 1
    if not os.path.isfile(local_files["user_config"]):
        write_file(local_files["user_config"], "{}")
        x += 1
    return x


async def send_embed(embed_string, message_channel):
    temp_embed = discord.Embed(description=embed_string, color=0x000000)
    await message_channel.send(embed=temp_embed)
    return 0


def write_file(path, data):
    file = open(path, "w")
    file.write(data)
    file.close()
    return


def bot_log(message):
    cmd_string = "{}{} ({}) in {} ({}) on {} says {}".format(message.author.name.encode(), message.author.discriminator.encode(), message.author.id, message.guild.name.encode(), message.guild.id, message.created_at.strftime('%d/%m/%Y, %H:%M:%S'), message.content.encode())
    # cmd_string = "{} said {}".format(message.author.name.encode(), message.content.encode())

    print(cmd_string)

    file = open(local_files["log"], "a")
    file.write(cmd_string + "\n")
    file.close()
    return


def bot_log_2(message):
    cmd_string = "{}{} ({}) in {} ({}) on {} says {}".format(message.author.name.encode(), message.author.discriminator.encode(), message.author.id, message.guild.name.encode(), message.guild.id, message.created_at.strftime('%d/%m/%Y, %H:%M:%S'), message.content.encode())
    print(cmd_string)

    file = open(local_files["log2"], "a")
    file.write(cmd_string + "\n")
    file.close()
    return


def read_file(path):
    file = open(path, "r")
    data = file.read()
    file.close()
    return data


def get_decode_load(web_link):
    link_data = get(web_link)
    link_data_decode = link_data.content.decode("utf8")
    link_data_loads = loads(link_data_decode)
    return link_data_loads
    

async def get_decode_load2(url):
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        async with session.get(url, timeout=timeout) as resp:
            return await resp.text()


def read_set_return_pretty_string(my_set):
    if len(my_set) == 0:
        return "-"
    my_string = ""
    for i in my_set:
        my_string += str(i) + " "
    return my_string[:-1]


async def update_matchmaker_dict():
    global matchmaker_dict
    global web_links

    matchmaker_dict["players_online"] = 0
    matchmaker_dict["players_maximum"] = 0
    matchmaker_dict["servers_online"] = 0
    matchmaker_dict["names"] = set()
    matchmaker_dict["sp_games"] = {}

    mm_dict_temp = get_decode_load(web_links["matchmaker"])

    games = mm_dict_temp["games"]

    for game in games:
        custom = 1 if (game[4]["cs"]) else 0

        full_name = game[4]["i"].split("_", 1)
        mode = full_name[0]
        name = full_name[1]

        full_link = game[0].split(":", 1)
        link = full_link[1]
        region = full_link[0]

        p_online = game[2]
        p_max = game[3]

        if str(custom) not in matchmaker_dict["sp_games"]:
            matchmaker_dict["sp_games"][str(custom)] = {}
        if region not in matchmaker_dict["sp_games"][str(custom)]:
            matchmaker_dict["sp_games"][str(custom)][region] = {}
        if mode not in matchmaker_dict["sp_games"][str(custom)][region]:
            matchmaker_dict["sp_games"][str(custom)][region][mode] = {}
        if name not in matchmaker_dict["sp_games"][str(custom)][region][mode]:
            matchmaker_dict["sp_games"][str(custom)][region][mode][name] = []

        matchmaker_dict["sp_games"][str(custom)][region][mode][name].append({"po": p_online, "pm": p_max, "l": web_links["game_link"] + region + ":" + link})

        if not (region in matchmaker_dict["regions"]):
            matchmaker_dict["regions"].add(region)

        if not (mode in matchmaker_dict["modes"]):
            matchmaker_dict["modes"].add(mode)

        if not (name in matchmaker_dict["names"]):
            matchmaker_dict["names"].add(name)

        matchmaker_dict["players_online"] += p_online
        matchmaker_dict["players_maximum"] += p_max
        matchmaker_dict["servers_online"] += 1
    # print(matchmaker_dict)

y = local_files_init()
print("Initialized local files. {} new files were created".format(y))
client.run(read_file(local_files["token"]))
