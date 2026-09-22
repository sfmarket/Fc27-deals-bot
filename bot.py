import os
import discord
import requests
import json
import sqlite3
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
DB_FILE = "prices.db"


def init_database():
    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            player_id TEXT PRIMARY KEY,
            name TEXT,
            rating INTEGER,
            position TEXT,
            platform TEXT,
            price INTEGER,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


init_database()


def get_previous_price(player_id):
    conn = sqlite3.connect(DB_FILE)

    row = conn.execute(
        "SELECT price FROM prices WHERE player_id = ?",
        (player_id,)
    ).fetchone()

    conn.close()

    return row[0] if row else None


def save_player_price(
    player_id,
    name,
    rating,
    position,
    platform,
    price
):
    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        INSERT OR REPLACE INTO prices
        (player_id, name, rating, position, platform, price)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        player_id,
        name,
        rating,
        position,
        platform,
        price
    ))

    conn.commit()
    conn.close()


def load_prices():
    conn = sqlite3.connect(DB_FILE)

    rows = conn.execute(
        "SELECT player_id, price FROM prices"
    ).fetchall()

    conn.close()

    return {player_id: price for player_id, price in rows}


def save_prices(prices):
    conn = sqlite3.connect(DB_FILE)

    for player_id, price in prices.items():
        conn.execute(
            "UPDATE prices SET price = ?, scanned_at = CURRENT_TIMESTAMP WHERE player_id = ?",
            (price, player_id)
        )

    conn.commit()
    conn.close()


@client.tree.command(
    name="scan",
    description="Scan real FC27 market prices"
)
async def scan(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        players = get_fc27_players("ps", 85)

        if not players:
            await interaction.followup.send(
                "⚠️ No FC27 players were returned."
            )
            return

        old_prices = load_prices()
        new_prices = {}
        deals = []

        for player in players:
            name = player.get("name", "Unknown")
            rating = player.get("rating", "?")
            position = player.get("position", "?")
            card_type = player.get("card_type", "")
            price = player.get("price", 0)

            player_id = f"{name}|{rating}|{position}|{card_type}"

            new_prices[player_id] = price

            if player_id in old_prices:
                old_price = old_prices[player_id]

                if old_price > 0 and price < old_price:
                    drop = ((old_price - price) / old_price) * 100

                    if drop >= 5:
                        deals.append({
                            "name": name,
                            "rating": rating,
                            "position": position,
                            "price": price,
                            "old_price": old_price,
                            "drop": round(drop, 1)
                        })

        save_prices(new_prices)

        if not deals:
            await interaction.followup.send(
                f"🔎 **SCAN COMPLETE**\n\n"
                f"Scanned **{len(players)} players**.\n"
                f"💾 Prices saved.\n\n"
                f"📊 No price drops of 5%+ detected yet.\n\n"
                f"Run `/scan` again later to compare prices."
            )
            return

        deals.sort(key=lambda deal: deal["drop"], reverse=True)

        embed = discord.Embed(
            title="🔥 FC27 DEALS FOUND",
            description=f"Found {len(deals)} price drops.",
            color=discord.Color.green()
        )

        for deal in deals[:10]:
            embed.add_field(
                name=f"👤 {deal['name']} — {deal['rating']} {deal['position']}",
                value=(
                    f"💰 Now: **{deal['price']:,} coins**\n"
                    f"📊 Previous: **{deal['old_price']:,} coins**\n"
                    f"📉 Drop: **{deal['drop']}%**"
                ),
                inline=False
            )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"SCAN API ERROR: {type(e).__name__}: {e!r}")

        await interaction.followup.send(
            "❌ Couldn't complete the FC27 market scan."
        )
        
def calculate_price_drop(current_price, average_price):
    if average_price <= 0:
        return 0

    drop = ((average_price - current_price) / average_price) * 100
    return round(drop, 1)


def is_deal(current_price, average_price, minimum_drop=20):
    drop = calculate_price_drop(current_price, average_price)
    return drop >= minimum_drop
    
PARSE_API_KEY = os.getenv("PARSE_API_KEY")

def get_fc27_players(platform="ps", min_rating=85):
    url = "https://api.parse.bot/scraper/a1271aad-bcbf-4464-8762-47f1d15efa81/list_players"

    headers = {
        "X-API-Key": PARSE_API_KEY
    }

    all_players = []

    for page in range(1, 4):
        params = {
            "page": page,
            "platform": platform,
            "min_rating": min_rating
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()
        page_data = data.get("data", {})
        players = page_data.get("players", [])

        all_players.extend(players)

        if not page_data.get("next_page"):
            break

    return all_players
@client.tree.command(name="live", description="Test live FC27 market prices")
async def live(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        players = get_fc27_players("ps", 85)

        if not players:
            await interaction.followup.send(
                "⚠️ No FC27 players were returned."
            )
            return

        player = players[0]

        await interaction.followup.send(
                f"🟢 **LIVE FC27 DATA WORKING!**\n\n"
                f"👤 **{player['name']}**\n"
                f"⭐ Rating: **{player['rating']}**\n"
                f"📍 Position: **{player['position']}**\n"
                f"💰 Price: **{player['price']:,} coins**\n"
                f"🎮 Platform: **PlayStation**"
        )
        
    except Exception as e:
        print(f"FUT API ERROR: {type(e).__name__}: {e!r}")
        
        await interaction.followup.send(
            "❌ Couldn't retrieve live FC27 data."
        )
        
client.run(TOKEN)

