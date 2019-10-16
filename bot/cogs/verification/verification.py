import logging
from datetime import datetime

from discord import Message, NotFound, Object
from discord.ext import tasks
from discord.ext.commands import Bot, Cog, Context, command

from bot.cogs.modlog import ModLog
from bot.constants import Bot as BotConfig, Channels, Event, Roles
from bot.decorators import InChannelCheckFailure, in_channel, without_role

log = logging.getLogger(__name__)


WELCOME_MESSAGE = f"""
"""

PERIODIC_PING = (
    f"@everyone To verify that you have read our rules, please type `!accept`."
    f" Ping <@&{Roles.admin}> if you encounter any problems during the verification process."
)


class Verification(Cog):
    """User verification and role self-management."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @property
    def mod_log(self) -> ModLog:
        """Get currently loaded ModLog cog instance."""
        return self.bot.get_cog("ModLog")

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        """Check new message event for messages to the checkpoint channel and process."""
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)

        if ctx.command is not None and ctx.command.name == "accept":
            return

        if ctx.channel.id == Channels.verification:
            for role in ctx.author.roles:
                if role.id == Roles.verified:
                    log.warning(f"{ctx.author} posted '{ctx.message.content}' "
                                "in the verification channel, but is already verified.")
                    return

            log.debug(f"{ctx.author} posted '{ctx.message.content}' in the verification "
                      "channel. We are providing instructions how to verify.")
            await ctx.send(
                f"{ctx.author.mention} Please type `!accept` to verify that you accept our rules. "
                f"and gain access to the rest of the server.",
                delete_after=20
            )

            log.trace(f"Deleting the message posted by {ctx.author}")

            try:
                await ctx.message.delete()
            except NotFound:
                log.trace("No message found, it must have been deleted by another bot or by the user.")

    @command(name="accept", aliases=["verify", "verified", "accepted"], hideen=True)
    @without_role(Roles.verified)
    @in_channel(Channels.verification)
    async def accept_command(self, ctx: Context, *_) -> None:
        """Accept our rules and gain access to the rest of the server."""
        log.debug(f"{ctx.author} called !accept. Assigning the 'Lost In Space' role.")

        await ctx.author.add_roles(Object(Roles.verified), reason="Accepted the rules")

        try:
            await ctx.author.send(WELCOME_MESSAGE)
        except Exception:
            # Catch the exception, in case they have DMs off or something
            log.exception(f"Unable to send welcome message to user {ctx.author}.")

        log.trace(f"Deleting the message posted by {ctx.author}.")

        try:
            self.mod_log.ignore(Event.message_delete, ctx.message.id)

            await ctx.message.delete()
        except NotFound:
            log.trace("No message found, it must have been deleted by another bot.")

    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        """Check for and ignore any InChannelCheckFailure."""
        if isinstance(error, InChannelCheckFailure):
            error.handled = True

    @staticmethod
    def bot_check(ctx: Context) -> bool:
        """Block any command within the verification channel that is not !accept."""
        if ctx.channel.id == Channels.verification:
            return ctx.command.name == "accept"
        else:
            return True
