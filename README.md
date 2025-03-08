# decache
Python 3 library to extract files from browser caches.
This is in the very earliest stages of experimentation. 

ATM the cache lives somewhere like this:

$ ls /Users/elharo/Library/Caches/Firefox/Profiles/gtnrin5y.default-1427795996109/cache2
doomed	entries	index


Here gtnrin5y.default-1427795996109 is the profile name. This will vary from install to install and their can be more than one.

See https://www.forensicfocus.com/articles/firefox-cache-format-and-extraction/ and https://code.google.com/archive/p/firefox-cache-forensics/ for some old info about this. Not clear how it's changed since then.

Where is the C++ code for reading/writing the cache in Firefox located?