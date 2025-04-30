# decache
Python 3 library to extract files from browser caches.
This is in the very earliest stages of experimentation. 

At the moment, the cache lives somewhere like this:

$ ls /Users/elharo/Library/Caches/Firefox/Profiles/gtnrin5y.default-1427795996109/cache2
doomed	entries	index

Here gtnrin5y.default-1427795996109 is the profile name. This will vary from install to install, and there can be more than one.

See https://github.com/libyal/dtformats/blob/main/documentation/Firefox%20cache%20file%20format.asciidoc https://www.forensicfocus.com/articles/firefox-cache-format-and-extraction/ and https://code.google.com/archive/p/firefox-cache-forensics/ for some old info about this. Not clear how it's changed since then.

C++ code for reading/writing the cache in Firefox is part of
[necko](https://wiki.mozilla.org/Networking). The source code 
appears to be in mozilla-unified/netwerk/cache2/CacheEntry.cpp, mozilla-unified/netwerk/cache2/CacheEntry.h
and related classes. [The Mozilla wiki describes the cache layout and format](https://wiki.mozilla.org/Necko/Cache) but seems very out of date.
In particular there seems to have been a very big move from cache to cache2 in the last few years that invalidates most of this.
E.g. there's no more _CACHE_MAP_ file. Instead there's an index file. [Bugs for necko caching](https://bugzilla.mozilla.org/buglist.cgi?product=Core&component=Networking%3A%20Cache&resolution=---&list_id=17534843) are in bugzilla.

Claude Code does a better job than Gemini of analyzing the ctual C++ code. According to Claude, which tentatively looks correct:

>   Format of the Index File:
> 
>   1. Header (CacheIndexHeader):
>     - Version (uint32_t)
>     - Timestamp (uint32_t)
>     - Dirty flag (uint32_t)
>     - Amount of data written (uint32_t)
>   2. Records (Series of CacheIndexRecord):
>     - SHA1 hash (20 bytes)
>     - Frecency (uint32_t)
>     - Origin attributes hash (uint64_t)
>     - On-start time (uint16_t)
>     - On-stop time (uint16_t)
>     - Content type (uint8_t)
>     - Flags (uint32_t) - contains file size and status flags
>   3. Hash (uint32_t):
>     - A checksum of the file contents for integrity verification


This is what Gemini thinks is true about the Firefox cache:


> The Firefox web browser cache is a complex system involving multiple components, and the relevant C++ source code is spread across several directories within the Mozilla codebase. Here's a breakdown of the key areas and files involved, along with some explanations:
> 
> **Key Components and Locations:**
> * **Necko (Network Library):**
>     * This is the core networking library of Firefox, and it handles the HTTP protocol, including caching.
>     * `netwerk/cache2/`: This directory contains the primary implementation of the modern Firefox cache. It's where the logic for storing and retrieving cached data resides.
>     * `netwerk/cache2/CacheStorage.cpp`: This file contains the main cache storage logic, including how entries are managed and evicted.
>     * `netwerk/cache2/CacheEntry.cpp`: This file defines the CacheEntry class, which represents a single cached resource.
>     * `netwerk/cache2/CacheFileIO.cpp`: This file handles the file I/O operations for reading and writing cached data to disk.
>     * `netwerk/cache2/CacheIndex.cpp`: This file manages the index that tracks cached entries.
> * **Storage:**
>     * Firefox uses a variety of storage mechanisms, including files and databases, to persist cached data.
>     * The code interacts with the underlying file system and database APIs to manage the cache files.
> * **Disk Cache:**
>     * Firefox can store cached data on disk for persistence.
>     * The `netwerk/cache2/` directory is the primary location for the disk cache implementation.
> * **Memory Cache:**
>     * Firefox also uses an in-memory cache for frequently accessed resources.
>     * The memory cache is integrated with the disk cache and is managed by the Necko library.
> 
> **Key Concepts and Operations:**
> 
> * **Cache Entries:**
>     * Each cached resource is represented by a cache entry, which contains the resource data, metadata (e.g., headers, timestamps), and other information.
> * **Cache Index:**
>     * The cache index is a data structure that maps URLs to cache entries, allowing Firefox to quickly find cached resources.
> * **Cache Storage:**
>     * The cache storage component manages the storage and retrieval of cache entries.
> * **Cache Eviction:**
>     * Firefox uses cache eviction policies to remove old or unused cache entries when the cache reaches its capacity.
> * **File I/O:**
>     * The file I/O component handles the reading and writing of cached data to disk.
> 
> **How to Explore the Code:**
> 
> 1.  **Mozilla Source Code:**
>     * The Mozilla source code is available on the Mozilla Developer Network (MDN) and on GitHub.
>     * You can use a code search tool like Searchfox (searchfox.org) to explore the codebase.
> 2.  **Debugging:**
>     * You can build Firefox from source and use a debugger to step through the cache code and understand how it works.
> 
> **Important Notes:**
> 
> * The Firefox cache is a complex and evolving system.
> * The code is subject to change as Firefox is updated.
> * The Cache2 system is the current implementation of the disk cache. Older versions of firefox used Cache.
> * Understanding the inner workings of the Firefox cache requires a good understanding of C++, networking, and file system concepts.
> 
> By exploring the `netwerk/cache2/` directory and related files, you can gain a deeper understanding of how Firefox manages its web browser cache.


This directory seems to be in the vicinity of 200-300 thousand tokens if I were to upload it into Gemini.


```
~$ find mozilla-unified/netwerk/cache2 -type f \( -name "*.txt" -o -name "*.py" -o -name "*.cc" -o -name "*.java" -o -name "*.h" -o -name "*.md" -o -name "*.json" -o -name "*.cpp" -o -name "*.yaml" -o -name "*.idl" -o -name "*.build" \) -print0 | xargs -0 cat | wc -c
  826728
```

(826728 is a character count that needs to be divided by 4 to estimate the number of input tokens.)

I gave Gemini some more context and used the Gemini 2.0 model and now it tells me:

> Okay, this is a great start. I've reviewed the provided GitHub repository and the Necko Cache Wiki page. Based on this information, here's an analysis of the cache format and how you can extract data using a Python program.
> 
> **Overall Structure and Key Concepts:**
> 
> The Necko Cache is designed for high performance and robustness. Key concepts to understand include:
> 
> *   **Cache Storage Service (CSS):**  The overall cache system in Firefox.  `netwerk/cache2` implements a major part of it.
> *   **Cache Entries:** Each entry represents a cached resource (e.g., HTML page, image, JavaScript file).  A Cache Entry has a unique key derived from the URL and a set of associated data and metadata.
> *   **Groups (or Streams):** A Cache Entry can contain multiple "streams" of data.  Typically, there are streams for:
>     *   **HTTP Headers:** The HTTP response headers from the server.
>     *   **Content Data:** The actual payload of the resource (e.g., the image data, the HTML content).
>     *   **Metadata:** Additional information about the resource, like expiration times, validation tokens, etc.
> *   **Container Files:**  The cache data is physically stored in a set of files called "Container Files" (`*.container`).  These files are large and contain many cache entries, grouped into "blocks."
> *   **Index Files:** Index files (`*.sidx`) provide a map that allows the system to quickly find cache entries within the container files.  The Wiki page mentions a newer index format (`*.idx`) that is intended to replace the older ones.
> *   **Storage Version:** The overall cache structure has a storage version associated with it. This will change over time as the cache format evolves.
> 
> **File Formats and Location:**
> 
> *   **Cache Directory:** The location of the cache on disk varies depending on the operating system and Firefox configuration. You can often find it by looking in the Firefox profile directory. It's usually called something like `cache2` or `netwerk`. Inside the cache directory you'll find the container files and index files.
> *   **Container Files (`*.container`):** These are binary files containing the actual cached data.  The format is complex and described in the source code (mainly `netwerk/cache2/`).
> *   **Index Files (`*.sidx`, `*.idx`):** These are binary files that index the container files.  The source code, especially related to `IndexFile`, `SIndexFile`, and related classes in `netwerk/cache2`, defines the index formats.
> 
> **Understanding the `CacheEntry` Class and Related Code:**
> 
> The `CacheEntry` class and its associated classes (like `StreamIO`, `Group`, etc.) are central to how the cache is managed.  You'll need to carefully examine these classes in the C++ code to understand how data is read from and written to the container files.  Pay particular attention to the functions that:
> 
> *   Read data from streams (e.g., `StreamIO::Read()`).
> *   Write data to streams (e.g., `StreamIO::Write()`).
> *   Handle the different data types and encodings.
> *   Manage the index files.
> 
> **Extracting Data with Python:**
> 
> Given that you're writing a Python program to read the cache, here's a general outline of how you might approach it:
> 
> 1.  **Locate the Cache Directory:**  Determine the path to the Firefox cache directory.
> 2.  **Read the Index Files:**  Parse the index files (`*.sidx` or `*.idx`) to find the locations of cache entries within the container files.  This will likely require reverse-engineering the binary format of the index files.  The Wiki page mentions that the format is based on B-trees, which should give you a starting point. You will want to use the Python `struct` module to unpack the binary data.
> 3.  **Read the Container Files:**  For each cache entry you want to extract, read the corresponding data from the container file. This will involve:
>     *   Opening the container file in binary mode (`'rb'`).
>     *   Seeking to the correct offset within the file (using `file.seek()`).
>     *   Reading the data (using `file.read()`).
> 4.  **Parse the Cache Entry Data:**  Once you have the data for a cache entry, you'll need to parse it to extract the HTTP headers, content data, and metadata.  This is where understanding the internal structure of the `CacheEntry` (as defined in the C++ code) becomes critical.
> 5.  **Write Extracted Data to Files:**  Write the extracted data (headers, content, metadata) to separate files.
> 
> **Python Libraries to Consider:**
> 
> *   **`struct`:**  For unpacking binary data from the container and index files. This is crucial for handling the binary formats.  Use `struct.unpack()` and `struct.pack()` to read and write data in various formats (integers, floats, strings) according to the endianness and size specified in the cache format.
> *   **`os` and `os.path`:** For interacting with the file system (finding files, creating directories, etc.).
> *   **`zlib`:**  If the cache uses compression (which is likely), you'll need to use `zlib` to decompress the data. Look for zlib usage in the C++ source.
> *   **`http.client`:**  For parsing HTTP headers.
> *   **`json`:** If any metadata is stored as JSON, this library can be used to parse it. However, based on the documentation, the older format does not use JSON. Newer formats may do so.
> *   **`lxml` or `xml.etree.ElementTree`:** If any metadata is stored as XML, this library can be used to parse it.
> 
> **Multiple Files/Resources Per Cache Entry:**
> 
> *   **Multiple Streams:** The primary mechanism for multiple resources is the use of multiple streams within a single `CacheEntry`. One stream would be the HTTP headers, and subsequent streams would be the content data for each resource (e.g., the main HTML page and several embedded images). You'll need to parse the entry carefully to identify the boundaries between these streams. The index probably won't tell you where the stream boundaries are; the entry format within the container will.
> *   **Splitting Across Entries (Less Common):**  It's *possible* that a large resource could be split across multiple cache entries, but this is less likely. If it happens, there would likely be a mechanism in the metadata to indicate that a cache entry is a fragment of a larger resource and to link it to the other fragments.  Look for flags or fields in the `CacheEntry` class that might indicate this.  The cache key itself is used as a lookup mechanism, so you'll need to identify what goes into generating a particular key, and how multiple related keys might be generated.
> 
> **Challenges and Caveats:**
> 
> *   **Binary Format Complexity:**  Reverse-engineering binary formats is notoriously difficult. You'll need to be very patient and methodical.
> *   **Documentation Gaps:** The Wiki documentation provides a high-level overview, but it's likely to be incomplete or outdated. You'll need to rely heavily on the C++ source code.
> *   **Storage Version Changes:** The cache format may change between Firefox versions. Your program might need to be updated to handle different storage versions.  The code and documentation should contain a storage version number you can use to determine the format.
> *   **Potential for Corruption:** Cache files can sometimes become corrupted.  Your program should be able to handle errors gracefully.
> *   **Asynchronous Operations:** The C++ code may use asynchronous operations for file I/O, which can complicate the process of understanding the data flow.
> 
> **Starting Points:**
> 
> 1.  **Focus on the `CacheEntry` class:** This is the central point for understanding the cache entry structure.
> 2.  **Trace File I/O:** Follow the code paths for reading and writing data to the container files.
> 3.  **Examine the `IndexFile` and `SIndexFile` classes:** Understand how the index files are structured and how they map cache entries to locations in the container files.
> 4.  **Write Small Test Programs:** Start by writing small Python test programs to read and parse specific parts of the cache format (e.g., the index file header, a single cache entry).
> 
> **Example: Reading the Index File Header (Illustrative):**
> 
> Let's say you've determined that the index file header has the following structure:
> 
> *   Magic number (4 bytes, string): `b'NeCk'`
> *   Version (4 bytes, unsigned integer, little-endian)
> *   Number of entries (4 bytes, unsigned integer, little-endian)
> 
> Here's how you might read the header in Python:
> 
> ```python
> import struct
> 
> def read_index_header(filename):
>     with open(filename, 'rb') as f:
>         magic = f.read(4)
>         version = struct.unpack('<I', f.read(4))[0]  # '<I' means little-endian unsigned int
>         num_entries = struct.unpack('<I', f.read(4))[0]
>     return magic, version, num_entries
> 
> # Example usage:
> index_file = "path/to/your/cache/index/file.sidx"
> magic, version, num_entries = read_index_header(index_file)
> print(f"Magic: {magic}")
> print(f"Version: {version}")
> print(f"Number of entries: {num_entries}")
> ```
> 
> This is a very basic example, but it demonstrates how you can use the `struct` module to unpack binary data. You'll need to adapt this approach to read the more complex structures within the container and index files.
> 
> This is a challenging project, but by carefully analyzing the C++ code and the Wiki documentation, you can build a Python program to extract data from the Firefox cache. Good luck!



