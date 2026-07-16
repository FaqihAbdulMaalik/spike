from abc import ABC, abstractmethod


class BaseProvider(ABC):
    id = "base"
    label = "Base"

    @abstractmethod
    def reply(self, history):
        ...

    def stream_reply(self, history):
        yield self.reply(history)
