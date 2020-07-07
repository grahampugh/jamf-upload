# Jamf Cloud package upload script

Upload one or more packages to Jamf Cloud Distribution Points

    usage: jamf_upload.py [-h] [--replace] [--curl] [--url URL] [--user USER]
                         [--password PASSWORD] [--prefs PREFS] [-v[v]]
                         pkg [pkg ...]

## Positional arguments

    pkg                  Full path to the package(s) to upload

## Optional arguments

    -h, --help           show help message and exit
    --replace            overwrite an existing uploaded package (experimental)
    --curl               use curl instead of requests (experimental)
    --url URL            the Jamf Pro Server URL
    --user USER          a user with the rights to upload a package
    --timeout TIMEOUT    set timeout in seconds for HTTP request for problematic
                         packages
    --password PASSWORD  password of the user with the rights to upload a
                         package
    --category CATEGORY  a category to assign to the package (experimental)
    --prefs PREFS        full path to an AutoPkg prefs file containing JSS URL,
                         API_USERNAME and API_PASSWORD, for example an AutoPkg
                         preferences file which has been configured for use with
                         JSSImporter
                         (~/Library/Preferences/com.github.autopkg.plist) or a
                         separate plist anywhere (e.g.
                         ~/.com.company.jcds_upload.plist)
    -v, --verbose        print verbose output headers

Missing arguments (URL, username, password) will be asked for interactively if not already supplied.

## Examples

Here, we supply the JSS URL, API user and password, and the package to upload.

    ./jamf_upload.py --url https://myserver.jamfcloud.com --user jamf_admin --password myPasswordIsSecure /path/to/FoldingAtHome-7.5.1.pkg

Here, we point to the AutoPkg preferences file, whicb should contains the JSS URL, API user and password. We add verbosity and specify that the package should be replaced.

    ./jamf_upload.py --prefs ~/Library/Preferences/com.github.autopkg.plist -vv --replace ~/Library/AutoPkg/Cache/local.pkg.FoldingAtHome/FoldingAtHome-7.5.1.pkg

Here, we point to a custom plist, whicb should contains the JSS URL, API user and password. We specify that the package should be replaced, and supply a category to assign to the package object.

    ./jamf_upload.py --prefs ../credentials/custom.plist --category Applications --replace ~/Library/AutoPkg/Cache/local.pkg.FoldingAtHome/FoldingAtHome-7.5.1.pkg

Here, we point to the AutoPkg preferences file, whicb should contains the JSS URL, API user and password. We specify multiple packages that we wish to be uploaded in one run.

    ./jamf_upload.py --prefs ~/Library/Preferences/com.github.autopkg.plist \
    /path/to/FoldingAtHome-7.5.1.pkg \
    /path/to/AdoptOpenJDK11-11.0.6.pkg \
    /path/to/Firefox-77.0.1.pkg \
    ...

## Known issues in latest version

`jamf_upload.py` uses an undocumented API for uploading packages to Jamf Cloud. As far as I know, this is the same API used by the Jamf Admin app. It is also the same method used by JSSImporter.

The HTTP responses from this API are unpredictable. You may see a `504` response, which indicates a Gateway Timeout error, but the package may well be delivered anyway. This is true whether uploading a new package or overwriting an existing one.

As the HTTP response cannot be guaranteed, and package metadata such as category, manifest etc., must be supplied by a different API call after the package object has been uploaded, it can be unpredictable as to whether the package will be successfully uploaded. For this reason, please consider the `--category` option as experimental.

# AutoPkg users

Users of AutoPkg can use the `JamfCloudPackageUploader` processor to upload packages. It shares the functionality of this script, though will only upload one package per process. This can be run as a post-processor, e.g.:

    autopkg run FoldingAtHome.pkg --post com.github.grahampugh.recipes.postprocessors/JamfCloudPackageUploader

When running this processor, the `JSS_URL`, `API_USER` and `API_PASSWORD` preferences must be supplied in your AutoPkg preferences.

The processor could also be added to an override, or a new recipe could be made wth the `.pkg` recipe as its parent. As long as there is a `pkg_path` output from the `.pkg` recipe, no parameters would need to be supplied. If not, you could supply a value for the `pkg_path` key as an argument to the processor. This would allow you to use the `.download` recipe as a parent if the download is a valid `pkg`.

Please don't use the `.jss` suffix for such a recipe if you publish it, as that would confuse the recipe with JSSImporter recipes. I suggest `.jamf-upload.recipe`.
