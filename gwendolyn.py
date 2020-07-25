# Author: Tristan Ferrua
# 2020-07-24 23:02
# Filename: gwendolyn.py 

import sys
import sqlite3
import discord
from discord.ext import commands
import asyncio
import json
import random
import datetime

class Database:
    def __init__(self, dbFile):
        # Open database
        self.conn = sqlite3.connect(dbFile)
        self.cursor = self.conn.cursor()

        # Query if table already exists
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='servers'")
        res = self.cursor.fetchone()

        if res is None:
            # Create table if it does not exist
            self.cursor.execute("CREATE TABLE servers (guildHash int, data str)")
            self.conn.commit()

    def update(self, guild: discord.Guild, data):
        # Function to update data
        guildHash = hash(guild)
        self.cursor.execute("SELECT data FROM servers WHERE guildHash=?", (guildHash, ))
        res = self.cursor.fetchone()

        # Dump data to json
        dumpedData = json.dumps(data)

        if res is None:
            # Create row if it does not exist
            self.cursor.execute("INSERT INTO servers VALUES (?, ?)", (guildHash, dumpedData))
        else:
            # Update row if it does exist
            self.cursor.execute("UPDATE servers SET data=? WHERE guildHash=?", (dumpedData, guildHash))

        self.conn.commit()

    def get(self, guild: discord.Guild):
        # Fetch data from database
        guildHash = hash(guild)
        self.cursor.execute("SELECT data FROM servers WHERE guildHash=?", (guildHash, ))
        res = self.cursor.fetchone()

        # Load from json if it is there
        if res is not None:
            res = json.loads(res[0])

        return res

    def forget(self, guild: discord.Guild):
        # Function to delete all data from server
        guildHash = hash(guild)
        self.cursor.execute("DELETE FROM servers WHERE guildHash=?", (guildHash, ))
        self.conn.commit()

    def start(self, guild: discord.Guild):
        data = {
                "greetChannel": None,
                "logChannel": None,
                "greetMessage": None,
                "farewellMessage": None,
                "logJoin": True,
                "logLeave": True
               }
        self.update(guild, data)

# Load config
with open("config.json", "r") as f:
    config = json.loads(f.read())

# Init bot
activity = discord.Game("g!help")

gwendolyn = commands.Bot(case_insensitive=True,
                         command_prefix=config["prefixes"],
                         activity=activity)

gwendolyn.remove_command("help")

# Database class
db = Database("servers.db")

# Accent colour
accent_colour = discord.Colour(int("698a9e", 16))

# Admin perm cehck
def config_permission(ctx):
    if not isinstance(ctx.channel, discord.abc.GuildChannel):
        return False
    perms = (ctx.author == ctx.guild.owner)
    for role in ctx.author.roles:
        if role.permissions.administrator:
            perms = True
            break
    return perms



@gwendolyn.event
async def on_ready():
    print(f"User:\t\t{gwendolyn.user}")
    for guild in gwendolyn.guilds:
        print(guild.name)
    print()


@gwendolyn.event
async def on_guild_join(guild):
    db.start(guild)
    print(f"Joined guild {guild.name}")


@gwendolyn.event
async def on_member_join(member):
    # Get current date and time
    date = datetime.datetime.utcnow().strftime("%d %b %Y at %H:%M UTC")

    # Get username
    username = member.mention

    # Get data
    data = db.get(member.guild)
    if data is None:
        db.start(member.guild)
        data = db.get(member.guild)

    # Get channel ids
    greetChannelId = data["greetChannel"]
    logChannelId = data["logChannel"]

    # Post greeting
    if greetChannelId is not None:
        greetChannel = member.guild.get_channel(greetChannelId)

        # Check if channel is not found
        if greetChannel is None:
            data["greetChannel"] = None
            db.update(member.guild, data)

        elif data["greetMessage"] is not None:
            await greetChannel.send(data["greetMessage"].format(username=username))

    # Post log
    if logChannelId is not None:
        logChannel = member.guild.get_channel(logChannelId)

        # Check if channel is not found
        if greetChannel is None:
            data["logChannel"] = None
            db.update(member.guild, data)

        elif data["logJoin"]:
            embed = discord.Embed(title="User joined", colour=accent_colour)
            embed.add_field(name="Username", value=str(member))
            embed.add_field(name="Time", value=date)
            embed.set_image(url=member.avatar_url)
            await logChannel.send(embed=embed)


