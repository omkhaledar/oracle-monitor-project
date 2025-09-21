#!/usr/bin/env python3
import asyncio
import aiohttp
import time

LMSTUDIO_URL = "http://127.0.0.1:1234/v1"
MODEL = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"  # change to your loaded model

async def main():
    print("[DEBUG] Starting test script...")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        # Step 1: List models
        print("[DEBUG] Requesting models...")
        try:
            async with session.get(f"{LMSTUDIO_URL}/models") as resp:
                print(f"[DEBUG] /models status: {resp.status}")
                models = await resp.json()
                print("[DEBUG] Models response:", models)
        except Exception as e:
            print(f"[ERROR] Failed to get models: {e}")
            return

        # Step 2: Chat completion
        print("[DEBUG] Sending chat completion request...")
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Write a haiku about Oracle databases."}
            ]
        }

        start = time.time()
        try:
            async with session.post(f"{LMSTUDIO_URL}/chat/completions", json=payload) as resp:
                print(f"[DEBUG] /chat/completions status: {resp.status}")
                data = await resp.json()
                elapsed = time.time() - start
                print(f"[DEBUG] Response received in {elapsed:.2f} seconds")
                print("\n=== Assistant Reply ===")
                print(data["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"[ERROR] Failed to call chat completion: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

