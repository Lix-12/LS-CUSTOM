# client.py (fichier Cog)
from discord.ext import commands

class ClientEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Bot connecté avec succès : {self.bot.user}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Exemple de réponse simple
        if message.content.lower() == "ping":
            await message.channel.send("pong")

async def setup(bot):
    await bot.add_cog(ClientEvents(bot))

