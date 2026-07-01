#!/usr/local/autopkg/python
"""Unit tests for poll_pkg_hash — exercises hash/size verification logic without a live server.

Run with:
    /usr/local/autopkg/python _tests/test_poll_pkg_hash.py
"""

import sys
from time import sleep as _real_sleep


LOCAL_SHA3 = "aabbcc" * 10   # fake but consistent local hash
OLD_HASH = "112233" * 10     # hash the server held before upload
MISMATCHED_HASH = "deadbeef" * 6  # a different hash that doesn't match local


def _noop_sleep(_):
    pass


def make_obj(responses):
    """Return a minimal object with poll_pkg_hash wired up, whose
    get_pkg_server_sha3_and_size cycles through the provided (sha3512, size) tuples."""

    class _Obj:
        def __init__(self, responses):
            self._iter = iter(responses)
            self._messages = []

        def get_pkg_server_sha3_and_size(self, api_url, pkg_id, token, tenant_id=""):
            return next(self._iter)

        def output(self, msg, verbose_level=1):
            self._messages.append(msg)

        def poll_pkg_hash(
            self,
            api_url,
            pkg_id,
            pkg_name,
            local_sha3,
            previous_hash,
            token,
            poll_interval=15,
            poll_timeout=300,
            tenant_id="",
        ):
            elapsed = 0
            while elapsed < poll_timeout:
                sha3512, size = self.get_pkg_server_sha3_and_size(
                    api_url, pkg_id, token, tenant_id
                )
                if sha3512 and sha3512 != previous_hash:
                    try:
                        size_is_zero = int(size) == 0
                    except (ValueError, TypeError):
                        size_is_zero = False
                    if size_is_zero:
                        self.output(
                            f"WARNING: Package '{pkg_name}' — server reported size=0, "
                            "indicating a failed upload",
                            verbose_level=1,
                        )
                        return False
                    if sha3512 == local_sha3:
                        self.output(
                            f"Package '{pkg_name}' hash verified (SHA3-512 match)",
                            verbose_level=1,
                        )
                        return True
                    else:
                        self.output(
                            f"WARNING: Package '{pkg_name}' hash mismatch — "
                            f"server={sha3512}, local={local_sha3}",
                            verbose_level=1,
                        )
                        return False
                self.output(
                    f"Waiting for server to compute hash for '{pkg_name}' "
                    f"(elapsed {elapsed}s / {poll_timeout}s) …",
                    verbose_level=2,
                )
                elapsed += poll_interval

            self.output(
                f"WARNING: Timed out waiting for server hash for '{pkg_name}' "
                f"after {poll_timeout}s",
                verbose_level=1,
            )
            return False

    return _Obj(responses)


def run(label, obj, expected):
    result = obj.poll_pkg_hash(
        api_url="https://example.jamfcloud.com",
        pkg_id="1",
        pkg_name="Test.pkg",
        local_sha3=LOCAL_SHA3,
        previous_hash=OLD_HASH,
        token="fake-token",
        poll_interval=1,
        poll_timeout=5,
    )
    status = "PASS" if result == expected else "FAIL"
    print(f"[{status}] {label}")
    if result != expected:
        print(f"       expected={expected}, got={result}")
        for m in obj._messages:
            print(f"       > {m}")
    return result == expected


passed = 0
total = 0

# --- Test 1: hash matches local, size is an integer > 0 → success
total += 1
passed += run("Hash matches, size=12345 (int) → True", make_obj([(LOCAL_SHA3, 12345)]), True)

# --- Test 2: hash matches local, size is empty string (common in practice) → success
total += 1
passed += run("Hash matches, size='' (empty string) → True", make_obj([(LOCAL_SHA3, "")]), True)

# --- Test 3: size == 0 as integer → failure (upload error)
total += 1
passed += run("Hash matches, size=0 (int) → False", make_obj([(LOCAL_SHA3, 0)]), False)

# --- Test 4: size == "0" as string → failure (upload error)
total += 1
passed += run("Hash matches, size='0' (string) → False", make_obj([(LOCAL_SHA3, "0")]), False)

# --- Test 5: hash mismatch (corruption) → failure
total += 1
passed += run("Hash mismatch, size=12345 → False", make_obj([(MISMATCHED_HASH, 12345)]), False)

# --- Test 6: hash mismatch with empty size → failure
total += 1
passed += run("Hash mismatch, size='' → False", make_obj([(MISMATCHED_HASH, "")]), False)

# --- Test 7: server returns old hash first, then correct hash → success (two polls)
total += 1
passed += run(
    "Old hash first, then match → True (polls twice)",
    make_obj([(OLD_HASH, ""), (LOCAL_SHA3, "")]),
    True,
)

# --- Test 8: server returns empty hash first, then correct hash → success
total += 1
passed += run(
    "Empty hash first, then match → True (polls twice)",
    make_obj([("", ""), (LOCAL_SHA3, 9999)]),
    True,
)

# --- Test 9: timeout — server never returns a new hash
# poll_timeout=5, poll_interval=1 → 5 iterations before exit; supply 10 stale responses
total += 1
passed += run(
    "Timeout — hash never computed → False",
    make_obj([("", "")] * 10),
    False,
)

print(f"\n{passed}/{total} tests passed")
sys.exit(0 if passed == total else 1)
