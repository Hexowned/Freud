import logging
import re
from datetime import datetime
from ssl import CertificateError
from typing import Union

import discord
import dateutil.parser
import dateutil.tz
from dateutil.relativedelta import relativedelta
from aiohttp import ClientConnectorError
from discord.ext.commands import BadArgument, Context, Converter


log = logging.getLogger(__name__)


