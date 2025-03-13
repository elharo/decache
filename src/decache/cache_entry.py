from dataclasses import dataclass


@dataclass
class CacheEntry:

    url: str
    media_type: str

