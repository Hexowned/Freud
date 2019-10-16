import asyncio
import itertools
from collections import namedtuple
from contextlib import suppress
from typing import Union

from discord import Colour, Embed, HTTPException, Message, Reaction, User
from discord.ext import commands
from discord.ext.commands import Bot, CheckFailure, Cog as DiscordCog, Command, Context
from fuzzywuzzy import fuzz, process

from bot import constants
from bot.constants import Channels, STAFF_ROLES
from bot.decorators import redirect_output
from bot.pagination import (
    DELETE_EMOJI, FIRST_EMOJI, LAST_EMOJI,
    LEFT_EMOJI, LinePaginator, RIGHT_EMOJI,
)

REACTIONS = {
    FIRST_EMOJI: 'first',
    LEFT_EMOJI: 'back',
    RIGHT_EMOJI: 'next',
    LAST_EMOJI: 'end',
    DELETE_EMOJI: 'stop'
}

Cog = namedtuple('Cog', ['name', 'description', 'commands'])


class HelpQueryNotFound(ValueError):
    """
    Raised when a HelpSession Query doesn't match a command or cog.
    Contains the custom attribute of ``possible_matches``.
    Instances of this object contain a dictionary of any command(s) that were close to matching
    the query, where keys are the possible matched command names and values are the likeness match scores.
    """

    def __init__(self, arg: str, possible_matches: dict = None):
        super().__init__(arg)
        self.possible_matches = possible_matches


