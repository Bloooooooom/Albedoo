import imp
from random import choice, choices
import discord
from discord.ext import commands

from discord import OptionChoice, SlashCommandGroup as slashgroup

from core.checks import PermissionLevel
from core import checks


class AutoMod(commands.Cog):
    _id = "automod"

    # can also be warn ban kick mute but not implemented yet
    valid_flags = {OptionChoice("Delete", "delete"), OptionChoice(
        "Whole", "whole"), OptionChoice("Case", "case")}

    guild_ids = {}

    default_cache = {  # can also store more stuff like warn logs or notes for members if want to implement in future
        "bannedWords": {  # dictionary of word and an array of it's flags

        }
    }

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.api.get_collection(self._id)
        self.cache = {}

        self.guild_ids = self.bot.guilds

        self.bot.loop.create_task(self.load_cache())  # this only runs once xD

    async def update_db(self):  # updates database with cache
        await self.db.find_one_and_update(
            {"_id": self._id},
            {"$set": self.cache},
            upsert=True,
        )

    async def load_cache(self):
        await self.bot.wait_for_connected()

        db = await self.db.find_one({"_id": self._id})
        if db is None:
            db = self.default_cache

        self.cache = db

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        delete = False

        for banned_word in self.cache["bannedWords"]:
            whole = "whole" in self.cache["bannedWords"][banned_word]
            case = "case" in self.cache["bannedWords"][banned_word]

            if await self.find_banned_word(message, banned_word, whole, case):
                delete |= "delete" in self.cache["bannedWords"][banned_word]
                break

        # delete message
        if delete:
            await message.delete()

    async def find_banned_word(self, message, banned_word, whole=False, case=False):
        content = message.content

        if not case:
            content = content.lower()
            banned_word = banned_word.lower()

        if whole:
            words = content.split(' ')

            for word in words:
                if word == banned_word:
                    return True

            return False

        return banned_word in content

    @slashgroup.subgroup(name="blacklist", description="Manages blacklisted words.", guild_ids=guild_ids)
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def _bl(self, ctx):
        """
        Manages blacklisted words.

        First, to blacklist a word, use the command:
        - `{prefix}bl add blacklisted_word flags`

        Current flags supported include:
        - %whole (makes sure that the blacklisted word is alone)
        - %delete (deletes all blacklisted words)
        - %case (case sensitive searching)

        """

    # Adds a word to the blacklist. Takes in a word to word/phrase to blacklist first followed by flags. Flags will start with the prefix %. Possible flags include %whole, %delete, %warn, etc.
    @_bl.slash_command(name="add", description="Blacklist a word with given flags.", guild_ids=guild_ids)
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def bl_add(self, ctx, banned_word: discord.Option(str, "The word you want to ban."),
                     *flags: discord.Option(str, "The flags for the given word", choices=valid_flags)):
        """
        Blacklist a word with given flags.

        """

        if banned_word in self.cache["bannedWords"]:
            await ctx.send("Word already blacklisted")
            return

        self.cache["bannedWords"].update({banned_word: flags[0:]})
        await self.update_db()

        embed = discord.Embed(
            title="Success.",
            description=f"{banned_word} was added to the blacklist.",
            color=self.bot.main_color,
        )

        await ctx.send(embed=embed)

    @_bl.slash_command(name="remove", description="Remove a word from the blacklist.")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def bl_remove(self, ctx, banned_word: discord.Option(str, "The word you want to unban.")):
        """
        Remove a word from the blacklist.

        """

        if self.cache["bannedWords"].pop(banned_word, "Word not found") == "Word not found":
            embed = discord.Embed(
                title="Error: Argument not found",
                description=f"{banned_word} was not blacklisted",
                color=self.bot.error_color,
            )

            ctx.send(embed=embed)
            return

        await self.update_db()

        embed = discord.Embed(
            title="Success.",
            description=f"{banned_word} was removed from blacklist.",
            color=self.bot.main_color,
        )

        await ctx.send(embed=embed)

    # Lists all the banned words in the cache
    @_bl.slash_command(name="list", description="Lists all the blacklisted words and their flags.")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def bl_list(self, ctx):
        """
        Lists all the blacklisted words and their flags.
        
        """

        message = ""
        for banned_word in self.cache["bannedWords"]:
            message += banned_word + ": "

            for flag in self.cache["bannedWords"][banned_word]:
                message += flag + " "

            message += "\n"

        embed = discord.Embed(
            title="Blacklisted words:",
            description=message,
            color=self.bot.main_color
        )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(AutoMod(bot))
