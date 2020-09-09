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
        regex = subprocess.check_output(cmd).decode("ascii")
        # TODO complex version strings might output two lines
        # so we will have to account for this and have a second output variable
        self.output("Regex for version string {}:".format(self.version))
        self.output(regex)
        self.env["version_regex"] = regex


if __name__ == "__main__":
    PROCESSOR = VersionRegexGenerator()
    PROCESSOR.execute_shell()
