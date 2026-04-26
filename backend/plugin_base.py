from abc import ABC, abstractmethod
from typing import Any, Dict

class NodePlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def input_type(self) -> str:
        pass

    @property
    @abstractmethod
    def output_type(self) -> str:
        pass

    @abstractmethod
    def run(self, input_data: Any, params: Dict) -> Any:
        pass

class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, NodePlugin] = {}

    def register(self, plugin: NodePlugin):
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> NodePlugin:
        if name not in self._plugins:
            raise ValueError(f"Plugin {name} not registered")
        return self._plugins[name]
