import logging

from discord import Embed
from discord.ext.commands import Bot, Cog

from bot.constants import Channels

log = logging.getLogger(__name__)


class Events(Cog):
    # Debug logging module for simple events

    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.loop.create_task(self.startup_greeting())

    async def startup_greeting(self) -> None:
        # Announce our presence to the configured channel
        await self.bot.wait_until_ready()
        log.info("Freud connected!")

        embed = Embed(description="Connected!")
        embed.set_author(
            name="Freud",
            url="https://github.com/Nexowned/Freud",
            icon_url=(
                "https://avatars3.githubusercontent.com/u/"
                "49051663?s=400&u=c410b8b24353b442cf1c93e8bb446f7acf2d84bc&v=4"
            )
        )

        await self.bot.get_channel(Channels.bot).send(embed=embed)
