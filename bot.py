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


@client.tree.command(
    name="ping",
    description="Check if the FC Deals bot is online"
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🏆 FC Deals bot is online!"
    )


@client.tree.command(
    name="deal",
    description="Post an FC27 deal"
)
@app_commands.describe(
    player="Player/item name",
    price="Current price",
    old_price="Previous price",
    platform="Platform, e.g. PS5, Xbox or PC"
)
async def deal(
    interaction: discord.Interaction,
    player: str,
    price: int,
    old_price: int,
    platform: str
):
    saving = old_price - price

    if old_price > 0:
        discount = round((saving / old_price) * 100)
    else:
        discount = 0

    embed = discord.Embed(
        title="🏆 FC27 DEAL",
        description=f"**{player}**",
        color=discord.Color.green()
    )

    embed.add_field(
        name="💰 Current Price",
        value=f"**{price:,} coins**",
        inline=True
    )

    embed.add_field(
        name="📉 Previous Price",
        value=f"{old_price:,} coins",
        inline=True
    )

    embed.add_field(
        name="🔥 Saving",
        value=f"**{saving:,} coins ({discount}% OFF)**",
        inline=False
    )

    embed.add_field(
        name="🎮 Platform",
        value=platform,
        inline=True
    )

    embed.set_footer(
        text="FC27 Deals • Automated Deal Finder"
    )

    await interaction.response.send_message(embed=embed)


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")


client.run(TOKEN)
