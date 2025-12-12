from __future__ import annotations

import sys
import warnings
from functools import wraps
from typing import TYPE_CHECKING, ClassVar, TypeVar

import attrs

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from typing_extensions import ParamSpec

    ArgsT = ParamSpec("ArgsT")

RetT = TypeVar("RetT")


def _url_for_issue(issue: int) -> str:
    return f"https://github.com/CoolCat467/Neuro-API/issues/{issue}"


def _stringify(thing: object) -> str:
    if hasattr(thing, "__module__") and hasattr(thing, "__qualname__"):
        return f"{thing.__module__}.{thing.__qualname__}"
    return str(thing)


def warn_deprecated(
    thing: object,
    version: str,
    *,
    issue: int | None,
    instead: object,
    stacklevel: int = 2,
) -> None:
    stacklevel += 1
    msg = f"{_stringify(thing)} is deprecated since Neuro-API {version}"
    if instead is None:
        msg += " with no replacement"
    else:
        msg += f"; use {_stringify(instead)} instead"
    if issue is not None:
        msg += f" ({_url_for_issue(issue)})"
    warning_class = DeprecationWarning
    warnings.warn(warning_class(msg), stacklevel=stacklevel)


# @deprecated("0.2.0", issue=..., instead=...)
# def ...
def deprecated(
    version: str,
    *,
    thing: object = None,
    issue: int | None,
    instead: object,
) -> Callable[[Callable[ArgsT, RetT]], Callable[ArgsT, RetT]]:
    def do_wrap(fn: Callable[ArgsT, RetT]) -> Callable[ArgsT, RetT]:
        nonlocal thing

        @wraps(fn)
        def wrapper(*args: ArgsT.args, **kwargs: ArgsT.kwargs) -> RetT:
            warn_deprecated(
                thing,
                version,
                instead=instead,
                issue=issue,
            )
            return fn(*args, **kwargs)

        # If our __module__ or __qualname__ get modified, we want to pick up
        # on that, so we read them off the wrapper object instead of the (now
        # hidden) fn object
        if thing is None:
            thing = wrapper

        if wrapper.__doc__ is not None:
            doc = wrapper.__doc__
            doc = doc.rstrip()
            doc += "\n\n"
            doc += f".. deprecated:: {version}\n"
            if instead is not None:
                doc += f"   Use {_stringify(instead)} instead.\n"
            if issue is not None:
                doc += f"   For details, see `issue #{issue} <{_url_for_issue(issue)}>`__.\n"
            doc += "\n"
            wrapper.__doc__ = doc

        return wrapper

    return do_wrap


def deprecated_alias(
    old_qualname: str,
    new_fn: Callable[ArgsT, RetT],
    version: str,
    *,
    issue: int | None,
) -> Callable[ArgsT, RetT]:
    @deprecated(version, issue=issue, instead=new_fn)
    @wraps(new_fn, assigned=("__module__", "__annotations__"))
    def wrapper(*args: ArgsT.args, **kwargs: ArgsT.kwargs) -> RetT:
        """Deprecated alias."""  # noqa: D401
        return new_fn(*args, **kwargs)

    wrapper.__qualname__ = old_qualname
    wrapper.__name__ = old_qualname.rpartition(".")[-1]
    return wrapper


def deprecated_async_alias(
    old_qualname: str,
    new_fn: Callable[ArgsT, Awaitable[RetT]],
    version: str,
    *,
    issue: int | None,
) -> Callable[ArgsT, Awaitable[RetT]]:
    @deprecated(version, issue=issue, instead=new_fn)
    @wraps(new_fn, assigned=("__module__", "__annotations__"))
    async def wrapper(  # type: ignore[misc]
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
    ) -> RetT:
        """Deprecated alias."""  # noqa: D401
        return await new_fn(*args, **kwargs)

    wrapper.__qualname__ = old_qualname
    wrapper.__name__ = old_qualname.rpartition(".")[-1]
    return wrapper


@attrs.frozen(slots=False)
class DeprecatedAttribute:
    _not_set: ClassVar[object] = object()

    value: object
    version: str
    issue: int | None
    instead: object = _not_set


def deprecate_attributes(
    module_name: str,
    deprecated_attributes: dict[str, DeprecatedAttribute],
) -> None:
    def __getattr__(name: str) -> object:  # noqa: N807
        if name in deprecated_attributes:
            info = deprecated_attributes[name]
            instead = info.instead
            if instead is DeprecatedAttribute._not_set:
                instead = info.value
            thing = f"{module_name}.{name}"
            warn_deprecated(
                thing,
                info.version,
                issue=info.issue,
                instead=instead,
            )
            return info.value

        msg = "module '{}' has no attribute '{}'"
        raise AttributeError(msg.format(module_name, name))

    sys.modules[module_name].__getattr__ = __getattr__  # type: ignore[method-assign]
