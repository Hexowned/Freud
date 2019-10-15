from abc import ABCMeta
from typing import Any, Generator, Hashable, Iterable

from discord.ext.commands import CogMeta


class CogABCMeta(CogMeta, ABCMeta):
    """Metaclass for ABcs meant to be implemented as Cogs."""

    pass


class CaseInsensitiveDict(dict):
    """

    """

    @ classmethod
    def _k(cls, key: Hashable) -> Hashable:
        """Return lowered key if a string-like is passed, otherwise pass key straight through."""
        return key.lower() if isinstance(key, str) else key

    def __init__(self, *args, **kwargs):
        super(CaseInsensitiveDict, self).__init__(*args, **kwargs)
        self._convert_keys()

    def __getitem__(self, key: Hashable) -> Any:
        """Case insensitive __setitem__."""
        return super(CaseInsensitiveDict, self).__getitem__(self.__class__._k(key))

    def __setitem__(self, key: Hashable, value: Any):
        """Case insensitive __setitem__."""
        super(CaseInsensitiveDict, self).__setitem__(self.__class__._k(key), value)

    def __delitem__(self, key: Hashable) -> Any:
        """Case insensitive __delitem__."""
        return super(CaseInsensitiveDict, self).__delitem__(self.__class__._k(key))

    def __contains__(self, key: Hashable) -> bool:
        """Case insensitive __contains__."""
        return super(CaseInsensitiveDict, self).__contains__(self.__class__._k(key))

    def pop(self, key: Hashable, *args, **kwargs) -> Any:
        """Case insensitive pop."""
        return super(CaseInsensitiveDict, self).pop(self.__class__._k(key), *args, **kwargs)

    def get(self, key: Hashable, *args, **kwargs) -> Any:
        """Case insensitive get."""
        return super(CaseInsensitiveDict, self).get(self.__class__._k(key), *args, **kwargs)

    def setdefault(self, key: Hashable, *args, **kwargs) -> Any:
        """Case insensitive setdefault."""
        return super(CaseInsensitiveDict, self).setdefault(self.__class__._k(key), *args, **kwargs)

    def update(self, E: Any = None, **F) -> None:
        """Case insensitive update."""
        super(CaseInsensitiveDict, self).update(self.__class__(E))
        super(CaseInsensitiveDict, self).update(self.__class__(**F))

    def _convert_keys(self) -> None:
        """Helper method to lowercase all existing string-like keys."""
        for k in list(self.keys()):
            v = super(CaseInsensitiveDict, self).pop(k)
            self.__setitem__(k, v)


def chunks(iterable: Iterable, size: int) -> Generator[Any, None, None]:
    """
    Generator that allows you to iterate over any indexable collection in `size`-length chunks.
    """
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]
