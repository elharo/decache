from decache import cache_entry


def test_cache_entry():
    entry = cache_entry.CacheEntry(url="https://www.example.org/foo.jpg", media_type="image/jpg")
    assert entry.url == "https://www.example.org/foo.jpg"
    assert entry.media_type == "image/jpg"


def test_cache_map():
    pass
