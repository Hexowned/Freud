import logging
import socket
import asyncio
import discord
from discord.ext.commands import Bot, when_mentioned_or
from aiohttp import ClientSession, AsyncResolver, TCPConnector
from bot.constants import Bot as BotConfig

log = logging.getLogger('bot')

bot = Bot(
    command_prefix=when_mentioned_or('Freud ', 'freud ', '!'),
    activity=discord.Game(name="Commands: Freud help"),
    case_insensitive=True,
    max_messages=10_000,
)

bot.http_session = ClientSession(
    connector=TCPConnector(
        resolver=AsyncResolver(),
        family=socket.AF_INET,
    )
)

# Cog extension loaders
bot.load_extension("bot.cogs.events")
bot.load_extension("bot.cogs.information")
bot.load_extension("bot.cogs.clean")
bot.load_extension("bot.cogs.modlog")
bot.load_extension("bot.cogs.verification")

bot.run(BotConfig.token)

loop = asyncio.get_event_loop()
loop.run_until_complete(bot.close())

bot.http_session.close()
