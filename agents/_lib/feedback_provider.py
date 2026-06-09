"""Async feedback provider — raises HumanFeedbackPending to pause the Flow.

In a Web/SSE context, 'pause' means: return the current output to the client
and end the HTTP response. The next HTTP request delivers the user's reply
via flow.resume_async(feedback).
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from crewai.flow.async_feedback.types import (
    HumanFeedbackPending,
    HumanFeedbackProvider,
    PendingFeedbackContext,
)

if TYPE_CHECKING:
    from crewai.flow.flow import Flow


class PagesAsyncProvider(HumanFeedbackProvider):
    """Always pauses. The SSE response delivers the output to the user;
    the next HTTP request delivers the user's reply via resume_async."""

    def request_feedback(self, context: PendingFeedbackContext, flow: "Flow") -> str:
        raise HumanFeedbackPending(context=context)


PROVIDER = PagesAsyncProvider()
