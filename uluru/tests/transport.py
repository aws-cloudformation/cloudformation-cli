from abc import ABC, abstractmethod


class Transport(ABC):
    @abstractmethod
    def send(self, payload, callback_endpoint):
        """Send payload to specified endpoint
        """
        pass
