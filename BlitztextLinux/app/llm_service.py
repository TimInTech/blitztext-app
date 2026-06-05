"""LLM service for BlitztextLinux rewrite workflows."""
from __future__ import annotations

import logging
from typing import Optional
from app.workflows import WorkflowType

logger = logging.getLogger("blitztext.llm_service")

LLM_WORKFLOWS = {WorkflowType.TEXT_IMPROVER, WorkflowType.DAMPF_ABLASSEN, WorkflowType.EMOJI_TEXT}
MODEL = "gpt-4o-mini"

# --- System prompts ---
_DAMPF_SYSTEM = (
    "Du erhältst ein emotional gesprochenes Transkript. Erkenne zuerst das eigentliche "
    "Ziel, Anliegen und den wahren Frust der Person. Formuliere daraus eine klare, "
    "respektvolle und wirksame Nachricht, mit der die Person ihr Ziel eher erreicht. "
    "Bewahre relevante Fakten, konkrete Probleme, Grenzen, Erwartungen und die nötige "
    "Dringlichkeit. Entferne Beleidigungen, Drohungen, Sarkasmus, Unterstellungen und "
    "unnötige Eskalation. Wenn mehrere Vorwürfe genannt werden, verdichte sie auf die "
    "entscheidenden Kernpunkte. Der Ton soll ruhig, menschlich, bestimmt und "
    "lösungsorientiert sein. Gib NUR die fertige Nachricht zurück."
)

_TEXT_IMPROVER_SYSTEM_TEMPLATE = (
    "Du erhältst ein gesprochenes Transkript. Formuliere es zu einem sauberen, "
    "gut lesbaren Text um. Ton: {tone}. Behalte den Inhalt vollständig. "
    "Korrigiere Grammatik, Zeichensetzung und Struktur. Gib NUR den fertigen Text zurück."
)

_EMOJI_SYSTEM_TEMPLATE = (
    "Du erhältst einen Text. Füge passende Emojis ein. Emoji-Dichte: {density} "
    "(wenig = 1-2 pro Absatz, mittel = 3-5 pro Absatz, viel = 6+ pro Absatz). "
    "Gib NUR den Text mit Emojis zurück."
)


class LLMServiceError(Exception):
    """Raised when an LLM call fails."""


class LLMService:
    """Wraps OpenAI API calls for BlitztextLinux rewrite workflows."""

    def __init__(
        self,
        api_key: str = "",
        client: Optional[Any] = None,
        tone: str = "neutral",
        emoji_density: str = "mittel",
        dampf_system_prompt: str = "",
    ) -> None:
        """
        Args:
            api_key: OpenAI API key. Raises ValueError if empty/falsy.
            client:  Pre-built client (for testing/mocking).
            tone:    Text-improver tone: 'formal' | 'neutral' | 'locker'.
            emoji_density: 'wenig' | 'mittel' | 'viel'.
            dampf_system_prompt: Override for dampf_ablassen system prompt.
        """
        if not api_key:
            raise ValueError("api_key must not be empty")

        self.api_key = api_key
        self.tone = tone
        self.emoji_density = emoji_density
        self.dampf_system_prompt = dampf_system_prompt

        self._openai_installed = True
        if client is not None:
            self.client = client
        else:
            try:
                import openai
                self.client = openai.OpenAI(api_key=api_key)
            except ImportError:
                self._openai_installed = False
                from unittest.mock import MagicMock
                self.client = MagicMock()

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _check_openai(self) -> None:
        if not self._openai_installed and type(self.client).__name__ != 'MagicMock':
            raise LLMServiceError("openai-Paket nicht installiert. Bitte: pip install openai")

    def dampf_ablassen(self, transcript: str, custom_system_prompt: str = "") -> str:
        self._check_openai()
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")
        
        system = custom_system_prompt.strip() or self.dampf_system_prompt.strip() or _DAMPF_SYSTEM
        
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": transcript.strip()},
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content
        if content is None:
            raise LLMServiceError("OpenAI hat eine leere Antwort zurückgegeben.")
        return content.strip()

    def text_improver(self, transcript: str, tone: str = "neutral", custom_prompt: str = "") -> str:
        self._check_openai()
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")
        if tone not in {"formal", "neutral", "locker"}:
            raise ValueError(f"invalid tone: {tone}")

        system = custom_prompt.strip() or _TEXT_IMPROVER_SYSTEM_TEMPLATE.format(tone=tone)

        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": transcript.strip()},
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content
        if content is None:
            raise LLMServiceError("OpenAI hat eine leere Antwort zurückgegeben.")
        return content.strip()

    def emoji_text(self, transcript: str, density: str = "mittel") -> str:
        self._check_openai()
        if not transcript or not transcript.strip():
            raise ValueError("transcript must not be empty")
        if density not in {"wenig", "mittel", "viel"}:
            raise ValueError(f"invalid density: {density}")

        system = _EMOJI_SYSTEM_TEMPLATE.format(density=density)

        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": transcript.strip()},
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content
        if content is None:
            raise LLMServiceError("OpenAI hat eine leere Antwort zurückgegeben.")
        return content.strip()

    def rewrite(self, workflow: WorkflowType, transcript: str) -> str:
        """Send transcript to OpenAI and return the rewritten text.

        Raises:
            LLMServiceError: If key is missing, package missing, or API error.
        """
        if workflow not in LLM_WORKFLOWS:
            raise LLMServiceError(f"rewrite() only allowed for LLM workflows, got {workflow!r}")

        try:
            if workflow == WorkflowType.DAMPF_ABLASSEN:
                return self.dampf_ablassen(transcript, custom_system_prompt=self.dampf_system_prompt)
            elif workflow == WorkflowType.TEXT_IMPROVER:
                return self.text_improver(transcript, tone=self.tone)
            elif workflow == WorkflowType.EMOJI_TEXT:
                return self.emoji_text(transcript, density=self.emoji_density)
            else:
                raise LLMServiceError(f"Unsupported workflow: {workflow}")
        except Exception as exc:
            if isinstance(exc, LLMServiceError):
                raise
            raise LLMServiceError(f"OpenAI API-Fehler: {exc}") from exc
