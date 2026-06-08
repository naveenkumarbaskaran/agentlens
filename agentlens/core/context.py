from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentlens.core.session import LensSession

current_session: ContextVar["LensSession | None"] = ContextVar(
    "current_session", default=None
)
