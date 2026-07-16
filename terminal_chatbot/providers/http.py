import json
import time
import urllib.request
import urllib.error

from .base import BaseProvider


class HTTPProvider(BaseProvider):
    def __init__(self, id, label, base_url, api_key, model, env_key):
        self.id = id
        self.label = label
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.env_key = env_key

        if not api_key:
            raise RuntimeError(f"No API key for {label}. Set {env_key} environment variable.")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "terminal-chatbot/2.0",
        }

    def _post(self, history, stream):
        payload = json.dumps({
            "model": self.model,
            "messages": history,
            "stream": stream,
        }).encode()
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=payload,
            headers=self._headers(),
            method="POST",
        )
        return urllib.request.urlopen(req, timeout=120)

    def reply(self, history):
        try:
            resp = self._post(history, False)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode()[:300]}")
        data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"].strip()

    def chat(self, history, tools=None):
        body = {"model": self.model, "messages": history, "stream": False}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=payload,
            headers=self._headers(),
            method="POST",
        )
        last_err = None
        for attempt in range(3):
            try:
                resp = urllib.request.urlopen(req, timeout=120)
                data = json.loads(resp.read().decode())
                return data["choices"][0]["message"]
            except urllib.error.HTTPError as exc:
                last_err = exc
                if exc.code == 429 and attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode()[:300]}")
        raise RuntimeError(f"HTTP request failed: {last_err}")

    def stream_reply(self, history):
        try:
            resp = self._post(history, True)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode()[:300]}")
        for raw in resp:
            line = raw.decode().strip()
            if not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                break
            try:
                obj = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            if not obj.get("choices"):
                continue
            delta = obj["choices"][0].get("delta", {}).get("content")
            if delta:
                yield delta

    def chat_stream(self, history, tools=None):
        body = {"model": self.model, "messages": history, "stream": True}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=payload,
            headers=self._headers(),
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=120)
        tool_calls_buffer = {}
        text_content = ""
        is_tool_call = False
        for raw in resp:
            line = raw.decode().strip()
            if not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                break
            try:
                obj = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            if not obj.get("choices"):
                continue
            delta = obj["choices"][0].get("delta", {})
            if "tool_calls" in delta:
                is_tool_call = True
                for tc_delta in delta["tool_calls"]:
                    idx = tc_delta.get("index", 0)
                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                    tc = tool_calls_buffer[idx]
                    if "id" in tc_delta:
                        tc["id"] = tc_delta["id"]
                    if "function" in tc_delta:
                        fn = tc_delta["function"]
                        if "name" in fn:
                            tc["function"]["name"] += fn["name"]
                        if "arguments" in fn:
                            tc["function"]["arguments"] += fn["arguments"]
            elif "content" in delta and delta["content"] is not None:
                text_content += delta["content"]
                yield ("delta", delta["content"])
        if is_tool_call and tool_calls_buffer:
            yield ("tool_calls", {
                "role": "assistant",
                "content": text_content or None,
                "tool_calls": [tool_calls_buffer[i] for i in sorted(tool_calls_buffer.keys())],
            })
        elif text_content:
            yield ("text", text_content)
