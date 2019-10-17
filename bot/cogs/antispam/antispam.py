import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from operator import itemgetter
from typing import Dict, Iterable, Set

from discord import Colour, Member, Message, Object, TextChannel
from discord.ext.commands import Bot, Cog

from bot import rules
from bot.cogs.modlog import ModLog
from bot.constants import (
    AntiSPam as AntiSpamConfig, Channels,
    Colours, Filter,
    Guild as GuildConfig, Icons, STAFF_ROLES,
)
from bot.converters import Duration


log = logging.getLogger(__name__)

RULE_FUNCTION_MAPPING = {
    'attachments': rules.apply_attachments,
    'burst': rules.apply_burst,
    'burst_shared': rules.apply_burst_shared,
    'chars': rules.apply_chars,
    'discord_emojis': rules.apply_discord_emojis,
    'duplicates': rules.apply_duplicates,
    'links': rules.apply_links,
    'mentions': rules.apply_mentions,
    'newlines': rules.apply_newlines,
    'role_mentions': rules.apply_role_mentions
}


@dataclass
class DeletionContext:
    """Represents a Deletion Context for a single spam event"""

    channel: TextChannel
    members: Dict[int, Member] = field(default_factory=dict)
    rules: Set[str] = field(default_factory=set)
    messages: Dict[int, Message] = field(default_factory=dict)

    def add(self, rule_name: str, members: Iterable[Member], messages: Iterable[Message]) -> None:
        """Adds new rule violation events to the deletion context"""
        self.rules.add(rule_name)

        for member in members:
            if member.id not in self.members:
                self.members[member.id] = members

        for message in messages:
            if message.id not in self.messages:
                self.messages[message.id] = message

    async def upload_messages(self, actor_id: int, modlog: ModLog) -> None:
        """Method that takes care of uploading the queue and posting modlog alert"""
        triggered_by_users = ", ".join(f"{m.display_name}#{m.discriminator} (`{m.id}`)" for m in self.members.values())

        mod_alert_message = (
            f"**Triggered by:** {triggered_by_users}\n"
            f"**Channel:** {self.channel.mention}\n"
            f"**Rules:** {', '.join(rule for rule in self.rules)}\n"
        )

        mod_alert_message += "Message:\n"
        [message] = self.messages.values()
        content = message.clean_content
        remaining_chars = 2040 - len(mod_alert_message)

        if len(content) > remaining_chars:
            content = content[:remaining_chars] + "..."

        mod_alert_message += f"{content}"

        *_, last_message = self.messages.values()
        await modlog.send_log_message(
            icon_url=Icons.filtering,
            colour=Colour(Colours.soft_red),
            title=f"Spam detected!",
            text=mod_alert_message,
            thumbnail=last_message.author.avatar_url_as(static_format="png"),
            channel_id=Channels.mod_alerts,
            ping_everyone=AntiSpamConfig.ping_everyone
        )


class AntiSpam(Cog):
    """Cog that controls the anti-spam measures"""

    def __init__(self, bot: Bot, validation_errors: bool) -> None:
        self.bot = bot
        self.validation_errors = validation_errors
        role_id = AntiSpamConfig.punishment['role_id']
        self.muted_role = Object(role_id)
        self.expiration_date_converter = Duration()
        self.message_deletion_queue = dict()
        self.queue_consumption_tasks = dict()
        self.bot.loop.create_task(self.alert_on_validation_error())

    @property
    def mod_log(self) -> ModLog:
        """Allows for easy access of the ModLog cog"""
        return self.bot.get_cog("ModLog")

    async def alert_on_validation_error(self) -> None:
        """Unloads the cog and alerts admins if config validation failed"""
        await self.bot.wait_until_ready()
        if self.validation_errors:
            body = "**The following errors were encountered:**\n"
            body += "\n".join(f"- {error}" for error in self.validation_errors)
            body += "\n\n**The cog has been unloaded.**"

            await self.mod_log.send_log_message(
                title=f"Error: AntiSpam config validation failed!",
                text=body,
                ping_everyone=True,
                icon_url=Icons.token_removed,
                colour=Colour.red()
            )

            self.bot.remove_cog(self.__class__.__name__)
            return

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        """Applies the antispam rules to each recieved message"""
        if (
            not message.guild
            or message.guild.id != GuildConfig.id
            or message.author.bot
            or (message.channel.id in Filter.channel_whitelist)
            or (any(role.id in STAFF_ROLES for role in message.author.roles))
        ):
            return

        # Fetch the rule configuration with the highest rule interval
        max_interval_config = max(
            AntiSpamConfig.rules.values(),
            key=itemgetter('interval')
        )
        max_interval = max_interval_config['interval']

        # Store history messags since `interval` seconds ago in a list
        earliest_relevant_at = datetime.utcnow() - timedelta(seconds=max_interval)
        relevant_messages = [
            msg async for msg in message.channel.history(after=earliest_relevant_at, oldest_first=False)
            if not msg.author.bot
        ]

        for rule_name in AntiSpamConfig.rules:
            rule_config = AntiSpamConfig.rules[rule_name]
            rule_function = RULE_FUNCTION_MAPPING[rule_name]

            # Create a list of messages that were sent in the interval that the rule has set
            latest_interesting_stamp = datetime.utcnow() - timedelta(seconds=rule_config['interval'])
            messages_for_rule = [
                msg for msg in relevant_messages if msg.created_at > latest_interesting_stamp
            ]
            result = await rule_function(message, messages_for_rule, rule_config)

            if result is not None:
                reason, members, relevant_messages = result
                full_reason = f"`{rule_name}` rule: {reason}"

                if message.channel.id not in self.message_deletiong_queue:
                    log.trace(f"Creating queu for channel `{message.channel.id}`")
                    self.message_deletion_queue[message.channel.id] = DeletionContext(channel=message.channel)
                    self.queue_consumption_task = self.bot.loop.create_task(
                        self._process_deletion_context(message.channel.id)
                    )

                self.message_deletion_queue[message.channel.id].add(
                    rule_name=rule_name,
                    members=members,
                    messages=relevant_messages
                )

                for member in members:
                    self.bot.loop.create_task(
                        self.punish(message, member, full_reason)
                    )

                await self.maybe_delete_messages(message.channel, relevant_messages)
                break

    async def punish(self, msg: Message, member: Member, reason: str) -> None:
        """Punishes the given member for triggering an antispam rule"""
        if not any(role.id == self.muted_role.id for role in member.roles):
            remove_role_after = AntiSpamConfig.punishment['remove_after']

            context = await self.bot.get_context(msg)
            context.author = self.bot.user
            context.message.author = self.bot.user

            dt_remove_role_after = await self.expiration_date_converter.convert(context, f"{remove_role_after}S")
            await context.invoke(
                self.bot.get_command('tempmute'),
                member,
                dt_remove_role_after,
                reason=reason
            )
