import asyncio
import contextlib
import logging
from abc import abstractmethod
from typing import Coroutine, Dict, Union

from bot.utilities import CogABCMeta

log = logging.getLogger(__name__)


class Scheduler(metaclass=CogABCMeta):
    """Task scheduler"""

    def __init__(self):

        self.cog_name = self.__class__.__name__
        self.scheduled_task: Dict[str, asyncio.Task] = {}

    @abstractmethod
    async def _scheduled_task(self, task_object: dict) -> None:
        """
        A coroutine which handles the scheduling.
        This is added to the scheduled task, and should wait the task duration, execute the desired
        code, and then clean up the task.
        """

    def schedule_task(self, loop: asyncio.AbstractEventLoop, task_id: str, task_data: dict) -> None:
        """Schedules a task"""
        if task_id in self.scheduled_task:
            return

        task: asyncio.Task = create_task(loop, self._scheduled_task(task_data))

        self.scheduled_task[task_id] = task

    def cancel_task(self, task_id: str) -> None:
        """Un-schedules a task"""
        task = self.scheduled_task.get(task_id)

        if task is None:
            log.warning(
                f"{self.cog_name}: Failed to unschedule {task_id} (no task found).")
            return

        task.cancel()
        log.debug(f"{self.cog_name}: Unscheduled {task_id}.")
        del self.scheduled_task[task_id]


def create_task(loop: asyncio.AbstractEventLoop, coro_or_future: Union[Coroutine, asyncio.Future]) -> asyncio.Task:
    """Creates an asyncio.Task object from a coroutine or future object."""
    task: asyncio.Task = asyncio.ensure_future(coro_or_future, loop=loop)

    # Silently ignore exceptions in a callback (handles the CancelledError nonsense)
    task.add_done_callback(_silent_exception)
    return task


def _silent_exception(future: asyncio.Future) -> None:
    """Supress future's exceptions"""
    with contextlib.suppress(Exception):
        future.exception()
