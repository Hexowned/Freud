import logging

from discord.ext.commands import Bot

from .modlog import ModLog

log = logging.getLogger(__name__)


def setup(bot: Bot) -> None:
    """Load the modlog cog"""
    bot.add_cog(ModLog(bot))
    log.info("Cog loaded: ModLog")