@gwendolyn.event
async def on_member_remove(member):
    # Get current date and time
    date = datetime.datetime.utcnow().strftime("%d %b %Y at %H:%M UTC")

    # Get username
    username = member.mention

    # Get data
    data = db.get(member.guild)
    if data is None:
        db.start(member.guild)
        data = db.get(member.guild)

    # Get channel ids
    greetChannelId = data["greetChannel"]
    logChannelId = data["logChannel"]

    # Post greeting
    if greetChannelId is not None:
        greetChannel = member.guild.get_channel(greetChannelId)

        # Check if channel is not found
        if greetChannel is None:
            data["greetChannel"] = None
            db.update(member.guild, data)

        elif data["farewellMessage"] is not None:
            await greetChannel.send(data["farewellMessage"].format(username=username))

    # Post log
    if logChannelId is not None:
        logChannel = member.guild.get_channel(logChannelId)

        # Check if channel is not found
        if greetChannel is None:
            data["logChannel"] = None
            db.update(member.guild, data)

        elif data["logLeave"]:
            embed = discord.Embed(title="User left", colour=accent_colour)
            embed.add_field(name="Username", value=str(member))
            embed.add_field(name="Time", value=date)
            embed.set_image(url=member.avatar_url)
            await logChannel.send(embed=embed)

@gwendolyn.event
async def on_guild_remove(guild):
    db.forget(guild)


@gwendolyn.event
async def on_command_error(ctx, error):
    print("COMMAND ERROR")
    print("Command:\t{}".format(ctx.message.content))
    print("Error:\t\t{}".format(error))
    if isinstance(error, discord.ext.commands.errors.CommandNotFound):
        await ctx.author.send(content="The command `{}` is unknown.".format(ctx.message.content))
    elif isinstance(error, discord.ext.commands.errors.CheckFailure):
        pass
    else:
        await ctx.author.send(content="There was an unknown error executing your command `{}`.".format(ctx.message.content))


@gwendolyn.command()
async def ping(ctx):
    await ctx.channel.send("Pong!")


@gwendolyn.command()
async def help(ctx):
    prefix = config["prefixes"][0]
    embed = discord.Embed(title="Help", colour=accent_colour)
    embed.add_field(name=f"{prefix}help", value="Shows this message.", inline=False)
    embed.add_field(name=f"{prefix}configure", value="Opens the configuration.", inline=False)
    embed.add_field(name=f"{prefix}forget", value="Deletes all data stored for this server from this bot.", inline=False)
    embed.add_field(name=f"{prefix}ping", value="Pings the bot.", inline=False)

    await ctx.author.send(embed=embed)


