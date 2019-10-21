import logging
from .filtering import Filtering
from discord.ext.commands import Bot

def setup(bot: Bot) -> None:
    """Filtering cog load."""
    bot.add_cog(Filtering(bot))
    log.info("Cog loaded: Filtering")
