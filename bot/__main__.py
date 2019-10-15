import logging
import json
import asyncio
import socket
import discord
from discord.ext.commands import Bot, when_mentioned_or
from aiohttp import ClientSession, AsyncResolver, TCPConnector

log = logging.getLogger('bot')


class Freud(Bot):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.http_session = None
        with open('./config.json') as config_file:
            self.config = json.load(config_file)
        self.last_errors = []

    async def start(self, *args, **kwargs):
        self.http_session = ClientSession(
            connector=TCPConnector(
                resolver=AsyncResolver(),
                family=socket.AF_INET,
            )
        )
        await super().start(self.config["token"], *args, **kwargs)

    # async def close(self):
    #     await self.http_session.close()
    #     await super().close
    # This calls a coroutine, so it doesn't do anything at the moment


bot = Freud(
    command_prefix=when_mentioned_or('Freud ', 'freud ', '!'),
    activity=discord.Game(name="MoonlightMS: Freud help"),
    case_insensitive=True,
    max_messages=10_000,
)


@bot.event
async def on_ready():
    main_id = bot.config['main_guild']
    bot.main_guild = bot.get_guild(main_id) or bot.guilds[0]
    print('\nActive in these servers:')
    [print(g.name) for g in bot.guilds]
    print('\nMain Server:', bot.main_guild.name)
    print('\nFreud started successfully')
    return True


@bot.event
async def on_message(msg):
    if isinstance(msg.channel, discord.DMChannel):
        return

    await bot.process_commands(msg)


bot.run()
