import json
import logging
from datetime import datetime

import requests
from django.conf import settings

MODEL_NAME = settings.MODEL_NAME
API_ENDPOINT = settings.MODEL_API_ENDPOINT
API_KEY = settings.MODEL_KEY
GPT = settings.GPT
MODEL_NAME = settings.MODEL_NAME
API_ENDPOINT = settings.MODEL_API_ENDPOINT
API_KEY = settings.MODEL_KEY
GPT = settings.GPT


def parse_streaming_response(response_stream):
    """
    Helper function to parse streaming response from the API.
    """
    content = ""
    try:
        for line in response_stream.iter_lines():
            if line:
                try:
                    json_line = json.loads(line.decode("utf-8"))
                    if "message" in json_line and "content" in json_line["message"]:
                        content += json_line["message"]["content"]
                    if json_line.get("done", False):
                        break  # Stop processing when done
                except json.JSONDecodeError:
                    print(f"Failed to decode JSON: {line.decode('utf-8')}")
    except Exception as e:
        print(f"Error while parsing response: {str(e)}")
    return content


def send_message(
    message: str,
    prompt: str | None = None,
):
    """
    Sends a message to the AI model and returns the response as a string.
    Uses the new LLM API: POST /api/generate, format=json, stream=false.
    """
    try:
        data = {
            "model": MODEL_NAME,
            "prompt": prompt if prompt else message,
            "format": "json",
            "stream": False,
        }
        headers = {}
        if GPT:
            headers["Authorization"] = f"Bearer {API_KEY}"
        response = requests.post(API_ENDPOINT, json=data, headers=headers, timeout=60)
        if response.status_code == 200:
            try:
                result = response.json()
                return result.get("response", "")
            except Exception as e:
                logging.error(
                    f"Failed to decode LLM JSON response: {e}\nRaw: {response.text}"
                )
                return None
        logging.error(
            f"Error response ({response.status_code}): {response.content.decode('utf-8')}"
        )
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request exception occurred: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Unexpected exception occurred: {str(e)}")
        return None
