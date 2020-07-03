# jamf-upload Change Log

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](http://semver.org/).

## Known issues in latest version

`jamf_upload.py` uses an undocumented API for uploading packages to Jamf Cloud. As far as I know, this is the same API used by the Jamf Admin app. It is also the same method used by JSSImporter.

The HTTP responses from this API are unpredictable. You may see a `504` response, which indicates a Gateway Timeout error, but the package may well be delivered anyway. This is true whether uploading a new package or overwriting an existing one.

As the HTTP response cannot be guaranteed, I have not yet added the ability to write any package metadata such as category, manifest etc., which, as far as I can tell, must be supplied by a different API call after the package object has been uploaded. There is no predictable way to check that the package was successfully loaded unless we can guarantee that we are making our HTTP request to the same cluster node to which the package was uploaded.

I intend to add such functionality if changes are made to the Jamf Pro API so that these guarantees can be made.

## [Unreleased] - TBD

Any untagged tests will be announced here.

## [0.2] - 2020-07.03

- Bundle-style packages are now handled properly, by zipping them before performing the upload to Jamf. If a zip file of the correct name is already present in the same folder as the package, it will not be recreated. Delete it if you need it to be remade.

This is developing into a testing script to accompany the AutoPkg processor `JamfCloudPackageUpload`, so some debug modes are now available

- You can now use the `--curl` option to switch to using the system `curl` rather than the Python `requests` module, in case this improves reliability, or just to perform tests. My initial tests have not shown any improvement in upload reliability, but YMMV.

- You can set a timeout limit using the `--timeout` flag. This sets the `timeout` option in `requests`, or the `--max-time` option if using `curl`.

- Different output verbosity levels (`-v[v]`) are available.

## 0.1 - 2020-06-26

Initial commit. Formerly a GitHub gist.

[unreleased]: https://github.com/grahampugh/JSSImporter/compare/v0.2...HEAD
[0.2]: https://github.com/grahampugh/JSSImporter/compare/v0.1...v0.2
