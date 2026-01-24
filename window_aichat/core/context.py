from typing import List, Dict, Any, Optional


class PromptTemplate:
    def __init__(self, system_prompt: str = ""):
        self.system_prompt = system_prompt

    def format(self, history: List[Dict[str, str]], user_input: str) -> str:
        """
        Format messages into a single string (legacy/simple mode).
        Useful for models that expect a single prompt string.
        """
        messages = self.format_messages(history, user_input)
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

    def format_messages(
        self, history: List[Dict[str, str]], user_input: str
    ) -> List[Dict[str, str]]:
        """
        Format messages into a structured list.
        """
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        # Add history
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            messages.append({"role": role, "content": content})

        # Add current user input
        messages.append({"role": "user", "content": user_input})

        return messages

    def update_system_prompt(self, new_prompt: str):
        self.system_prompt = new_prompt
