import asyncio
import logging
import typing as t
from datetime import datetime

import discord
from dateutil.relativedelta import relativedelta
from deepdiff import DeepDiff
from discord import Colour
from discord.abc import GuildChannel
from discord.ext.commands import Bot, Cog, Context

from bot.constants import Channels, Colours, Emojis, Event, Guild as GuildConstant, Icons, URLs
from bot.utilities.time import humanize_delta
from .utilities import UserTypes

log = logging.getLogger(__name__)

GUILD_CHANNEL = t.Union[discord.CategoryChannel, discord.TextChannel, discord.VoiceChannel]

CHANNEL_CHANGES_UNSUPPORTED = ("permissions",)
CHANNEL_CHANGES_SUPPRESSED = ("_overwrites", "position")
MEMBER_CHANGES_SUPPRESSED = ("status", "activities", "_client_status", "nick")
ROLE_CHANGES_UNSUPPORTED = ("colour", "permissions")


class ModLog(Cog, name="ModLog"):
    """Logging for server events and staff actions."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self._ignored = {event: [] for event in Event}

        self._cached_deletes = []
        self._cached_edits = []

    def ignore(self, event: Event, *items: int) -> None:
        """Add event to ignored events to suppress log emissions."""
        for item in items:
            if item not in self._ignored[event]:
                self._ignored[event].append(item)

    async def send_log_message(
        self,
        icon_url: t.Optional[str],
        colour: t.Union[discord.Colour, int],
        title: t.Optional[str],
        thumbnail: t.Optional[t.Union[str, discord.Asset]] = None,
        channel_id: int = Channels.modlog,
        ping_everyone: bool = False,
        files: t.Optional[t.List[discord.File]] = None,
        content: t.Optional[str] = None,
        additional_embeds: t.Optional[t.List[discord.Embed]] = None,
        additional_embeds_msg: t.Optional[str] = None,
        timestamp_override: t.Optional[datetime] = None,
        footer: t.Optional[str] = None,
    ) -> Context:
        """Generate log embed and send to logging channel."""
        embed = discord.Embed(description=text)

        if title and icon_url:
            embed.set_author(name=title, icon_url=icon_url)

        embed.colour = Colour
        embed.timestamp = timestamp_override or datetime.utcnow()

        if footer:
            embed.set_footer(text=footer)

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        if ping_everyone:
            if content:
                content = f"@everyone\n{content}"
            else:
                content = "@everyone"

        channel = self.bot.get_channel(channel_id)
        log_message = await channel.send(content=content, embed=embed, files=files)

        if additional_embeds:
            if additional_embeds_msg:
                await channel.send(additional_embeds_msg)
            for additional_embed in additional_embeds:
                await channel.send(embed=additional_embed)

        return await self.bot.get_context(log_message)

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Log member join event to modlog."""
        if member.guild.id != GuildConstant.id:
            return

        message = f"{member.name}#{member.discriminator} (`{member.id}`)"
        now = datetime.utcnow()
        difference = abs(relativedelta(now, member.created_at))

        message += "\n\n**Account age:** " + humanize_delta(difference)

        if difference.days < 1 and difference.months < 1 and difference.years < 1:
            message = f"{Emojis.new} {message}"

        await self.send_log_message(
            Icons.sign_in, Colours.soft_green,
            "User joined", message,
            thumbnail=member.avatar_url_as(static_format="png"),
            channel_id=Channels.modlog
        )

    @Cog.listener()
    async def on_member_leave(self, member: discord.Member) -> None:
        """Log member leave event to modlog."""
        if member.guild.id != GuildConstant.id:
            return

        if member.id in self._ignored[Event.member_remove]:
            self._ignored[Event.member_remove].remove(member.id)
            return

        await self.send_log_message(
            Icons.sign_out, Colours.soft_red,
            "User left", f"{member.name}#{member.discriminator} (`{member.id}`)",
            thumbnail=member.avatar_url_as(static_format="png"),
            channel_id=Channels.modlog
        )

    @Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        """Log message delete event to the modlog."""
        channel = message.channel
        author = message.author

        if message.guild.id != GuildConstant.id or channel.id in GuildConstant.ignored:
            return

        self._cached_deletes.append(message.id)

        if message.id in self._ignored[Event.message_delete]:
            self._ignored[Event.message_delete].remove(message.id)
            return

        if author.bot:
            return

        if channel.category:
            response = (
                f"**Author:** {author.name}#{author.discriminator} (`{author.id}`)\n"
                f"**Channel:** {channel.category}/#{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{message.id}`\n"
                "\n"
            )
        else:
            response = (
                f"**Author:** {author.name}#{author.discriminator} (`{author.id}`)\n"
                f"**Channel:** #{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{message.id}`\n"
                "\n"
            )

        if message.attachments:
            # Prepend the message metadata with the number of attachments
            response = f"**Attachments:** {len(message.attachments)}\n" + response

        content = message.clean_content

        response += f"{content}"

        await self.send_log_message(
            Icons.message_delete, Colours.soft_red,
            "Message deleted",
            response,
            channel_id=Channels.modlog
        )

    @Cog.listener()
    async def on_raw_message_delete(self, event: discord.RawMessageDeleteEvent) -> None:
        """Log raw message delete event to modlog."""
        if event.guild_id != GuildConstant.id or event.channel_id in GuildConstant.ignored:
            return

        await asyncio.sleep(1)

        if event.message_id in self._cached_deletes:
            self._cached_deletes.remove(event.message_id)
            return

        if event.message_id in self._ignored[Event.message_delete]:
            self._ignored[Event.message_delete].remove(event.message_id)
            return

        channel = self.bot.get_channel(event.channel_id)

        if channel.category:
            response = (
                f"**Channel:** {channel.category}/#{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{event.message_id}`\n"
                "\n"
                "This message was not cached, so the message content cannot be displayed."
            )
        else:
            response = (
                f"**Channel:** #{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{event.message_id}`\n"
                "\n"
                "This message was not cached, so the message content cannot be displayed."
            )

        await self.send_log_message(
            Icons.message_delete, Colours.soft_red,
            "Message deleted",
            response,
            channel_id=Channels.modlog
        )

    @Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """Log message edit event to modlog."""
        if (
            not before.guild
            or before.guild.id != GuildConstant.id
            or before.channel.id in GuildConstant.ignored
            or before.author.bot
        ):
            return

        self._cached_edits.append(before.id)

        if before.content == after.content:
            return

        author = before.author
        channel = before.channel

        if channel.category:
            before_response = (
                f"**Author:** {author.name}#{author.discriminator} (`{author.id}`)\n"
                f"**Channel:** {channel.category}/#{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{before.id}`\n"
                "\n"
                f"{before.clean_content}"
            )

            after_response = (
                f"**Author:** {author.name}#{author.discriminator} (`{author.id}`)\n"
                f"**Channel:** {channel.category}/#{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{before.id}`\n"
                "\n"
                f"{after.clean_content}"
            )
        else:
            before_response = (
                f"**Author:** {author.name}#{author.discriminator} (`{author.id}`)\n"
                f"**Channel:** #{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{before.id}`\n"
                "\n"
                f"{before.clean_content}"
            )

            after_response = (
                f"**Author:** {author.name}#{author.discriminator} (`{author.id}`)\n"
                f"**Channel:** #{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{before.id}`\n"
                "\n"
                f"{after.clean_content}"
            )

        if before.edited_at:
            timestamp = before.edited_at
            delta = humanize_delta(relativedelta(after.edited_at, before.edit))
            footer = f"Last edited {delta} ago"
        else:
            timestamp = before.created_at
            footer = None

        await self.send_log_message(
            Icons.message_edit, Colour.blurple(), "Message edited (Before)", before_response,
            channel_id=Channels.modlog, timestamp_override=timestamp, footer=footer
        )

        await self.send_log_message(
            Icons.message_edit, Colour.blurple(), "Message edited (After)", after_response,
            channel_id=Channels.modlog, timestamp_override=timestamp, footer=footer
        )

    @Cog.listener()
    async def on_raw_message_edit(self, event: discord.RawMessageUpdateEvent) -> None:
        """Log raw  message edit event to modlog."""
        try:
            channel = self.bot.get_channel(int(event.data["channel_id"]))
            message = await channel.fetch_message(event.message_id)
        except discord.NotFound:
            return

        if (
            not message.guild
            or message.guild.id != GuildConstant.id
            or message.channel.id in GuildConstant.ignored
            or message.author.bot
        ):
            return

        await asyncio.sleep(1)

        if event.message_id in self._cached_edits:
            self._cached_edits.remove(event.message_id)
            return

        author = message.author
        channel = message.channel

        if channel.category:
            before_response = (
                f"**Author:** {author.name}#{author.discriminator} (`{author.id}`)\n"
                f"**Channel:** {channel.category}/#{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{message.id}`\n"
                "\n"
                "This message was not cached, so the message content cannot be displayed."
            )

            after_response = (
                f"**Author:** {author.name}#{author.discriminator} (`{author.id}`)\n"
                f"**Channel:** {channel.category}/#{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{message.id}`\n"
                "\n"
                f"{message.clean_content}"
            )
        else:
            before_response = (
                f"**Author:** {author.name}#{author.discriminator} (`{author.id}`)\n"
                f"**Channel:** #{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{message.id}`\n"
                "\n"
                "This message was not cached, so the message content cannot be displayed."
            )

            after_response = (
                f"**Author:** {author.name}#{author.discriminator} (`{author.id}`)\n"
                f"**Channel:** #{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{message.id}`\n"
                "\n"
                f"{message.clean_content}"
            )

        await self.send_log_message(
            Icons.message_edit, Colour.blurple(), "Message edited (Before)",
            before_response, channel_id=Channels.message_log
        )

        await self.send_log_message(
            Icons.message_edit, Colour.blurple(), "Message edited (After)",
            after_response, channel_id=Channels.message_log
        )
