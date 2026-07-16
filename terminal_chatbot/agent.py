import json

from .tools import TOOLS, SENSITIVE_TOOLS, execute_tool


class Agent:
    def __init__(self, provider, history=None, system_prompt=None, max_tool_rounds=4):
        self.provider = provider
        self.history = history if history is not None else []
        self.tools = TOOLS
        self.max_tool_rounds = max_tool_rounds
        if system_prompt and not (self.history and self.history[0].get("role") == "system"):
            self.history.insert(0, {"role": "system", "content": system_prompt})

    def send(self, text):
        self.history.append({"role": "user", "content": text})

        rounds = 0
        while True:
            message = self.provider.chat(self.history, tools=self.tools)

            if message.get("tool_calls"):
                rounds += 1
                if rounds > self.max_tool_rounds:
                    self.history.append({
                        "role": "user",
                        "content": "Stop using tools. Answer the user's question now using what you have.",
                    })
                    continue
                self.history.append(message)
                for call in message["tool_calls"]:
                    name = call["function"]["name"]
                    try:
                        args = json.loads(call["function"]["arguments"] or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    yield ("tool", (name, args))
                    result = execute_tool(name, args)
                    self.history.append({
                        "role": "tool",
                        "content": result,
                        "tool_call_id": call["id"],
                    })
                continue

            content = message.get("content") or ""
            self.history.append({"role": "assistant", "content": content})
            yield ("text", content)
            break

    def send_stream(self, text):
        self.history.append({"role": "user", "content": text})
        rounds = 0
        while True:
            full_text = ""
            tool_message = None
            for event in self.provider.chat_stream(self.history, tools=self.tools):
                if event[0] == "delta":
                    full_text += event[1]
                    yield event
                elif event[0] == "tool_calls":
                    tool_message = event[1]
                elif event[0] == "text":
                    full_text = event[1]
            if tool_message:
                rounds += 1
                if rounds > self.max_tool_rounds:
                    self.history.append({
                        "role": "user",
                        "content": "Stop using tools. Answer the user's question now using what you have.",
                    })
                    continue
                self.history.append(tool_message)
                for call in tool_message["tool_calls"]:
                    name = call["function"]["name"]
                    try:
                        args = json.loads(call["function"]["arguments"] or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    if name in SENSITIVE_TOOLS:
                        confirmed = yield ("verify", {"tool": name, "args": args, "description": call["function"].get("description", "")})
                        if not confirmed:
                            self.history.append({
                                "role": "tool",
                                "content": f"[tool {name} skipped: user denied verification]",
                                "tool_call_id": call["id"],
                            })
                            continue
                    yield ("tool", (name, args))
                    result = execute_tool(name, args)
                    self.history.append({
                        "role": "tool",
                        "content": result,
                        "tool_call_id": call["id"],
                    })
                continue
            self.history.append({"role": "assistant", "content": full_text})
            if full_text:
                yield ("text", full_text)
            break
