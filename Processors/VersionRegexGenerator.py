#!/usr/local/autopkg/python

"""
VersionRegexGenerator processor for generating a regex which matches 
the supplied version string or higher 
    by G Pugh

"""

# import variables go here. Do not import unused modules
import os.path
import subprocess
from pathlib import Path
from autopkglib import Processor, ProcessorError  # pylint: disable=import-error


class VersionRegexGenerator(Processor):
    """A processor for AutoPkg that will generating a regex which matches the supplied version string or higher."""

    input_variables = {
        "version": {
            "required": True,
            "description": "A version string from which to perform the regex generation.",
        },
        "path_to_match_version_number_or_higher_script": {
            "required": False,
            "description": "A version string from which to perform the regex generation.",
            "default": "match-version-number-or-higher.bash",
        },
    }

    output_variables = {
        "version_regex": {
            "description": "Regex which matches or exceeds the inputted version string.",
        },
        "version_regex_1": {
            "description": "Regex which matches or exceeds the inputted version string - second line for complex version numbers.",
        },
        "version_regex_3": {
            "description": "Regex which matches or exceeds the inputted version string - third line for complex version numbers.",
        },
    }

    def get_path_to_file(self, filename):
        """AutoPkg is not very good at finding dependent files. This function will look 
        inside the search directories for any supplied file """
        # if the supplied file is not a path, use the override directory or
        # recipe dir if no override
        recipe_dir = self.env.get("RECIPE_DIR")
        filepath = os.path.join(recipe_dir, filename)
        if os.path.exists(filepath):
            self.output(f"File found at: {filepath}")
            return filepath

        # if not found, search RECIPE_SEARCH_DIRS to look for it
        search_dirs = self.env.get("RECIPE_SEARCH_DIRS")
        for d in search_dirs:
            for path in Path(d).rglob(filename):
                matched_filepath = str(path)
                break
        if matched_filepath:
            self.output(f"File found at: {matched_filepath}")
            return matched_filepath

    def main(self):
        """Do the main thing here"""
        self.version = self.env.get("version")
        if not self.version:
            raise ProcessorError("No version supplied!")

        self.path_to_match_version_number_or_higher_script = self.env.get(
            "path_to_match_version_number_or_higher_script"
        )
        # handle files with no path
        if "/" not in self.path_to_match_version_number_or_higher_script:
            self.path_to_match_version_number_or_higher_script = self.get_path_to_file(
                self.path_to_match_version_number_or_higher_script
            )

        cmd = [
            "/bin/bash",
            self.path_to_match_version_number_or_higher_script,
            "-q",
            "-j",
            self.version,
        ]
        regex_lines = subprocess.check_output(cmd).decode("ascii").splitlines()
        # complex version strings might output two or even three lines
        # so we have to account for this and have a second and third output variable
        self.env["version_regex"] = ""
        self.env["version_regex_2"] = ""
        self.env["version_regex_3"] = ""
        for i in range(0, len(regex_lines)):
            self.output(
                "Regex {} for version string {}: {}".format(
                    i, self.version, regex_lines[i]
                )
            )
            if i == 0:
                self.env["version_regex"] = regex_lines[i]
            if i == 1:
                self.env["version_regex_2"] = regex_lines[i]
            if i == 2:
                self.env["version_regex_3"] = regex_lines[i]


if __name__ == "__main__":
    PROCESSOR = VersionRegexGenerator()
    PROCESSOR.execute_shell()
