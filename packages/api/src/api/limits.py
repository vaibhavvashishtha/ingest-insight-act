"""Shared slowapi limiter — imported by main and routers so the same instance is used everywhere."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
