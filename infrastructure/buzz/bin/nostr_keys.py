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


# --- BIP-340 Schnorr signing -------------------------------------------------------------------
# Needed because setting a NIP-05 handle means publishing a signed kind:0 event, and signing has to
# happen ON the role's own account — signing centrally would require reading all seven private
# keys, which would undo the per-account isolation the keys exist inside.
#
# Verified against the official BIP-340 test vectors in --selftest. This is the one place in the
# repository doing cryptography by hand, so it refuses to be used if those vectors fail.

import hashlib


def _tagged_hash(tag: str, msg: bytes) -> bytes:
    th = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(th + th + msg).digest()


def _has_even_y(pt) -> bool:
    return pt[1] % 2 == 0


def _lift_x(x: int):
    if x >= P:
        return None
    y_sq = (pow(x, 3, P) + 7) % P
    y = pow(y_sq, (P + 1) // 4, P)
    if pow(y, 2, P) != y_sq:
        return None
    return (x, y if y % 2 == 0 else P - y)


def schnorr_sign(msg: bytes, seckey_hex: str, aux_rand: bytes = b"\x00" * 32) -> str:
    d0 = int(seckey_hex, 16)
    if not 1 <= d0 < N:
        raise ValueError("private key out of range")
    pt = _mul(d0)
    d = d0 if _has_even_y(pt) else N - d0
    t = d ^ int.from_bytes(_tagged_hash("BIP0340/aux", aux_rand), "big")
    px = pt[0].to_bytes(32, "big")
    rand = _tagged_hash("BIP0340/nonce", t.to_bytes(32, "big") + px + msg)
    k0 = int.from_bytes(rand, "big") % N
    if k0 == 0:
        raise ValueError("nonce is zero")
    r = _mul(k0)
    k = k0 if _has_even_y(r) else N - k0
    rx = r[0].to_bytes(32, "big")
    e = int.from_bytes(_tagged_hash("BIP0340/challenge", rx + px + msg), "big") % N
    return (rx + ((k + e * d) % N).to_bytes(32, "big")).hex()


def schnorr_verify(msg: bytes, pubkey_hex: str, sig_hex: str) -> bool:
    pt = _lift_x(int(pubkey_hex, 16))
    if pt is None:
        return False
    sig = bytes.fromhex(sig_hex)
    r, s = int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")
    if r >= P or s >= N:
        return False
    e = int.from_bytes(_tagged_hash("BIP0340/challenge", sig[:32] + pt[0].to_bytes(32, "big") + msg), "big") % N
    big_r = _add(_mul(s), _mul(N - e, pt))
    return big_r is not None and _has_even_y(big_r) and big_r[0] == r


def sign_event(seckey_hex: str, kind: int, content: str, tags=None, created_at=None) -> dict:
    """Build and sign a Nostr event (NIP-01 id is sha256 over the canonical serialization)."""
    import json as _j
    import time as _t
    tags = tags or []
    pub = xonly_pubkey(seckey_hex)
    created_at = created_at if created_at is not None else int(_t.time())
    ser = _j.dumps([0, pub, created_at, kind, tags, content],
                   separators=(",", ":"), ensure_ascii=False)
    eid = hashlib.sha256(ser.encode()).hexdigest()
    return {"id": eid, "pubkey": pub, "created_at": created_at, "kind": kind,
            "tags": tags, "content": content,
            "sig": schnorr_sign(bytes.fromhex(eid), seckey_hex)}


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


def selftest_quiet() -> int:
    """selftest with output suppressed, for callers that must refuse on failure."""
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return selftest()


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
    # BIP-340 signing vectors, verbatim from the specification: index, seckey, aux_rand, msg, sig.
    for sk, aux, msg, want in [
        ("0000000000000000000000000000000000000000000000000000000000000003",
         "0000000000000000000000000000000000000000000000000000000000000000",
         "0000000000000000000000000000000000000000000000000000000000000000",
         "E907831F80848D1069A5371B402410364BDF1C5F8307B0084C55F1CE2DCA821525F66A4A85EA8B71E482A74F382D2CE5EBEEE8FDB2172F477DF4900D310536C0"),
        ("B7E151628AED2A6ABF7158809CF4F3C762E7160F38B4DA56A784D9045190CFEF",
         "0000000000000000000000000000000000000000000000000000000000000001",
         "243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89",
         "6896BD60EEAE296DB48A229FF71DFE071BDE413E6D43F917DC8DCF8C78DE33418906D11AC976ABCCB20B091292BFF4EA897EFCB639EA871CFA95F6DE339E4B0A"),
        ("C90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B14E5C9",
         "C87AA53824B4D7AE2EB035A2B5BBBCCC080E76CDC6D1692C4B0B62D798E6D906",
         "7E2D58D8B3BCDF1ABADEC7829054F90DDA9805AAB56C77333024B9D0A508B75C",
         "5831AAEED7B44BB74E5EAB94BA9D4294C49BCF2A60728D8B4C200F50DD313C1BAB745879A5AD954A72C45A91C3A51D3C7ADEA98D82F8481E0E1E03674A6F3FB7"),
    ]:
        got = schnorr_sign(bytes.fromhex(msg), sk, bytes.fromhex(aux))
        good = got.upper() == want
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  BIP-340 sign {sk[:12]}...")
        v = schnorr_verify(bytes.fromhex(msg), xonly_pubkey(sk), got)
        ok &= v
        print(f"  {'PASS' if v else 'FAIL'}  BIP-340 verify round trip")

    # A tampered signature must not verify — a verifier that only ever says yes proves nothing.
    bad = ("f" + got[1:]) if got[0] != "f" else ("0" + got[1:])
    tampered_rejected = not schnorr_verify(bytes.fromhex(msg), xonly_pubkey(sk), bad)
    ok &= tampered_rejected
    print(f"  {'PASS' if tampered_rejected else 'FAIL'}  tampered signature rejected")

    print("selftest passed" if ok else "SELFTEST FAILED — do not trust this tool", file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selftest":
        sys.exit(selftest())
    arg = sys.argv[1].strip()
    if arg == "--pub":
        # Derive the public key from a hex SECRET key. Explicit rather than inferred: a bare
        # 64-char hex is ambiguous between a pubkey and a seckey, and guessing wrong silently
        # produces a plausible-looking answer.
        print(xonly_pubkey(sys.argv[2].strip()))
        raise SystemExit(0)
    if arg == "--generate":
        import secrets as _s
        while True:
            sk = _s.token_bytes(32).hex()
            if 1 <= int(sk, 16) < N:
                break
        print(f"{sk} {xonly_pubkey(sk)}")
        raise SystemExit(0)
    if arg.startswith(("npub1", "nsec1")):
        hrp, hx = bech32_decode(arg)
        print(hx if hrp == "npub" else xonly_pubkey(hx))
    elif len(arg) == 64:
        print(bech32_encode("npub", arg))
    else:
        sys.exit("give a 64-char hex pubkey, an npub, or an nsec")
