import logging
from .clean import Clean
from discord.ext.commands import Bot

log = logging.getLogger(__name__)


def setup(bot: Bot) -> None:
    """Clean cog load."""
    bot.add_cog(Clean(bot))
    log.info("Cog loaded: Clean")
