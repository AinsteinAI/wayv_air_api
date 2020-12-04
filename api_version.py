'''
api_version.py

Copyright 2020, Ainstein AI. All rights reserved.

This version number is specific to the code that is stored in the wayv_air_api
repo, and NOT in the wayv_air. This version number should increment for any PR
that changes code in the wayv_air_api repo.
'''
VERSION_MAJOR = '1'  # increment this when non-backwards-compatible changes are made
VERSION_MINOR = '0'  # increment this when backwards-compatible changes are made
VERSION_BF = '0'     # increment this when bugs are fixed

class api_version():
    def __init__(self):
        self.version = (VERSION_MAJOR + '.'
                        + VERSION_MINOR + '.'
                        + VERSION_BF)
