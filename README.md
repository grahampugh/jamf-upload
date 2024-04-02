# JamfUploader

JamfUploader is a name given to a set of [AutoPkg](https://github.com/autopkg/autopkg) Processors designed to interact with the Jamf Pro APIs. Most of these processors are concerned with uploading things to a Jamf Pro Server. This includes:

* Packages
* Categories
* Computer Groups
* Configuration Profiles
* Scripts
* Extension Attributes
* Policies (and their icons)
* Patch Policies
* Dock Items
* Accounts

There are some additional processors.

This repo contains the sourcecode of the JamfUploader processors. Identical copies of the processors are hosted in the [autopkg/grahampugh-recipes](https://github.com/autopkg/grahampugh-recipes) repo, in the [JamfUploaderProcessors](https://github.com/autopkg/grahampugh-recipes/tree/main/JamfUploaderProcessors) folder).

**Please see the [Wiki](https://github.com/grahampugh/jamf-upload/wiki/JamfUploader-AutoPkg-Processors) for instructions on using the AutoPkg processors.**

## Additional Resources

The `jamf-upload.sh` script can be used to take advantage of the JamfUploader processors without needing any AutoPkg recipes.

The `jamf-api-tool` folder contains a standalone python script `jamf-api-tool.py` for performing certain operations on a Jamf Pro instance, primarily associated with cleaning up unused packages and other objects.

Please see the [Wiki](https://github.com/grahampugh/jamf-upload/wiki) for instructions on using both the standalone script, `jamf-upload.sh`, the AutoPkg processors, and other tips and tricks.
