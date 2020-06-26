# jamf-upload Change Log

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](http://semver.org/).

## Known issues in latest version

`jamf_upload.py` uses an undocumented API for uploading packages to Jamf Cloud. As far as I know, this is the same API used by the Jamf Admin app. It is also the same method used by JSSImporter.

The HTTP responses from this API are unpredictable. You may see a `504` response, which indicates a Gateway Timeout error, but the package may well be delivered anyway. This is true whether uploading a new package or overwriting an existing one.

As the HTTP response cannot be guaranteed, I have not yet added the ability to write any package metadata such as category, manifest etc., which, as far as I can tell, must be supplied by a different API call after the package object has been uploaded. There is no predictable way to check that the package was successfully loaded unless we can guarantee that we are making our HTTP request to the same cluster node to which the package was uploaded.

I intend to add such functionality if changes are made to the Jamf Pro API so that these guarantees can be made.

## [0.1] - 2020-06-26

Initial commit. Formerly a GitHub gist.
