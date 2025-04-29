import os
import platform
import glob
import re
import sys
import hashlib

# --- Configuration ---
# Add more image types and extensions if needed
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    # "image/webp": ".webp",
    # "image/svg+xml": ".svg", # SVG is text, handle differently if needed
    # "image/avif": ".avif",
    # "image/bmp": ".bmp",
}
# Maximum size of metadata file to read (safety measure)
MAX_METADATA_SIZE = 1 * 1024 * 1024  # 1 MB

# --- Helper Functions ---

def find_firefox_cache_dirs():
    """
    Attempts to find Firefox cache2 directories for the current user.
    Returns a list of potential cache directory paths.
    """
    system = platform.system()
    cache_dirs = []
    potential_paths = []

    if system == "Windows":
        # AppData\Local is more common for caches
        app_data_local = os.environ.get("LOCALAPPDATA")
        # AppData\Roaming might also be used sometimes, less common for cache2
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
        # Find profile directories (e.g., xxxxxxxx.default-release)
        try:
            profile_dirs = glob.glob(os.path.join(path, "*.*")) # Heuristic for profile names
            for profile_dir in profile_dirs:
                if os.path.isdir(profile_dir):
                    # Look for cache2 specifically
                    cache2_dir = os.path.join(profile_dir, "cache2", "entries")
                    if os.path.isdir(cache2_dir):
                        cache_dirs.append(cache2_dir)
                    # Sometimes it might be just 'cache' for older versions? Less likely for cache2.
                    # cache_dir_old = os.path.join(profile_dir, "cache", "entries") # Unlikely needed
                    # if os.path.isdir(cache_dir_old):
                    #     cache_dirs.append(cache_dir_old)
        except OSError as e:
            print(f"Warning: Could not access profile directories in {path}: {e}", file=sys.stderr)


    if not cache_dirs:
         # Fallback: Check common flat structure if profiles structure not found/accessible
        if system == "Linux":
            home = os.path.expanduser("~")
            flat_cache_path = os.path.join(home, ".cache", "mozilla", "firefox", "cache2", "entries")
            if os.path.isdir(flat_cache_path):
                 cache_dirs.append(flat_cache_path)


    return list(set(cache_dirs)) # Return unique paths

def read_data_chunks(meta_file_path):
    """
    Finds and reads data associated with a metadata file.
    Handles simple (HASH^...) and chunked (HASH^..._#) data files.
    Returns concatenated data bytes or None if not found/error.
    """
    base_name = os.path.basename(meta_file_path)
    dir_name = os.path.dirname(meta_file_path)
    data_pattern = os.path.join(dir_name, f"{base_name}^*") # Matches HASH^... files

    data_files = glob.glob(data_pattern)
    if not data_files:
        return None

    # Check if it's chunked or simple
    chunked_files = {}
    simple_file = None
    chunk_pattern = re.compile(r"(.+)_(\d+)$") # Pattern to match _CHUNKNUM at the end

    for f in data_files:
        match = chunk_pattern.search(f)
        if match:
            try:
                chunk_num = int(match.group(2))
                chunked_files[chunk_num] = f
            except ValueError:
                # Doesn't end in _<number>, might be the simple data file
                if simple_file is None: # Only expect one simple file
                     simple_file = f
                else:
                     print(f"Warning: Found multiple non-chunked data files for {base_name}: {simple_file}, {f}", file=sys.stderr)
                     # Prefer the shortest name perhaps? Or just skip? Let's skip for now.
                     return None # Ambiguous
        elif simple_file is None:
             simple_file = f
        else:
            # Found another file that isn't chunked - ambiguous
            print(f"Warning: Found multiple non-chunked data files for {base_name}: {simple_file}, {f}", file=sys.stderr)
            return None # Ambiguous


    all_data = bytearray()

    try:
        if chunked_files:
            if simple_file:
                 print(f"Warning: Found both chunked files and a simple file ({simple_file}) for {base_name}. Prioritizing chunks.", file=sys.stderr)

            # Sort chunks by number and read them
            for chunk_num in sorted(chunked_files.keys()):
                chunk_file_path = chunked_files[chunk_num]
                try:
                    with open(chunk_file_path, "rb") as df:
                        all_data.extend(df.read())
                except OSError as e:
                    print(f"Error reading data chunk {chunk_file_path}: {e}", file=sys.stderr)
                    return None # Incomplete data
                except Exception as e:
                    print(f"Unexpected error reading chunk {chunk_file_path}: {e}", file=sys.stderr)
                    return None


        elif simple_file:
            # Read the single data file
            try:
                with open(simple_file, "rb") as df:
                    all_data.extend(df.read())
            except OSError as e:
                print(f"Error reading data file {simple_file}: {e}", file=sys.stderr)
                return None
            except Exception as e:
                    print(f"Unexpected error reading data file {simple_file}: {e}", file=sys.stderr)
                    return None
        else:
            # Should not happen if data_files was populated, but safety check
            print(f"Warning: No data file identified for {base_name}", file=sys.stderr)
            return None

    except Exception as e:
        print(f"Unexpected error processing data files for {base_name}: {e}", file=sys.stderr)
        return None

    return bytes(all_data) # Return immutable bytes


