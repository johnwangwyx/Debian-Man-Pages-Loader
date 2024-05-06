# Debian-Man-Pages-Loader
A Python tool to automate the downloading, extracting, and processing of Debian man pages from all `.deb` packages with multithreading.

Takes around 90 minutes on my machine (i5-12400f CPU) with 32 concurrent jobs to unpack and extract man pages from all ~65000 packages on Debian 12.5.
