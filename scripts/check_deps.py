#!/usr/bin/env python3
#
# Copyright (c) 2025 Project CHIP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Check for dependency conflicts and security issues."""
import subprocess
import sys


def run_safety_check():
    """Run safety check for known security vulnerabilities."""
    try:
        result = subprocess.run(["safety", "check", "--json"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print("⚠️  Security vulnerabilities found:")
            print(result.stdout)
            return False
        else:
            print("✅ No known security vulnerabilities found")
            return True
    except FileNotFoundError:
        print("💡 Install 'safety' to check for security vulnerabilities: pip install safety")
        return True


def check_dependency_conflicts():
    """Check for dependency conflicts."""
    try:
        result = subprocess.run(["pip", "check"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print("⚠️  Dependency conflicts found:")
            print(result.stdout)
            return False
        else:
            print("✅ No dependency conflicts found")
            return True
    except FileNotFoundError:
        print("❌ pip not found")
        return False


def main():
    """Main function."""
    print("🔍 Checking dependencies...")

    safety_ok = run_safety_check()
    conflicts_ok = check_dependency_conflicts()

    if safety_ok and conflicts_ok:
        print("\n✅ All dependency checks passed!")
        sys.exit(0)
    else:
        print("\n❌ Some dependency checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
