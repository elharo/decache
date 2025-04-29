import os
import platform
import glob
import sys
import struct # For unpacking binary data

# --- Helper Functions ---

def find_firefox_cache_dirs():
    """
    Attempts to find Firefox cache2 directories for the current user.
    Returns a list of potential cache directory paths.
    (Same function as before)
    """
    system = platform.system()
    cache_dirs = []
    potential_paths = []

    if system == "Windows":
        app_data_local = os.environ.get("LOCALAPPDATA")
        app_data_roaming = os.environ.get("APPDATA")
        if app_data_local:
            potential_paths.append(os.path.join(app_data_local, "Mozilla", "Firefox", "Profiles"))
        if app_data_roaming:
            potential_paths.append(os.path.join(app_data_roaming, "Mozilla", "Firefox", "Profiles"))
    elif system == "Darwin": # macOS
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
            profile_dirs = glob.glob(os.path.join(path, "*.*")) # Heuristic for profile names
            for profile_dir in profile_dirs:
                if os.path.isdir(profile_dir):
                    cache2_dir = os.path.join(profile_dir, "cache2", "entries")
                    if os.path.isdir(cache2_dir):
                        cache_dirs.append(cache2_dir)
        except OSError as e:
            print(f"Warning: Could not access profile directories in {path}: {e}", file=sys.stderr)

    # Fallback for Linux flat structure
    if not cache_dirs and system == "Linux":
         home = os.path.expanduser("~")
         flat_cache_path = os.path.join(home, ".cache", "mozilla", "firefox", "cache2", "entries")
         if os.path.isdir(flat_cache_path):
              cache_dirs.append(flat_cache_path)

    return list(set(cache_dirs))

def extract_url_from_metadata(meta_file_path):
    """
    Attempts to read the URL (cache key) from the start of a metadata file.
    Returns the URL string or None if parsing fails.
    """
    try:
        with open(meta_file_path, "rb") as f:
            # Based on mozilla-central/netwerk/cache2/CacheEntry.h and CacheEntryIO.cpp
            # The structure near the start often looks like:
            # uint32_t mVersion;
            # uint32_t mFetchCount;
            # uint64_t mLastFetched; // time_t usually 64-bit
            # uint64_t mLastModified;
            # uint64_t mExpirationTime;
            # uint64_t mDataSize;
            # uint32_t mKeySize;   // <<< Length of the URL (key)
            # char mKey[mKeySize]; // <<< The URL itself

            # Assuming little-endian, common on x86/amd64
            # Format: < (little-endian)
            #         I (uint32_t)
            #         I (uint32_t)
            #         Q (uint64_t)
            #         Q (uint64_t)
            #         Q (uint64_t)
            #         Q (uint64_t)
            #         I (uint32_t) -> mKeySize
            header_format = "<IIQQQQI"
            header_size = struct.calcsize(header_format)

            header_bytes = f.read(header_size)
            if len(header_bytes) < header_size:
                # print(f"Debug: File {os.path.basename(meta_file_path)} too small for header ({len(header_bytes)} bytes)")
                return None # File too small

            # Unpack the header fields up to key_size
            unpacked_header = struct.unpack(header_format, header_bytes)
            key_size = unpacked_header[-1] # The last 'I' is the key size

            # Sanity check the key size
            # Limit key size to prevent reading huge amounts of data if parsing is wrong
            MAX_REASONABLE_URL_LENGTH = 10 * 1024 # 10 KB seems very generous for a URL
            if key_size <= 0 or key_size > MAX_REASONABLE_URL_LENGTH:
                 # print(f"Debug: Unreasonable key size {key_size} for {os.path.basename(meta_file_path)}")
                 return None

            # Read the key (URL) itself
            key_bytes = f.read(key_size)
            if len(key_bytes) < key_size:
                # print(f"Debug: Could not read expected key size {key_size} (got {len(key_bytes)}) for {os.path.basename(meta_file_path)}")
                return None # Couldn't read the full key

            # Decode the key (URL), assuming UTF-8
            try:
                url = key_bytes.decode('utf-8')
                return url
            except UnicodeDecodeError:
                # print(f"Debug: Failed to decode key as UTF-8 for {os.path.basename(meta_file_path)}")
                # Try latin-1 as a fallback? Might reveal some patterns but less likely correct.
                try:
                    url = key_bytes.decode('latin-1', errors='ignore')
                    return f"[DECODE ERROR] {url}" # Mark as potentially incorrect
                except:
                    return "[DECODE ERROR - UNREADABLE]"


    except struct.error as e:
        # print(f"Debug: Struct unpacking error for {os.path.basename(meta_file_path)}: {e}")
        return None # File structure doesn't match expected header
    except OSError as e:
        print(f"Warning: Cannot read metadata file {meta_file_path}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        # Catch unexpected errors during processing
        print(f"Warning: Unexpected error processing {meta_file_path}: {e}", file=sys.stderr)
        return None


# --- Main Execution ---

def main():
    print("Finding Firefox cache directories...")
    cache_dirs = find_firefox_cache_dirs()

    if not cache_dirs:
        print("Error: No Firefox cache2/entries directories found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found cache directories:")
    for d in cache_dirs:
        print(f"- {d}")

    url_count = 0
    processed_meta_files = set()

    print("\nScanning metadata files for URLs...")

    for cache_dir in cache_dirs:
        print(f"\nProcessing cache directory: {cache_dir}")
        try:
            # Iterate through files in the 'entries' directory
            for filename in os.listdir(cache_dir):
                # Metadata files don't contain '^'
                if '^' in filename:
                    continue

                meta_file_path = os.path.join(cache_dir, filename)

                if meta_file_path in processed_meta_files:
                    continue
                if not os.path.isfile(meta_file_path):
                    continue

                url = extract_url_from_metadata(meta_file_path)
                processed_meta_files.add(meta_file_path) # Mark as processed even if URL extraction fails

                if url:
                    # Avoid printing excessively long garbage if decoding failed badly
                    if len(url) > 2048:
                         url_display = url[:2048] + "..."
                    else:
                         url_display = url

                    # Only print if it looks somewhat like a URL (simple check)
                    # or if it was marked as a decode error
                    if url_display.startswith("http") or \
                       url_display.startswith("https") or \
                       url_display.startswith("[DECODE ERROR"):
                        print(f"  {filename}: {url_display}")
                        url_count += 1
                    # else: # Optional: print non-http keys if interested
                    #    print(f"  {filename}: [Non-HTTP Key?] {url_display}")


        except FileNotFoundError:
             print(f"Warning: Cache directory not found during processing: {cache_dir}", file=sys.stderr)
        except PermissionError:
             print(f"Warning: Permission denied for accessing {cache_dir}", file=sys.stderr)
        except OSError as e:
            print(f"Error listing files in {cache_dir}: {e}", file=sys.stderr)
        except Exception as e:
             print(f"Unexpected error processing directory {cache_dir}: {e}", file=sys.stderr)

    print(f"\nScan complete. Found {url_count} potential URLs.")

if __name__ == "__main__":
    main()
