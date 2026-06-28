# 对称密码与哈希攻击

> 何时用：AES/DES 分组密码（CBC/ECB/CTR/GCM）、padding 报错、IV 可控；MD5/SHA 系列、长度扩展、MAC 伪造。

## 1. 分组密码模式速查

| 模式 | 特征 | 常见攻击 |
|------|------|---------|
| ECB | 相同明文→相同密文块、无 IV | 块模式识别、重排、codebook |
| CBC | `C_i = E(P_i ⊕ C_{i-1})`，IV 可控 | Padding Oracle、CBC bit flip、IV 重用 |
| CTR | 流式、nonce 重用致命 | Nonce 重用 → 明文 XOR |
| GCM | AEAD、nonce 重用致命 | Nonce 重用 → 恢复认证密钥 |

---

## 2. ECB

- **识别**：密文块重复出现、无 IV、图片加密后仍有图案。
- **攻击**：penguin 图还原、块字典（byte-at-a-time，当有加密 oracle 时）。

## 3. CBC Padding Oracle（PKCS7）

**识别**：解密 oracle 返回"padding 对/错"（或错误码不同、时序不同）。

**原理**：CBC 下修改 `C_{i-1}` 影响 `P_i`；逐字节调整使最后一块 padding 合法，反推 `P_i`。

**实现**：用 `python-paddingoracle` 库或手写：
```python
# 伪代码：对每块 C，逐字节从末尾求中间态
def attack_block(prev, block, oracle):
    inter = [0]*16
    for pad in range(1,17):
        for guess in range(256):
            forged = bytes([inter[i]^pad^(pad) for i in ...])  # 构造使末尾 = pad
            if oracle(prev=forged, c=block):  # padding 合法
                inter[-pad] = guess ^ pad
                break
    return bytes(inter[i]^prev[i] for i in range(16))   # 明文
```
工具：`paddingoracle`（pip）、pwntools 脚本模板。

## 4. CBC Bit Flip

**识别**：能修改密文，想改对应明文的某个字节（如 `admin=0` → `admin=1`）。

```python
# CBC: P_i = D(C_i) ⊕ C_{i-1}。改 C_{i-1}[k] 一个比特，P_i[k] 对应翻转
new_prev = bytes(prev[k] ^ ord(old) ^ ord(new) if k==idx else prev[k] for k in range(len(prev)))
```

## 5. Nonce/IV 重用（CTR/GCM/Stream）

**识别**：同一密钥流加密两段明文。
- CTR nonce 重用：`c1 ⊕ c2 = m1 ⊕ m2`，已知一段明文可解另一段。
- GCM nonce 重用：可恢复认证密钥 H，伪造 tag。

## 6. 哈希长度扩展

**识别**：`mac = hash(secret ∥ message)`，`hash` 是 MD5/SHA1/SHA256（Merkle-Damgård 结构），且能控制 message 末尾追加。

**攻击**：不知 secret，仅知其长度，即可算出 `hash(secret ∥ message ∥ padding ∥ append)`。

```python
# 用 hashpumpy 库
import hashpumpy
new_mac, new_msg = hashpumpy.hashpump(old_mac, original_msg, append_data, secret_len)
```
工具：`hashpumpy`、`hash_extender`。触发判据：构造 `key∥msg` 形 MAC + 服务端按此校验。

## 7. MD5/SHA1 碰撞

- MD5 碰撞：`hashclash`、`fastcoll`（造前缀碰撞）。
- SHA1：`shattered`。
- 用于构造两份同哈希不同内容（如 PDF / 证书）。

## 8. 弱随机/PRNG

| 类型 | 攻击 |
|------|------|
| `random`（Python，Mersenne） | 抓足够输出 → 反推状态（梅森旋转） |
| LCG | 解同余方程恢复 seed |
| LFSR | Berlekamp-Massey 恢复 |
| 时间戳 seed | 爆破时间窗口 |

```python
# Mersenne 恢复（已知 624 个 32-bit 输出）
from randcrack import RandCrack
rc = RandCrack()
for _ in range(624): rc.feed(next_output())
rc.predict_getrandbits(32)
```

## 决策

```
padding 报错差异？        → CBC Padding Oracle
能改密文/IV 控明文？      → CBC Bit Flip
nonce/IV 重用？           → 流密钥重用 / GCM 恢复
mac = hash(secret∥msg)？  → 长度扩展
弱 PRNG？                 → 状态恢复
ECB 块重复？              → ECB 模式利用
```

## 注意

- Padding Oracle 需大量请求，注意题目速率限制，必要时带 sleep/重连。
- 长度扩展要求知道 secret 长度，常需爆破长度。
- AES key/IV 常藏在题目脚本里（白盒），先读全脚本再判断哪段可控。
