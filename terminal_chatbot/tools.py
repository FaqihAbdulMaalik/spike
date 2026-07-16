import ast
import base64
import datetime
import json
import re
import urllib.parse
import urllib.request

SYSTEM_PROMPT = (
    "You are Veronica AI, a helpful terminal assistant with tool access. "
    "When the user asks something that needs current information, call the "
    "web_search tool. For weather, call get_weather. To fetch and read a page, call read_url. "
    "Keep replies concise and in the user's language. "
    "When you have the answer from a tool, summarize it clearly and cite sources by URL."
)


def _fetch(url, extra_headers=None):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")


def _strip(html):
    return re.sub(r"<.*?>", "", html).strip()


def _ddg(query, num):
    html = _fetch("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query) + "&kl=id-id")
    blocks = re.findall(
        r'class="result__a"[^>]*href="([^"]+)".*?>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>',
        html,
        re.S,
    )
    out = []
    for link, title, snippet in blocks:
        link = urllib.parse.unquote(link)
        if link.startswith("//"):
            link = "https:" + link
        out.append((_strip(title), link, _strip(snippet)))
        if len(out) >= num:
            break
    return out


def _decode_bing_url(href):
    m = re.search(r"u=a1([^&]+)", href)
    if not m:
        return href
    try:
        return base64.b64decode(m.group(1) + "==").decode("utf-8", "ignore")
    except Exception:
        return href


def _bing(query, num):
    html = _fetch("https://www.bing.com/search?q=" + urllib.parse.quote(query) + "&setlang=id&cc=ID")
    blocks = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', html, re.S)
    out = []
    for block in blocks:
        tm = re.search(r'<h2[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not tm:
            continue
        sm = re.search(r'<p[^>]*>(.*?)</p>', block, re.S)
        out.append((_strip(tm.group(2)), _decode_bing_url(tm.group(1)), _strip(sm.group(1)) if sm else ""))
        if len(out) >= num:
            break
    return out


def _google(query, num):
    html = _fetch("https://www.google.com/search?q=" + urllib.parse.quote(query) + "&hl=id&gl=ID&cr=countryID",
                  {"Accept-Language": "id-ID,id;q=0.9"})
    out = []
    for m in re.finditer(
        r'<div class="g"[^>]*>.*?<h3[^>]*>(.*?)</h3>.*?<a href="(https?://[^"]+)".*?<div[^>]*>(.*?)</div>',
        html,
        re.S,
    ):
        title, link, snippet = _strip(m.group(1)), m.group(2), _strip(m.group(3))
        if "google" in link or "http" not in link:
            continue
        out.append((title, link, snippet))
        if len(out) >= num:
            break
    return out


def web_search(query, num_results=5):
    last_err = ""
    for backend in (_ddg, _bing, _google):
        try:
            results = backend(query, num_results)
        except Exception as exc:
            last_err = str(exc)
            continue
        if results:
            lines = [f"{i}. {t}\n   {u}\n   {s}" for i, (t, u, s) in enumerate(results, 1)]
            return "\n\n".join(lines)
        last_err = "no results"

    return f"[web_search failed: {last_err}]"


def get_current_time(timezone=None):
    now = datetime.datetime.now()
    return now.strftime("Current local time: %Y-%m-%d %H:%M:%S")


def calculate(expression):
    try:
        node = ast.parse(expression, mode="eval")
        for n in ast.walk(node):
            if not isinstance(n, (ast.Expression, ast.Constant, ast.BinOp,
                                  ast.UnaryOp, ast.Num, ast.Name, ast.Load,
                                  ast.Add, ast.Sub, ast.Mult, ast.Div,
                                  ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd)):
                return "[calculate error: only arithmetic allowed]"
        return str(eval(compile(node, "<calc>", "eval")))
    except Exception as exc:
        return f"[calculate error: {exc}]"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, news, or facts. Returns result titles, URLs and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Return the current local date and time.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a basic arithmetic expression, e.g. '23 * 47 + 12'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Arithmetic expression"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather conditions for a location. Returns conditions, temperature, humidity and wind.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name or location"}
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_url",
            "description": "Fetch a URL and return its page title and text content (up to 3000 chars).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The full URL to fetch"}
                },
                "required": ["url"],
            },
        },
    },
]


def get_weather(location):
    url = "https://wttr.in/" + urllib.parse.quote(location) + "?format=%C+%t+%h+%w&lang=id"
    try:
        return _fetch(url).strip()
    except Exception as exc:
        return f"[weather error: {exc}]"


def read_url(url):
    try:
        html = _fetch(url)
        title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)
        title = _strip(title_m.group(1)) if title_m else ""
        body_m = re.search(r'<body[^>]*>(.*?)</body>', html, re.I | re.S)
        body = _strip(body_m.group(1)) if body_m else _strip(html)
        body = re.sub(r'\s+', ' ', body)[:3000]
        return f"Title: {title}\n\n{body}" if title else body[:3000]
    except Exception as exc:
        return f"[read_url error: {exc}]"


DISPATCH = {
    "web_search": lambda args: web_search(args.get("query", "")),
    "get_current_time": lambda args: get_current_time(),
    "calculate": lambda args: calculate(args.get("expression", "")),
    "get_weather": lambda args: get_weather(args.get("location", "")),
    "read_url": lambda args: read_url(args.get("url", "")),
}


def execute_tool(name, args):
    fn = DISPATCH.get(name)
    if not fn:
        return f"[unknown tool: {name}]"
    try:
        return str(fn(args))
    except Exception as exc:
        return f"[tool {name} error: {exc}]"
