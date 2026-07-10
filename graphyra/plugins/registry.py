from typing import Dict, Any, Type


class PluginRegistry:
    """
    Global registry for dynamic Graphyra plugin extensions (adapters, strategies, policies).
    Allows decoupling and runtime registration of domain-specific components.
    """
    _adapters: Dict[str, Type] = {}

    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type):
        cls._adapters[name] = adapter_class

    @classmethod
    def get_adapter(cls, name: str) -> Type | None:
        return cls._adapters.get(name)

    @classmethod
    def list_adapters(cls) -> list[str]:
        return list(cls._adapters.keys())
