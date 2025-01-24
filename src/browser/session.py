from dataclasses import dataclass

from browser_use.browser.views import BrowserState


@dataclass
class SessionState:
    step_number: int = 0
    is_complete: bool = False
    error: str | None = None

@dataclass
class Session:
    browser_state: BrowserState | None = None
    session_state: SessionState | None = None

    @classmethod
    def create(cls) -> "Session":
        return cls(
            session_state=SessionState()
        )