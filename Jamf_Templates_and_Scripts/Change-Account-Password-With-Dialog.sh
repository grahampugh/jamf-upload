#!/bin/bash

# Script for Jamf Pro to change a user password by asking for the password interactively.
# Parameters are optional - dialog boxes will ask if these fields are missing

# Parameter 4 - short user name (account name)
# Parameter 5 - minimum characters for password
# Parameter 6 - password complexity: none/complex
#               complex: must have small, large, numeral, special

# Short name (i.e. account name and home directory name)
AccountShortName="$4"
# Minimum password length - must be a number
MinPasswordLength="$5"
# Password Complexity
PasswordComplexity="$6"

function askForShortName () {
    $osascript <<EOT
        set nameentry to text returned of (display dialog "Please enter the short name of the account for which you wish to reset the password" default answer "" buttons {"Enter"} default button 1 with icon 2)
EOT
}

function askForPassword () {
    $osascript <<EOT
        set nameentry to text returned of (display dialog "Please enter a new password for the $AccountShortName account" default answer "" with hidden answer buttons {"Enter"} default button 1 with icon 2)
EOT
}

function verifyPassword () {
    $osascript <<EOT
        set nameentry to text returned of (display dialog "Please re-enter the new password for the $AccountShortName account" default answer "" with hidden answer buttons {"Enter"} default button 1 with icon 2)
EOT
}

function passwordsDontMatch () {
    return=$(osascript <<-EOF
    tell application "System Events" to display dialog "Passwords did not match! Please try again" buttons {"OK", "Try again"} default button 2 with icon 2
EOF
)
    # Check status of osascript
    if [[ "$return" == "button returned:OK" ]] ; then
       echo "User aborted. Exiting..."
       exit 1
    fi
}

function passwordTooShort () {
    $osascript <<EOT
        display dialog "Password is too short! Please try again" buttons {"OK"} default button 1 with icon 2
EOT
}

function passwordTooSimple () {
    $osascript <<EOT
        display dialog "Password is too simple! Please try again" buttons {"OK"} default button 1 with icon 2
EOT
}

function userDoesNotExist () {
    $osascript <<EOT
        display dialog "User $1 does not exist!" buttons {"OK"} default button 1 with icon 2
EOT
}

function askForAdmin () {
    $osascript <<EOT
        set nameentry to text returned of (display dialog "Please enter an administrator account" default answer "" buttons {"Enter"} default button 1 with icon 2)
EOT
}

function askForAdminPw () {
    $osascript <<EOT
        set nameentry to text returned of (display dialog "Please the password for the $AdminUser account" default answer "" with hidden answer buttons {"Enter"} default button 1 with icon 2)
EOT
}

function failedToChangePassword () {
    $osascript <<EOT
        display dialog "Password change attempt failed" buttons {"OK"} default button 1 with icon 2
EOT
}

function changedPassword () {
    $osascript <<EOT
        display dialog "Password change successful. Please note that the Keychain password for account $1 has not been reset." buttons {"OK"} default button 1 with icon 2
EOT
}

function resetPassword(){
    echo "Changing password for account $AccountShortName"
    $sysadminctl -resetPasswordFor $AccountShortName -newPassword $AccountPassword -adminUser $AdminUser -adminPassword $AdminPassword

    # Report user creation in log
    [[ $? == 0 ]] & changedPassword $AccountShortName || failedToChangePassword
}

function complexityCheck() {
    # code thanks to https://www.linuxquestions.org/questions/linux-server-73/bash-script-to-test-string-complexity-like-password-complexity-807370/
    readonly re_digit='[[:digit:]]'
    readonly re_lower='[[:lower:]]'
    readonly re_punct='[[:punct:]]'
    readonly re_space='[[:space:]]'
    readonly re_upper='[[:upper:]]'

    score=0
    for re in "$re_digit" "$re_lower" "$re_punct" "$re_space" "$re_upper"
    do
        [[ $1 =~ $re ]] && let score++
    done
    echo $score
}

## Main

# commands
sysadminctl="/usr/sbin/sysadminctl"
id="/usr/bin/id"
osascript="/usr/bin/osascript"

# check validity of password length check
case $MinPasswordLength in
    ''|*[!0-9]*)
        echo "Invalid minimum password length string. Setting to default (4)"
        MinPasswordLength=4
        ;;
    *) echo "Minimum password length set to $MinPasswordLength" ;;
esac

# check passowrd complexity setting
case $PasswordComplexity in
    complex)
        echo "Complex password check mode selected."
        ;;
    *)
        echo "Simple password complexity mode selected."
        PasswordComplexity="none"
        ;;
esac

# get account name (short name)
if [[ $AccountShortName == "" ]]; then
    AccountShortName=$(askForShortName)
fi

if ! $id "$AccountShortName" >/dev/null 2>&1; then
    echo "$AccountShortName Account does not exist!"
    userDoesNotExist $AccountShortName
    exit 0
fi

# get a password
PasswordsMatch=0
while [[ $PasswordsMatch = 0 ]]; do
    AccountPassword=$(askForPassword)
    # check password length
    if [ ${#AccountPassword} -lt $MinPasswordLength ]; then
        echo "Password length ${#AccountPassword} is less than the allowed minimum ($MinPasswordLength)"
        passwordTooShort
        continue
    else
        echo "Password length OK"
    fi

    # check password complexity
    if [[ $PasswordComplexity == "complex" ]]; then
        score=$(complexityCheck "$AccountPassword")
        if [[ $score -lt 3 ]]; then
            echo "Password is not complex enough (score is $score)."
            passwordTooSimple
            continue
        fi
    fi

    PasswordVerify=$(verifyPassword)
    if [[ "$AccountPassword" != "$PasswordVerify" ]]; then
        passwordsDontMatch
    else
        PasswordsMatch=1
        break
    fi
done

# Ask for an admin user
AdminUser=$(askForAdmin)

if ! $id "$AdminUser" >/dev/null 2>&1; then
    echo "$AdminUser Account does not exist!"
    userDoesNotExist $AdminUser
    exit 0
fi

# now ask for the admin password
AdminPassword=$(askForAdminPw)

# create the account
resetPassword

# end