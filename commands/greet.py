import discord
from discord.ext import commands
import os
from commands.blacklist import Blacklist


class Greet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command()
    async def greet(self, ctx):
        if await Blacklist.is_blacklist(ctx):
            return
        await ctx.respond(f"Hello {ctx.author.mention}!")

def setup(bot):
    bot.add_cog(Greet(bot))