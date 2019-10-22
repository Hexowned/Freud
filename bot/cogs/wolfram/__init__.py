import logging
from .wolfram import Wolfram
from discord.ext.commands import Bot

log = logging.getLogger(__name__)


def setup(bot: Bot) -> None:
    bot.add_cog(Wolfram(bot))
    log.info("Cog loaded: Wolfram")