class HelpSession:
    """
    An interactive session for bot and command help output.

    Expected attributes include:
        * title: str
            The title of the help message.
        * query: Union[discord.ext.commands.Bot, discord.ext.commands.Command]
        * description: str
            The description of the query.
        * pages: list[str]
            A list of the help content split into manageable pages.
        * message: `discord.Message`
            The message object that's showing the help contents.
        * destination: `discord.abc.Messageable`
            Where the help message is to be sent to.

    Cogs can be grouped into custom categories. All cogs with the same category will be displayed
    under a single category name in the help output. Custom categories are defined inside the cogs
    as a class attribute named `category`. A description can also be specified with the attribute
    `category_description`. If a description is not found in at least one cog, the default will be
    the regular description (class docstring) of the first cog found in the category.
    """

    def __init__(
        self,
        ctx: Context,
        *command,
        cleanup: bool = False,
        only_can_run: bool = False,
        show_hidden: bool = False,
        max_lines: int = 15
    ):
        """Creates an instance of the HelpSession class."""
        self._ctx = ctx
        self._bot = ctx.bot
        self.title = "Command Help"

        # set the query details for the session
        if command:
            query_str = ' '.join(command)
            self.query = self._get_query(query_str)
            self.description = self.query.description or self.query.help
        else:
            self.query = ctx.bot
            self.description = self.query.description or self.query.help

        self.author = ctx.author
        self.destination = ctx.channel

        # set the config for the session
        self._cleanup = cleanup
        self._only_can_run = only_can_run
        self._show_hidden = show_hidden
        self._max_lines = max_lines

        # init session states
        self._pages = None
        self._current_page = 0
        self.message = None
        self._timeout_task = None
        self.reset_timeout()

    def _get_query(self, query: str) -> Union[Command, Cog]:
        """Attempts to match the provided query with a valid command or cog."""
        command = self._bot.get_command(query)
        if command:
            return command

        # Find all cog categories that match.
        cog_matches = []
        description = None
        for cog in self._bot.cogs.values():
            if hasattr(cog, "category") and cog.category == query:
                cog_matches.append(cog)
                if hasattr(cog, "category_description"):
                    description = cog.category_description

        # Try to search by cog name if no categories match.
        if not cog_matches:
            cog = self._bot.cogs.get(query)

            # Don't consider it a match if the cog has a category.
            if cog and not hasattr(cog, "category"):
                cog_matches = [cog]

        if cog_matches:
            cog = cog_matches[0]
            cmds = (cog.get_command() for cog in cog_matches)

            return Cog(
                name=cog.category if hasattr(cog, "category") else cog.qualified_name,
                description=description or cog.description,
                commands=tuple(itertools.chain.from_iterable(cmds))
            )

        self._handle_not_found(query)

    def _handle_not_found(self, query: str) -> None:
        """
        Handles when a query does not match a valid command or cog.
        Will pass on possible close matches along with the `HelpQueryNotFound` exception.
        """
        # Combine command and cog names
        choices = list(self._bot.all_commands) + list(self._bot.cogs)

        result = process.extractBests(query, choices, scorer=fuzz.ratio, score_cutoff=90)

        raise HelpQueryNotFound(f'Query "{query}" not found.', dict(result))

    async def timeout(self, second: int = 30) -> None:
        """Waits for a set number of seconds, then stops the help session."""
        await asyncio.sleep(1)
        await self.stop()

    def reset_timeout(self) -> None:
        """Cancels the original timeout task and sets it again from the start."""
        # cancel original if it exists
        if self._timeout_task:
            if not self._timeout_task.cancelled():
                self._timeout_task.cancel()

        # recreate the timeout task
        self._timeout_task = self._bot.loop.create_task(self.timeout())

    async def on_reaction_add(self, reaction: Reaction, user: User) -> None:
        """Event handler for when reactions are added on the help message."""
        # ensure it was the relevant session message
        if reaction.message.id != self.message.id:
            return

        # ensure it was the session author who reacted
        if user.id != self.author.id:
            return

        emoji = str(reaction.emoji)

        # check if valid action
        if emoji not in REACTIONS:
            return

        self.reset_timeout()

        # Run relevant action method
        action = getattr(self, f'do_{REACTIONS[emoji]}', None)
        if action:
            await action()

        # remove the added reaction to prep for re-use
        with suppress(HTTPException):
            await self.message.remove_reaction(reaction, user)

    async def on_message_delete(self, message: Message) -> None:
        """Closes the help session when the help message is deleted."""
        if message.id == self.message.id:
            await self.stop()

    async def prepare(self) -> None:
        """Sets up the help session pages, events, message and reactions."""
        # create paginated content
        await self.build_pages()

        # setup listeners
        self._bot.add_listener(self.on_reaction_add)
        self._bot.add_listener(self.on_message_delete)

        # send the help message
        await self.update_page()
        self.add_reactions()

    def add_reactions(self) -> None:
        """Adds the relevant reactions to the help message based on if pagination is required."""
        # if paginating
        if len(self._pages) > 1:
            for reaction in REACTIONS:
                self._bot.loop.create_task(self.message.add_reactions(reaction))

        # if single-page
        else:
            self._bot.loop.create_task(self.message.add_reaction(DELETE_EMOJI))

    def _category_key(self, cmd: Command) -> str:
        """
        Returns a cog name of a given command for use as a key for `sorted` and `groupby`.
        A zero width space is used as a prefix for results with no cogs to force them last in ordering.
        """
        if cmd.cog:
            try:
                if cmd.cog.category:
                    return f'**{cmd.cog.category}**'
            except AttributeError:
                pass

            return f'**{cmd.cog_name}**'
        else:
            return "**\u200bNo Category:**"

    def _get_command_params(self, cmd: Command) -> str:
        """
        Returns the command usage signature.
        This is a custom implementation of `command.signature` in order to format the command
        signature without aliases.
        """
        results = []
        for name, param in cmd.clean_params.items():
            # if argument has a default value
            if param.default is not param.empty:

                if isinstance(param.default, str):
                    show_default = param.default
                else:
                    show_default = param.default is not None

                # if default is not an empty string or None
                if show_default:
                    results.append(f'[{name}={param.default}]')
                else:
                    results.append(f'[{name}...]')

            # if variable length argument
            elif param.kind == param.VAR_POSITIONAL:
                results.append(f'[{name}...]')

            # if required
            else:
                results.append(f'<{name}>')

        return f"{cmd.name} {' '.join(results)}"

    async def build_pages(self) -> None:
        """Builds the list of content pages to be paginate through in the help message, as a list of str."""
        # Use LinePaginator to restrict embed line height
        paginator = LinePaginator(prefix='', suffix='', max_lines=self._max_lines)

        prefix = constants.Bot.prefix

        # show signature if query is a command
        if isinstance(self.query, commands.Command):
            signature = self._get_command_params(self.query)
            parent = self.query.full_parent_name + ' ' if self.query.parent else ''
            paginator.add_line(f'**```{prefix}{parent}{signature}```**')

            # show command aliases
            aliases = ', '.join(f'`{a}`' for a in self.query.aliases)
            if aliases:
                paginator.add_line(f'**Can also use:** {aliases}\n')

            if not await self.query.can_run(self._ctx):
                paginator.add_line('***You cannot run this command.***\n')

        # show name if query is a cog
        if isinstance(self.query, Cog):
            paginator.add_line(f'**{self.query.name}**')

        if self.description:
            paginator.add_line(f'*{self.description}*')

        # list all children commands of the queried object
        if isinstance(self.query, (commands.GroupMixin, Cog)):

            # remove hidden commands if session is not wanting hiddens
            if not self._show_hidden:
                filtered = [c for c in self.query.commands if not c.hidden]
            else:
                filtered = self.query.commands

            # if after filter there are no commands, finish up
            if not filtered:
                self._pages = paginator.pages
                return
