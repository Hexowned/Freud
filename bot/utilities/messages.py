import asyncio
import contextlib
from io import BytesIO
from typing import Optional, Sequence, Union

from discord import Client, Embed, File, Member, Message, Reaction, TextChannel, Webhook
from discord.abc import Snowflake
from discord.errors import HTTPException

from bot.constants import Emojis
