# -*- coding: utf-8 -*-
"""Halton 低差异序列（参数搜索器的采样层）。

为什么用低差异序列而不是随机采样：维度只有 4~5、评估预算 32 个点，
均匀随机在 2 维投影上会留下大块空洞；Halton 的每维投影都是「分层」的，
32 个点就能把参数盒覆盖到「任意 1/4 区间里都有点」的程度。

可复现性（写死，不要改）：
  * 数值本身完全由 Halton 决定性给出；
  * `numpy.random.default_rng(20261101)` **只**用来做两件事：
      1) 打乱「维度 → 底数」的对应顺序（避免 skirt_margin 永远吃 base=2
         这个分层最好的序列、而 joint_blend_mm 永远吃 base=11）；
      2) 抽一个跳跃起点 skip，避开序列最前面的 0 附近。
    两件事都由 seed 唯一决定，所以只记录 seed 即可完全复现。
"""
import numpy as np

DEFAULT_SEED = 20261101


def halton(i, base):
    """第 i 个（i>=1）以 base 为底的 Halton 数值，落在 [0,1)。"""
    i = int(i)
    base = int(base)
    if base < 2:
        raise ValueError("base 必须 >= 2")
    if i < 0:
        raise ValueError("i 必须 >= 0")
    f = 1.0
    r = 0.0
    while i > 0:
        f /= base
        r += f * (i % base)
        i //= base
    return r


def _first_primes(k):
    """前 k 个质数（Halton 的底数必须两两互质）。"""
    out = []
    n = 2
    while len(out) < k:
        ok = True
        for p in out:
            if p * p > n:
                break
            if n % p == 0:
                ok = False
                break
        if ok or not out:
            out.append(n)
        n += 1
    return out[:k]


def halton_seq(n, d, bases=None, seed=DEFAULT_SEED):
    """返回 n×d 的 [0,1) 矩阵（第 0 维 …… 第 d-1 维对应调用方的 DIMS 顺序）。

    bases 只决定「每列用哪个底数」，列与维度的对应关系由 seed 打乱。
    """
    n = int(n)
    d = int(d)
    if n < 0 or d < 0:
        raise ValueError("n/d 必须 >= 0")
    if d == 0 or n == 0:
        return np.zeros((max(0, n), max(0, d)), dtype=np.float64)

    primes = _first_primes(max(d, 16))
    if bases is None:
        bases = tuple(primes[:d])
    bases = list(bases)
    if len(bases) < d:
        bases += [p for p in primes if p not in bases][: d - len(bases)]

    rng = np.random.default_rng(int(seed))          # 只干下面两件事
    perm = rng.permutation(d)                       # 1) 维度乱序
    skip = int(rng.integers(1, 1000))               # 2) 跳跃起点

    out = np.empty((n, d), dtype=np.float64)
    for k in range(d):
        base = bases[k]
        col = np.fromiter((halton(skip + j, base) for j in range(n)),
                          dtype=np.float64, count=n)
        out[:, perm[k]] = col
    return out


def seq_meta(d, bases=None, seed=DEFAULT_SEED):
    """把 seed 决定的两件事复算出来，供报告/复验打印（不是采样结果的一部分）。"""
    rng = np.random.default_rng(int(seed))
    perm = rng.permutation(int(d)).tolist()
    skip = int(rng.integers(1, 1000))
    primes = _first_primes(max(int(d), 16))
    if bases is None:
        bases = primes[:int(d)]
    return {"seed": int(seed), "skip": skip, "perm": perm,
            "bases": list(bases)}