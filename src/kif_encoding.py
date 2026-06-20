"""
KIF text encoding detection.
"""


class KifEncodingError(ValueError):
    """Raised when KIF bytes cannot be decoded with supported encodings."""


def decode_kif_bytes(data: bytes) -> str:
    """Decode KIF bytes as UTF-8 or CP932.

    KIF files commonly appear as UTF-8 or Shift-JIS compatible CP932. Keep the
    detection deterministic and dependency-free: prefer UTF-8, then fall back to
    CP932.
    """

    for encoding in ("utf-8-sig", "cp932"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise KifEncodingError("KIF file encoding must be UTF-8 or CP932")
