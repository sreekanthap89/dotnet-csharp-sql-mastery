import httpx
import json
import re
from typing import List, Dict, Any, Optional

class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", default_model: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    async def is_available(self) -> bool:
        """Checks if Ollama server is running and reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def get_models(self) -> List[str]:
        """Returns a list of all model names installed in Ollama."""
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m["name"] for m in data.get("models", [])]
                    # Filter out purely image/flux models
                    return [m for m in models if not any(img_kw in m.lower() for img_kw in ["flux", "z-image", "safetensors"])]
        except Exception:
            pass
        return []

    async def get_best_model(self) -> Optional[str]:
        """Auto-detects the best available model for code & interview question generation."""
        if self.default_model:
            return self.default_model

        models = await self.get_models()
        if not models:
            return None

        # Preference hierarchy:
        # 1. Coding-specialized models (qwen3-coder:30b)
        for m in models:
            if "qwen3-coder" in m.lower():
                return m
        # 2. Large reasoning models
        for m in models:
            if "gemma4-26b" in m.lower():
                return m
        for m in models:
            if "qwen" in m.lower() or "gemma" in m.lower():
                return m

        return models[0]

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 45.0
    ) -> str:
        """Generates a text completion using Ollama with streaming, repeat-penalty, and automatic failover."""
        available_models = await self.get_models()
        target_model = model or self.default_model or await self.get_best_model()

        # Build prioritized list of candidate models for failover
        candidates = [target_model] if target_model else []
        for m in available_models:
            if m not in candidates:
                candidates.append(m)

        last_error = None
        for active_model in candidates[:2]:
            try:
                url = f"{self.base_url}/api/generate"
                payload = {
                    "model": active_model,
                    "prompt": prompt,
                    "system": system_prompt or "You are an expert technical interviewer and Principal Software Architect.",
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "repeat_penalty": 1.15,
                        "top_p": 0.9,
                    }
                }

                full_response = []
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        if response.status_code != 200:
                            raise RuntimeError(f"Ollama error {response.status_code}")
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                                if "error" in chunk:
                                    raise RuntimeError(chunk["error"])
                                full_response.append(chunk.get("response", ""))
                                if chunk.get("done"):
                                    break
                            except Exception as ex:
                                if "error" in str(ex):
                                    raise ex
                                continue

                raw_text = "".join(full_response).strip()
                if not raw_text:
                    raise RuntimeError("Ollama returned empty response.")

                # Strip out <think> ... </think> reasoning tokens from reasoning/thinking models
                clean_text = re.sub(r"<think>[\s\S]*?</think>", "", raw_text).strip()
                if clean_text:
                    return clean_text

            except Exception as e:
                print(f"[OllamaClient] Model '{active_model}' failed ({e}). Trying failover candidate...")
                last_error = e

        raise RuntimeError(f"All Ollama models failed. Last error: {last_error}")

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 50.0
    ) -> Any:
        """Generates structured JSON from Ollama with robust extraction."""
        instructed_prompt = (
            prompt + 
            "\n\nCRITICAL REQUIREMENT: Output MUST be strictly valid JSON only. "
            "Do NOT wrap with markdown backticks. Do NOT include any conversational preamble or postscript."
        )
        response_text = await self.generate(
            prompt=instructed_prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=0.2,
            timeout=timeout
        )

        # Clean markdown code blocks if the model wrapped output
        cleaned = response_text.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        # Try to parse directly
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback: extract substring between [ ... ] or { ... }
            array_match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', cleaned)
            if array_match:
                return json.loads(array_match.group(0))
            obj_match = re.search(r'\{[\s\S]*\}', cleaned)
            if obj_match:
                return json.loads(obj_match.group(0))
            raise ValueError(f"Could not parse valid JSON from Ollama response:\n{response_text[:300]}")
