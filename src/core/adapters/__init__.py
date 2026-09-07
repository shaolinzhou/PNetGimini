"""
Vendor Adapters package for PNetGimini.
Provides normalized abstraction for Cisco, Huawei, and future network vendors.
"""
from .factory import AdapterFactory
from .base import BaseAdapter

__all__ = ["AdapterFactory", "BaseAdapter"]
