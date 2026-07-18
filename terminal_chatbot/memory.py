import json
import os

MEMORY_PATH = os.path.expanduser("~/.veronica_memory.json")


def _load():
    if not os.path.exists(MEMORY_PATH):
        return {}
    try:
        with open(MEMORY_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data):
    dirname = os.path.dirname(MEMORY_PATH)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)
    with open(MEMORY_PATH, "w") as f:
        json.dump(data, f, indent=2)


def remember(key, value):
    data = _load()
    data[key] = value
    _save(data)
    return f"[remembered '{key}']"


def recall(key):
    data = _load()
    return data.get(key, f"[nothing remembered for '{key}']")


def forget(key):
    data = _load()
    if key in data:
        del data[key]
        _save(data)
        return f"[forgotten '{key}']"
    return f"[nothing to forget for '{key}']"


def list_memories():
    data = _load()
    if not data:
        return "[nothing remembered yet]"
    lines = [f"  {k}: {v}" for k, v in data.items()]
    return "Stored memories:\n" + "\n".join(lines)


def clear_memory():
    _save({})
    return "[all memories cleared]"
