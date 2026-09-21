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

@client.tree.command(
    name="scan",
    description="Test the FC27 deal scanner"
)
async def scan(interaction: discord.Interaction):

test_players = [
    {
        "name": "Example Player 1",
        "current_price": 85000,
        "average_price": 120000,
        "platform": "Console"
    },
    {
        "name": "Example Player 2",
        "current_price": 95000,
        "average_price": 105000,
        "platform": "PC"
    }
]

    deals = []

    for player in test_players:
        drop = calculate_price_drop(
            player["current_price"],
            player["average_price"]
        )

        if is_deal(
            player["current_price"],
            player["average_price"]
        ):
            deals.append({
                "name": player["name"],
                "current": player["current_price"],
                "average": player["average_price"],
                "drop": drop,
                "platform": player["platform"]
            })

    if not deals:
        await interaction.response.send_message(
            "🔎 Scan complete — no deals found."
        )
        return

    embed = discord.Embed(
        title="🚨 FC27 DEAL SCAN",
        description="Potential price drops detected!",
        color=discord.Color.green()
    )

    for deal in deals:
        embed.add_field(
            name=f"🔥 {deal['name']}",
            value=(
                f"💰 Current: **{deal['current']:,}**\n"
                f"📊 Average: **{deal['average']:,}**\n"
                f"📉 Drop: **{deal['drop']}%**\n"
                f"🎮 Platform: **{deal['platform']}**"
            ),
            inline=False
        )

    await interaction.response.send_message(embed=embed)
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")


client.run(TOKEN)
def calculate_price_drop(current_price, average_price):
    if average_price <= 0:
        return 0

    drop = ((average_price - current_price) / average_price) * 100
    return round(drop, 1)


def is_deal(current_price, average_price, minimum_drop=20):
    drop = calculate_price_drop(current_price, average_price)

    return drop >= minimum_drop
