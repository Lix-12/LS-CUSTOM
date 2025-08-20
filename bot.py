import os
import site
import subprocess

LOCAL_SITE_PACKAGES = "/home/container/.local/lib/python3.11/site-packages"
if not os.path.exists(LOCAL_SITE_PACKAGES):
    print("📦 Installation des packages...")
    subprocess.call([
        "pip", "install", "--prefix=/home/container/.local", "-r", "/home/container/requirements.txt"
    ])
else:
    print("✅ Packages trouvés")

site.addsitedir(LOCAL_SITE_PACKAGES)

from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands

intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ✅ Bonne méthode pour charger les cogs
@bot.event
async def setup_hook():
    try:
        await bot.load_extension("event")
        print("✅ Extension 'event' chargée")
    except Exception as e:
        print(f"❌ Impossible de charger l'extension 'event' : {type(e).__name__} - {e}")

    try:
        await bot.load_extension("client")
        print("✅ Extension 'client' chargée")
    except Exception as e:
        print(f"❌ Impossible de charger l'extension 'client' : {type(e).__name__} - {e}")

@bot.event
async def on_ready():
    print(f"🤖 Bot connecté : {bot.user}")

bot.run(os.getenv("DISCORD_TOKEN"))
