from dataclasses import dataclass


@dataclass
class DebouncedTextInput:
    delay_seconds: float = 0.04
    pending_text: str | None = None
    update_queued: bool = False

    def schedule(self, text: str) -> bool:
        """Store text and return True when the caller should arm a timer."""
        self.pending_text = text
        if self.update_queued:
            return False
        self.update_queued = True
        return True

    def pop_pending(self) -> str | None:
        text = self.pending_text
        self.pending_text = None
        self.update_queued = False
        return text

    def has_pending(self) -> bool:
        return self.pending_text is not None
