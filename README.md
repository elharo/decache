# decache
Python 3 library to extract files from browser caches.
This is in the very earliest stages of experimentation. 

ATM the cache lives somewhere like this:

$ ls /Users/elharo/Library/Caches/Firefox/Profiles/gtnrin5y.default-1427795996109/cache2
doomed	entries	index


Here gtnrin5y.default-1427795996109 is the profile name. This will vary from install to install and their can be more than one.

See https://www.forensicfocus.com/articles/firefox-cache-format-and-extraction/ and https://code.google.com/archive/p/firefox-cache-forensics/ for some old info about this. Not clear how it's changed since then.

C++ code for reading/writing the cache in Firefox is part of
[necko](https://wiki.mozilla.org/Networking). The source code 
appears to be in netwerk/cache2/CacheEntry.cpp, netwerk/cache2/CacheEntry.h
and related classes.

This is what Gemini thinks is true about the Firefox cache:

he Firefox web browser cache is a complex system involving multiple components, and the relevant C++ source code is spread across several directories within the Mozilla codebase. Here's a breakdown of the key areas and files involved, along with some explanations:

**Key Components and Locations:**

* **Necko (Network Library):**
    * This is the core networking library of Firefox, and it handles the HTTP protocol, including caching.
    * `netwerk/cache2/`: This directory contains the primary implementation of the modern Firefox cache. It's where the logic for storing and retrieving cached data resides.
    * `netwerk/cache2/CacheStorage.cpp`: This file contains the main cache storage logic, including how entries are managed and evicted.
    * `netwerk/cache2/CacheEntry.cpp`: This file defines the CacheEntry class, which represents a single cached resource.
    * `netwerk/cache2/CacheFileIO.cpp`: This file handles the file I/O operations for reading and writing cached data to disk.
    * `netwerk/cache2/CacheIndex.cpp`: This file manages the index that tracks cached entries.
* **Storage:**
    * Firefox uses a variety of storage mechanisms, including files and databases, to persist cached data.
    * The code interacts with the underlying file system and database APIs to manage the cache files.
* **Disk Cache:**
    * Firefox can store cached data on disk for persistence.
    * The `netwerk/cache2/` directory is the primary location for the disk cache implementation.
* **Memory Cache:**
    * Firefox also uses an in-memory cache for frequently accessed resources.
    * The memory cache is integrated with the disk cache and is managed by the Necko library.

**Key Concepts and Operations:**

* **Cache Entries:**
    * Each cached resource is represented by a cache entry, which contains the resource data, metadata (e.g., headers, timestamps), and other information.
* **Cache Index:**
    * The cache index is a data structure that maps URLs to cache entries, allowing Firefox to quickly find cached resources.
* **Cache Storage:**
    * The cache storage component manages the storage and retrieval of cache entries.
* **Cache Eviction:**
    * Firefox uses cache eviction policies to remove old or unused cache entries when the cache reaches its capacity.
* **File I/O:**
    * The file I/O component handles the reading and writing of cached data to disk.

**How to Explore the Code:**

1.  **Mozilla Source Code:**
    * The Mozilla source code is available on the Mozilla Developer Network (MDN) and on GitHub.
    * You can use a code search tool like Searchfox (searchfox.org) to explore the codebase.
2.  **Debugging:**
    * You can build Firefox from source and use a debugger to step through the cache code and understand how it works.

**Important Notes:**

* The Firefox cache is a complex and evolving system.
* The code is subject to change as Firefox is updated.
* The Cache2 system is the current implementation of the disk cache. Older versions of firefox used Cache.
* Understanding the inner workings of the Firefox cache requires a good understanding of C++, networking, and file system concepts.

By exploring the `netwerk/cache2/` directory and related files, you can gain a deeper understanding of how Firefox manages its web browser cache.