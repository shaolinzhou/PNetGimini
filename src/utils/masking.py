import re
import logging
from typing import Any

# Regular expression patterns for sensitive data masking in network automation
SENSITIVE_PATTERNS = [
    # Passwords and secrets
    (re.compile(r"((?:password|secret|pwd)\s+(?:[0-9]\s+)?)['\"]?([^\s'\"]+)['\"]?", re.IGNORECASE), r"\1********"),
    # SNMP communities
    (re.compile(r"((?:snmp-server\s+community|community)\s+)['\"]?([^\s'\"]+)['\"]?", re.IGNORECASE), r"\1********"),
    # VPN / IPsec Pre-Shared Keys & key-strings
    (re.compile(r"((?:pre-shared-key|key-string|psk|preshared-key)\s+)['\"]?([^\s'\"]+)['\"]?", re.IGNORECASE), r"\1********"),
    # API tokens & Bearer auth
    (re.compile(r"((?:token|api[_-]?key)\s*[:=]\s*)['\"]?([^\s'\"]+)['\"]?", re.IGNORECASE), r"\1********"),
    (re.compile(r"(Bearer\s+)([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE), r"\1********"),
    # Private Key blocks
    (re.compile(r"-----BEGIN [A-Z\s]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z\s]+ PRIVATE KEY-----", re.MULTILINE), "[PRIVATE KEY REDACTED]"),
]

def mask_sensitive_data(text: Any) -> Any:
    """
    Sanitizes string inputs by redacting passwords, secrets, tokens, and community strings.
    If input is not a string, it is converted or returned as is if None.
    """
    if not isinstance(text, str):
        return text

    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized

class MaskingFilter(logging.Filter):
    """
    Logging filter that intercepts log records and masks sensitive network credentials
    before messages reach terminal streams or disk log files.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = mask_sensitive_data(record.msg)
            elif hasattr(record, "getMessage"):
                # Mask formatted arguments if msg wasn't formatted yet
                pass
            
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: mask_sensitive_data(v) if isinstance(v, str) else v for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(mask_sensitive_data(arg) if isinstance(arg, str) else arg for arg in record.args)
        except Exception:
            # Masking filter must never break logging pipeline
            pass
        return True
