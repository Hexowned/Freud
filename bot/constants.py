import logging
import os
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Dict, List

import yaml

log = logging.getLogger(__name__)


with open("config.yml", encoding="UTF-8") as f:
    config_yaml = yaml.safe_load(f)


class YAML(type):
    """
    Implements a custom metaclass for accessing configuration data by simply accessing class attributes.
    Supports getting configuration from up to 2 levels of nested configuration through `section` and `subsection`
    """
    subsection = None

    def __getattr__(cls, name):
        name = name.lower()
        try:
            if cls.subsection is not None:
                return config_yaml[cls.section][cls.subsection][name]
            return config_yaml[cls.section][name]
        except KeyError:
            dotted_path = '.'.join(
                (cls.section, cls.subsection, name)
                if cls.subsection is not None else (cls.section, name)
            )
            log.critical(f"Tried accessing configuration variable at `{dotted_path}`, but it could not be found.")
            raise

    def __getitem__(cls, name):
        return cls.__getattr__(name)


# Dataclasses
class Bot(metaclass=YAML):
    section = "bot"

    token: str


class Cooldowns(metaclass=YAML):
    section = "bot"
    subsection = "cooldowns"


class CleanMessages(metaclass=YAML):
    section = "bot"
    subsection = "clean"

    message_limit: int


class Roles(metaclass=YAML):
    section = "guild"
    subsection = "roles"

    owner: int
    bot: int
    admin: int
    moderator: int
    staff: int
    nitro_booster: int
    donor: int
    nautical_twilight: int
    civil_twilight: int
    lunar_eclipse: int
    equinox: int
    verified: int
    muted: int


class Channels(metaclass=YAML):
    section = "guild"
    subsection = "channels"

    bot: int


class Guild(metaclass=YAML):
    section = "guild"

    id: int
    ignored: List[int]


class Filter(metaclass=YAML):
    section = "filter"


class Colours(metaclass=YAML):
    section = "style"
    subsection = "colours"


class Emojis(metaclass=YAML):
    section = "style"
    subsection = "emojis"

    status_online: str
    status_offline: str
    status_idle: str
    status_dnd: str


class Icons(metaclass=YAML):
    section = "style"
    subsection = "icons"


class Categories(metaclass=YAML):
    section = "guild"
    subsection = "categories"


class Keys(metaclass=YAML):
    section = "keys"


class URLs(metaclass=YAML):
    section = "urls"


class AntiSpam(metaclass=YAML):
    section = "anti_spam"

    clean_offending: bool
    ping_everyone: bool

    punishment: Dict[str, Dict[str, int]]
    rules: Dict[str, Dict[str, int]]


class RedirectOutput(metaclass=YAML):
    section = "redirect_output"

    delete_invocation: bool
    delete_delay: int


# Paths
BOT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(BOT_DIR, os.pardir))

# Default role combinations
OWNER_ROLE = Roles.owner
MODERATION_ROLES = Roles.moderator, Roles.admin, Roles.owner
STAFF_ROLES = Roles.staff, Roles.moderator, Roles.admin, Roles.owner

# Bot replies
NEGATIVE_REPLIES = [
    "Noooooo!!",
    "Nope.",
    "I'm sorry Dave, I'm afraid I can't do that.",
    "I don't think so.",
    "Not gonna happen.",
    "Out of the question.",
    "Huh? No.",
    "Nah.",
    "Naw.",
    "Not likely.",
    "No way, José.",
    "Not in a million years.",
    "Fat chance.",
    "Certainly not.",
    "NEGATORY.",
    "Nuh-uh.",
    "Not in my house!",
]

POSITIVE_REPLIES = [
    "Yep.",
    "Absolutely!",
    "Can do!",
    "Affirmative!",
    "Yeah okay.",
    "Sure.",
    "Sure thing!",
    "You're the boss!",
    "Okay.",
    "No problem.",
    "I got you.",
    "Alright.",
    "You got it!",
    "ROGER THAT",
    "Of course!",
    "Aye aye, cap'n!",
    "I'll allow it.",
]

ERROR_REPLIES = [
    "Please don't do that.",
    "You have to stop.",
    "Do you mind?",
    "In the future, don't do that.",
    "That was a mistake.",
    "You blew it.",
    "You're bad at computers.",
    "Are you trying to kill me?",
    "Noooooo!!",
    "I can't believe you've done this",
]


class Event(Enum):
    guild_channel_create = "guild_channel_create"
    guild_channel_delete = "guild_channel_delete"
    guild_channel_update = "guild_channel_update"
    guild_role_create = "guild_role_create"
    guild_role_delete = "guild_role_delete"
    guild_role_update = "guild_role_update"
    guild_update = "guild_update"

    member_join = "member_join"
    member_remove = "member_remove"
    member_ban = "member_ban"
    member_unban = "member_unban"
    member_update = "member_update"

    message_delete = "message_delete"
    message_edit = "message_edit"
