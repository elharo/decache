import os
import platform
import glob
import sys
import struct  # For unpacking binary data
from datetime import datetime
from typing import LiteralString, Optional


# "Plan to throw one away. You will anyway." -- Fred Brooks
# This is the one I plan to throw away.

# TODO use exception instead of return None
# TODO handle multiple profiles
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

    file_size = os.path.getsize(cache_index)
    record_size = 20 + 4 + 8 + 2 + 2 + 1 + 4
    hash_size = 4
    num_header_bytes = 16  # 4 * sizeof(unit32_t)
    num_records = (file_size - num_header_bytes - hash_size) // record_size

    if file_size < num_header_bytes + hash_size:
        # TODO exception
        print(f"Error: File '{cache_index}' is too small. "
              f"File too small {file_size}.")
        sys.exit(1)

    with open(cache_index, "rb") as f:
        # Read the required number of bytes (16) from the beginning of the file
        header_bytes = f.read(num_header_bytes)

        version, timestamp, is_dirty, kb_written = struct.unpack(">IIII", header_bytes)
        # format defined in source/netwerk/cache2/CacheIndex.h
        print(
            f"version={version}, timestamp={datetime.fromtimestamp(timestamp)}, is_dirty={bool(is_dirty)}, kb_written={kb_written}")

        """
          2. Records (Series of CacheIndexRecord):
            - SHA1 hash (20 bytes)
            - Frecency (uint32_t)
            - Origin attributes hash (uint64_t)
            - On-start time (uint16_t)
            - On-stop time (uint16_t)
            - Content type (uint8_t)
            - Flags (uint32_t) - contains file size and status flags
        """

        # Read all records
        records = []
        for i in range(num_records):
            # Read each field of the record
            hash_value = f.read(20)
            frecency = struct.unpack('>I', f.read(4))[0]
            origin_attrs_hash = struct.unpack('>Q', f.read(8))[0]
            on_start_time = struct.unpack('>H', f.read(2))[0]
            on_stop_time = struct.unpack('>H', f.read(2))[0]
            content_type = f.read(1)[0]
            flags = struct.unpack('>I', f.read(4))[0]

            filename = hash_value.hex().upper()
            filepath = os.path.join(cache_directory, "entries", filename)
            print(f"{filename} {content_type} {os.path.isfile(filepath)}")
            records.append({
                'filename': filename,
                'frecency': frecency,
                'origin_attrs_hash': origin_attrs_hash,
                'on_start_time': on_start_time,
                'on_stop_time': on_stop_time,
                'content_type': content_type,
                'flags': flags
            })

        # Read the hash at the end
        file_hash = struct.unpack('>I', f.read(4))[0]

    """
    > How do the records in this file map to/locate the actual cached data?

  The records in the Firefox cache index file serve as a map to locate the
  actual cached data stored separately. Here's how the mapping works:

  Cache Record Structure to Actual Data

  1. Hash-Based Filename System:
    - The most critical field in each record is the mHash (SHA1Sum::Hash),
  which is a 20-byte SHA-1 hash
    - This hash directly corresponds to the filename of the actual cached
  content
    - The cached data is stored in files named with the hexadecimal
  representation of this hash
  2. File Location:
    - The actual cached data files are stored in the cache2/entries/
  directory
    - Example: If a record has a hash value of 1a2b3c4d5e..., the
  corresponding data file would be at cache2/entries/1a2b3c4d5e...
  3. Metadata vs. Content:
    - The index file only contains metadata about the cached items
  (frequency of use, size, content type, etc.)
    - It doesn't contain any of the actual cached content - just
  information to find and manage it

  Process of Retrieving Cached Data

  When Firefox needs to retrieve something from the cache:

  1. It computes the SHA-1 hash of the resource's key (typically its URL)
  2. It looks up this hash in the cache index to check if it exists and to
  get metadata
  3. If found, it retrieves the corresponding file from the entries
  directory
  4. Each entry file contains both metadata and the actual cached content

  Additional Details

  - Entry File Structure: Each entry file in the entries directory has its
  own structure:
    - A metadata section containing HTTP headers and other information
    - The actual cached content (HTML, images, JS, etc.)
  - Optimization: The index provides quick lookup without having to open
  each individual cached file
    - Fields like mFrecency help determine which entries to keep when space
   is needed
    - mFlags contains information about the entry's state and the file size
  - Content Types: The mContentType field helps Firefox categorize and
  manage different types of cached content (JavaScript, images,
  stylesheets, etc.)
  """


if __name__ == "__main__":
    main()
