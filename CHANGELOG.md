# jamf-upload Change Log

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](http://semver.org/).

## Known issues in latest version

`jamf_pkg_upload.py` uses an undocumented API for uploading packages to Jamf Cloud. As far as I know, this is the same API used by the Jamf Admin app. It is also the same method used by JSSImporter.

The HTTP responses from this API are unpredictable. You may see a `504` response, which indicates a Gateway Timeout error, but the package may well be delivered anyway. This is true whether uploading a new package or overwriting an existing one.

As the HTTP response cannot be guaranteed, I have not yet added the ability to write any package metadata such as category, manifest etc., which, as far as I can tell, must be supplied by a different API call after the package object has been uploaded. There is no predictable way to check that the package was successfully loaded unless we can guarantee that we are making our HTTP request to the same cluster node to which the package was uploaded.

I intend to add such functionality if changes are made to the Jamf Pro API so that these guarantees can be made.

## [Unreleased] - TBD

- Moved `jamf_upload.py` to `jamf_pkg_upload.py` since we now have multiple scripts.

- Added the `jamf_script_upload.py` script. This is used for uploading scripts to Jamf Pro. The option to include variables as in AutoPkg (`%VARIABLE%`) has been included.

- Added the `jamf_category_upload.py` script. This is used for creating or uploading categories in Jamf Pro.

- Added the `jamf_computergroup_upload.py` script. This is used for creating or uploading computer groups in Jamf Pro. The option to include variables as in AutoPkg (`%VARIABLE%`) has been included.

- Added the `jamf_ea_upload.py` script. This is used for uploading script-based extension attributes to Jamf Pro. The option to include variables as in AutoPkg (`%VARIABLE%`) has been included. Other types of EA will be included in due course.

- Added the `jamf_policy_upload.py` script. This is used for creating or uploading a policy in Jamf Pro. The option to include variables as in AutoPkg (`%VARIABLE%`) has been included.

- Added the `jamf_computerprofile_upload.py` script. This is used for creating or uploading configuration profiles in Jamf Pro. Profiles can be supplied as either a payload plist or a complete mobileconfig file.

- Added the `jamf_computerprofile_sign.py` script. This can be used for signing profiles.

- Common functions have been moved into the `jamf_upload_lib` folder and included in each script to avoid too much repetition.

- Examples in the `_tests` folder have been used for testing each script.

- Added AutoPkg processors, `JamfScriptUploader.py`, `JamfCategorytUploader.py`, `JamfComputerGroupUploader.py`, `JamfExtensionAttributeUploader.py`, `JamfPackageUploader.py` and `JamfPolicyUploader.py`, which perform the same tasks as the standalone scripts. Unlike the standalone scripts, these are not designed to upoload multiple packages/policies etc in one process, but they can be called multiple times from withing an AutoPkg recipe to upload multiple objects in a single AutoPkg run. Due to the limitations of AutoPkg, these do not share common modules from this repo - instead, the functions are repeated in each Processor. This allows each Processor to be called independently without installing any dependencies.

- Added various working `.jamf` recipes, and associated templates and Self Service icons.

- Switched from using Python's `requests` package to using a built-in `nscurl` library for most functions. Only `jamf.pkg_upload.py` retains an option to use `requests` for uploading a package, or using the `--direct` method, both of which require the `requests` package to be present in your python3 environment. The default upload method does not require `requests`.

## [0.2.0] - 2020-07-24

- Added the `--direct` method to `jamf.pkg_upload.py`, which allows package upload using the same method as performed via the Jamf Cloud GUI. This method has been ported here from `python-jss`. Packages are uploaded in chunks. The default chunk size is 1MB, but this can be altered using the `--chunksize` option. Many thanks to `@mosen` for porting this across.

- Changed the `requests` option to upload via the `data` option rather than the `files` option. This prevents a problem of files larger than 2GB failing to upload due to a limitation in the `ssl` module (see [https://github.com/psf/requests/issues/2717#issuecomment-130343655](https://github.com/psf/requests/issues/2717#issuecomment-130343655)).

## [0.1.0] - 2020-07-03

- Bundle-style packages are now handled properly, by zipping them before performing the upload to Jamf. If a zip file of the correct name is already present in the same folder as the package, it will not be recreated. Delete it if you need it to be remade.

This is developing into a testing script to accompany the AutoPkg processor `JamfPackageUpload`, so some debug modes are now available

- You can now use the `--curl` option to switch to using the system `curl` rather than the Python `requests` module, in case this improves reliability, or just to perform tests. My initial tests have not shown any improvement in upload reliability, but YMMV.

- You can set a timeout limit using the `--timeout` flag. This sets the `timeout` option in `requests`, or the `--max-time` option if using `curl`.

- Different output verbosity levels (`-v[v]`) are available.

## 0.0.1 - 2020-06-26

Initial commit. Formerly a GitHub gist.

[unreleased]: https://github.com/grahampugh/JSSImporter/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/grahampugh/JSSImporter/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/grahampugh/JSSImporter/compare/v0.0.1...v0.1.0
