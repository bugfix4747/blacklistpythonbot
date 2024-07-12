import discord
from discord.ext import commands, tasks
import aiosqlite
from datetime import datetime, timedelta
from discord.utils import format_dt

class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.creators = [852888051432685608]
        self.db = "blacklist.db"

    @commands.Cog.listener()
    async def on_ready(self):
        async with aiosqlite.connect(self.db) as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS blacklist (
                                user_id INTEGER PRIMARY KEY,
                                reason TEXT,
                                moderator_id INTEGER,
                                expires_at DATETIME
                                )''')
            await db.commit()
        self.check_blacklist_loop.start()

    def calculate_expiry(self, duration, duration_type):
        now = datetime.utcnow()
        if duration_type == "Seconds":
            return now + timedelta(seconds=duration)
        elif duration_type == "Minutes":
            return now + timedelta(minutes=duration)
        elif duration_type == "Hours":
            return now + timedelta(hours=duration)
        elif duration_type == "Days":
            return now + timedelta(days=duration)
        elif duration_type == "Weeks":
            return now + timedelta(weeks=duration)
        elif duration_type == "Months":
            return now + timedelta(days=duration*30)
        elif duration_type == "Years":
            return now + timedelta(days=duration*365)
        elif duration_type == "Lifetime":
            return None
    

    @tasks.loop(minutes=1)
    async def check_blacklist_loop(self):
        async with aiosqlite.connect(self.db) as db:
            result = await db.execute('SELECT * FROM blacklist')
            rows = await result.fetchall()
            for row in rows:
                if row[3] != "Lifetime":
                    expires_at = datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S")
                    if datetime.utcnow() > expires_at:
                        await db.execute('DELETE FROM blacklist WHERE user_id = ?', (row[0],))
                        await db.commit()

    @staticmethod
    async def is_blacklist(ctx):
        async with aiosqlite.connect("blacklist.db") as db:
            cursor = await db.execute("SELECT * FROM blacklist WHERE user_id = ?", (ctx.author.id,))
            result = await cursor.fetchone()
        if result:
            formatted_time = datetime.strptime(result[3], "%Y-%m-%d %H:%M:%S")
            timestamp = format_dt(formatted_time, "R")
            embed = discord.Embed(title="You are Banned!", description=f"""
                **Oh, it looks like you got banned from the bot**
                > **Expires At:** {timestamp}
                > **Moderator:** {ctx.guild.get_member(result[2]).mention}
                
                **Reason:**
                ```{result[1]}```
            """, color=discord.Color.yellow())
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Appeal", url="https://discord.gg/invite"))
            await ctx.respond(embed=embed, view=view)
            return True
        else:
            return False

    @commands.slash_command(name="add-blacklist", description="Add user to blacklist")
    async def add_blacklist(self, ctx, user: discord.Member, duration: int, duration_type: discord.Option(str, choices=["Seconds", "Minutes", "Hours", "Days", "Weeks", "Months", "Years", "Lifetime"]), *, reason: str):
        if ctx.author.id not in self.creators:
            await ctx.respond("You don't have permission to use this command.", ephemeral=True)
            return
        if user.id == ctx.author.id:
            await ctx.respond("You can't blacklist yourself.", ephemeral=True)
            return

        expires_at = self.calculate_expiry(duration, duration_type)
        expires_at_str = expires_at.strftime("%Y-%m-%d %H:%M:%S") if expires_at else "Lifetime"

        async with aiosqlite.connect(self.db) as db:
            await db.execute('INSERT OR REPLACE INTO blacklist (user_id, reason, moderator_id, expires_at) VALUES (?, ?, ?, ?)', 
                             (user.id, reason, ctx.author.id, expires_at_str))
            await db.commit()

        formatted_time = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
        timestamp = format_dt(formatted_time, "R")
        embed = discord.Embed(title="User Blacklisted", description=f"""
        User: {user.mention}
        Moderator: {ctx.author.mention}
        Expires At: {timestamp}

        Reason: ```{reason}```
        """, color=0x00FF04)
        await ctx.respond(embed=embed)


    @commands.slash_command(name="remove-blacklist", description="Remove user from blacklist")
    async def remove_blacklist(self, ctx, user: discord.Member):
        if ctx.author.id not in self.creators:
            await ctx.respond("You don't have permission to use this command.", ephemeral=True)
            return
        if user.id == ctx.author.id:
            await ctx.respond("You can't remove yourself from the blacklist.", ephemeral=True)
            return

        async with aiosqlite.connect(self.db) as db:
            await db.execute('DELETE FROM blacklist WHERE user_id = ?', (user.id,))
            await db.commit()
            result = await db.execute('SELECT * FROM blacklist WHERE user_id = ?', (user.id,))
            row = await result.fetchone()
        if not row:
            await ctx.respond(f"{user.mention} is not in the blacklist.", ephemeral=True)
            return
        else:
            embed = discord.Embed(title="User Removed from Blacklist", description=f"{user.mention} has been removed from the blacklist.", color=0x00FF00)
            await ctx.respond(embed=embed)


    @commands.slash_command(name="blacklist-info", description="Show user blacklist")
    async def blacklist_info(self, ctx, user: discord.Member = None):
        if user is None:
            user = ctx.author

        async with aiosqlite.connect(self.db) as db:
            result = await db.execute('SELECT * FROM blacklist WHERE user_id = ?', (user.id,))
            row = await result.fetchone()
        if not row:
            await ctx.respond(f"{user.mention} is not in the blacklist.", ephemeral=True)
            return
        else:
            formatted_time = datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S")
            timestamp = format_dt(formatted_time, "R")
            embed = discord.Embed(title="User Blacklist Info", description=f"""
            User: {user.mention}
            Moderator: <@{row[2]}>
            Expires At: {timestamp}

            Reason: ```{row[1]}```
            """, color=0xFFB600)
            if user.avatar:
                embed.set_thumbnail(url=user.avatar.url)
            else:
                embed.set_thumbnail(url=user.default_avatar.url)
            await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Blacklist(bot))
