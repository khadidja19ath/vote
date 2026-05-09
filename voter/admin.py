"""
admin.py — The Administrator
RSA Parameters: N=55, e=27, d=3, φ(N)=40
"""
from math import gcd

N = 55
e = 27
d = 3


def mod_inverse(k: int, n: int) -> int:
    if gcd(k, n) != 1:
        raise ValueError(f"k={k} is not coprime with N={n}!")
    old_r, r = k, n
    old_s, s = 1, 0
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
    return old_s % n


def get_valid_k_values() -> list:
    return [k for k in range(2, N) if gcd(k, N) == 1]


def mask_vote(vote: int, k: int) -> int:
    if gcd(k, N) != 1:
        raise ValueError(f"k={k} must be coprime with N={N}!")
    return (vote * pow(k, e, N)) % N


def blind_sign(m_prime: int) -> int:
    return pow(m_prime, d, N)


def unmask_signature(m_double_prime: int, k: int) -> int:
    k_inv = mod_inverse(k, N)
    return (m_double_prime * k_inv) % N


def verify_signature(vote: int, s: int) -> bool:
    return pow(s, e, N) == vote % N
