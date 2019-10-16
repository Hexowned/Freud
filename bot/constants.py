import logging
import os
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Dict, List

import yaml

log = logging.getLogger(__name__)


def _env_var_constructor(loader, node):
    """
    Implements a custom YAML tag for loading optional environment variables.
    If the environment variable is set, returns the value of it.
    Otherwise, returns None
    """
    default = None

    # Check if the node is a plain string value
    if node.id == 'scalar':
        value = loader.construct_scalar(node)
        key = str(value)
    else:
        # The node value is a list
        value = loader.construct_scalar(node)

        if len(value) >= 2:
            # If we have at least two values, then we have both a key and default value
            default = value[1]
            key = value[0]
        else:
            # Otherwise, we just have a key
            key = value[0]

    return os.getenv(key, default)


def _join_var_constructor(loader, node):
    """
    Implements a custom YAML tag for concatenating other tags in the document to strings.
    This allows for a much for DRY configuration file.
    """
    fields = loader.construct_sequence(node)
    return "".join(str(x) for x in fields)


yaml.SafeLoader.add_constructor("!ENV", _env_var_constructor)
yaml.SafeLoader.add_constructor("!JOIN", _join_var_constructor)
yaml.SafeLoader.add_constructor("!REQUIRED_ENV", _env_var_constructor)

with open("config.yml", encoding="UTF-8") as f:
    _config_yaml = yaml.safe_load(f)


def check_required_keys(keys):
    """
    Verifies that keys that are set to be required are present in the loading configuration
    """
    for key_path in keys:
        lookup = _config_yaml
        try:
            for key in key_path.split('.'):
                lookup = lookup[key]
                if lookup is None:
                    raise KeyError(key)
        except KeyError:
            log.critical(
                f"A configuration for `{key_path}` is required, but was not found. "
                "Please set it in `config.yml` or setup an environment variable and try again."
            )
            raise


try:
    required_keys = _config_yaml['config']['required_keys']
except KeyError:
    pass
else:
    check_required_keys(required_keys)


class YAMLGet(type):
    """
    Implements a custom metaclass for accessing configuration data by simply accessing class attributes.
    Supports getting configuration from up to 2 levels of nested configuration through `section` and `subsection`
    """
    subsection = None

    def __getattr__(cls, name):
        name = name.lower()
        try:
            if cls.subsection is not None:
                return _config_yaml[cls.section][cls.subsection][name]
            return _config_yaml[cls.section][name]
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
class Bot(metaclass=YAMLGet):
    section = "bot"

    token: str
    prefix: str


class Cooldowns(metaclass=YAMLGet):
    section = "bot"
    subsection = "cooldowns"


class CleanMessages(metaclass=YAMLGet):
    section = "bot"
    subsection = "clean"

    message_limit: int


class Roles(metaclass=YAMLGet):
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


class Channels(metaclass=YAMLGet):
    section = "guild"
    subsection = "channels"

    chat: int
    modlog: int
    announcements: int
    verification: int
    website: int
    forum: int
    teasers: int
    updates: int
    gitupdates: int
    faq: int
    general: int
    nx_suggestions: int
    help: int
    bug_reports: int
    player_reports: int
    bot: int
    memes: int
    nsfw: int
    buy: int
    sell: int
    trade: int
    price_check: int


class Guild(metaclass=YAMLGet):
    section = "guild"

    id: int
    ignored: List[int]


class Filter(metaclass=YAMLGet):
    section = "filter"

    filter_zalgo: bool
    filter_invites: bool
    filter_domains: bool
    watch_rich_embeds: bool
    watch_words: bool
    watch_tokens: bool

    # Notifications are not expected for "watchlist" type filters
    notify_user_zalgo: bool
    notify_user_invites: bool
    notify_user_domains: bool

    ping_everyone: bool
    guild_invite_whitelist: List[int]
    domain_blacklist: List[str]
    word_watchlist: List[str]
    token_watchlist: List[str]

    channel_whitelist: List[int]
    role_whitelist: List[int]


class Colours(metaclass=YAMLGet):
    section = "style"
    subsection = "colours"

    soft_red: int
    soft_green: int
    soft_orange: int


class Emojis(metaclass=YAMLGet):
    section = "style"
    subsection = "emojis"

    status_online: str
    status_offline: str
    status_idle: str
    status_dnd: str

    bullet: str
    new: str
    pencil: str
    cross_mark: str


class Icons(metaclass=YAMLGet):
    section = "style"
    subsection = "icons"

    crown_blurple: str
    crown_green: str
    crown_red: str

    filtering: str

    guild_update: str

    hash_blurple: str
    hash_green: str
    hash_red: str

    message_bulk_delete: str
    message_delete: str
    message_edit: str

    sign_in: str
    sign_out: str

    token_removed: str

    user_ban: str
    user_unban: str
    user_update: str

    user_mute: str
    user_unmute: str
    user_verified: str

    user_warn: str

    pencil: str

    remind_blurple: str
    remind_green: str
    remind_red: str

    questionmark: str


class Categories(metaclass=YAMLGet):
    section = "guild"
    subsection = "categories"


class Keys(metaclass=YAMLGet):
    section = "keys"


class URLs(metaclass=YAMLGet):
    section = "urls"


class AntiSpam(metaclass=YAMLGet):
    section = "anti_spam"

    clean_offending: bool
    ping_everyone: bool

    punishment: Dict[str, Dict[str, int]]
    rules: Dict[str, Dict[str, int]]


class RedirectOutput(metaclass=YAMLGet):
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
