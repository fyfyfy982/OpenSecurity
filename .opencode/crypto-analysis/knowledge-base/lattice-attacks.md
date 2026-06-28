# 格攻击（Lattice / LLL）

> 何时用：题目含多个"近似/线性"关系——如 `a*p+b*q` hint、截断比特、HNP、隐含线性方程。**SageMath 必装**（手写 LLL 极易错）。

## 核心：LLL 格规约

LLL 在格中找"短向量"。构造一个矩阵 M，使目标解（小的系数或差值）成为 M 的某短行/列，`M.LLL()` 后取出来。

---

## 1. `a*p + b*q` 提示型（如 SekaiCTF apbq-rsa-iv）

**识别**：给 n=p*q 和若干 `hint_i = a_i*p + b_i*q`，其中 a_i,b_i 未知但较小（上界已知）。

**思路**：构造格，把短向量 `(p, q, ...)` 暴露出来。给定 hint 与 n，p 满足 `hint ≡ a*p (mod q)` 类关系，但 a,b 都未知——用多组 hint 构造使 `(p,q)` 成为短解。

**构造要点**（3 组 hint 时）：
- 把 hint 和 n 排进矩阵，用大缩放因子压住已知大数，留出 p,q 所在小行。
- 缩放因子 K 取 ≈ hint 上界级别，让 LLL 偏好含 p,q 的短行。

```sage
# 模板（按题调参）：n, hints 已知，a,b 上界 B
# 构造 M 使其某短行 ∝ (p, q)
# 常见技巧：行 = [hint_i 缩放, 单位项], 末行 = [n 缩放, K]
# LLL 后在某行读出 (p, q)（可能差符号/倍数，验证 n%p==0）
n = ...
hints = [...]
B = 4**312   # a,b 上界
# 例：构造矩阵后
M = Matrix(ZZ, [...])
L = M.LLL()
for row in L:
    # 尝试解读 row 为 (p, q) 或含其线性组合
    cand = abs(row[0])
    if n % cand == 0 and 1 < cand < n:
        p = cand; q = n // p; print("FOUND", p, q); break
# 求出 p,q 后 RSA 解密
```

> 实际构造随 hint 数量/上界变化。**先用 3 组 hint + 大缩放试，无解则调缩放/加 n 行**。

## 2. 隐含数问题（HNP, Hidden Number Problem）

**识别**：知道 `t_i` 和 `a_i = ⌊t_i * α / 2^k⌉`（α 未知密钥，a_i 是截断高位）。即已知乘积的高位，恢复 α（常见于 DSA/ECDSA nonce 部分泄漏）。

**构造**：
```sage
# 已知 t_i, a_i, k（已知高位比特数），求 α
# M 行 = [2^k, 0,..., t_i, 0], 最后一行含 a_i 与大常数
# LLL 找 (α - a_i*2^k) 等小量
d = len(t)
M = Matrix(ZZ, d+2, d+2)
K = 2^(k+1)   # 上界缩放
for i in range(d):
    M[i,i] = 2^k
    M[d,i] = t[i]
    M[i,d] = ... # 视实现
M[d,d] = 1
M[d+1,d+1] = K
L = M.LLL()
# 在短行里找 α
```

## 3. 截断 LSB/MSB 恢复

**识别**：已知 `x_i = r_i * α + β (mod p)` 的高位或低位。类似 HNP，构造格求 α,β。

## 4. knapsack / 背包

**识别**：求子集使其和 = 目标（超增背包或一般背包）。CJLOSS 格：
```sage
# 已知 a_i（权重），目标 S。求 e_i∈{0,1} 使 Σ e_i a_i = S
n = len(a)
M = Matrix(ZZ, n+1, n+1)
for i in range(n): M[i,i] = 1; M[i,n] = a[i]
M[n,n] = -S
# 加大缩放后 LLL
```

## 5. 通用构造原则

1. **未知的小量放短行**：把要恢复的小变量对应的列"不加缩放"或小缩放，已知大数列加大缩放。
2. **维度 = 变量数 + 约束数**，宁少勿多（维度大 LLL 慢且不稳）。
3. **缩放因子（weights）**：让目标行长度 ≈ 其它行长度，LLL 才会选它。常试 `K = 上界`、`K = √n` 等。
4. **验证**：LLL 出的每个短行都试解（除以倍数/换符号），用题目约束验证（如 `n % p == 0`）。

## 6. 决策

```
hint 形式含 p,q → §1
nonce/随机数部分泄漏（DSA/ECDSA） → HNP §2
已知乘积的高/低位 → §3
子集求和 → §4
其它线性隐含关系 → 通用构造 §5
```

## 注意

- **必须用 sage** `M.LLL()` / `M.BKZ()`；BKZ 更强但慢，LLL 失败时换 BKZ(block_size=20~30)。
- LLL 不出 → 调缩放/维度，别急着换攻击，可能只差一个 weight。
- 求出 p 后务必 `n % p == 0` 验证再解密。
