# JamfUploader

JamfUploader is a name given to a set of [AutoPkg](https://github.com/autopkg/autopkg) Processors designed to interact with the Jamf Pro APIs. Most of these processors are concerned with uploading things to a Jamf Pro Server. This includes:

* Packages
* Categories
* Computer Groups
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

The `standalone_uploaders` folder contains standalone scripts that do the same thing as the AutoPkg processors. These are now deprecated and require a python 3 installation.

Please see the [Wiki](https://github.com/grahampugh/jamf-upload/wiki) for instructions on using both the standalone scripts, `jamf-upload.sh`, the AutoPkg processors, and other tips and tricks.
