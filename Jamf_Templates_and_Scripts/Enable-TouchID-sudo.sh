#!/bin/bash
# enabled touch id for sudo
# from https://github.com/flammable/enable_sudo_touchid/blob/master/munki_postinstall_script.sh

sed="/usr/bin/sed"

enable_touchid="auth       sufficient     pam_tid.so"

${sed} -i '' -e "1s/^//p; 1s/^.*/${enable_touchid}/" /etc/pam.d/sudo

exit