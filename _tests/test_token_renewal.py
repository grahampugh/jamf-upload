#!/usr/local/autopkg/python
"""Unit tests for bearer token renewal in JamfUploaderBase.curl() — no live server needed.

curl() renews a token the server rejects (401) and retries the request. These tests check
that the replacement is remembered, so a caller still holding the old token does not trigger
a new authentication on every request, and that a replacement which is rejected too is not
kept.

Run with:
    /usr/local/autopkg/python _tests/test_token_renewal.py
"""

import os
import sys
import tempfile

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "JamfUploaderProcessors", "JamfUploaderLib"
    ),
)

import JamfUploaderBase as base  # pylint: disable=import-error, wrong-import-position

JamfUploaderBase = base.JamfUploaderBase
URL = "https://example.jamfcloud.com/api/v1/packages/1"


class _Obj(JamfUploaderBase):
    """The real curl() with the network and authentication replaced by fakes"""

    def __init__(self, tmp_dir, valid_tokens, new_tokens):
        # deliberately not calling Processor.__init__
        self.env = {"jamfupload_tmp_dir": tmp_dir, "JSS_URL": "https://example.jamfcloud.com"}
        self.valid_tokens = set(valid_tokens)
        self.new_tokens = list(new_tokens)
        self.tokens_sent = []
        self.auth_calls = 0

    def output(self, msg, verbose_level=1):
        pass

    def handle_api_auth(self, *args, **kwargs):  # pylint: disable=unused-argument
        self.auth_calls += 1
        return self.new_tokens.pop(0)

    def fake_curl(self, curl_cmd):
        """Stand in for subprocess.check_output: answer 200 or 401 by the bearer token"""
        headers_file = curl_cmd[curl_cmd.index("--dump-header") + 1]
        auth = next(a for a in curl_cmd if str(a).startswith("authorization: Bearer "))
        token = auth.split("Bearer ", 1)[1]
        self.tokens_sent.append(token)
        status = 200 if token in self.valid_tokens else 401
        with open(headers_file, "w", encoding="utf-8") as file:
            file.write(f"HTTP/2 {status}\n")


def run_requests(valid, new, requests):
    """Make each request with the token given, returning (statuses, obj)"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        obj = _Obj(tmp_dir, valid, new)
        base.subprocess.check_output = obj.fake_curl
        statuses = [
            obj.curl(api_type="jpapi", request="GET", url=URL, token=token).status_code
            for token in requests
        ]
    return statuses, obj


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}")
    if not condition and detail:
        print(f"       {detail}")
    return condition


def reset():
    JamfUploaderBase._renewed_tokens.clear()  # pylint: disable=protected-access


results = []

# a rejected token is renewed once, then later requests with the old token use the new one
reset()
statuses, obj = run_requests(valid={"b"}, new=["b"], requests=["a", "a", "a"])
results.append(
    check(
        "stale token renewed once, then substituted on later requests",
        statuses == [200, 200, 200]
        and obj.auth_calls == 1
        and obj.tokens_sent == ["a", "b", "b", "b"],
        f"statuses={statuses} auth_calls={obj.auth_calls} sent={obj.tokens_sent}",
    )
)

# renewals chain: a is replaced by b, b is later rejected and replaced by c
reset()
statuses, obj = run_requests(valid={"b"}, new=["b"], requests=["a"])
obj.valid_tokens = {"c"}
obj.new_tokens = ["c"]
base.subprocess.check_output = obj.fake_curl
with tempfile.TemporaryDirectory() as tmp:
    obj.env["jamfupload_tmp_dir"] = tmp
    status = obj.curl(api_type="jpapi", request="GET", url=URL, token="a").status_code
results.append(
    check(
        "chained renewal a→b→c resolves to the latest token",
        status == 200 and obj.current_token("a") == "c",
        f"status={status} current={obj.current_token('a')}",
    )
)

# a replacement that is also rejected is not kept
reset()
statuses, obj = run_requests(valid=set(), new=["b"], requests=["a"])
results.append(
    check(
        "replacement rejected too → mapping removed",
        statuses == [401] and obj.current_token("a") == "a",
        f"statuses={statuses} current={obj.current_token('a')}",
    )
)

# a valid token is untouched and never re-authenticates
reset()
statuses, obj = run_requests(valid={"a"}, new=[], requests=["a", "a"])
results.append(
    check(
        "valid token is sent as is, no authentication",
        statuses == [200, 200] and obj.auth_calls == 0 and obj.tokens_sent == ["a", "a"],
        f"statuses={statuses} auth_calls={obj.auth_calls}",
    )
)

# a replacement cycle must not loop forever
reset()
JamfUploaderBase._renewed_tokens.update({"a": "b", "b": "a"})  # pylint: disable=protected-access
results.append(
    check(
        "cycle in the replacement map terminates",
        _Obj("", [], []).current_token("a") in ("a", "b"),
    )
)
reset()

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
