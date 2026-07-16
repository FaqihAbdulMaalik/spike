from .config import PROVIDERS, build_provider
from .providers.local import LocalProvider, should_exit, normalize
from .tools import SYSTEM_PROMPT, execute_tool

COMMANDS = {"!help", "!clear", "!list", "!provider", "!model", "!web", "!quit"}

CREATOR_KEYWORDS = ["who made you", "who created you", "siapa pembuat", "pembuatmu",
                    "siapa yang membuat", "creator", "buat kamu", "pembuat veronica"]

CREATOR_ANSWER = (
    "I was made by faqihabdulmaalik, a junior data analyst. "
    "His Python skill is currently at grade 9 (since July 5, 2012)."
)


class ChatBot:
    def __init__(self, provider_id="local", model=None, api_key=None):
        self.provider_id = provider_id
        self.model = model
        self.api_key = api_key
        self.history = []
        self._load()

    def _load(self):
        self.provider = build_provider(self.provider_id, self.model, self.api_key)
        if hasattr(self.provider, "chat"):
            from .agent import Agent

            self.agent = Agent(self.provider, history=self.history, system_prompt=SYSTEM_PROMPT)
        else:
            self.agent = None

    def switch_provider(self, provider_id, model=None):
        self.provider_id = provider_id
        self.model = model
        self._load()
        return f"Switched to provider '{provider_id}' (model: {self.provider.model})."

    def set_model(self, model):
        if self.provider_id == "local":
            return "Local provider has no model to set."
        self.model = model
        self._load()
        return f"Model set to '{model}'."

    def handle_command(self, text):
        parts = text.split()
        cmd = parts[0]

        if cmd == "!help":
            return (
                "Commands:\n"
                "  !help               show this help\n"
                "  !list               list providers and models\n"
                "  !provider <id>      switch provider (local/opencode)\n"
                "  !model <name>       set model for current provider\n"
                "  !web <query>        search the web directly\n"
                "  !clear              clear conversation memory\n"
                "  !quit               exit\n"
                "  exit / bye          exit"
            )
        if cmd == "!clear":
            self.history = []
            self._load()
            return "Memory cleared."
        if cmd == "!list":
            lines = ["Providers:"]
            for pid, spec in PROVIDERS.items():
                tag = "free" if spec.get("free") else "needs key"
                lines.append(f"  {pid}  [{tag}]  ({spec['env_key']})")
                for m in spec["models"]:
                    marker = " *" if m == spec["default_model"] else "  "
                    lines.append(f"      {marker} {m}")
            return "\n".join(lines)
        if cmd == "!provider":
            if len(parts) < 2:
                return "Usage: !provider <id>"
            return self.switch_provider(parts[1])
        if cmd == "!model":
            if len(parts) < 2:
                return "Usage: !model <name>"
            return self.set_model(parts[1])
        if cmd == "!web":
            if len(parts) < 2:
                return "Usage: !web <query>"
            return self.web(" ".join(parts[1:]))
        if cmd == "!quit":
            return "__quit__"
        return None

    def web(self, query):
        result = execute_tool("web_search", {"query": query})
        self.history.append({
            "role": "user",
            "content": f"[web search results for '{query}']\n{result}",
        })
        return result

    def keyword_reply(self, text):
        if any(k in normalize(text) for k in CREATOR_KEYWORDS):
            return CREATOR_ANSWER
        return None

    def run(self, text):
        kw = self.keyword_reply(text)
        if kw:
            self.history.append({"role": "user", "content": text})
            self.history.append({"role": "assistant", "content": kw})
            yield ("text", kw)
            return

        if self.agent is not None:
            if hasattr(self.provider, "chat_stream"):
                for event in self.agent.send_stream(text):
                    yield event
            else:
                for event in self.agent.send(text):
                    yield event
            return
        self.history.append({"role": "user", "content": text})
        reply = self.provider.reply(self.history)
        self.history.append({"role": "assistant", "content": reply})
        yield ("text", reply)

    def should_exit(self, text):
        return should_exit(text)
