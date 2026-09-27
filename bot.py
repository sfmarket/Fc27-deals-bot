import os
import discord
import requests
import json
import sqlite3
from discord import app_commands
from discord.ext import tasks

TOKEN = os.getenv("DISCORD_TOKEN")
MINIMUM_DROP = 5
AUTO_SCAN_MINUTES = 15
AUTO_SCAN_CHANNEL_ID = int(os.getenv("AUTO_SCAN_CHANNEL_ID", "0"))
FUTBIN_API_BASE = "https://api.parse.bot/scraper/21963078-8a17-40ff-a896-9b0b0ec3e828"

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

    if not auto_scan.is_running():
        auto_scan.start()


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
    def load_price_history():
        conn = sqlite3.connect(DB_FILE)
        rows = conn.execute("SELECT player_id, price, scanned_at FROM prices").fetchall()
        conn.close()

        return {player_id: {
            "price": price,
            "scanned_at": scanned_at
        }
        for player_id, price, scanned_at in rows
    }


def save_prices(prices):
    conn = sqlite3.connect(DB_FILE)

    for player_id, price in prices.items():
        conn.execute(
            """
            INSERT INTO prices (player_id, price, scanned_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(player_id) DO UPDATE SET
                price = excluded.price,
                scanned_at = CURRENT_TIMESTAMP
            """,
            (player_id, price)
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
        players = get_fc27_players("ps")

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

                    if drop >= MINIMUM_DROP and (old_price - price) >= 5000:
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
                f"📊 No price drops of {MINIMUM_DROP}%+ detected yet.\n\n"
                f"Run `/scan` again later to compare prices."
            )
            return

        deals.sort(key=lambda deal: (deal["old_price"] - deal["price"], deal["drop"]), reverse=True)

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

def get_fc27_players(platform="ps"):
    url = "https://api.parse.bot/scraper/a1271aad-bcbf-4464-8762-47f1d15efa81/list_players"

    headers = {
        "X-API-Key": PARSE_API_KEY
    }

    card_types = [
        "Base Icon",
        "Base Hero",
        "Team of the week"
    ]

    all_players = []

    for card_type in card_types:
        page = 1
        pages_fetched = 0

        while True:
            if pages_fetched >= 1:
                break
                
            params = {
                "page": page,
                "platform": platform,
                "card_type": card_type
            }
            
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=60
            )

            response.raise_for_status()
            pages_fetched += 1

            data = response.json()
            page_data = data.get("data", {})
            players = page_data.get("players", [])

            all_players.extend(players)

            next_page = page_data.get("next_page")

            if next_page is None:
                break

            page = next_page

        return all_players

def get_fc27_watchlist():
    url = f"{FUTBIN_API_BASE}/get_players"

    headers = {
        "X-API-Key": PARSE_API_KEY
    }

    all_players = []

    versions = [
        "ICON",
        "HERO",
        "TOTW"
    ]

    for version in versions:
        page = 1

        while True:
            params = {
                "page": page,
                "version": version,
                "fc27_only": "true"
            }

            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=60
            )

            response.raise_for_status()

            data = response.json()
            payload = data.get("data", data)

            players = payload.get("players", [])

            if not players:
                break

            all_players.extend(players)

            next_page = payload.get("next_page")

            if next_page is None:
                break

            page = next_page

    return all_players
def get_market_trends():
    url = f"{FUTBIN_API_BASE}/get_market_trends"

    headers = {
        "X-API-Key": PARSE_API_KEY
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=60
    )

    response.raise_for_status()

    return response.json()
def get_market_movers():
    data = get_market_trends()

    payload = data.get("data", data)

    return payload.get("top_movers", [])
def get_card_price(player_id):
    url = f"{FUTBIN_API_BASE}/get_fc27_player_price"

    headers = {
        "X-API-Key": PARSE_API_KEY
    }

    params = {
        "player_id": player_id
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    return data.get("data", data)
@client.tree.command(name="versions", description="Check FC27 card versions")
async def versions(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        url = f"{FUTBIN_API_BASE}/get_players"

        headers = {
            "X-API-Key": PARSE_API_KEY
        }

        versions_to_test = [
            "Hero",
            "TOTW"
        ]

        results = {}

        for version in versions_to_test:
            params = {
                "page": 1,
                "fc27_only": "true",
                "version": version
            }

            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=60
            )

            response.raise_for_status()

            data = response.json()
            payload = data.get("data", data)

            players = payload.get("players", [])

            actual_versions = sorted(
                set(
                    player.get("version")
                    for player in players
                    if player.get("version")
                )
            )

            results[version] = {
                "count": len(players),
                "actual_versions": actual_versions
            }

        print("FC27 VERSION TEST:")
        print(json.dumps(results, indent=2))

        await interaction.followup.send(
            "✅ Hero + TOTW version test completed. Check Railway logs."
        )

    except Exception as e:
        print(f"VERSION TEST ERROR: {type(e).__name__}: {e}")

        await interaction.followup.send(
            "❌ Couldn't retrieve FC27 versions."
        )
@client.tree.command(name="trends", description="Test FC27 market trends")
async def trends(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        data = get_market_trends()

        print("MARKET TRENDS RESPONSE:")
        print(json.dumps(data, indent=2))

        await interaction.followup.send(
            "✅ Market trends data retrieved. Check Railway logs."
        )

    except Exception as e:
        print(f"TRENDS ERROR: {type(e).__name__}: {e}")

        await interaction.followup.send(
            "❌ Couldn't retrieve market trends."
        )
@client.tree.command(name="live", description="Test live FC27 market prices")
async def live(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        players = get_fc27_players(platform="ps")

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
@tasks.loop(minutes=AUTO_SCAN_MINUTES)
async def auto_scan():
    try:
        players = get_fc27_players("ps")

        if not players:
            print("AUTO SCAN: No players returned.")
            return

        old_prices = load_prices()
        new_prices = {}
        deals = []

        for player in players:
            name = player.get("name", "Unknown")
            rating = player.get("rating", "?")
            position = player.get("position", "?")
            card_type = player.get("card_type", "?")
            price = player.get("price", 0)

            player_id = f"{name}|{rating}|{position}|{card_type}"

            new_prices[player_id] = price

            if player_id in old_prices:
                old_price = old_prices[player_id]

                if old_price > 0 and price < old_price:
                    drop = ((old_price - price) / old_price) * 100

                    if drop >= 5 and (old_price - price) >= 5000:
                        deals.append({
                            "name": name,
                            "rating": rating,
                            "position": position,
                            "price": price,
                            "old_price": old_price,
                            "drop": round(drop, 1)
                        })

                save_prices(new_prices)

        print(f"AUTO SCAN: Scanned {len(players)} players.")

        if deals:
            deals.sort(
                key=lambda deal: (
                    deal["old_price"] - deal["price"],
                    deal["drop"]
                ),
                reverse=True
            )

        print(f"AUTO SCAN: Found {len(deals)} deals!")

        channel = client.get_channel(AUTO_SCAN_CHANNEL_ID)

        if channel and deals:
            message = "🔥 **FC27 DEALS FOUND**\n\n"

            for deal in deals[:10]:
                message += (
                    f"👤 **{deal['name']}** — {deal['rating']} {deal['position']}\n"
                    f"💰 Now: **{deal['price']:,} coins**\n"
                    f"📈 Previous: **{deal['old_price']:,} coins**\n"
                    f"📉 Drop: **{deal['drop']}%**\n\n"
                )

            await channel.send(message)

    except Exception as e:
        print(f"AUTO SCAN ERROR: {type(e).__name__}: {e}")

client.run(TOKEN)