@gwendolyn.command(checks=[config_permission])
async def configure(ctx):
    # Configuration for the bot

    # Emojis
    cancel = "\u274C"
    unset = "\U0001F47B"
    checkmark = "\u2705"

    # Init converter
    tcc = discord.ext.commands.TextChannelConverter()

    # Emojis
    with open("emojis.txt", "r") as f:
        emojis = f.read().strip().split("\n")

    random.shuffle(emojis)

    # funciton for editing a message
    async def editMessage(msg, entry):


        # Set the channel title
        if entry == "greetMessage":
            messagetitle = "greeting"
        elif entry == "farewellMessage":
            messagetitle = "farewell"

        # Get data
        data = db.get(ctx.guild)
        if data is None:
            db.start(ctx.guild)
            data = db.get(ctx.guild)

        # Generate embed
        embed = discord.Embed(title=f"Updating the {messagetitle} message", description=f"React with the appropriate emoji:\n\n {checkmark} Update the message\n\n{unset} Unset the message\n\n{cancel} Cancel", colour=accent_colour)
        embed.add_field(name="Currently set to", value=str(data[entry]).format(username="**USER**"))


        # Clear reactions
        try:
            await msg.clear_reactions()
            await msg.edit(embed=embed)
        except discord.errors.Forbidden:
            await msg.delete()
            msg = await ctx.channel.send(embed=embed)

        # Add reactions
        await msg.add_reaction(checkmark)
        await msg.add_reaction(unset)
        await msg.add_reaction(cancel)

        def check(reaction, user):
            return reaction.emoji in [cancel, unset, checkmark] and user == ctx.author

        # Wait for input
        try:
            r, _ = await gwendolyn.wait_for("reaction_add", check=check)
        except asyncio.TimeoutError:
            return msg

        if r.emoji == unset:
            # Unset
            data[entry] = None
        elif r.emoji == cancel:
            # cancel
            return msg
        elif r.emoji == checkmark:
            # Edit message
            embed = discord.Embed(title=f"Setting the {messagetitle} message", description="Please reply with the message you would like to set.\nUse `{username}` as a placeholder for the user's username.", colour=accent_colour)

            # Clear reactions
            try:
                await msg.clear_reactions()
                await msg.edit(embed=embed)
            except discord.errors.Forbidden:
                await msg.delete()
                msg = await ctx.channel.send(embed=embed)

            def check(msg):
                return msg.author == ctx.author

            try:
                reply = await gwendolyn.wait_for("message", check=check)
            except asyncio.TimeoutError:
                return msg
            data[entry] = reply.content

            try:
                await reply.delete()
            except discord.errors.Forbidden:
                pass

        db.update(ctx.guild, data)

        return msg

    # function for editing a channel
    async def editChannel(msg, entry):
        # Set the channel title
        if entry == "greetChannel":
            channeltitle = "greetings"
        elif entry == "logChannel":
            channeltitle = "log"

        # Get data
        data = db.get(ctx.guild)
        if data is None:
            db.start(ctx.guild)
            data = db.get(ctx.guild)

        # Generate mention string
        if data[entry] is None:
            mention = "None"
        else:
            channel = await tcc.convert(ctx, str(data[entry]))
            mention = channel.mention

        # Generate embed

        embed = discord.Embed(title=f"Updating the {channeltitle} channel", description=f"React with the appropriate emoji:\n\n {checkmark} Set the channel\n\n{unset} Unset the channel\n\n{cancel} Cancel", colour=accent_colour)
        embed.add_field(name="Currently set to", value=mention)

        # Clear reactions
        try:
            await msg.clear_reactions()
            await msg.edit(embed=embed)
        except  discord.errors.Forbidden:
            await msg.delete()
            msg = await ctx.channel.send(embed=embed)

        # Add reactions
        await msg.add_reaction(checkmark)
        await msg.add_reaction(unset)
        await msg.add_reaction(cancel)

        def check(reaction, user):
            return reaction.emoji in [cancel, unset, checkmark] and user == ctx.author

        # Wait for input
        try:
            r, _ = await gwendolyn.wait_for("reaction_add", check=check)
        except asyncio.TimeoutError:
            return msg

        if r.emoji == unset:
            # Unset
            data[entry] = None
        elif r.emoji == cancel:
            # cancel
            return msg
        elif r.emoji == checkmark:
            # Edit message
            embed = discord.Embed(title=f"Setting the {channeltitle} channel", description="Please reply with the channel mention. (The name with a `#` in front).", colour=accent_colour)

            # Clear reactions
            try:
                await msg.clear_reactions()
                await msg.edit(embed=embed)
            except discord.errors.Forbidden:
                await msg.delete()
                msg = await ctx.channel.send(embed=embed)

            def check(msg):
                return msg.author == ctx.author

            # Wait for reply
            try:
                while True:
                    reply = await gwendolyn.wait_for("message", check=check)
                    # Check if channel is valid
                    try:
                        channel = await tcc.convert(ctx, reply.content)
                        break
                    except discord.ext.commands.BadArgument:
                        pass
            except asyncio.TimeoutError:
                return msg

            # Update
            data[entry] = channel.id

            try:
                await reply.delete()
            except discord.errors.Forbidden:
                pass

        db.update(ctx.guild, data)

        return msg


    # function for editing toggle
    def editToggle(entry):
        data = db.get(ctx.guild)
        if data is None:
            db.start(ctx.guild)
            data = db.get(ctx.guild)
        data[entry] = not data[entry]
        db.update(ctx.guild, data)



    # Generate main config embed
    async def genEmbed():
        # Get data
        data = db.get(ctx.guild)
        if data is None:
            db.start(ctx.guild)
            data = db.get(ctx.guild)

        # Work data

        if data["greetChannel"] is not None:
            greetChannel = await tcc.convert(ctx, str(data["greetChannel"]))
            greetChannelMention = greetChannel.mention
        else:
            greetChannel = None
            greetChannelMention = None

        if data["logChannel"] is not None:
            logChannel = await tcc.convert(ctx, str(data["logChannel"]))
            logChannelMention = logChannel.mention
        else:
            logChannel = None
            logChannelMention = None

        # Generate embed
        embed = discord.Embed(title="Configuration", colour=accent_colour)
        embed.add_field(name=f"{emojis[0]} Greetings & farewell channel", value=str(greetChannelMention), inline=False)
        embed.add_field(name=f"{emojis[1]} Log channel", value=str(logChannelMention), inline=False)

        embed.add_field(name=f"{emojis[2]} Greeting message", value=str(data["greetMessage"]).format(username="**USER**"), inline=False)
        embed.add_field(name=f"{emojis[3]} Farewell message", value=str(data["farewellMessage"]).format(username="**USER**"), inline=False)

        embed.add_field(name=f"{emojis[4]} Log joins", value=str(data["logJoin"]), inline=True)
        embed.add_field(name=f"{emojis[5]} Log leaves", value=str(data["logLeave"]), inline=True)

        return embed

    # Send the message
    configuremsg = await ctx.channel.send(embed=await genEmbed())

    updateReactions = True
    first = True

    # Config loop
    while True:
        # Update reactions
        emojis_avail = emojis[0:6]

        if updateReactions:
            # Clear reactions
            try:
                if not first:
                    await configuremsg.clear_reactions()
            except discord.errors.Forbidden:
                await configuremsg.delete()
                configuremsg = await ctx.channel.send(embed=await genEmbed())

            first = False
            # Add back reactions
            for emoji in emojis_avail:
                await configuremsg.add_reaction(emoji)
            await configuremsg.add_reaction(cancel)

        def check(reaction, user):
            if user == ctx.author:
                if reaction.emoji == cancel:
                    raise asyncio.TimeoutError
                return reaction.emoji in emojis_avail

        # Wait for input
        try:
            r, _ = await gwendolyn.wait_for("reaction_add", check=check)
        except asyncio.TimeoutError:
            break

        cmd = emojis_avail.index(r.emoji)

        if cmd == 0:
            configuremsg = await editChannel(configuremsg, "greetChannel")
            updateReactions = True
        elif cmd == 1:
            configuremsg = await editChannel(configuremsg, "logChannel")
            updateReactions = True
        elif cmd == 2:
            configuremsg = await editMessage(configuremsg, "greetMessage")
            updateReactions = True
        elif cmd == 3:
            configuremsg = await editMessage(configuremsg, "farewellMessage")
            updateReactions = True
        elif cmd == 4:
            editToggle("logJoin")
            try:
                await r.remove(ctx.author)
            except discord.errors.Forbidden:
                pass
            updateReactions = False
        elif cmd == 5:
            editToggle("logLeave")
            try:
                await r.remove(ctx.author)
            except discord.errors.Forbidden:
                pass
            updateReactions = False

        if updateReactions:
            # Get new emoji
            with open("emojis.txt", "r") as f:
                emojis = f.read().strip().split("\n")

            random.shuffle(emojis)

            emojis_avail = emojis[0:6]

        # Update message
        await configuremsg.edit(embed=await genEmbed())


    await configuremsg.delete()


@gwendolyn.command(checks=[config_permission])
async def forget(ctx):
    db.forget(ctx.guild)
    await ctx.channel.send("All data deleted.")


# Start bot
gwendolyn.run(config["discord_api_key"])

