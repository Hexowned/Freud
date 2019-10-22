import logging
from .snekbox import Snekbox
from discord.ext.commands import Bot

log = logging.getLogger(__name__)


def setup(bot: Bot) -> None:
    """Snekbox cog load."""
    bot.add_cog(Snekbox(bot))
    log.info("Cog loaded: Snekbox")
