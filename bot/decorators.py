import logging
import random
from asyncio import Lock, sleep
from contextlib import suppress
from functools import wraps
from typing import Callable, Container, Union
from weakref import WeakValueDictionary

from discord import Colour, Embed, Member
from discord.errors import NotFound
from discord.ext import commands
from discord.ext.commands import CheckFailure, Cog, Context

from bot.constants import ERROR_REPLIES, RedirectOutput
from bot.utilities.checks import with_role_check, without_role_check

log = logging.getLogger(__name__)
