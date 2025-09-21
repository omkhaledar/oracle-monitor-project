#!/usr/bin/env python3
import asyncio
import aiohttp

LMSTUDIO_URL = "http://swd2504001.elsewedy.home:1234/v1"
MODEL = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"   # change to the model you loaded in LM Studio


async def list_models(session: aiohttp.ClientSession):
    """GET /v1/models"""
    async with session.get(f"{LMSTUDIO_URL}/models") as resp:
        print("\n=== GET /v1/models ===")
        if resp.status != 200:
            print("Failed:", resp.status, await resp.text())
            return
        data = await resp.json()
        for m in data.get("data", []):
            print(f"- {m['id']}")
        return data


async def chat_completion(session: aiohttp.ClientSession):
    """POST /v1/chat/completions"""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Write a haiku about Oracle databases."}
        ]
    }
    async with session.post(f"{LMSTUDIO_URL}/chat/completions", json=payload) as resp:
        print("\n=== POST /v1/chat/completions ===")
        if resp.status != 200:
            print("Failed:", resp.status, await resp.text())
            return
        data = await resp.json()
        print(data["choices"][0]["message"]["content"])
        return data


async def completion(session: aiohttp.ClientSession):
    """POST /v1/completions"""
    payload = {
        "model": MODEL,
        "prompt": "Summarize the role of an Oracle DBA in one sentence.",
        "temperature": 0.7
    }
    async with session.post(f"{LMSTUDIO_URL}/completions", json=payload) as resp:
        print("\n=== POST /v1/completions ===")
        if resp.status != 200:
            print("Failed:", resp.status, await resp.text())
            return
        data = await resp.json()
        print(data["choices"][0]["text"])
        return data


async def embeddings(session: aiohttp.ClientSession):
    """POST /v1/embeddings"""
    payload = {
        "model": MODEL,
        "input": "Oracle alert log critical error ORA-600"
    }
    async with session.post(f"{LMSTUDIO_URL}/embeddings", json=payload) as resp:
        print("\n=== POST /v1/embeddings ===")
        if resp.status != 200:
            print("Failed:", resp.status, await resp.text())
            return
        data = await resp.json()
        print("Embedding vector length:", len(data["data"][0]["embedding"]))
        return data


async def main():
    async with aiohttp.ClientSession() as session:
        await list_models(session)
        await chat_completion(session)
        await completion(session)
        await embeddings(session)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

