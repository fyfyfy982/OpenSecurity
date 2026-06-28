# RSA 攻击

> 何时用：题目出现 `n=p*q`、`e`、`c=pow(m,e,n)`，或给了 p/q/d 的 hint。

## 通用准备

```python
from Crypto.Util.number import long_to_bytes
import gmpy2
def dec(c,d,n): return long_to_bytes(pow(c,d,n))
```

---

## 1. 共模攻击（同 n，不同 e1/e2，且 gcd(e1,e2)=1）

**识别**：同一 n、两条密文 c1（用 e1）、c2（用 e2）。

```python
import gmpy2
g,s,t = gmpy2.gcdext(e1,e2)        # s*e1 + t*e2 = 1
m = (pow(c1,s,n)*pow(c2,t,n)) % n
print(long_to_bytes(m))
```

## 2. 小 e + 明文小（e=3 常见）

### 2a. 无填充、m^e < n → 直接开方
```python
m,toofar = gmpy2.iroot(c,e)
if toofar: print(long_to_bytes(int(m)))
```

### 2b. m^e 略大于 n（Coppersmith small_roots）
**识别**：e 小，且知道明文高位/部分（如已知 flag 前缀）。
```python
# sage
n,e,c = ...
P.<x> = PolynomialRing(Zmod(n))
# 已知前缀 prefix，明文 = prefix*2^k + x
f = (prefix*2^k + x)^e - c
roots = f.small_roots(X=2^k, beta=1, epsilon=0.05)
print([long_to_bytes(int(prefix*2^k + r)) for r in roots])
```

## 3. Wiener（d 很小，e 很大 ≈ n）

**识别**：e 很大（接近 n），私钥 d 小。用连分数。

```sage
def wiener(e,n):
    # 连分数展开 e/n
    cf = continued_fraction(e/n)
    for k in cf.convergents()[1:]:
        d = k.denominator()
        if (e*d-1) % k.numerator() == 0:
            phi = (e*d-1)//k.numerator()
            # 验证 p,q
            s = n - phi + 1
            disc = s*s - 4*n
            if disc.is_square():
                p = (s + isqrt(disc))//2; q = n//p
                return d,p,q
```

## 4. Boneh-Durfee（d 稍大，Wiener 失败时）

**识别**：d < n^0.292。比 Wiener 适用范围大，需格（Coppersmith 的 partial）。实现较复杂，查现成 sage 脚本（关键字 `boneh durfee sage`），核心是构造方程 `e*d = 1 + k*phi`，用 small_roots 求 k。

## 5. 已知 p/q 之一、或 partial p/q（Coppersmith）

**识别**：知道 p 的高位/低位部分（如 p 高位泄漏）。
```sage
# 已知 p_high（p 的高位），p = p_high + x，x 较小
P.<x> = PolynomialRing(Zmod(n))
f = p_high + x
roots = f.small_roots(X=2^(bits_unknown), beta=0.5)
p = int(p_high + roots[0]); assert n % p == 0
```

## 6. 多素数 n（n = p*q*r...）

**识别**：n 分解出多个素数（factor 成功，或题目明给）。phi = ∏(pi-1)，照常求 d。

## 7. Padding Oracle（PKCS#1 v1.5 / OAEP）

**识别**：有解密 oracle，返回"padding 对/错"或错误码差异。

需一个可重复提交密文、能区分 padding 正误的接口。Bleichenbacher（PKCS1v1.5）或 Manger（OAEP）算法。标准实现较长，用现成工具（如 `python-paddingoracle` 库或 pwntools 脚本），核心是二分逼近明文。

## 8. 低私钥指数以外的快速判断

| 现象 | 做法 |
|------|------|
| `factor(n)` 秒出 | n 弱，直接分解 |
| n = p*q 但 p,q 接近 | Fermat 分解（`gmpy2` 或 sage `factor`） |
| 多个 n 共享因子 | 两两 gcd：`gcd(n1,n2)` 得 p |
| e=1 | c=m，直接 long_to_bytes(c) |
| e 与 phi 不互素 | 求 m^gcd(e,phi) 的根（Rabin / 一般化） |

## 9. 选攻击决策树

```
有解密 oracle？ → Padding Oracle
e 很小？ → 2a/2b
e 很大(d 小)？ → Wiener → 失败试 Boneh-Durfee
多条密文同 n？ → 共模
已知 p/q 部分？ → Coppersmith
n 可分解/共享因子？ → 直接分解
都不像？ → 看 lattice-attacks.md（可能有 hint 走格）
```

## 注意

- 求出 m 后必须 `long_to_bytes` 验证像 flag。
- Coppersmith 的 `X`（未知量上界）要估准，太大无解、太小漏解；`epsilon` 调小更稳但慢。
- Wiener 失败不代表 d 大，可能 e/n 连分数收敛慢；试 Boneh-Durfee。
