import logging
from .antispam import AntiSpam
from discord.ext.commands import Bot

log = logging.getLogger(__name__)


def setup(bot: Bot) -> None:
    bot.add_cog(AntiSpam(bot))
    log.info("Cog loaded: AntiSpam")
