#!/bin/bash

#######################################################################
#
# Uninstall Cisco AnyConnect
#
# Note: versions of AnyConnect which include a System Extension
# cannot be uninstalled without an admin user providing credentials
# via a GUI prompt.
#
#######################################################################

appName="Cisco AnyConnect Secure Mobility Client"

if [[ $(pgrep -x "$appName") ]]; then
	echo "Closing $appName"
	osascript -e "quit app \"$appName\""
	sleep 1

	# double-check
	countUp=0
	while [[ $countUp -le 10 ]]; do
		if [[ -z $(pgrep -x "$appName") ]]; then
			echo "$appName closed."
			break
		else
			(( countUp=countUp+1 ))
			sleep 1
		fi
	done
    if [[ $(pgrep -x "$appName") ]]; then
	    echo "$appName failed to quit - killing."
	    /usr/bin/pkill "$appName"
    fi
fi

# Run Cisco's built-in uninstaller
# Taken from http://kb.mit.edu/confluence/display/mitcontrib/Cisco+Anyconnect+Manual+uninstall+Mac+OS
echo "Removing application: ${appName}"

cisco_uninstaller="/opt/cisco/vpn/bin/vpn_uninstall.sh"
cisco_uninstaller_new="/opt/cisco/anyconnect/bin/anyconnect_uninstall.sh"
if [[ -f "$cisco_uninstaller" ]]; then 
	"$cisco_uninstaller"
elif [[ -f "$cisco_uninstaller_new" ]]; then 
	"$cisco_uninstaller_new"
else
	echo "no Cisco uninstaller found"
fi

# Removing any plugins from Office
# Forget packages
echo "Forgetting packages"
pkgutilcmd="/usr/sbin/pkgutil"
$pkgutilcmd --pkgs=com.cisco.pkg.anyconnect.vpn && $pkgutilcmd --forget com.cisco.pkg.anyconnect.vpn
$pkgutilcmd --pkgs=ch.ethz.id.pkg.CiscoAnyConnect && $pkgutilcmd --forget ch.ethz.id.pkg.CiscoAnyConnect

echo "${appName} removal complete!"
