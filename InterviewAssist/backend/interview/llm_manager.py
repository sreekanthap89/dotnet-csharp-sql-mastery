import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx

from config import (
    SETTINGS_FILE,
    DEFAULT_OLLAMA_URL,
    DEFAULT_LM_STUDIO_URL,
    DEFAULT_OPENROUTER_URL,
    GEMINI_API_KEY,
    ANTHROPIC_API_KEY,
    OPENROUTER_API_KEY,
    OPENAI_API_KEY,
)
from interview.ollama_client import OllamaClient


class LLMManager:
    """
    Unified manager for all Local and Cloud LLM providers:
    - Ollama (Local GPU/Metal)
    - LM Studio (Local OpenAI-compatible)
    - Google Gemini (Cloud)
    - Anthropic Claude (Cloud)
    - OpenRouter (Multi-model Cloud aggregator)
    """

    DEFAULT_CONFIG = {
        "active_provider": "ollama",
        "active_model": "qwen3-coder:30b",
        "default_questions": 10,
        "default_level": "intermediate",
        "providers": {
            "ollama": {
                "name": "Ollama (Local)",
                "icon": "🦙",
                "base_url": DEFAULT_OLLAMA_URL,
                "model": "qwen3-coder:30b",
                "is_local": True
            },
            "lm_studio": {
                "name": "LM Studio (Local)",
                "icon": "🖥️",
                "base_url": DEFAULT_LM_STUDIO_URL,
                "model": "local-model",
                "is_local": True
            },
            "gemini": {
                "name": "Google Gemini",
                "icon": "✨",
                "api_key": GEMINI_API_KEY,
                "model": "gemini-2.5-flash",
                "is_local": False
            },
            "claude": {
                "name": "Anthropic Claude",
                "icon": "🧠",
                "api_key": ANTHROPIC_API_KEY,
                "model": "claude-3-5-sonnet-20241022",
                "is_local": False
            },
            "openrouter": {
                "name": "OpenRouter",
                "icon": "🌐",
                "base_url": DEFAULT_OPENROUTER_URL,
                "api_key": OPENROUTER_API_KEY,
                "model": "anthropic/claude-3.5-sonnet",
                "is_local": False
            }
        }
    }

    # Curated model suggestions for providers without dynamic model endpoints
    KNOWN_MODELS = {
        "gemini": [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ],
        "claude": [
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229"
        ],
        "openrouter": [
            "anthropic/claude-3.5-sonnet",
            "deepseek/deepseek-r1",
            "meta-llama/llama-3.3-70b-instruct",
            "google/gemini-2.5-flash",
            "openai/gpt-4o",
            "qwen/qwen-2.5-coder-32b-instruct"
        ]
    }

    def __init__(self):
        self.config: Dict[str, Any] = self._load_config()
        self.ollama_client = OllamaClient(
            base_url=self.get_provider_config("ollama").get("base_url", DEFAULT_OLLAMA_URL),
            default_model=self.get_provider_config("ollama").get("model")
        )

    def _load_config(self) -> Dict[str, Any]:
        """Loads configuration from disk or returns defaults."""
        config = json.loads(json.dumps(self.DEFAULT_CONFIG))
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    # Merge saved with defaults
                    if "active_provider" in saved:
                        config["active_provider"] = saved["active_provider"]
                    if "active_model" in saved:
                        config["active_model"] = saved["active_model"]
                    if "default_questions" in saved:
                        config["default_questions"] = saved["default_questions"]
                    if "default_level" in saved:
                        config["default_level"] = saved["default_level"]
                    if "providers" in saved:
                        for p_name, p_data in saved["providers"].items():
                            if p_name in config["providers"]:
                                config["providers"][p_name].update(p_data)
            except Exception as e:
                print(f"[LLMManager] Warning loading settings: {e}")
        return config

    def save_config(self):
        """Persists current configuration to disk."""
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"[LLMManager] Error saving settings: {e}")

    def get_config(self) -> Dict[str, Any]:
        """Returns the current configuration, with masked secrets for safe frontend display."""
        safe_copy = json.loads(json.dumps(self.config))
        for p_name, p_data in safe_copy.get("providers", {}).items():
            key = p_data.get("api_key")
            if key:
                # Mask key: show only first 4 and last 4 chars
                if len(key) > 8:
                    p_data["api_key_masked"] = f"{key[:4]}...{key[-4:]}"
                else:
                    p_data["api_key_masked"] = "********"
                p_data["has_key"] = True
            else:
                p_data["api_key_masked"] = ""
                p_data["has_key"] = False
        return safe_copy

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates and persists configuration."""
        if "active_provider" in updates:
            self.config["active_provider"] = updates["active_provider"]
        if "active_model" in updates:
            self.config["active_model"] = updates["active_model"]
        if "default_questions" in updates:
            self.config["default_questions"] = updates["default_questions"]
        if "default_level" in updates:
            self.config["default_level"] = updates["default_level"]

        if "providers" in updates and isinstance(updates["providers"], dict):
            for p_name, p_data in updates["providers"].items():
                if p_name in self.config["providers"]:
                    # Preserve existing API key if updated with empty/placeholder
                    new_key = p_data.get("api_key")
                    if new_key is not None:
                        if new_key.strip() and not new_key.startswith("***"):
                            self.config["providers"][p_name]["api_key"] = new_key.strip()
                        elif new_key == "":
                            self.config["providers"][p_name]["api_key"] = ""

                    if "base_url" in p_data and p_data["base_url"]:
                        self.config["providers"][p_name]["base_url"] = p_data["base_url"].strip().rstrip("/")
                    if "model" in p_data and p_data["model"]:
                        self.config["providers"][p_name]["model"] = p_data["model"].strip()

        # Update ollama client if ollama settings changed
        ollama_cfg = self.get_provider_config("ollama")
        self.ollama_client.base_url = ollama_cfg.get("base_url", DEFAULT_OLLAMA_URL).rstrip("/")
        self.ollama_client.default_model = ollama_cfg.get("model")

        self.save_config()
        return self.get_config()

    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        return self.config.get("providers", {}).get(provider_name, {})

    def get_active_info(self) -> Dict[str, str]:
        active_p = self.config.get("active_provider", "ollama")
        p_cfg = self.get_provider_config(active_p)
        active_m = self.config.get("active_model") or p_cfg.get("model", "default")
        return {
            "provider": active_p,
            "provider_name": p_cfg.get("name", active_p.title()),
            "icon": p_cfg.get("icon", "⚡"),
            "model": active_m
        }

    # =========================================================================
    # MODEL DISCOVERY
    # =========================================================================
    async def fetch_models(self, provider_name: str, config_override: Optional[Dict[str, Any]] = None) -> List[str]:
        """Dynamically queries the provider's API for installed/available models."""
        cfg = dict(self.get_provider_config(provider_name))
        if config_override:
            cfg.update(config_override)

        if provider_name == "ollama":
            url = cfg.get("base_url", DEFAULT_OLLAMA_URL).rstrip("/")
            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    res = await client.get(f"{url}/api/tags")
                    if res.status_code == 200:
                        data = res.json()
                        models = [m["name"] for m in data.get("models", [])]
                        return [m for m in models if not any(k in m.lower() for k in ["flux", "z-image", "safetensors"])]
            except Exception as e:
                print(f"[LLMManager] Ollama model fetch failed: {e}")
                return []

        elif provider_name == "lm_studio":
            url = cfg.get("base_url", DEFAULT_LM_STUDIO_URL).rstrip("/")
            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    res = await client.get(f"{url}/models")
                    if res.status_code == 200:
                        data = res.json()
                        return [m["id"] for m in data.get("data", [])]
            except Exception as e:
                print(f"[LLMManager] LM Studio model fetch failed: {e}")
                return ["local-model"]

        elif provider_name == "openrouter":
            api_key = cfg.get("api_key")
            url = cfg.get("base_url", DEFAULT_OPENROUTER_URL).rstrip("/")
            if api_key:
                try:
                    headers = {"Authorization": f"Bearer {api_key}"}
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        res = await client.get(f"{url}/models", headers=headers)
                        if res.status_code == 200:
                            data = res.json()
                            ids = [m["id"] for m in data.get("data", [])]
                            if ids:
                                return ids[:40]
                except Exception as e:
                    print(f"[LLMManager] OpenRouter models fetch failed: {e}")
            return self.KNOWN_MODELS.get("openrouter", [])

        # Gemini & Claude return known curated lists
        return self.KNOWN_MODELS.get(provider_name, [])

    # =========================================================================
    # LIVE TEST CONNECTION
    # =========================================================================
    async def test_connection(self, provider_name: str, config_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sends a lightweight test ping prompt to the provider and model.
        Returns latency in milliseconds, response sample, and status.
        """
        cfg = dict(self.get_provider_config(provider_name))
        if config_override:
            cfg.update(config_override)

        model = cfg.get("model", "")
        start_time = time.time()

        try:
            if provider_name == "ollama":
                url = cfg.get("base_url", DEFAULT_OLLAMA_URL).rstrip("/")
                target_model = model or "qwen3-coder:30b"
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.post(
                        f"{url}/api/generate",
                        json={
                            "model": target_model,
                            "prompt": "Say 'READY' and nothing else.",
                            "stream": False,
                            "options": {"num_predict": 10, "temperature": 0.1}
                        }
                    )
                    if res.status_code != 200:
                        return {"status": "error", "message": f"Ollama HTTP {res.status_code}: {res.text[:200]}"}
                    data = res.json()
                    reply = data.get("response", "").strip()

            elif provider_name == "lm_studio":
                url = cfg.get("base_url", DEFAULT_LM_STUDIO_URL).rstrip("/")
                target_model = model or "local-model"
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.post(
                        f"{url}/chat/completions",
                        json={
                            "model": target_model,
                            "messages": [{"role": "user", "content": "Say 'READY' and nothing else."}],
                            "max_tokens": 10,
                            "temperature": 0.1
                        }
                    )
                    if res.status_code != 200:
                        return {"status": "error", "message": f"LM Studio HTTP {res.status_code}: {res.text[:200]}"}
                    data = res.json()
                    reply = data["choices"][0]["message"]["content"].strip()

            elif provider_name == "gemini":
                key = cfg.get("api_key", "").strip()
                if not key:
                    return {"status": "error", "message": "Gemini API Key is missing. Please enter your API key."}
                target_model = model or "gemini-2.5-flash"
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={key}"
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.post(
                        endpoint,
                        json={
                            "contents": [{"parts": [{"text": "Say 'READY' and nothing else."}]}],
                            "generationConfig": {"maxOutputTokens": 10}
                        }
                    )
                    if res.status_code != 200:
                        return {"status": "error", "message": f"Gemini HTTP {res.status_code}: {res.text[:200]}"}
                    data = res.json()
                    reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()

            elif provider_name == "claude":
                key = cfg.get("api_key", "").strip()
                if not key:
                    return {"status": "error", "message": "Anthropic API Key is missing. Please enter your API key."}
                target_model = model or "claude-3-5-sonnet-20241022"
                endpoint = "https://api.anthropic.com/v1/messages"
                headers = {
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.post(
                        endpoint,
                        headers=headers,
                        json={
                            "model": target_model,
                            "max_tokens": 15,
                            "messages": [{"role": "user", "content": "Say 'READY' and nothing else."}]
                        }
                    )
                    if res.status_code != 200:
                        return {"status": "error", "message": f"Claude HTTP {res.status_code}: {res.text[:200]}"}
                    data = res.json()
                    reply = data["content"][0]["text"].strip()

            elif provider_name == "openrouter":
                key = cfg.get("api_key", "").strip()
                if not key:
                    return {"status": "error", "message": "OpenRouter API Key is missing. Please enter your API key."}
                target_model = model or "anthropic/claude-3.5-sonnet"
                url = cfg.get("base_url", DEFAULT_OPENROUTER_URL).rstrip("/")
                headers = {
                    "Authorization": f"Bearer {key}",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "InterviewAssist",
                    "Content-Type": "application/json"
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.post(
                        f"{url}/chat/completions",
                        headers=headers,
                        json={
                            "model": target_model,
                            "messages": [{"role": "user", "content": "Say 'READY' and nothing else."}],
                            "max_tokens": 10,
                            "temperature": 0.1
                        }
                    )
                    if res.status_code != 200:
                        return {"status": "error", "message": f"OpenRouter HTTP {res.status_code}: {res.text[:200]}"}
                    data = res.json()
                    reply = data["choices"][0]["message"]["content"].strip()
            else:
                return {"status": "error", "message": f"Unknown provider: {provider_name}"}

            latency_ms = int((time.time() - start_time) * 1000)
            return {
                "status": "success",
                "provider": provider_name,
                "model": model,
                "latency_ms": latency_ms,
                "reply": reply[:100]
            }

        except httpx.ConnectError:
            return {
                "status": "error",
                "message": f"Connection refused. Is {cfg.get('name', provider_name)} server running at {cfg.get('base_url', '')}?"
            }
        except httpx.TimeoutException:
            return {
                "status": "error",
                "message": f"Connection timed out after 15s. The model may be cold-loading or the server is busy."
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # CORE COMPLETION ENGINE
    # =========================================================================
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: float = 45.0
    ) -> str:
        """Executes text generation against the currently active provider."""
        active_p = self.config.get("active_provider", "ollama")
        cfg = self.get_provider_config(active_p)
        model = self.config.get("active_model") or cfg.get("model")

        if active_p == "ollama":
            return await self.ollama_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                timeout=timeout
            )

        elif active_p == "lm_studio":
            url = cfg.get("base_url", DEFAULT_LM_STUDIO_URL).rstrip("/")
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(
                    f"{url}/chat/completions",
                    json={
                        "model": model or "local-model",
                        "messages": messages,
                        "temperature": 0.2
                    }
                )
                if res.status_code != 200:
                    raise RuntimeError(f"LM Studio error {res.status_code}: {res.text}")
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()

        elif active_p == "gemini":
            key = cfg.get("api_key") or GEMINI_API_KEY
            if not key:
                raise RuntimeError("Gemini API key is not configured.")
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model or 'gemini-2.5-flash'}:generateContent?key={key}"
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(
                    endpoint,
                    json={"contents": [{"parts": [{"text": full_prompt}]}]}
                )
                if res.status_code != 200:
                    raise RuntimeError(f"Gemini error {res.status_code}: {res.text}")
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()

        elif active_p == "claude":
            key = cfg.get("api_key") or ANTHROPIC_API_KEY
            if not key:
                raise RuntimeError("Claude API key is not configured.")
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            body: Dict[str, Any] = {
                "model": model or "claude-3-5-sonnet-20241022",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}]
            }
            if system_prompt:
                body["system"] = system_prompt

            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
                if res.status_code != 200:
                    raise RuntimeError(f"Claude error {res.status_code}: {res.text}")
                data = res.json()
                return data["content"][0]["text"].strip()

        elif active_p == "openrouter":
            key = cfg.get("api_key") or OPENROUTER_API_KEY
            if not key:
                raise RuntimeError("OpenRouter API key is not configured.")
            url = cfg.get("base_url", DEFAULT_OPENROUTER_URL).rstrip("/")
            headers = {
                "Authorization": f"Bearer {key}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "InterviewAssist",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(
                    f"{url}/chat/completions",
                    headers=headers,
                    json={
                        "model": model or "anthropic/claude-3.5-sonnet",
                        "messages": messages,
                        "temperature": 0.2
                    }
                )
                if res.status_code != 200:
                    raise RuntimeError(f"OpenRouter error {res.status_code}: {res.text}")
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()

        raise RuntimeError(f"Unsupported active provider: {active_p}")

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: float = 45.0
    ) -> Any:
        """Generates structured JSON from the active provider with markdown block stripping."""
        json_instruction = (
            prompt +
            "\n\nCRITICAL FORMAT REQUIREMENT: Output MUST be strictly valid, parseable JSON only. "
            "Do NOT include markdown backticks ```json or ```. Do NOT include any conversational preamble or sign-off."
        )
        raw = await self.generate_text(json_instruction, system_prompt=system_prompt, timeout=timeout)

        # Robust JSON cleaning
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Attempt to extract first array or object if wrapped in text
            match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", cleaned)
            if match:
                return json.loads(match.group(1))
            raise RuntimeError(f"Failed to parse valid JSON from LLM response: {raw[:300]}")
