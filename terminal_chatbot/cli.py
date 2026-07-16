import argparse
import os
import sys

from .config import list_providers, PROVIDERS
from .bot import ChatBot, COMMANDS
from .ui import header, prompt, tool_line, status, error, separator, status_bar, user_line, render_markdown


def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def build_arg_parser():
    p = argparse.ArgumentParser(
        prog="terminal-chatbot",
        description="A private, agentic terminal chatbot with web search, powered by OpenCode Zen free models.",
    )
    p.add_argument("-p", "--provider", default="opencode",
                   help="provider: opencode (default, online+search), local")
    p.add_argument("-m", "--model", default=None, help="model id (defaults to provider default)")
    p.add_argument("-k", "--key", default=None, help="API key override (else read from env)")
    p.add_argument("--list", action="store_true", help="list providers and models, then exit")
    p.add_argument("--local", action="store_true", help="force offline mode (no network)")
    return p


def print_list():
    print("Providers:")
    for pid, label, default_model, tag in list_providers():
        print(f"  {pid:<10} [{tag}] {label}")
        spec = PROVIDERS[pid]
        for m in spec["models"]:
            mark = " *" if m == default_model else "  "
            print(f"      {mark} {m}")


def run_repl(bot):
    print(header(bot.provider.label, bot.provider.model))
    print(status("Private agentic chat · web search on · conversation kept in memory only"))
    print(status("Type '!help' for commands · 'exit' to quit\n"))

    while True:
        try:
            user = input(prompt()).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n" + status("Sampai jumpa!"))
            break

        if not user:
            continue

        if user in COMMANDS or user.split()[0] in COMMANDS:
            out = bot.handle_command(user)
            if out == "__quit__":
                print(status("Sampai jumpa!"))
                break
            print(out)
            continue

        if bot.should_exit(user):
            print(status("Sampai jumpa!"))
            break

        try:
            streaming_text = ""
            for kind, payload in bot.run(user):
                if kind == "tool":
                    name, args = payload
                    print(tool_line(name, args))
                elif kind == "delta":
                    streaming_text += payload
                    print(payload, end="", flush=True)
                elif kind == "text":
                    if streaming_text:
                        print()
                    else:
                        print(render_markdown(payload))
        except Exception as exc:
            print(error(f"[error: {exc}]"))
        print(status_bar(bot.provider.label, bot.provider.model))
        print(separator())


def main(argv=None):
    load_env()
    args = build_arg_parser().parse_args(argv)

    if args.list:
        print_list()
        return

    if args.local:
        args.provider = "local"

    try:
        bot = ChatBot(provider_id=args.provider, model=args.model, api_key=args.key)
    except Exception as exc:
        if args.provider in PROVIDERS and PROVIDERS[args.provider].get("free") is not True and not (
            args.key or os.environ.get(PROVIDERS[args.provider]["env_key"])
        ):
            print(status(f"No API key for '{args.provider}' — falling back to local offline mode."))
            bot = ChatBot(provider_id="local")
        elif args.provider == "opencode" and not (args.key or os.environ.get("OPENCODE_API_KEY")):
            print(status("No OPENCODE_API_KEY found — falling back to local offline mode."))
            bot = ChatBot(provider_id="local")
        else:
            print(error(f"Error: {exc}"), file=sys.stderr)
            sys.exit(1)

    run_repl(bot)


if __name__ == "__main__":
    main()
