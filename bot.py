import os
import discord
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")

class DealsBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = DealsBot()

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    print("FC Deals bot is online!")

@client.tree.command(name="ping", description="Check if the FC Deals bot is online")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏆 FC Deals bot is online!")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

client.run(TOKEN)
