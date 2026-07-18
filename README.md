# Veronica AI

An **open-source, agentic terminal chatbot** — your Python-powered AI assistant
that runs in the terminal, calls tools autonomously, and remembers everything
between chats.

Built with **zero third-party dependencies** — only the Python standard library.
Free to use, free to modify, free to build on.

## Features

- **25+ tools** — web search, file read/write/list, run & review Python code,
  GitHub API, email sending, file upload, HTTP requests, weather, URL fetching,
  currency & unit conversion, news headlines, and more
- **Conversation memory** — remembers your name, preferences, watchlists, and
  GitHub identity between sessions (JSON-based, stored locally)
- **Agentic** — the model autonomously decides which tools to call, capped at
  4 tool rounds
- **Online by default** via `opencode` (free Zen models: `hy3-free`,
  `deepseek-v4-flash-free`, …)
- **Web search** (DuckDuckGo → Bing → Google fallback, no API key)
- **Streaming output** — responses appear token-by-token in real time
- **Privacy** — conversations stay in memory only, never written to disk,
  no telemetry
- **OpenAI-compatible API server** — `server.py` exposes a REST API
- **Sensitive tool verification** — destructive operations prompt `(y/N)`
  before executing
- **Claude-Code-style terminal UI** — colored status bar, tool indicators,
  markdown rendering
- **Offline mode** — built-in rule-based replies with `--local`

## Install

```bash
git clone https://github.com/FaqihAbdulMaalik/veronica-agent-system.git
cd veronica-agent-system
```

No `pip install` needed. Python 3.10+ required (uses `ast` module features).

## Run

```bash
python -m terminal_chatbot                    # online with web search
python -m terminal_chatbot --local            # offline mode
python -m terminal_chatbot --list             # list providers & models
python -m terminal_chatbot -p opencode -m hy3-free
```

Get a free Zen API key at https://opencode.ai and put it in `.env`:
```
OPENCODE_API_KEY=zen-....
```

## Tools

| Category | Tools |
|----------|-------|
| **Memory** | `remember`, `recall`, `forget`, `list_memories`, `clear_memory` |
| **Files** | `read_file`, `write_file`, `list_dir` |
| **Code** | `run_code`, `review_code` |
| **Web** | `web_search`, `fetch_page`, `read_url`, `get_news` |
| **Conversion** | `convert` (currency + units) |
| **Weather** | `get_weather` |
| **Time** | `get_current_time`, `calculate` |
| **GitHub** | `github_get_repo`, `github_list_issues`, `github_create_issue`, `github_search_code` |
| **Network** | `http_request`, `upload_file` |
| **Email** | `send_email` |

## Commands

```
  !help               show help
  !list               list providers and models
  !provider <id>      switch provider (local/opencode)
  !model <name>       set model
  !web <query>        search the web directly
  !clear              clear conversation memory
  !quit               exit
```

## API Server

```bash
python server.py
```

Exposes an OpenAI-compatible API at `POST /v1/chat/completions`.

## Contributing

**This is an open-source project** and everyone is welcome to contribute!

### How to contribute

1. **Fork** the repo on GitHub
2. Make your changes in your fork
3. Open a **Pull Request** back to `FaqihAbdulMaalik/veronica-agent-system`
4. Wait for review — all PRs are welcome!

- **Python learners** — study the code, add new tools, improve existing ones.
  The entire project uses only the standard library — great for learning how
  things work under the hood.
- **ML practitioners** — plug in your own models via the provider system,
  experiment with agentic loops, or build custom toolchains.
- **Web developers** — build a web interface for Veronica (the API server
  already speaks OpenAI-compatible format).
- **Anyone** — fork it, feature it, ship it. Build a desktop app, a website,
  a Slack bot, whatever you want.

Ideas to get started:
- [ ] Web-based UI (React/Vue/Svelte frontend for the API server)
- [ ] Desktop app (Tkinter, Electron, or native)
- [ ] More providers (OpenAI, Anthropic, local LLMs via Ollama)
- [ ] SQLite-backed memory instead of JSON
- [ ] Plugin system for community-contributed tools
- [ ] Voice input/output

## License

MIT — do whatever you want.

## Author

Built by **faqihabdulmaalik** — a proud vibecoder. ⚡
