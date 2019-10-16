import logging

from .verification import Verification
from discord.ext.commands import Bot

log = logging.getLogger(__name__)


def setup(bot: Bot) -> None:
    """Verification cog load."""
    bot.add_cog(Verification(bot))
    log.info("Cog loaded: Verification")
