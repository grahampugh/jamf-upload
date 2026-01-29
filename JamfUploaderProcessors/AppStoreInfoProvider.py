#!/usr/local/autopkg/python

"""
Copyright 2026 Graham Pugh, Neil Martin

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

ACKNOWLEDGEMENTS:
This processor was originally developed by Neil Martin
"""

import json
import os
import subprocess
from collections import namedtuple
import re
import tempfile

from time import sleep

from autopkglib import (  # pylint: disable=import-error
    URLGetter,
    ProcessorError,
)

__all__ = ["AppStoreInfoProvider"]


class AppStoreInfoProvider(URLGetter):
    """Provides metadata from the iTunes/App Store Search API."""

    description = __doc__
    input_variables = {
        "app_store_url": {
            "required": False,
            "description": "App Store URL (e.g., https://apps.apple.com/gb/app/name/id284882215)",
        },
        "app_store_id": {
            "required": False,
            "description": "App Store ID (e.g., 284882215)",
        },
        "max_tries": {
            "required": False,
            "description": (
                "Maximum number of attempts to request the info. "
                "Must be an integer between 1 and 10."
            ),
            "default": "5",
        },
    }

    output_variables = {
        "track_name": {"description": "Name of the app"},
        "track_view_url": {"description": "URL to the app in the App Store"},
        "bundle_id": {"description": "Bundle identifier"},
        "version": {"description": "Current version"},
        "minimum_os_version": {"description": "Minimum OS version required"},
        "release_date": {"description": "Release date"},
        "description": {"description": "App description"},
        "seller_name": {"description": "Developer/seller name"},
        "track_id": {"description": "App Store track ID"},
        "artwork_path": {"description": "Full path to downloaded artwork file"},
    }

    def write_temp_file(self, data):
        """dump some text to a temporary file"""
        tf = self.init_temp_file(suffix=".txt")
        with open(tf, "w", encoding="utf-8") as fp:
            fp.write(data)
        return tf

    def make_tmp_dir(self, tmp_dir="/tmp/jamf_upload_"):
        """make the tmp directory"""
        if not self.env.get("jamfupload_tmp_dir"):
            base_dir, prefix_dir = tmp_dir.rsplit("/", 1)
            self.env["jamfupload_tmp_dir"] = tempfile.mkdtemp(
                prefix=prefix_dir, dir=base_dir
            )
        return self.env["jamfupload_tmp_dir"]

    def init_temp_file(
        self, prefix="jamf_upload_", suffix=None, tmp_dir=None, text=True
    ):
        """dump some text to a temporary file"""
        return tempfile.mkstemp(
            prefix=prefix,
            suffix=suffix,
            dir=self.make_tmp_dir() if tmp_dir is None else tmp_dir,
            text=text,
        )[1]

    def curl_request(self, url, accept="application/json", max_tries=5, binary=False):
        """Make a curl request and return the response."""
        tmp_dir = self.make_tmp_dir()
        headers_file = os.path.join(tmp_dir, "curl_headers.txt")
        output_file = self.init_temp_file(prefix="appstore_", suffix=".txt")

        curl_cmd = [
            self.curl_binary(),
            "--silent",
            "--show-error",
            "--no-buffer",
            "--dump-header",
            headers_file,
            "--speed-time",
            "30",
            "--location",
            "--url",
            url,
            "--request",
            "GET",
            "--output",
            output_file,
        ]

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AutoPkg/1.0",
            "Accept": accept,
        }

        self.add_curl_headers(curl_cmd, headers)

        count = 0
        while True:
            count += 1
            self.output(
                f"GET request attempt {count}",
                verbose_level=2,
            )

            proc_stdout, _, status_code = self.execute_curl(curl_cmd)
            self.output(f"Curl command: {curl_cmd}", verbose_level=4)
            header = self.parse_headers(proc_stdout)

            # check HTTP response
            if self.status_check(header) == "break":
                break
            if count >= max_tries:
                self.output(
                    f"Slack webhook send did not succeed after {max_tries} attempts"
                )
                self.output(f"\nHTTP POST Response Code: {status_code}")
                raise ProcessorError("ERROR: Slack webhook failed to send")
            sleep(10)

        Response = namedtuple(
            "Response",
            ["headers", "status_code", "output"],
            defaults=(None, None, None),
        )

        headers_list = None
        status_code = None
        output_data = None

        try:
            with open(headers_file, "r", encoding="utf-8") as file:
                headers = file.readlines()
            headers_list = [x.strip() for x in headers]
            for header in headers_list:
                if re.match(r"HTTP/(1.1|2)", header) and "Continue" not in header:
                    status_code = int(header.split()[1])
        except IOError as e:
            raise ProcessorError(f"Warning: {headers_file} not found") from e

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            if binary:
                with open(output_file, "rb") as file:
                    output_data = file.read()
            else:
                with open(output_file, "r", encoding="utf-8") as file:
                    if accept == "application/json":
                        output_data = json.load(file)
                    else:
                        output_data = file.read()
        else:
            self.output(f"No output from request ({output_file} not found or empty)")

        return Response(
            headers=headers_list, status_code=status_code, output=output_data
        )

    def status_check(self, header):
        """Return a message dependent on the HTTP response"""
        http_result_code = int(header.get("http_result_code"))
        self.output(f"Response: {http_result_code}", verbose_level=2)
        if http_result_code == 200 or http_result_code == 201:
            self.output("Request sent successfully")
            return "break"
        self.output(f"WARNING: Request failed (status code {http_result_code})")
        return None

    def download_artwork(self, artwork_url, track_id, max_tries):
        """Download artwork and save it as PNG."""
        if not artwork_url:
            return None

        if artwork_url.endswith(".jpg"):
            artwork_url = artwork_url[:-4] + ".png"

        try:
            cache_dir = self.env["RECIPE_CACHE_DIR"]
            filename = f"artwork_{track_id}.png"
            artwork_path = os.path.join(cache_dir, filename)

            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)

            response = self.curl_request(
                artwork_url, accept="image/png", max_tries=max_tries
            )

            if response.status_code == 200:
                with open(artwork_path, "wb") as artwork_file:
                    artwork_file.write(response.output)
                return artwork_path
            else:
                self.output(
                    f"Warning: Artwork download failed with status {response.status_code}"
                )
                return None

        except (OSError, ProcessorError, KeyError) as e:
            self.output(f"Warning: Failed to download artwork: {e}")
            return None

    def parse_app_store_url(self, url):
        """Extract the app ID and country code from an App Store URL."""
        try:
            parts = url.split("/")
            if "apps.apple.com" not in url:
                raise ProcessorError("URL must be from apps.apple.com")

            country_code = None
            app_id = None
            for i, part in enumerate(parts):
                if part == "apps.apple.com" and i + 1 < len(parts):
                    country_code = parts[i + 1]
                if part.startswith("id"):
                    app_id = part[2:]

            if not country_code or len(country_code) != 2:
                raise ProcessorError("Invalid country code in URL")
            if not app_id:
                raise ProcessorError("Invalid app ID format in URL")

            return app_id, country_code

        except (ValueError, IndexError, AttributeError) as e:
            raise ProcessorError(f"Error parsing App Store URL: {e}") from e

    def main(self):
        """Main process"""

        app_store_url = self.env.get("app_store_url")
        app_store_id = self.env.get("app_store_id")

        if not app_store_url and not app_store_id:
            raise ProcessorError("Either app_store_url or app_store_id is required")
        if app_store_url and app_store_id:
            raise ProcessorError(
                "Specify either app_store_url or app_store_id, not both"
            )

        if app_store_url:
            app_id, country = self.parse_app_store_url(app_store_url)
        else:
            app_id = app_store_id
            country = "gb"

        lookup_url = (
            f"https://itunes.apple.com/lookup?"
            f"id={app_id}&country={country}&entity=software"
        )

        # set max tries
        max_tries = self.env.get("max_tries")

        # verify that max_tries is an integer greater than zero and less than 10
        try:
            max_tries = int(max_tries)
            if max_tries < 1 or max_tries > 10:
                raise ValueError
        except (ValueError, TypeError):
            max_tries = 5

        try:
            response = self.curl_request(lookup_url, max_tries)

            if response.status_code != 200:
                raise ProcessorError(
                    f"API request failed with status {response.status_code}"
                )

            content = response.output
            if not content.get("results"):
                raise ProcessorError("No results found for the specified app")

            result = content["results"][0]

            self.env["track_name"] = result.get("trackName", "")
            self.env["track_view_url"] = result.get("trackViewUrl", "")
            self.env["bundle_id"] = result.get("bundleId", "")
            self.env["version"] = result.get("version", "")
            self.env["minimum_os_version"] = result.get("minimumOsVersion", "")
            self.env["release_date"] = result.get("releaseDate", "")
            self.env["description"] = result.get("description", "")
            self.env["seller_name"] = result.get("sellerName", "")
            self.env["track_id"] = result.get("trackId", "")

            artwork_url = result.get("artworkUrl512")
            if artwork_url:
                artwork_path = self.download_artwork(
                    artwork_url, self.env["track_id"], max_tries
                )
                if artwork_path:
                    self.env["artwork_path"] = artwork_path
                else:
                    self.env["artwork_path"] = ""
            else:
                self.env["artwork_path"] = ""

        except (KeyError, ValueError, TypeError) as e:
            raise ProcessorError(f"Error processing app information: {e}") from e


if __name__ == "__main__":
    PROCESSOR = AppStoreInfoProvider()
    PROCESSOR.execute_shell()
