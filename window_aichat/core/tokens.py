import logging
from typing import List, Dict, Optional
import tiktoken

logger = logging.getLogger(__name__)


class Tokenizer:
    def __init__(self, model_name: str = "gpt-4"):
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            logger.warning(f"Model {model_name} not found. Using cl100k_base encoding.")
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        if not text:
            return 0
        return len(self.encoding.encode(text))

    def count_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in a list of messages (simplified)."""
        num_tokens = 0
        for message in messages:
            # simple approximation: 4 tokens per message + content tokens
            num_tokens += 4
            for key, value in message.items():
                num_tokens += self.count_tokens(value)
        num_tokens += 2  # priming tokens
        return num_tokens

    def trim_context(
        self, messages: List[Dict[str, str]], max_tokens: int
    ) -> List[Dict[str, str]]:
        """
        Trim messages from the beginning (keeping system prompt) to fit within max_tokens.
        Assumes messages[0] might be system prompt and should be kept.
        """
        if not messages:
            return []

        current_tokens = self.count_message_tokens(messages)
        if current_tokens <= max_tokens:
            return messages

        # Keep system prompt if present
        trimmed_messages = []
        if messages[0].get("role") == "system":
            trimmed_messages.append(messages[0])
            messages = messages[1:]

        # Reverse iterate to keep most recent
        temp_messages = []
        tokens_so_far = self.count_message_tokens(trimmed_messages)

        for msg in reversed(messages):
            msg_tokens = self.count_message_tokens([msg])
            if tokens_so_far + msg_tokens > max_tokens:
                break
            temp_messages.append(msg)
            tokens_so_far += msg_tokens

        return trimmed_messages + list(reversed(temp_messages))