def extract_content_type(metadata_bytes):
    """
    Heuristically searches for 'content-type:' header in metadata bytes.
    Returns the content type string (e.g., 'image/jpeg') or None.
    """
    # Look for variations of 'content-type:' followed by space and the value
    # Need to handle case-insensitivity and potential whitespace variations
    # Headers are typically separated by CRLF (\r\n) but might just be LF (\n)
    # Try finding the header name first, then extract the value until the next line break
    try:
        # Search for b'content-type:' case-insensitively
        # This is tricky with raw bytes. Let's try common patterns.
        patterns = [
            rb'\r\n[Cc][Oo][Nn][Tt][Ee][Nn][Tt]-[Tt][Yy][Pp][Ee]:\s*(.*?)\r\n',
            rb'^[Cc][Oo][Nn][Tt][Ee][Nn][Tt]-[Tt][Yy][Pp][Ee]:\s*(.*?)\r\n', # At beginning of data?
            rb'\n[Cc][Oo][Nn][Tt][Ee][Nn][Tt]-[Tt][Yy][Pp][Ee]:\s*(.*?)\n', # Using LF only
            rb'^[Cc][Oo][Nn][Tt][Ee][Nn][Tt]-[Tt][Yy][Pp][Ee]:\s*(.*?)\n', # Using LF only at start
        ]
        for pattern in patterns:
            match = re.search(pattern, metadata_bytes)
            if match:
                value_bytes = match.group(1).strip()
                try:
                    # Decode assuming ASCII or UTF-8 (common for headers)
                    content_type = value_bytes.decode('ascii').lower()
                    # print(f"Debug: Found Content-Type: {content_type}") # Debug print
                    return content_type
                except UnicodeDecodeError:
                    # print(f"Debug: Found Content-Type bytes, but failed to decode: {value_bytes}") # Debug print
                    continue # Try next pattern or give up

        # Fallback: Simple search if regex fails (less precise about line endings)
        try:
            search_term = b'content-type:'
            index = metadata_bytes.lower().find(search_term)
            if index != -1:
                start_value = index + len(search_term)
                # Find the end of the line (either \r or \n)
                end_r = metadata_bytes.find(b'\r', start_value)
                end_n = metadata_bytes.find(b'\n', start_value)

                if end_r == -1 and end_n == -1:
                    end_line = len(metadata_bytes) # Goes to end of file
                elif end_r == -1:
                    end_line = end_n
                elif end_n == -1:
                    end_line = end_r
                else:
                    end_line = min(end_r, end_n)

                value_bytes = metadata_bytes[start_value:end_line].strip()
                if value_bytes:
                    content_type = value_bytes.decode('ascii').lower()
                    # print(f"Debug: Found Content-Type (fallback): {content_type}") # Debug print
                    return content_type
        except Exception: # Catch potential errors in fallback
             pass # Ignore errors in this less reliable fallback

    except Exception as e:
        print(f"Error during content type search: {e}", file=sys.stderr)

    # print("Debug: Content-Type not found.") # Debug print
    return None

