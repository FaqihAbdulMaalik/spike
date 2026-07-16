import re
import random

from .base import BaseProvider

FAREWELL_WORDS = {"bye", "dadah", "keluar", "exit", "quit", "out"}

GREETINGS = ["halo", "hai", "hi", "hello", "hey"]
FAREWELLS = ["bye", "dadah", "keluar", "exit", "quit", "out"]

RESPONSES = {
    "apa kabar": ["Alhamdulillah baik, kamu gimana?", "Lancar aja. Ada yang bisa dibantu?"],
    "nama": ["Aku Veronica AI, asisten kecilmu di terminal.", "Namaku Veronica AI."],
    "terima kasih": ["Sama-sama!", "Kapanpun, bos."],
}

FALLBACKS = [
    "Hmm, aku belum paham. Bisa dijelaskan lain?",
    "Menarik. Cerita lebih lanjut dong.",
    "Maaf, aku masih belajar. Coba tanya hal lain.",
]


def normalize(text):
    return re.sub(r"[^a-z0-9\s]", "", text.lower().strip())


def should_exit(text):
    words = set(re.findall(r"[a-z0-9]+", normalize(text)))
    return bool(words & FAREWELL_WORDS)


class LocalProvider(BaseProvider):
    id = "local"
    label = "Local (offline)"
    model = "rule-based"

    def reply(self, history):
        text = normalize(history[-1]["content"]) if history else ""

        if any(g in text for g in GREETINGS):
            return random.choice(["Halo!", "Hai! Ada yang bisa kubantu?", "Hey, senang bertemu."])
        if any(f in text for f in FAREWELLS):
            return "Sampai jumpa!"

        for key, replies in RESPONSES.items():
            if key in text:
                return random.choice(replies)

        return random.choice(FALLBACKS)
