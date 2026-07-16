import ast
import base64
import datetime
import io
import json
import os
import re
import sys
import traceback
import urllib.parse
import urllib.request

SENSITIVE_TOOLS = {"run_code", "write_file"}

SYSTEM_PROMPT = (
    "You are Veronica AI, an advanced terminal assistant with extensive tool access. "
    "You can read/write files (read_file, write_file, list_dir), run and review Python code "
    "(run_code, review_code), search the web (web_search), get weather (get_weather), "
    "fetch URLs (read_url, http_request), and more. Keep replies concise and in the user's language. "
    "When you have the answer from a tool, summarize it clearly."
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
            "description": "Get current weather conditions for a location using wttr.in.",
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
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the filesystem and return its text content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path (absolute or relative to cwd)"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text content to a file. New directories are created automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write to"},
                    "content": {"type": "string", "description": "Text content to write"}
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories at a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path (default: current directory)"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_code",
            "description": "Execute Python code and return its output. Will ask for user confirmation first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"}
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "review_code",
            "description": "Analyze Python code for syntax errors, style issues, and potential problems.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to review"}
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "http_request",
            "description": "Make an HTTP request to any REST API. Auto-injects GitHub token for api.github.com.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL (including https://)"},
                    "method": {"type": "string", "description": "HTTP method: GET, POST, PUT, DELETE, PATCH"},
                    "headers": {"type": "object", "description": "Optional headers as key/value pairs"},
                    "body": {"type": "string", "description": "Request body (string or JSON dict)"}
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


def read_file(path):
    abs_path = os.path.abspath(os.path.join(os.getcwd(), path))
    if not os.path.exists(abs_path):
        return f"[read_file error: file not found]"
    if os.path.isdir(abs_path):
        return f"[read_file error: path is a directory, use list_dir instead]"
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return content[:20000]
    except Exception as exc:
        return f"[read_file error: {exc}]"


def write_file(path, content):
    abs_path = os.path.abspath(os.path.join(os.getcwd(), path))
    dir_path = os.path.dirname(abs_path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    try:
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"[written {len(content)} bytes to {abs_path}]"
    except Exception as exc:
        return f"[write_file error: {exc}]"


def list_dir(path="."):
    abs_path = os.path.abspath(os.path.join(os.getcwd(), path))
    if not os.path.exists(abs_path):
        return f"[list_dir error: path not found]"
    if not os.path.isdir(abs_path):
        return f"[list_dir error: not a directory]"
    try:
        items = os.listdir(abs_path)
        lines = []
        for name in sorted(items):
            full = os.path.join(abs_path, name)
            suffix = "/" if os.path.isdir(full) else ""
            size = os.path.getsize(full) if os.path.isfile(full) else 0
            size_str = f" ({size} B)" if size else ""
            lines.append(f"  {name}{suffix}{size_str}")
        return f"Contents of {abs_path}:\n" + "\n".join(lines)
    except Exception as exc:
        return f"[list_dir error: {exc}]"


def run_code(code):
    local_vars = {"__builtins__": __builtins__}
    output = io.StringIO()
    old_out = sys.stdout
    sys.stdout = output
    try:
        exec(code, local_vars)
    except Exception:
        sys.stdout = old_out
        return traceback.format_exc()
    sys.stdout = old_out
    result = output.getvalue()
    return result or "[code executed successfully, no output]"


def review_code(code):
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"[syntax error]\n{exc}"
    lines = code.split("\n")
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if len(node.body) > 50:
                issues.append(f"Line {node.lineno}: Function '{node.name}' has {len(node.body)} body lines (keep under 50)")
            if not node.name.islower():
                issues.append(f"Line {node.lineno}: Function '{node.name}' should be snake_case")
            if not node.body:
                issues.append(f"Line {node.lineno}: Empty function '{node.name}'")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name in ("os", "sys", "subprocess", "shutil"):
                    pass
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("eval", "exec", "__import__"):
                issues.append(f"Line {node.lineno}: Avoid {node.func.attr}() — security risk")
        elif isinstance(node, ast.Try) and not node.handlers and not node.finalbody:
            issues.append(f"Line {node.lineno}: Bare try without except or finally")
    issues.append(f"Total: {len(lines)} lines, {len(list(ast.walk(tree)))} AST nodes")
    return "\n".join(issues) if issues else "No issues found."


def http_request(method="GET", url="", headers=None, body=None):
    extra_headers = dict(headers or {})
    if "api.github.com" in url:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token and "Authorization" not in extra_headers:
            extra_headers["Authorization"] = f"Bearer {token}"
    data = None
    if body:
        if isinstance(body, dict) or (isinstance(body, str) and body.strip().startswith("{")):
            if isinstance(body, str):
                body = json.loads(body)
            data = json.dumps(body).encode()
            extra_headers.setdefault("Content-Type", "application/json")
        else:
            data = body.encode() if isinstance(body, str) else body
    req = urllib.request.Request(url, data=data, method=method.upper() if method else "GET")
    req.add_header("User-Agent", "terminal-chatbot/2.0")
    for k, v in extra_headers.items():
        req.add_header(k, v)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        resp_body = resp.read().decode("utf-8", "ignore")
        return f"Status: {resp.status}\n\n{resp_body[:5000]}"
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}: {exc.read().decode('utf-8', 'ignore')[:1000]}"
    except Exception as exc:
        return f"[http_request error: {exc}]"


DISPATCH = {
    "web_search": lambda args: web_search(args.get("query", "")),
    "get_current_time": lambda args: get_current_time(),
    "calculate": lambda args: calculate(args.get("expression", "")),
    "get_weather": lambda args: get_weather(args.get("location", "")),
    "read_url": lambda args: read_url(args.get("url", "")),
    "read_file": lambda args: read_file(args.get("path", "")),
    "write_file": lambda args: write_file(args.get("path", ""), args.get("content", "")),
    "list_dir": lambda args: list_dir(args.get("path", ".")),
    "run_code": lambda args: run_code(args.get("code", "")),
    "review_code": lambda args: review_code(args.get("code", "")),
    "http_request": lambda args: http_request(
        args.get("method", "GET"),
        args.get("url", ""),
        args.get("headers"),
        args.get("body"),
    ),
}


def execute_tool(name, args):
    fn = DISPATCH.get(name)
    if not fn:
        return f"[unknown tool: {name}]"
    try:
        return str(fn(args))
    except Exception as exc:
        return f"[tool {name} error: {exc}]"
