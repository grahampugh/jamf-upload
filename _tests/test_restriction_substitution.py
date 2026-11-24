#!/usr/local/autopkg/python
"""Unit tests for software restriction template substitution — no live server needed.

JamfSoftwareRestrictionUploader converts match_exact_process_name, kill_process and
delete_executable to booleans before substituting them into the template. These tests check
that the booleans are written as Jamf Pro expects instead of crashing the XML escaping, and
that display_message keeps the text the recipe gave it.
See https://github.com/grahampugh/jamf-upload/issues/405.

Run with:
    /usr/local/autopkg/python _tests/test_restriction_substitution.py
"""

import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "JamfUploaderProcessors", "JamfUploaderLib"
    ),
)

# pylint: disable=import-error, wrong-import-position
import JamfSoftwareRestrictionUploaderBase as restriction

TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "templates", "RestrictionTemplate-allcomputers.xml"
)


class _Uploaded(Exception):
    """Raised in place of the upload once the template has been rendered"""


class _Obj(restriction.JamfSoftwareRestrictionUploaderBase):
    """The real upload_restriction() stopped just before anything is sent to Jamf Pro"""

    def __init__(self, env):
        # deliberately not calling Processor.__init__
        self.env = dict(env)
        self.rendered = None

    def output(self, msg, verbose_level=1):
        pass

    def write_temp_file(self, jamf_url, data):
        self.rendered = data
        raise _Uploaded()


def render(env):
    """Render the template the way execute() would, returning the XML"""
    obj = _Obj(env)
    with open(TEMPLATE_PATH, encoding="utf-8") as file:
        template = file.read()
    try:
        obj.upload_restriction(
            "https://example.jamfcloud.com",
            env["restriction_name"],
            env["process_name"],
            env.get("display_message"),
            obj.to_bool(env.get("match_exact_process_name")),
            obj.to_bool(env.get("restriction_send_notification")),
            obj.to_bool(env.get("kill_process")),
            obj.to_bool(env.get("delete_executable")),
            "",
            template,
            "",
            "token",
            "5",
        )
    except _Uploaded:
        pass
    return obj.rendered


def check(label, condition, detail=""):
    """Print a PASS or FAIL line and return the result"""
    print(f"[{'PASS' if condition else 'FAIL'}] {label}")
    if not condition and detail:
        print(f"       {detail}")
    return condition


BASE_ENV = {
    "restriction_name": "Install macOS Tahoe",
    "process_name": "Install macOS Tahoe.app",
    "display_message": "This application is restricted.",
    # AutoPkg fills in omitted inputs with the processor's declared defaults
    "match_exact_process_name": False,
    "restriction_send_notification": False,
    "kill_process": False,
    "delete_executable": False,
}

results = []

# the case from the issue: true values used to raise AttributeError in escape()
issue_env = dict(
    BASE_ENV,
    match_exact_process_name="true",
    restriction_send_notification="true",
    kill_process="true",
    delete_executable="false",
)
try:
    xml = render(issue_env)
    crash = ""
except AttributeError as e:
    xml, crash = None, str(e)
results.append(check("true values render without crashing", not crash, f"error={crash}"))
if xml:
    for tag, want in [
        ("match_exact_process_name", "true"),
        ("send_notification", "true"),
        ("kill_process", "true"),
        ("delete_executable", "false"),
        ("display_message", "This application is restricted."),
    ]:
        results.append(
            check(
                f"<{tag}> is {want}",
                f"<{tag}>{want}</{tag}>" in xml,
                xml,
            )
        )

# omitted flags take AutoPkg's False default and render as lowercase false
xml = render(dict(BASE_ENV, display_message="Blocked & logged"))
results.append(
    check(
        "omitted flags render as false",
        "<kill_process>false</kill_process>" in xml
        and "<match_exact_process_name>false</match_exact_process_name>" in xml,
        xml,
    )
)
results.append(
    check(
        "display_message text is XML escaped",
        "<display_message>Blocked &amp; logged</display_message>" in xml,
        xml,
    )
)

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
