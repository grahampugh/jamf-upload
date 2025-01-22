#!/usr/local/autopkg/python
# pylint: disable=invalid-name

# The MIT License (MIT)
# Copyright © 2024 <copyright holders>
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import annotations

from Foundation import NSMutableDictionary  # pylint: disable=import-error
from Security import (  # pylint: disable=import-error
    SecItemAdd,
    SecItemCopyMatching,
    SecItemDelete,
    kSecAttrAccount,
    kSecAttrService,
    kSecClass,
    kSecClassGenericPassword,
    kSecMatchLimit,
    kSecMatchLimitOne,
    kSecReturnData,
    kSecValueData,
)


class KeychainError(Exception):
    """An error occurred while accessing the keychain."""


def add(account: str, service: str, password: str | bytes) -> None:
    """Add a password to the keychain.

    Args:
        account: The account name.
        service: The service name.
        password: The password, as either a string or bytes.

    Returns:
        The status code.

    Raises:
        KeychainError: If the item could not be added.

    Examples:
        >>> keychain_access.add("my_account", "my_service", "my_password")

        >>> keychain_access.add("my_account", "my_service", b"my_password")
    """
    query = NSMutableDictionary.dictionary()
    query[kSecClass] = kSecClassGenericPassword
    query[kSecAttrAccount] = account
    query[kSecAttrService] = service
    query[kSecValueData] = password.encode() if isinstance(password, str) else password

    try:
        status, _ = SecItemAdd(query, None)
    except Exception as e:
        raise KeychainError(str(e)) from e

    if status != 0:
        raise KeychainError(f"Failed to add item to keychain (status={status})")


def get(account: str, service: str) -> str | None:
    """Get a password in the keychain.

    Args:
        account: The account name.
        service: The service name.

    Returns:
        The password, or `None` if not found.

    Raises:
        KeychainError: If an internal error occurred.

    Examples:
        >>> keychain_access.get("my_account", "my_service")
        "my_password"

        If the password is not found:
        >>> keychain_access.get("my_account", "my_service")
        None
    """
    query = NSMutableDictionary.dictionary()
    query[kSecClass] = kSecClassGenericPassword
    query[kSecAttrAccount] = account
    query[kSecAttrService] = service
    query[kSecReturnData] = True
    query[kSecMatchLimit] = kSecMatchLimitOne

    try:
        _, data = SecItemCopyMatching(query, None)
    except Exception as e:
        raise KeychainError(str(e)) from e

    return data.bytes().tobytes().decode() if data else None


def delete(account: str, service: str) -> None:
    """Delete a password from the keychain.

    Args:
        account: The account name.
        service: The service name.

    Returns:
        The status code.

    Raises:
        KeychainError: If the item could not be deleted.

    Examples:
        >>> keychain_access.delete("my_account", "my_service")
    """
    query = NSMutableDictionary.dictionary()
    query[kSecClass] = kSecClassGenericPassword
    query[kSecAttrAccount] = account
    query[kSecAttrService] = service

    try:
        status = SecItemDelete(query)
    except Exception as e:
        raise KeychainError(str(e)) from e

    if status != 0:
        raise KeychainError(f"Failed to delete item from keychain (status={status})")
