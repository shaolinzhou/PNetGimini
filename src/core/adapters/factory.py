from typing import Dict
from .base import BaseAdapter
from .cisco import CiscoAdapter
from .huawei import HuaweiAdapter

class AdapterFactory:
    """
    Factory for instantiating vendor-specific adapters based on device_type.
    """
    _adapters: Dict[str, BaseAdapter] = {}

    @classmethod
    def get_adapter(cls, device_type: str) -> BaseAdapter:
        dt_lower = device_type.lower()
        if "huawei" in dt_lower:
            if "huawei" not in cls._adapters:
                cls._adapters["huawei"] = HuaweiAdapter()
            return cls._adapters["huawei"]
        else:
            # Default to Cisco
            if "cisco" not in cls._adapters:
                cls._adapters["cisco"] = CiscoAdapter()
            return cls._adapters["cisco"]
