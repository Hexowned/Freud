import logging
import yaml
import socket
import discord
from discord.ext.commands import Bot, when_mentioned_or
from aiohttp import ClientSession, AsyncResolver, TCPConnector
from bot.constants import Bot as BotConfig

log = logging.getLogger('bot')

bot = Bot(
    command_prefix=when_mentioned_or('Freud ', 'freud ', '!'),
    activity=discord.Game(name="MoonlightMS: Freud help"),
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

bot.run(BotConfig.token)
