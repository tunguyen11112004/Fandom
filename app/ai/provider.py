from collections.abc import Iterator


class LLMProvider:
    """Contract every chat model has to follow: one full reply, or a stream of text pieces."""

    def generate_response(self, prompt: str) -> str:
        raise NotImplementedError

    def generate_stream(self, prompt: str) -> Iterator[str]:
        raise NotImplementedError
