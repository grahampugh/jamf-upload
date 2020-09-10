#!/bin/bash
## script to install and configure Adobe Flash Player

file="/Library/Application Support/Macromedia/mms.cfg"
mkdir -p "/Library/Application Support/Macromedia"

if [ -f "$file" ]; then
    AutoUpdate=$(grep "^AutoUpdateDisable=" "$file")
    if [ -z "$AutoUpdate" ]; then
        echo "AutoUpdateDisable=1" >> "$file"
    else
        sed -i.bak 's/^AutoUpdateDisable=.*/AutoUpdateDisable=1/' "$file"
    fi
    AutoUpdate=$(grep "^SilentAutoUpdateEnable=" "$file")
    if [ -z "$AutoUpdate" ]; then
        echo "SilentAutoUpdateEnable=0" >> "$file"
    else
        sed -i.bak 's/^SilentAutoUpdateEnable=.*/SilentAutoUpdateEnable=0/' "$file"
     fi
     AutoUpdate=$(grep "^DisableAnalytics=" "$file")
     if [ -z "$AutoUpdate" ]; then
         echo "DisableAnalytics=0" >> "$file"
    else
        sed -i.bak 's/^DisableAnalytics=.*/DisableAnalytics=0/' "$file"
    fi
else
    touch "$file"
    echo "AutoUpdateDisable=1" >> "$file"
    echo "SilentAutoUpdateEnable=0" >> "$file"
    echo "DisableAnalytics=0" >> "$file"
fi

chown root:admin "$file"
chmod 755 "$file"
