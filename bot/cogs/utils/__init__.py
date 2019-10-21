import logging
from .utils import Utils
from discord.ext.commands import Bot


def setup(bot: Bot) -> None:
    """Utils cog load."""
    bot.add_cog(Utils(bot))
    log.info("Cog loaded: Utils")
