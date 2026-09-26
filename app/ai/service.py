from collections.abc import Iterator

from ..support import site_brief
from .gemini import GeminiProvider
from .provider import LLMProvider


class AIService:
    """Builds the fandom-only prompt, then asks whichever provider was injected."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    def stream_answer(self, prompt: str) -> Iterator[str]:
        sanitized = " ".join((prompt or "").split())
        if not sanitized:
            raise ValueError("The question cannot be empty.")
        return self.llm_provider.generate_stream(self._fandom_prompt(sanitized))

    def _fandom_prompt(self, question: str) -> str:
        return (
            "You are Mina, the Fan Hub Plus support chat. Reply in the same language the visitor used. "
            "Two or three short sentences.\n"
            "You may only talk about fandom that is listed in the site notes: shelves, titles, characters, "
            "trailers, featured pieces, display merchandise, and fan events on this hub.\n"
            "If the question is about anything else, say you only help with fandom on Fan Hub Plus and ask which series they want. "
            "Do not answer the off-topic question.\n"
            "Do not invent a title, character, plot point, price, or checkout. "
            "If a name is not in the notes, say it is not on the shelf and point them to Explore.\n\n"
            "Site notes:\n"
            f"{site_brief()}\n\n"
            f"Visitor: {question}"
        )


def fandom_chat() -> AIService:
    return AIService(GeminiProvider())
