#!/usr/local/autopkg/python
"""Unit tests for poll_pkg_hash — exercises the real hash verification logic without a live server.

Run with:
    /usr/local/autopkg/python _tests/test_poll_pkg_hash.py
"""

import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "JamfUploaderProcessors", "JamfUploaderLib"
    ),
)

import JamfPackageUploaderBase as base  # pylint: disable=import-error, wrong-import-position

# no real sleeping in tests
base.sleep = lambda _: None

PBase = base.JamfPackageUploaderBase

LOCAL = {"sha3512": "aabbcc" * 10, "sha256": "ddeeff" * 10, "md5": "0a1b2c" * 5}
OLD = {"sha3512": "112233" * 10, "sha256": "445566" * 10, "md5": "778899" * 5}
BAD = "deadbeef" * 6


class _Obj:
    """Stub exposing the real poll_pkg_hash with canned package records."""

    HASH_PREFERENCE = PBase.HASH_PREFERENCE
    EMPTY_FILE_HASHES = PBase.EMPTY_FILE_HASHES

    def __init__(self, records):
        self._records = list(records)
        self._messages = []

    def get_pkg_server_record(self, api_url, pkg_id, token, platform_level_id=""):
        return self._records.pop(0) if len(self._records) > 1 else self._records[0]

    def get_pkg_server_hashes(self, record):
        return PBase.get_pkg_server_hashes(self, record)

    def output(self, msg, verbose_level=1):
        self._messages.append(msg)

    poll_pkg_hash = PBase.poll_pkg_hash


def run(label, records, expected, previous=None):
    obj = _Obj(records)
    result = obj.poll_pkg_hash(
        api_url="https://example.jamfcloud.com",
        pkg_id="1",
        pkg_name="Test.pkg",
        local_hashes=LOCAL,
        previous_hashes=previous if previous is not None else {},
        token="fake-token",
        poll_interval=1,
        poll_timeout=5,
    )
    ok = result == expected
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    if not ok:
        print(f"       expected={expected}, got={result}")
        for m in obj._messages:
            print(f"       > {m}")
    return ok


tests = [
    ("JCDS: sha3512 matches, size int", [{"sha3512": LOCAL["sha3512"], "size": 12345}], True, None),
    ("JCDS: sha3512 matches, size ''", [{"sha3512": LOCAL["sha3512"], "size": ""}], True, None),
    ("size=0 ignored when hash matches (AWS reports no size)", [{"md5": LOCAL["md5"], "size": 0}], True, None),
    (
        "md5 of empty file is waited out, then match → True",
        [{"md5": PBase.EMPTY_FILE_HASHES["md5"], "size": 0}, {"md5": LOCAL["md5"]}],
        True,
        None,
    ),
    ("only ever empty-file hash → timeout False", [{"md5": PBase.EMPTY_FILE_HASHES["md5"]}], False, None),
    ("sha3512 mismatch → False", [{"sha3512": BAD, "size": 1}], False, None),
    (
        "old sha3512 first, then match → True",
        [{"sha3512": OLD["sha3512"]}, {"sha3512": LOCAL["sha3512"]}],
        True,
        OLD,
    ),
    ("empty first, then match → True", [{}, {"sha3512": LOCAL["sha3512"], "size": 9}], True, None),
    ("timeout, nothing computed → False", [{}], False, None),
    # AWS S3: md5 only
    ("S3: md5 only matches → True", [{"md5": LOCAL["md5"], "cloudTransferStatus": "READY"}], True, None),
    ("S3: md5 mismatch (non-zero, non-previous) → False", [{"md5": BAD, "cloudTransferStatus": "READY"}], False, OLD),
    (
        "S3: previous md5 waited out, then match → True",
        [{"md5": OLD["md5"]}, {"md5": LOCAL["md5"]}],
        True,
        OLD,
    ),
    (
        "PENDING then READY → True",
        [{"md5": "", "cloudTransferStatus": "PENDING"}, {"md5": LOCAL["md5"], "cloudTransferStatus": "READY"}],
        True,
        None,
    ),
    ("transfer ERROR → False", [{"cloudTransferStatus": "ERROR"}], False, None),
    # preference order
    ("sha256 alone matches → True", [{"sha256": LOCAL["sha256"], "md5": ""}], True, None),
    ("sha3512 wins over wrong md5 → True", [{"sha3512": LOCAL["sha3512"], "md5": BAD}], True, None),
    ("wrong sha3512 fails despite matching md5 → False", [{"sha3512": BAD, "md5": LOCAL["md5"]}], False, None),
    ("hashValue ignored", [{"hashType": "SHA3_512", "hashValue": "junk", "md5": LOCAL["md5"]}], True, None),
]

passed = sum(run(*t) for t in tests)
print(f"\n{passed}/{len(tests)} tests passed")
sys.exit(0 if passed == len(tests) else 1)
