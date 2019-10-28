import logging
import socket
import asyncio
import discord
from discord.ext.commands import Bot, when_mentioned_or
from aiohttp import ClientSession, AsyncResolver, TCPConnector
from constants import Bot as BotConfig
# from bot.constants import Bot as BotConfig

log = logging.getLogger('bot')

bot = Bot(
    command_prefix=when_mentioned_or(BotConfig.prefix),
    activity=discord.Game(name="Moderating Discord"),
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
bot.load_extension("bot.cogs.antimalware")
bot.load_extension("bot.cogs.antispam")
bot.load_extension("bot.cogs.clean")
bot.load_extension("bot.cogs.code_evaluator")
bot.load_extension("bot.cogs.events")
bot.load_extension("bot.cogs.extensions")
bot.load_extension("bot.cogs.filtering")
bot.load_extension("bot.cogs.help")
bot.load_extension("bot.cogs.information")
bot.load_extension("bot.cogs.modlog")
bot.load_extension("bot.cogs.security")
bot.load_extension("bot.cogs.token_remover")
bot.load_extension("bot.cogs.utils")
bot.load_extension("bot.cogs.verification")
bot.load_extension("bot.cogs.wolfram")

bot.run(BotConfig.token)

loop = asyncio.get_event_loop()
loop.run_until_complete(bot.close())

bot.http_session.close()
