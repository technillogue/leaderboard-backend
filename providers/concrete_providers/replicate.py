import replicate
import os
import requests
import time
from providers.abstract_providers.base_provider import AbstractProvider

from dotenv import load_dotenv

load_dotenv()


class Replicate(AbstractProvider):
    NAME = "replicate"
    API_KEY = os.environ["REPLICATE_API_KEY"]
    MODEL_TO_URL = {
        "llama-2-70b-chat": "https://api.replicate.com/v1/models/meta/llama-2-70b-chat/predictions",
        "mixtral-8x7b": "https://api.replicate.com/v1/models/mistralai/mixtral-8x7b-instruct-v0.1/predictions",
    }
    SUPPORTED_MODELS = {
        "llama-2-70b-chat": "meta/llama-2-70b-chat",
        "mixtral-8x7b": "mistralai/mixtral-8x7b-instruct-v0.1",
    }

    def call_http(self, model_name: str, prompt: str, max_tokens: int) -> int:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.API_KEY}",
        }

        # Start the prediction
        response = requests.post(
            self.MODEL_TO_URL[model_name],
            json={"input": {"prompt": prompt, "max_new_tokens": max_tokens}},
            headers=headers,
        )

        if response.status_code != 201:
            raise Exception(
                f"Failed to start prediction: {response.status_code} - {response.text}"
            )

        prediction_id = response.json()["id"]

        # Poll for the prediction result
        while True:
            prediction_response = requests.get(
                f"https://api.replicate.com/v1/predictions/{prediction_id}",
                headers=headers,
            )

            if prediction_response.status_code != 200:
                raise Exception(f"Failed to pool prediction results.")

            prediction_data = prediction_response.json()
            if prediction_data["status"] == "succeeded":
                return prediction_data["metrics"]["output_token_count"]

    def call_sdk(self, model_name: str, prompt: str, max_tokens: int) -> int:
        output = replicate.run(
            self.SUPPORTED_MODELS[model_name],
            input={
                "prompt": prompt,
                "max_new_tokens": max_tokens,
            },
        )
        return len(list(output))

    def get_ttft(self, model_name: str, prompt: str, max_tokens: int = 5) -> float:
        start = time.time()
        for event in replicate.stream(
            self.SUPPORTED_MODELS[model_name],
            input={"prompt": prompt, "max_new_tokens": max_tokens},
        ):
            if event and event.data:
                return time.time() - start