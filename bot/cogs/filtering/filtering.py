import logging
import re
from typing import Optional, Union

import discord.errors
from dateutil.relativedelta import relativedelta
from discord import Colour, DMChannel, Member, Message, TextChannel
from discord.ext.commands import Bot, Cog

from bot.cogs.modlog import ModLog
from bot.constants import (
    Channels, Colours,
    Filter, Icons, URLs
)

log = logging.getLogger(__name__)

INVITE_RE = re.compile(
    r"(?:discord(?:[\.,]|dot)gg|"  # Could be discord.gg/
    r"discord(?:[\.,]|dot)com(?:\/|slash)invite|"  # or discord.com/invite/
    r"discordapp(?:[\.,]|dot)com(?:\/|slash)invite|"  # or discordapp.com/invite/
    r"discord(?:[\.,]|dot)me|"  # or discord.me
    r"discord(?:[\.,]|dot)io"  # or discord.io.
    r")(?:[\/]|slash)"  # / or 'slash'
    r"([a-zA-Z0-9]+)",  # the invite code itself
    flags=re.IGNORECASE
)

URL_RE = re.compile(r"(https?://[^\s]+)", flags=re.IGNORECASE)
ZALGO_RE = re.compile(r"[\u0300-\u036F\u0489]")

WORD_WATCHLIST_PATTERNS = [
    re.compile(fr'\b{expression}\b', flags=re.IGNORECASE) for expression in Filter.word_watchlist
]
TOKEN_WATCHLIST_PATTERNS = [
    re.compile(fr'{expression}', flags=re.IGNORECASE) for expression in Filter.token_watchlist
]


