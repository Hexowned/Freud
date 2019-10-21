import logging

from discord.ext.commands import Bot, Cog, Context, NoPrivateMessage

log = logging.getLogger(__name__)


class Security(Cog):
    """Security-related helpers."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.check(self.check_not_bot)
        self.bot.check(self.check_on_guild)

    def check_not_bot(self, ctx: Context) -> bool:
        """Check if the context is a bot user."""
        return not ctx.author.bot

    def check_on_guild(self, ctx: Context) -> bool:
        """Check if the context is in a guild."""
        if ctx.guild is None:
            raise NoPrivateMessage("This command cannot be used in private messages.")
        return True
