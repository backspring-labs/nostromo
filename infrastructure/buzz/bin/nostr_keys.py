#!/usr/bin/env python3
"""Nostr key helpers: secp256k1 x-only derivation and NIP-19 bech32, standard library only.

Needed from WP-3 onward because Buzz stores the private key in the OS keyring and derives the
public key at runtime, so there is no file to read a pubkey out of. Also used throughout WP-5,
where every agent identity has to be converted between hex and npub.

Self-verifying: --selftest checks derivation against the BIP-340 vectors and bech32 against the
NIP-19 vector. A wrong public key here would make the owner unable to authenticate to their own
relay, so this is not a place to trust untested arithmetic.
"""
from __future__ import annotations

import sys

# --- secp256k1 --------------------------------------------------------------------------------
P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def _add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    ax, ay = a
    bx, by = b
    if ax == bx and (ay + by) % P == 0:
        return None
    if a == b:
        lam = 3 * ax * ax * pow(2 * ay, P - 2, P) % P
    else:
        lam = (by - ay) * pow(bx - ax, P - 2, P) % P
    x = (lam * lam - ax - bx) % P
    return (x, (lam * (ax - x) - ay) % P)


def _mul(k: int, point=(GX, GY)):
    r = None
    while k:
        if k & 1:
            r = _add(r, point)
        point = _add(point, point)
        k >>= 1
    return r


def xonly_pubkey(seckey_hex: str) -> str:
    """The 32-byte x-only public key BIP-340 and Nostr use."""
    d = int(seckey_hex, 16)
    if not 1 <= d < N:
        raise ValueError("private key out of range")
    pt = _mul(d)
    return f"{pt[0]:064x}"


# --- bech32 (BIP-173), as NIP-19 uses it -------------------------------------------------------
CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _polymod(values):
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= gen[i] if ((b >> i) & 1) else 0
    return chk


def _hrp_expand(hrp):
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _convertbits(data, frm, to, pad=True):
    acc, bits, ret = 0, 0, []
    maxv = (1 << to) - 1
    for b in data:
        acc = (acc << frm) | b
        bits += frm
        while bits >= to:
            bits -= to
            ret.append((acc >> bits) & maxv)
    if pad and bits:
        ret.append((acc << (to - bits)) & maxv)
    return ret


def bech32_encode(hrp: str, data_hex: str) -> str:
    data = _convertbits(bytes.fromhex(data_hex), 8, 5)
    chk = _polymod(_hrp_expand(hrp) + data + [0, 0, 0, 0, 0, 0]) ^ 1
    return hrp + "1" + "".join(CHARSET[d] for d in data + [(chk >> 5 * (5 - i)) & 31 for i in range(6)])


def bech32_decode(s: str) -> tuple[str, str]:
    s = s.strip().lower()
    pos = s.rfind("1")
    hrp, data = s[:pos], [CHARSET.index(c) for c in s[pos + 1:]]
    if _polymod(_hrp_expand(hrp) + data) != 1:
        raise ValueError("bad bech32 checksum")
    return hrp, bytes(_convertbits(data[:-6], 5, 8, False)).hex()


def selftest() -> int:
    ok = True
    # BIP-340 test vectors: secret key -> x-only public key.
    for sec, pub in [
        ("0000000000000000000000000000000000000000000000000000000000000003",
         "F9308A019258C31049344F85F89D5229B531C845836F99B08601F113BCE036F9"),
        ("B7E151628AED2A6ABF7158809CF4F3C762E7160F38B4DA56A784D9045190CFEF",
         "DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659"),
    ]:
        got = xonly_pubkey(sec)
        good = got == pub.lower()
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  derive {sec[:12]}... -> {got[:16]}...")
    # NIP-19 vector: pubkey hex <-> npub.
    hexpub = "3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d"
    npub = "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"
    enc, dec = bech32_encode("npub", hexpub), bech32_decode(npub)[1]
    ok &= enc == npub and dec == hexpub
    print(f"  {'PASS' if enc == npub else 'FAIL'}  encode hex -> npub")
    print(f"  {'PASS' if dec == hexpub else 'FAIL'}  decode npub -> hex")
    print("selftest passed" if ok else "SELFTEST FAILED — do not trust this tool", file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selftest":
        sys.exit(selftest())
    arg = sys.argv[1].strip()
    if arg.startswith(("npub1", "nsec1")):
        hrp, hx = bech32_decode(arg)
        print(hx if hrp == "npub" else xonly_pubkey(hx))
    elif len(arg) == 64:
        print(bech32_encode("npub", arg))
    else:
        sys.exit("give a 64-char hex pubkey, an npub, or an nsec")