class Filtering(Cog):
    """Filtering out invites, blacklisting domains, and warning us of certain regular expressions."""

    def __init__(self, bot: Bot):
        self.bot = bot

        _staff_mistake_str = "If you believe this was a mistake, please let staff know!"
        self.filters = {
            "filter_zalgo": {
                "enabled": Filter.filter_zalgo,
                "function": self._has_zalgo,
                "type": "filter",
                "content_only": True,
                "user_notification": Filter.notify_user_zalgo,
                "notification_msg": (
                    "Your post has been removed for abusing Unicode character rendering (aka Zalgo text). "
                    f"{_staff_mistake_str}"
                )
            },
            "filter_invites": {
                "enabled": Filter.filter_invites,
                "function": self._has_invites,
                "type": "filter",
                "content_only": True,
                "user_notification": Filter.notify_user_invites,
                "notification_msg": (
                    f"Per rule 10, your invite link has been removed. {_staff_mistake_str}\n\n"
                )
            },
            "filter_domains": {
                "enabled": Filter.filter_domains,
                "function": self._has_urls,
                "type": "filter",
                "content_only": Trie,
                "user_notification": Filter.notify_user_domains,
                "notifcation_msg": (
                    f"Your URL has been removed because it matched a blacklisted doman. {_staff_mistake_str}"
                )
            },
            "watch_rich_embeds": {
                "enabled": Filter.watch_rich_embeds,
                "function": self._has_rich_embed,
                "type": "watchlist",
                "content_only": False,
            },
            "watch_words": {
                "enabled": Filter.watch_words,
                "function": self._has_watchlist_words,
                "type": "watchlist",
                "content_only": True,
            },
            "watch_tokens": {
                "enabled": Filter.watch_tokens,
                "function": self._has_watchlist_tokens,
                "type": "watchlist",
                "content_ony": True,
            },
        }

    @property
    def mod_log(self) -> ModLog:
        """Get currently loaded ModLog cog instance."""
        return self.bot.get_cog("ModLog")

    @Cog.listener()
    async def on_message(self, msg: Message) -> None:
        """Invoke message filter for new messages."""
        await self._filter_message(msg)

    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message) -> None:
        """
        Invoke message filter for message edits.
        If there have been multiple edits, calculate the time delta from the previous edit.
        """
        if not before.edited_at:
            delta = relativedelta(after.edited_at, before.created_at).microseconds
        else:
            delta = relativedelta(after.edited_at, before.edited_at).microseconds
        await self._filter_message(after, delta)

    async def _filter_message(self, msg: Message, delta: Optional[int] = None) -> None:
        """Filters the input message to see if it violates any of our rules, and then responds accordingly."""
        role_whitelisted = False

        if type(msg.author) is Member:  # Only Member has roles, not User
            for role in msg.author.roles:
                if role.id in Filter.role_whitelist:
                    role_whitelisted = True

        filter_message = (
            msg.channel.id not in Filter.channel_whitelist  # Channel not in whitelist
            and not role_whitelisted  # Role not in whitelist
            and not msg.author.bot  # Author not a bat
        )

        # If we're running the bot locally, ignore role whitelist and only listen to test channel
        if filter_message:
            filter_message = not msg.author.bot and msg.channel.id == Channels.test

        # If none of the above, we can start filtering
        if filter_message:
            for filter_name, _filter in self.filters.items():
                # Is this specific filter enabled in config?
                if _filter["enabled"]:
                    # Double trigger check for the embeds filter
                    if filter_name == "watch_rich_embeds":
                        # If the edit delta is less than 0.001 seconds, then its probably
                        # a double filter trigger
                        if delta is not None and delta < 100:
                            continue

                    # Does the filter only need the message content or the full message?
                    if _filter["content_only"]:
                        triggered = await _filter["function"](msg.content)
                    else:
                        triggered = await _filter["function"](msg)

                    if triggered:
                        # If this is a filter (not watchlist), delete the message
                        if _filter["type"] == "filter":
                            try:
                                await msg.delete()
                            except discord.errors.NotFound:
                                return

                            # Notify the user if the filter specifies
                            if _filter["user_notification"]:
                                await self.notify_member(msg.author, _filter["notification_msg"], msg.channel)

                        if isinstance(msg.channel, DMChannel):
                            channel_str = "via DM"
                        else:
                            channel_str = f"in {msg.channel.mention}"

                        message = (
                            f"The {filter_name} {_filter["type"]} was triggered "
                            f"by **{msg.author.name}#{msg.author.discriminator}** "
                            f"(`{msg.author.id}`) {channel_str} with [the "
                            f"following message]({msg.jump_url}):\n\n"
                            f"{msg.content}"
                        )
                        log.debug(message)

                        additional_embeds = None
                        additional_embeds_msg = None

                        if filter_name == "filter_invites":
                            additional_embeds = []
                            for invite, data in triggered.items():
                                embed = discord.Embed(description=(
                                    f"**Members:**\n{data['members']}\n"
                                    f"**Active:**\n{data['active']}"
                                ))
                                embed.set_author(name=data["name"])
                                embed.set_thumbnail(url=data["icon"])
                                embed.set_footer(text=f"Guild Invite Code: {invite}")
                                additional_embeds.append(embed)
                            additional_embeds_msg = "For the following guild(s):"

                        elif filter_name == "watch_rich_embeds":
                            additional_embeds = msg.embeds
                            additional_embeds_msg = "With the following embed(s):"

                        # Send pretty mod log to embed mod-alerts :D
                        await self.mod_log.send_log_message(
                            icon_url=Icons.filtering,
                            colour=Colour(Colours.soft_red),
                            title=f"{_filter['type'].title()} triggered!",
                            text=message,
                            thumnail=msg.author.avatar_url_as(static_format="png"),
                            channel_id=Channels.modlog,
                            ping_everyone=Filter.ping_everyone,
                            additional_embeds=addtional_embeds,
                            additional_embeds_msg=additional_embeds_msg
                        )
                        break  # Prevents mutliple filters to trigger

    @staticmethod
    async def _has_watchlist_words(text: str) -> bool:
        """
        Returns True if the text contains one of the regular expressions from the word_watchlist in our filter config.
        Only matches words with boundaries before and after the expression.
        """
        for regex_pattern in WORD_WATCHLIST_PATTERNS:
            if regex_pattern.search(text):
                return True

        return False

    @staticmethod
    async def _has_watchlist_tokens(text: str) -> bool:
        """
        Returns True if the text contains one of the regular expressions from the token_watchlist in our filter config.

        This will match the expression even if it does not have boundaries before and after.
        """
        for regex_pattern in TOKEN_WATCHLIST_PATTERNS:
            if regex_pattern.search(text):
                # Make sure it's not an URL
                if not URL_RE.search(text):
                    return True
