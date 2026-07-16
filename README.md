# Veronica AI

A **private, agentic** terminal chatbot written in Python. Runs **online by default**
via **OpenCode Zen (free models)** with **web search**, and falls back to offline
mode automatically if no API key is present.

## Privacy

- The conversation is kept **in memory only** — it is **never written to disk** and
  there is **no telemetry**.
- Only you and the AI model see the messages. (The AI provider necessarily receives
  the conversation to generate replies; your key stays local in `.env`, which is gitignored.)

## Features

- **Online by default** via `opencode` (free Zen models: `hy3-free`, `deepseek-v4-flash-free`, …)
- **Agentic**: the model autonomously calls tools (function calling), capped at 4 tool rounds
- **Web search** tool (DuckDuckGo → Bing → Google fallback, Indonesia-biased, no key)
- `get_current_time` and `calculate` helper tools
- Offline `local` mode (no key needed)
- Claude-Code-style terminal UI (colored status bar, `⚙ tool` indicators)
- Commands: `!help`, `!list`, `!provider`, `!model`, `!web`, `!clear`, `!quit`
- Clean package, no comments, standard library only

## Install

No third-party dependencies — uses only the Python standard library.

## Run

```bash
python -m terminal_chatbot          # online (opencode) by default, with web search
python -m terminal-chatbot --local  # force offline mode (no network)
python -m terminal_chatbot --list   # list providers and models
python -m terminal_chatbot -p opencode -m hy3-free
```

## Providers & keys

| Provider  | Env var              | Free? | Notes                                  |
| --------- | -------------------- | ----- | -------------------------------------- |
| `local`   | –                    | yes   | Built-in rule-based replies            |
| `opencode`| `OPENCODE_API_KEY`   | yes*  | Free models via OpenCode Zen gateway   |

`*` OpenCode free models need a free Zen API key from https://opencode.ai (sign in →
copy key). Get a key and export it:

```bash
export OPENCODE_API_KEY="zen-...."
python -m terminal_chatbot -p opencode
```

You can also pass a key inline with `-k`, or set provider/model at runtime:

```
you> !list
you> !provider opencode
you> !model deepseek-v4-flash-free
you> !web jakarta weather today
you> !clear
you> !quit
```

The assistant will call `web_search` automatically when it needs current info.
A `.env` file (gitignored) can hold `OPENCODE_API_KEY=...`.

## Author

Built by **faqihabdulmaalik** — a proud vibecoder. Thanks for checking it out! ⚡

## License

MIT
