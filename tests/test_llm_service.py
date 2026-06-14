"""Tests für LLMService — OpenAI-Calls werden vollständig gemockt."""
import pytest
from unittest.mock import MagicMock, patch
from app.llm_service import LLMService


API_KEY = "sk-test-dummy"
RAW_TRANSCRIPT = "Ich bin total genervt von diesem Projekt und alles ist kaputt!"


@pytest.fixture
def service():
    return LLMService(api_key=API_KEY)


class TestLLMServiceInit:
    def test_no_api_key_raises(self):
        with pytest.raises(ValueError, match="api_key"):
            LLMService(api_key="")

    def test_api_key_stored(self, service):
        assert service.api_key == API_KEY


class TestDampfAblassen:
    def test_returns_string(self, service):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Ich hätte gerne Feedback zum Projekt."
        with patch.object(service.client.chat.completions, "create", return_value=mock_response):
            result = service.dampf_ablassen(RAW_TRANSCRIPT)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_passes_transcript_in_user_message(self, service):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "OK"
        with patch.object(service.client.chat.completions, "create", return_value=mock_response) as mock_create:
            service.dampf_ablassen(RAW_TRANSCRIPT)
        call_kwargs = mock_create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
        user_messages = [m for m in messages if m["role"] == "user"]
        assert any(RAW_TRANSCRIPT in m["content"] for m in user_messages)

    def test_system_prompt_present(self, service):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "OK"
        with patch.object(service.client.chat.completions, "create", return_value=mock_response) as mock_create:
            service.dampf_ablassen(RAW_TRANSCRIPT)
        messages = mock_create.call_args.kwargs.get("messages") or mock_create.call_args.args[0]
        system_messages = [m for m in messages if m["role"] == "system"]
        assert len(system_messages) >= 1


class TestTextImprover:
    def test_neutral_tone(self, service):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Sauberer Text."
        with patch.object(service.client.chat.completions, "create", return_value=mock_response):
            result = service.text_improver("roher text", tone="neutral")
        assert isinstance(result, str)

    def test_invalid_tone_raises(self, service):
        with pytest.raises(ValueError, match="tone"):
            service.text_improver("text", tone="aggressiv")

    def test_custom_prompt_used(self, service):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "OK"
        custom = "Mein eigener Prompt:"
        with patch.object(service.client.chat.completions, "create", return_value=mock_response) as mock_create:
            service.text_improver("text", tone="neutral", custom_prompt=custom)
        messages = mock_create.call_args.kwargs.get("messages") or mock_create.call_args.args[0]
        all_content = " ".join(m["content"] for m in messages)
        assert custom in all_content


class TestEmojiText:
    @pytest.mark.parametrize("density", ["wenig", "mittel", "viel"])
    def test_valid_densities(self, service, density):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Text mit Emojis 🎉"
        with patch.object(service.client.chat.completions, "create", return_value=mock_response):
            result = service.emoji_text("Hallo Welt", density=density)
        assert isinstance(result, str)

    def test_invalid_density_raises(self, service):
        with pytest.raises(ValueError, match="density"):
            service.emoji_text("text", density="extrem")


class TestAPIError:
    def test_openai_error_propagates(self, service):
        """API-Fehler sollen nicht still geschluckt werden."""
        with patch.object(service.client.chat.completions, "create", side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                service.dampf_ablassen(RAW_TRANSCRIPT)
