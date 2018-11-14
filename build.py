#!/usr/bin/env python
#
# Copyright (C) 2018 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Bootstrapper for do_build.py."""
import logging
import os
import site
import subprocess
import sys


THIS_DIR = os.path.realpath(os.path.dirname(__file__))
ANDROID_TOP = os.path.join(THIS_DIR, '../..')


site.addsitedir(os.path.join(ANDROID_TOP, 'ndk'))
import bootstrap  # pylint: disable=import-error,wrong-import-position


def main():
    """Program entry point.

    Bootstraps the do_build.py with Python 3.
    """
    logging.basicConfig(level=logging.INFO)

    bootstrap.bootstrap()
    subprocess.check_call(
        ['python3', os.path.join(THIS_DIR, 'do_build.py')] +
        sys.argv[1:])


if __name__ == '__main__':
    main()
