import logging
from .information import Information
from discord.ext.commands import Bot

log = logging.getLogger(__name__)


def setup(bot: Bot) -> None:
    """Information cog load"""
    bot.add_cog(Information(bot))
    log.info("Cog loaded: Information")
