import base64
import os
import sys

from ddtrace.constants import APPSEC_ENV
from ddtrace.internal.compat import to_bytes_py2
from ddtrace.internal.utils.formats import asbool


def _appsec_rc_features_is_enabled():
    # type: () -> bool
    if asbool(os.environ.get("DD_REMOTE_CONFIGURATION_ENABLED", "true")):
        return APPSEC_ENV not in os.environ
    return False


def _appsec_rc_capabilities():
    # type: () -> str
    r"""return the bit representation of the composed capabilities in base64
    bit 0: Reserved
    bit 1: ASM 1-click Activation
    bit 2: ASM Ip blocking

    Int Number  -> binary number    -> bytes representation -> base64 representation
    ASM Activation:
    2           -> 10               -> b'\x02'              -> "Ag=="
    ASM Ip blocking:
    4           -> 100              -> b'\x04'              -> "BA=="
    ASM Activation and ASM Ip blocking:
    6           -> 110              -> b'\x06'              -> "Bg=="
    ...
    256         -> 100000000        -> b'\x01\x00'          -> b'AQA='
    """
    value = 0b0

    if _appsec_rc_features_is_enabled():
        value |= 1 << 1
        value |= 1 << 2

    result = ""
    if sys.version_info.major < 3:
        bytes_res = to_bytes_py2(value, (value.bit_length() + 7) // 8, "big")
        result = base64.b64encode(bytes_res)  # type: ignore[assignment, arg-type]
    else:
        result = str(base64.b64encode(value.to_bytes((value.bit_length() + 7) // 8, "big")), encoding="utf-8")

    return result
