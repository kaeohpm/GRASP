"""Secure storage for the Anthropic API key in the macOS Keychain."""

import Security
import Foundation

SERVICE = "com.grasp.app"
ACCOUNT = "anthropic_api_key"


def _base_query():
    return {
        Security.kSecClass: Security.kSecClassGenericPassword,
        Security.kSecAttrService: SERVICE,
        Security.kSecAttrAccount: ACCOUNT,
    }


def save_api_key(key: str) -> bool:
    raw = key.encode("utf-8")
    data = Foundation.NSData.dataWithBytes_length_(raw, len(raw))

    Security.SecItemDelete(_base_query())

    q = _base_query()
    q[Security.kSecValueData] = data
    status, _ = Security.SecItemAdd(q, None)
    return status == 0


def get_api_key():
    q = _base_query()
    q[Security.kSecReturnData] = True
    q[Security.kSecMatchLimit] = Security.kSecMatchLimitOne
    status, result = Security.SecItemCopyMatching(q, None)
    if status != 0 or result is None:
        return None
    try:
        return bytes(result).decode("utf-8").strip() or None
    except Exception:
        return None


def delete_api_key() -> bool:
    status = Security.SecItemDelete(_base_query())
    return status == 0
