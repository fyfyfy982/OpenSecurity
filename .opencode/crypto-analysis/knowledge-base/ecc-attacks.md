# 椭圆曲线（ECC）攻击

> 何时用：曲线方程 `y²=x³+ax+b (mod p)`、点加法、标量乘、求离散对数 `Q = kG` 求 k。**SageMath 强烈推荐**（点运算/离散对数内置）。

## sage 基础

```sage
p,a,b = ...
E = EllipticCurve(GF(p), [a,b])
G = E(xG,yG)
Q = E(xQ,yQ)
n = E.order()          # 曲线阶 #E(Fp)
# 直接求 k（阶小/光滑时可行）
k = discrete_log(Q, G, operation='+')
```

---

## 1. Smart（anomalous 曲线）

**识别**：`#E(Fp) == p`（阶恰好等于 p）。此时离散对数可在 O(1) 用 p-adic lift 求解。

```sage
def smart(p,a,b,G,Q):
    E = EllipticCurve(Qp(p,2), [a,b])   # p-adic 提升
    Gq = E.lift_x(ZZ(G.xy()[0]))
    Qq = E.lift_x(ZZ(Q.xy()[0]))
    # 取 formal logarithm
    plog_Q = ZZ(-Qq[1].log() + ...)
    plog_G = ZZ(-Gq[1].log() + ...)
    return plog_Q / plog_G % p
# 先检查 E.order() == p 再用
```
> 检查 `E.order() == p` 是触发 Smart 的判据。

## 2. MOV（嵌入度小）

**识别**：曲线的嵌入度 k 小（k = 使 p^k ≡ 1 mod n 的最小值）。把 ECDLP 归约到有限域 DLP。

```sage
# 把点映到 F_{p^k}，再用 finite field DLP
k = ... # 嵌入度
Fpk = GF(p^k, 'w')
E2 = EllipticCurve(Fpk, [a,b])
G2 = E2(G); Q2 = E2(Q)
# Weil pairing
T = E2.gens()[0]   # 阶 n 的点
w1 = G2.weil_pairing(T, n)
w2 = Q2.weil_pairing(T, n)
k = discrete_log(w2, w1)   # 有限域 DLP
```
> 触发判据：嵌入度小（计算 `n.divides(p^k - 1)` 找最小 k）。

## 3. Pohlig-Hellman（阶光滑）

**识别**：`n = #E` 分解成小素数乘积。discrete_log 可分解到各素数子群。

```sage
# sage 的 discrete_log 自动用 PH；或手动分解
print(factor(n))   # 若全是小素数
k = discrete_log(Q, G, n, operation='+')
```
> 若 n 含大素数因子，PH 无效；看是否 anomalous/MOV。

## 4. Invalid Curve（点不在曲线上）

**识别**：题目给的 G/Q 的 a,b 可能让点不在声明曲线上，或允许用不同 b 的曲线运算。

- 验证点在曲线上：`E(G)` 是否报错。
- 若 oracle 接受任意 b' 的点 → 用小阶曲线逐点恢复 k mod（各小阶）→ CRT 合成 k。

## 5. 其它快速判据

| 现象 | 攻击 |
|------|------|
| p 小 | 直接枚举 / baby-giant |
| n（阶）小 | 直接 `discrete_log` |
| a=0 或 b=0 特殊曲线 | 查该曲线已知弱点（如 supersingular → MOV） |
| 给了多条同结构曲线 | 可能利用同构/扭点 |

## 决策树

```
#E == p ?          → Smart
嵌入度小 ?         → MOV
#E 光滑 ?          → Pohlig-Hellman（discrete_log 直用）
点不在曲线上/oracle → Invalid Curve
否则              → baby-giant（阶不大）或看特殊结构
```

## 注意

- 先算 `E.order()` 和 `factor(n)`，这两步定方向。
- Smart 的 p-adic 实现细节多，用现成脚本调，验证 `k*G==Q`。
- sage 的 `discrete_log(Q, G, operation='+')` 已含 Pohlig-Hellman 与 BSGS，阶光滑或中等时直接用。
