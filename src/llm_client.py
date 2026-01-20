import os
from openai import OpenAI

def get_client() -> OpenAI:
    base_url = os.getenv("BASE_URL")
    api_key = os.getenv("API_KEY")
    if not base_url or not api_key:
        raise RuntimeError("Missing BASE_URL or API_KEY in environment/.env")
    return OpenAI(base_url=base_url, api_key=api_key)

def get_model_name() -> str:
    model = os.getenv("MODEL")
    if not model:
        raise RuntimeError("Missing MODEL in environment/.env")
    return model

def chat(messages, *, max_tokens=256, temperature=0.7):
    client = get_client()
    model = get_model_name()
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    return resp.choices[0].message.content or ""
