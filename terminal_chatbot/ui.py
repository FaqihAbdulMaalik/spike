import re

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    MAGENTA = "\033[35m"
    RED = "\033[31m"


def supports_color():
    return hasattr(__import__("sys").stdout, "isatty") and __import__("sys").stdout.isatty()


_USE_COLOR = supports_color()


def paint(text, *codes):
    if not _USE_COLOR:
        return text
    return "".join(codes) + text + C.RESET


def header(provider_label, model):
    line = paint("Veronica AI", C.BOLD, C.CYAN)
    line += paint("   " + "│" + "   ", C.DIM)
    line += paint(f"provider: {provider_label}", C.GREEN)
    line += paint("   " + "│" + "   ", C.DIM)
    line += paint(f"model: {model}", C.MAGENTA)
    return line


def tool_line(name, args):
    summary = ", ".join(f"{k}={v}" for k, v in (args or {}).items())
    text = f"⚙ {name}({summary})" if summary else f"⚙ {name}()"
    return paint("  " + text, C.YELLOW)


def prompt():
    return paint("❯ ", C.CYAN)


def status(text):
    return paint(text, C.DIM)


def error(text):
    return paint(text, C.RED)


def separator():
    return paint("─" * 52, C.DIM)


def status_bar(provider_label, model):
    return paint(f"│ {provider_label}  ·  {model}  ·  private session", C.DIM)


def user_line(text):
    return paint("❯ " + text, C.CYAN)


def render_markdown(text):
    lines = text.split("\n")
    out = []
    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            out.append(paint(m.group(2), C.BOLD, C.CYAN))
            continue
        if re.match(r"^---+$", line.strip()):
            out.append(paint("─" * 40, C.DIM))
            continue
        if re.match(r"^[-*]\s+", line):
            out.append("  • " + line[2:].strip())
            continue
        out.append(line)
    text = "\n".join(out)

    text = re.sub(r"`([^`]+)`", lambda m: paint(m.group(1), C.GREEN), text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: paint(m.group(1), C.BOLD), text)
    text = re.sub(r"\*([^*]+)\*", lambda m: paint(m.group(1), C.DIM), text)
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = text.replace("*", "")
    return text
