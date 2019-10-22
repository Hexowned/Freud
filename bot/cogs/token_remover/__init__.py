import logging
from .token_remover import TokenRemover
from discord.ext.commands import Bot

log = logging.getLogger(__name__)


def setup(bot: Bot) -> None:
    """Token Remover cog load."""
    bot.add_cog(TokenRemover(bot))
    log.info("Cog loaded: TokenRemover")
