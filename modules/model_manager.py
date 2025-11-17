# modules/model_manager.py

import os
import json
from typing import Dict, Any, Optional
from google.generativeai.client import GenerativeAIClient
from google.generativeai.types import GenerationConfig
import google.generativeai as genai
import ollama

class ModelManager:
    """
    Manages interactions with various language and embedding models.

    This class provides a unified interface for generating text and embeddings
    from different model providers like Google Gemini and Ollama. It loads
    configuration from 'config/models.json' and handles the initialization
    and authentication for each service.

    Attributes:
        config (Dict[str, Any]): The loaded model configuration.
        default_text_model (str): The default model for text generation.
        default_embedding_model (str): The default model for generating embeddings.
    """
    def __init__(self, config_path: str = "config/models.json"):
        """
        Initializes the ModelManager by loading the model configuration.

        Args:
            config_path (str): The path to the model configuration file.
        """
        with open(config_path, "r") as f:
            self.config = json.load(f)

        self.default_text_model = self.config["defaults"]["text_generation"]
        self.default_embedding_model = self.config["defaults"]["embedding"]

        # Configure Gemini if API key is present
        gemini_config = self.config["models"].get("gemini")
        if gemini_config and gemini_config.get("api_key_env"):
            api_key = os.getenv(gemini_config["api_key_env"])
            if api_key:
                genai.configure(api_key=api_key)

    def _get_model_config(self, model_name: str) -> Dict[str, Any]:
        """
        Retrieves the configuration for a specific model by name.

        Args:
            model_name (str): The name of the model.

        Returns:
            Dict[str, Any]: The configuration dictionary for the model.

        Raises:
            ValueError: If the model name is not found in the configuration.
        """
        if model_name not in self.config["models"]:
            raise ValueError(f"Model '{model_name}' not found in configuration.")
        return self.config["models"][model_name]

    async def generate_text(self, prompt: str, model_name: Optional[str] = None) -> str:
        """
        Generates text using the specified or default language model.

        Args:
            prompt (str): The input prompt for the model.
            model_name (Optional[str]): The name of the model to use. If None, the default is used.

        Returns:
            str: The generated text.
        """
        model_name = model_name or self.default_text_model
        config = self._get_model_config(model_name)

        if config["type"] == "gemini":
            model = genai.GenerativeModel(config["model"])
            response = await model.generate_content_async(
                prompt,
                generation_config=GenerationConfig(
                    # candidate_count=1,
                    # stop_sequences=['x'],
                    # max_output_tokens=20,
                    temperature=0.1,
                )
            )
            return response.text

        elif config["type"] == "ollama":
            response = await ollama.AsyncClient().generate(
                model=config["model"],
                prompt=prompt
            )
            return response['response']

        else:
            raise ValueError(f"Unsupported model type: {config['type']}")

    async def generate_embedding(self, text: str, model_name: Optional[str] = None) -> Any:
        """
        Generates an embedding for the given text.

        Args:
            text (str): The text to be embedded.
            model_name (Optional[str]): The name of the embedding model to use. If None, the default is used.

        Returns:
            Any: The generated embedding, typically a list of floats.
        """
        model_name = model_name or self.default_embedding_model
        config = self._get_model_config(model_name)

        if config["type"] == "gemini":
            model_id = config.get("embedding_model", "models/embedding-001")
            return genai.embed_content(model=model_id, content=text)["embedding"]

        elif config["type"] == "ollama":
            response = await ollama.AsyncClient().embeddings(
                model=config["model"],
                prompt=text
            )
            return response['embedding']

        else:
            raise ValueError(f"Unsupported embedding model type: {config['type']}")

# Example Usage
async def main():
    """An example of how to use the ModelManager."""
    model_manager = ModelManager()

    # Text generation
    # text_result = await model_manager.generate_text("Tell me a joke about AI.")
    # print(f"Generated text: {text_result}")

    # Embedding
    embedding_result = await model_manager.generate_embedding("Hello, world!")
    print(f"Generated embedding: {embedding_result[:5]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
