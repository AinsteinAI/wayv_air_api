'''
api_version.py

Copyright 2020, Ainstein Inc. All Rights Reserved


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Contact: hi@ainstein.ai

This version number is specific to the code that is stored in the wayv_air_api
repo, and NOT in the wayv_air. This version number should increment for any PR
that changes code in the wayv_air_api repo.
'''
VERSION_MAJOR = '1'  # increment this when non-backwards-compatible changes are made
VERSION_MINOR = '1'  # increment this when backwards-compatible changes are made
VERSION_BF = '0'     # increment this when bugs are fixed

class api_version():
    def __init__(self):
        self.version = (VERSION_MAJOR + '.'
                        + VERSION_MINOR + '.'
                        + VERSION_BF)
