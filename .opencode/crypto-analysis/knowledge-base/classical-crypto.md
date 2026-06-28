# 古典密码

> 何时用：凯撒/移位、维吉尼亚、单表替换、无密钥古典、字母频率类。多数不需 sage，纯 Python + 频率分析。

## 1. 识别类型

| 密文特征 | 类型 |
|----------|------|
| 全字母，保持空格，看着像英文 | 凯撒/单表替换 |
| 均匀字母分布、无明显单词 | 维吉尼亚（多表） |
| 含数字/符号、按位置变换 | 其它（培根/Playfair/Hill/Affine） |
| Base64/32/58/85 | 编码（非密码），先解码再看 |
| 二进制/十六进制串 | 先转 bytes 再判 |

> **先做编码识别**：很多"密码"其实是 Base 系列编码或 ROT，先试解码。

## 2. 凯撒（移位，26 种）

```python
def caesar(s,k): return ''.join(chr((ord(c)-65+k)%26+65) if c.isalpha() else c for c in s.upper())
# 暴力 1~25，看哪个像英文
for k in range(26):
    print(k, caesar(ct,k))
```

## 3. ROT13 / ROT47

```python
import codecs
codecs.decode(ct, 'rot_13')
# ROT47 处理 ASCII 33-126
def rot47(s): return ''.join(chr(33+(ord(c)-33+47)%94) if 33<=ord(c)<=126 else c for c in s)
```

## 4. 维吉尼亚（Vigenère）

**破解流程**：
1. Kasiski / 重合指数（IC）求密钥长度 k。
2. 按 k 分组，每组做凯撒（频率分析）。

```python
# 重合指数判定密钥长度
def ic(s):
    from collections import Counter
    cnt = Counter(s); n = len(s)
    return sum(c*(c-1) for c in cnt.values()) / (n*(n-1))
# 英文 IC ≈ 0.0667；随机 ≈ 0.038。对每个候选长度 k，分组算 IC 接近 0.0667 即密钥长
```
分好组后每组用频率分析（最常见字母映射到 E/T/A）。

工具：`pycipher`、在线 dcode.fr。

## 5. 单表替换

- 频率分析（字母 + 双字母 bigram/trigram）。
- 词模式匹配（已知明文样式时）。
- 工具：quipqiup.com、`substitution` 库。

## 6. 培根（Bacon，5-bit）

每 5 个符号一组，A/B 二选一 → 二进制 → 字母。常隐藏在两种字体/大小写里。

## 7. Playfair / Hill / Affine / Rail-Fence

| 类型 | 特征 | 解法 |
|------|------|------|
| Playfair | 双字母组、无 J | 字典/已知明文还原 5x5 |
| Hill | 矩阵加密、mod 26 | 求逆矩阵（mod 26） |
| Affine | `c=(a*m+b)%26` | 已知明文求 a,b |
| Rail-Fence | 按行重排 | 试栏数 |

## 8. 通用工具

- **CyberChef**（本地无则 webfetch 查用法，或用 Python 实现）：Base/ROT/古典全覆盖。
- **dcode.fr**：识别 + 解多种古典。
- Python：`pycipher` 库。

## 决策

```
看着像编码（Base/HEX）？ → 先解码
单表、字频像英文？ → 凯撒/替换/频率
多表、IC≈0.038？ → 维吉尼亚
两种符号混排？ → 培根/摩尔斯
按位置重排？ → Rail-Fence/列置换
```

## 注意

- CTF flag 可能藏在古典密码解码后的"中间结果"里（题目故意多套一层）。
- 密文含非字母符号常是有意线索（如分隔符指示分组）。
- 不要忽视题目给的 hint（题目名、描述常暗示密码类型）。
