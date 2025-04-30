import os
import platform
import glob
import sys
import struct  # For unpacking binary data
from datetime import datetime
from typing import LiteralString, Optional


# TODO use exception instead of return None
def find_firefox_cache_dir() -> Optional[LiteralString]:
    """
    Find Firefox cache2 directories for the current user.
    Returns a list of potential cache directory paths.
    """
    system = platform.system()
    potential_paths = []

    if system == "Windows":
        app_data_local = os.environ.get("LOCALAPPDATA")
        app_data_roaming = os.environ.get("APPDATA")
        if app_data_local:
            potential_paths.append(os.path.join(app_data_local, "Mozilla", "Firefox", "Profiles"))
        if app_data_roaming:
            potential_paths.append(os.path.join(app_data_roaming, "Mozilla", "Firefox", "Profiles"))
    elif system == "Darwin":  # macOS
        home = os.path.expanduser("~")
        potential_paths.append(os.path.join(home, "Library", "Caches", "Firefox", "Profiles"))
    elif system == "Linux":
        home = os.path.expanduser("~")
        potential_paths.append(os.path.join(home, ".cache", "mozilla", "firefox"))
    else:
        print(f"Unsupported operating system: {system}", file=sys.stderr)
        return []

    for path in potential_paths:
        if not os.path.isdir(path):
            continue
        try:
            profile_dirs = glob.glob(os.path.join(path, "*.*"))  # Heuristic for profile names
            # TODO handle multiple profiles
            for profile_dir in profile_dirs:
                if os.path.isdir(profile_dir):
                    cache2_dir = os.path.join(profile_dir, "cache2")
                    if os.path.isdir(cache2_dir):
                        return cache2_dir
        except OSError as e:
            print(f"Warning: Could not access profile directories in {path}: {e}", file=sys.stderr)

    # Fallback for Linux flat structure
    if system == "Linux":
        home = os.path.expanduser("~")
        flat_cache_path = os.path.join(home, ".cache", "mozilla", "firefox", "cache2")
        if os.path.isdir(flat_cache_path):
            return flat_cache_path

    return None


def main():
    print("Finding Firefox cache directories...")
    cache_directory = find_firefox_cache_dir()

    if not cache_directory:
        print("Error: No Firefox cache2 directory found.", file=sys.stderr)
        sys.exit(1)

    cache_index = os.path.join(cache_directory, "index")
    if not os.path.isfile(cache_index):
        print(f"Could not locate cache index: {cache_index}", file=sys.stderr)
        sys.exit(1)

    print(f"Found cache index:")
    print(f"- {cache_index}")

    num_bytes_expected = 16
    with open(cache_index, "rb") as f:
        # Read the required number of bytes (16) from the beginning of the file
        data_bytes = f.read(num_bytes_expected)

        # Ensure we actually read enough bytes
        if len(data_bytes) < num_bytes_expected:
            # TODO exception
            print(f"Error: File '{cache_index}' is too small. "
                  f"Expected {num_bytes_expected} bytes, but only found {len(data_bytes)}.")
            sys.exit(1)

        # Unpack the bytes according to the format string
        # This will return a tuple of 4 integers
        version, timestamp, is_dirty, kb_written = struct.unpack("<IIII", data_bytes)
        # format defined in source/netwerk/cache2/CacheIndex.h
        print(f"version={version}, timestamp={datetime.fromtimestamp(timestamp)}, is_dirty={bool(is_dirty)}, kb_written={kb_written}")


if __name__ == "__main__":
    main()