# --- Main Execution ---

def main():
    print("Finding Firefox cache directories...")
    cache_dirs = find_firefox_cache_dirs()

    if not cache_dirs:
        print("Error: No Firefox cache2/entries directories found.", file=sys.stderr)
        print("Make sure Firefox is installed and has been run.", file=sys.stderr)
        print("Searched paths typical for Windows, macOS, and Linux.", file=sys.stderr)
        sys.exit(1)

    print(f"Found cache directories:")
    for d in cache_dirs:
        print(f"- {d}")

    extracted_count = 0
    output_dir = os.getcwd()
    print(f"\nExtracting images to: {output_dir}")

    processed_meta_files = set() # Avoid processing duplicates if cache dirs overlap somehow

    for cache_dir in cache_dirs:
        print(f"\nProcessing cache directory: {cache_dir}")
        try:
            # Iterate through files in the 'entries' directory
            for filename in os.listdir(cache_dir):
                # Metadata files are typically hashes, don't contain '^'
                if '^' in filename:
                    continue

                meta_file_path = os.path.join(cache_dir, filename)

                # Skip if already processed (e.g., from another profile pointing to same cache)
                if meta_file_path in processed_meta_files:
                     continue

                if not os.path.isfile(meta_file_path):
                    continue

                # --- Read Metadata (Heuristically) ---
                try:
                    file_size = os.path.getsize(meta_file_path)
                    if file_size == 0 or file_size > MAX_METADATA_SIZE:
                        # print(f"Skipping empty or large metadata file: {filename} ({file_size} bytes)")
                        continue

                    with open(meta_file_path, "rb") as mf:
                        metadata_bytes = mf.read()

                    # Add to processed list *after* successfully opening
                    processed_meta_files.add(meta_file_path)

                except OSError as e:
                    print(f"Warning: Cannot read metadata file {meta_file_path}: {e}", file=sys.stderr)
                    continue
                except Exception as e:
                     print(f"Warning: Unexpected error reading metadata {meta_file_path}: {e}", file=sys.stderr)
                     continue


                # --- Extract Content-Type ---
                content_type = extract_content_type(metadata_bytes)

                if content_type and content_type in SUPPORTED_IMAGE_TYPES:
                    extension = SUPPORTED_IMAGE_TYPES[content_type]
                    print(f"Found potential image: {filename} (Type: {content_type})")

                    # --- Read Associated Data File(s) ---
                    image_data = read_data_chunks(meta_file_path)

                    if image_data:
                        # --- Save the Image ---
                        # Use the metadata filename + extension as the output name
                        output_filename = f"{filename}{extension}"
                        output_path = os.path.join(output_dir, output_filename)

                        # Prevent overwriting existing files (optional, but safer)
                        counter = 0
                        base_name = filename
                        while os.path.exists(output_path):
                            counter += 1
                            output_filename = f"{base_name}_{counter}{extension}"
                            output_path = os.path.join(output_dir, output_filename)


                        try:
                            with open(output_path, "wb") as outfile:
                                outfile.write(image_data)
                            print(f"  -> Saved as: {output_filename} ({len(image_data)} bytes)")
                            extracted_count += 1
                        except OSError as e:
                            print(f"  Error saving file {output_filename}: {e}", file=sys.stderr)
                        except Exception as e:
                            print(f"  Unexpected error saving file {output_filename}: {e}", file=sys.stderr)

                    else:
                        print(f"  Warning: Could not read data for {filename}", file=sys.stderr)

        except FileNotFoundError:
             print(f"Warning: Cache directory not found during processing: {cache_dir}", file=sys.stderr)
        except PermissionError:
             print(f"Warning: Permission denied for accessing {cache_dir}", file=sys.stderr)
        except OSError as e:
            print(f"Error listing files in {cache_dir}: {e}", file=sys.stderr)
        except Exception as e:
             print(f"Unexpected error processing directory {cache_dir}: {e}", file=sys.stderr)


    print(f"\nExtraction complete. Saved {extracted_count} images to {output_dir}.")

if __name__ == "__main__":
    main()
