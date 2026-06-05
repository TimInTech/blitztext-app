"""LLM service for BlitztextLinux rewrite workflows.

Usage:
    service = LLMService(api_key="sk-...")
    result = service.rewrite(WorkflowType.TEXT_IMPROVER, "mein rohes transkript")

For tests, inject a mock client:
    service = LLMService(api_key="test", client=mock_client)
"""
from __future__ import annotations

from enum import Enum
from typing import Optional


class WorkflowType(str, Enum):
    TRANSCRIPTION = "transcription"      # local only, no LLM
    LOCAL = "local"                       # local only, no LLM
    TEXT_IMPROVER = "text_improver"       # LLM: clean up raw dictation
    DAMPF_ABLASSEN = "dampf_ablassen"     # LLM: frustration → calm message
    EMOJI_TEXT = "emoji_text"             # LLM: add emojis


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
    """Raised when the LLM call cannot be completed."""


class LLMService:
    """Wraps OpenAI API calls for BlitztextLinux rewrite workflows."""

    def __init__(
        self,
        api_key: str = "",
        client=None,
        tone: str = "neutral",
        emoji_density: str = "mittel",
        dampf_system_prompt: str = "",
    ) -> None:
        """
        Args:
            api_key: OpenAI API key. Empty string = LLM features disabled.
            client:  Pre-built openai.OpenAI-compatible client (for testing/mocking).
            tone:    Text-improver tone: 'formal' | 'neutral' | 'locker'.
            emoji_density: 'wenig' | 'mittel' | 'viel'.
            dampf_system_prompt: Override for dampf_ablassen system prompt (empty = default).
        """
        self._api_key = api_key
        self._client = client
        self.tone = tone
        self.emoji_density = emoji_density
        self._dampf_system = dampf_system_prompt.strip() or _DAMPF_SYSTEM

    def is_available(self) -> bool:
        """Returns True if an API key is configured."""
        return bool(self._api_key and self._api_key.strip())

    def _get_client(self):
        """Lazy-init the OpenAI client. Raises LLMServiceError if no key set."""
        if self._client is not None:
            return self._client
        if not self.is_available():
            raise LLMServiceError(
                "Kein OpenAI API-Key konfiguriert. "
                "LLM-Workflows sind deaktiviert. "
                "API-Key in den Einstellungen hinterlegen."
            )
        try:
            import openai  # noqa: PLC0415
        except ImportError as exc:
            raise LLMServiceError(
                "openai-Paket nicht installiert. Bitte: pip install openai"
            ) from exc
        self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    def _system_prompt(self, workflow: WorkflowType) -> str:
        if workflow == WorkflowType.DAMPF_ABLASSEN:
            return self._dampf_system
        if workflow == WorkflowType.TEXT_IMPROVER:
            return _TEXT_IMPROVER_SYSTEM_TEMPLATE.format(tone=self.tone)
        if workflow == WorkflowType.EMOJI_TEXT:
            return _EMOJI_SYSTEM_TEMPLATE.format(density=self.emoji_density)
        raise LLMServiceError(f"Workflow {workflow!r} benötigt kein LLM.")

    def rewrite(self, workflow: WorkflowType, transcript: str) -> str:
        """Send transcript to OpenAI and return the rewritten text.

        Args:
            workflow:   Must be one of LLM_WORKFLOWS.
            transcript: Raw transcribed text.

        Returns:
            Rewritten text from the model.

        Raises:
            LLMServiceError: On missing key, missing package, or API error.
        """
        if workflow not in LLM_WORKFLOWS:
            raise LLMServiceError(
                f"rewrite() darf nur für LLM-Workflows aufgerufen werden. "
                f"Erhalten: {workflow!r}"
            )
        if not transcript or not transcript.strip():
            raise LLMServiceError("Transkript ist leer — kein API-Call durchgeführt.")

        client = self._get_client()
        system = self._system_prompt(workflow)

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": transcript.strip()},
                ],
                temperature=0.7,
            )
        except Exception as exc:
            raise LLMServiceError(f"OpenAI API-Fehler: {exc}") from exc

        content = response.choices[0].message.content
        if content is None:
            raise LLMServiceError("OpenAI hat leere Antwort zurückgegeben.")
        return content.strip()
