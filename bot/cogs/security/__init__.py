import logging
from .security import Security
from discord.ext.commands import Bot

def setup(bot: Bot) -> None:
    """Security cog load."""
    bot.add_cog(Security(bot))
    log.info("Cog loaded: Security")