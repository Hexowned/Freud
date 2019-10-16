import logging
import textwrap
import typing as t
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import Context

from bot.constants import Colours, Icons
from bot.converters import Duration, ISODateTime

log = logging.getLogger(__name__)


UserTypes = t.Union[discord.Member, discord.User]
MemberObject = t.Union[UserTypes, discord.Object]
Infraction = t.Dict[str, t.Union[str, int, bool]]
Expiry = t.Union[Duration, ISODateTime]


def proxy_user(user_id: str) -> discord.Object:
    """
    Create a proxy user object from the given id.
    Used when a Member or User object cannot be resolved.
    """
    try:
        user_id = int(user_id)
    except ValueError:
        raise commands.BadArgument

    user = discord.Object(user_id)
    user.mention = user.id
    user.avatar_url_as = lambda static_format: None

    return user


async def send_private_embed(user: UserTypes, embed: discord.Embed) -> bool:
    """
    A helper method for sending an embed to a user's DM
    Returns a boolean indicator of DM success.
    """
    try:
        await user.send(embed=embed)
        return True
    except (discord.HTTPException, discord.Forbidden, discord.NotFound):
        log.debug(
            f"Infraction-related information could not be sent to user {user} ({user.id}). "
            "The user either could not be retrieved or probably disabled their DMs."
        )

        return False
