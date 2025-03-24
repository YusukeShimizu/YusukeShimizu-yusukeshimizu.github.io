---
date: '2025-03-24T13:21:13+09:00'
title: 'CTV Template Hash詳細'
---

templateはなにが可変であり、なにが固定なのか、を整理する。  
様々な場所に情報があるが、BIPに記されたpython codeを見るのが一番良い。  

```python
def ser_compact_size(l):
    r = b""
    if l < 253:
        # Serialize as unsigned char
        r = struct.pack("B", l)
    elif l < 0x10000:
        # Serialize as unsigned char 253 followed by unsigned 2 byte integer (little endian)
        r = struct.pack("<BH", 253, l)
    elif l < 0x100000000:
        # Serialize as unsigned char 254 followed by unsigned 4 byte integer (little endian)
        r = struct.pack("<BI", 254, l)
    else:
        # Serialize as unsigned char 255 followed by unsigned 8 byte integer (little endian)
        r = struct.pack("<BQ", 255, l)
    return r

def ser_string(s):
    return ser_compact_size(len(s)) + s

class CTxOut:
    def serialize(self):
        r = b""
        # serialize as signed 8 byte integer (little endian)
        r += struct.pack("<q", self.nValue)
        r += ser_string(self.scriptPubKey)
        return r

def get_default_check_template_precomputed_data(self):
    result = {}
    # If there are no scriptSigs we do not need to precompute a hash
    if any(inp.scriptSig for inp in self.vin):
        result["scriptSigs"] = sha256(b"".join(ser_string(inp.scriptSig) for inp in self.vin))
    # The same value is also pre-computed for and defined in BIP-341 and can be shared.
    # each nSequence is packed as 4 byte unsigned integer (little endian)
    result["sequences"] = sha256(b"".join(struct.pack("<I", inp.nSequence) for inp in self.vin))
    # The same value is also pre-computed for and defined in BIP-341 and can be shared
    # See class CTxOut above for details.
    result["outputs"] = sha256(b"".join(out.serialize() for out in self.vout))
    return result

parameter precomputed must be passed in for DoS resistance
def get_default_check_template_hash(self, nIn, precomputed = None):
    if precomputed == None:
        precomputed = self.get_default_check_template_precomputed_data()
    r = b""
    # Serialize as 4 byte signed integer (little endian)
    r += struct.pack("<i", self.nVersion)
    # Serialize as 4 byte unsigned integer (little endian)
    r += struct.pack("<I", self.nLockTime)
    # we do not include the hash in the case where there is no
    # scriptSigs
    if "scriptSigs" in precomputed:
        r += precomputed["scriptSigs"]
    # Serialize as 4 byte unsigned integer (little endian)
    r += struct.pack("<I", len(self.vin))
    r += precomputed["sequences"]
    # Serialize as 4 byte unsigned integer (little endian)
    r += struct.pack("<I", len(self.vout))
    r += precomputed["outputs"]
    # Serialize as 4 byte unsigned integer (little endian)
    r += struct.pack("<I", nIn)
    return sha256(r)
```

OP_CHECKTEMPLATEVERIFY（OP_CTV）は「将来使われるトランザクションの形をあらかじめ決めておき、そこから外れる支払いを無効とする」仕組みを提供する。したがって、意図しない送金や改ざんを防ぎながら、VaultやChannel Factoryのような特定用途の“Covenant”機能をシンプルかつ安全に実装できる。

---

## 1. OP_CTVの基本的な動作

OP_CTVは「スクリプト内でコミットしたテンプレート（トランザクションのひな型）と、実際のトランザクションのハッシュが一致するか」を検証する。テンプレートと一致しなければコインは使えない。これにより、次回消費される形式を厳密に制約し、想定外のパラメータを排除できる。

1. テンプレートには、送金先アドレスや金額（nValue）、トランザクションバージョン、LockTime、入力数などを含める。  
2. テンプレートと異なる要素を含んだトランザクションは無効となる。

---

## 2. コード例が示すテンプレートハッシュ計算

`get_default_check_template_precomputed_data()`と`get_default_check_template_hash()`が含まれる。これらはトランザクションを構成する主要部分をハッシュ化した“テンプレートハッシュ”を生成する。

1. `get_default_check_template_precomputed_data()`  
   各入力のscriptSigやsequence、出力一覧（vout）のserializedデータなどを個別にSHA-256でハッシュ化し、その結果をまとめて返す。

2. `get_default_check_template_hash()`  
   バージョンやLockTime、入力数、出力数などの情報と先ほどの部分的ハッシュを組み合わせ、最終的なテンプレートハッシュを生成する。OP_CTVはスクリプト実行時、このテンプレートハッシュとトランザクションの実体が一致するかをチェックする。

---

## 3. OP_CTVの柔軟性と制約

### 3.1 柔軟性
- **出力（vout）の完全固定**  
  送金先アドレスや金額が厳密に定義され、改ざんの余地をなくす。  
- **入力数やLockTimeなど特定パラメータも固定**  
  コミットした要素が変わるとハッシュが変化し、無効になる。将来のマルチシグや複数人の共同トランザクションでも、明確なテンプレートを用意すれば対応できる。

### 3.2 できること
- **VaultなどのCovenant機能**  
  コインをロックして将来の引き出し条件を限定するシナリオ（例: Vault）をシンプルに実装できる。  
- **複数参加者のチャネル構成**  
  将来の各出力パターンをテンプレート化し、決まったルール内でのみ協調取引できる。  
- **CPU負荷削減**  
  データの事前ハッシュ（プリコンピュート）によって、無駄な計算量を減らせる。

### 3.3 制約
- **複雑な条件分岐の難しさ**  
  OP_CTVは「テンプレート一致のチェック」のみを行う。分岐や動的ロジックを増やすには、複数ハッシュパスを用意するなどの工夫が必要である。  
- **テンプレート外の自由度の低下**  
  コミットされた内容以外での送金やロジックは通用しない。多様な将来計画を考慮するなら、複数のテンプレートを準備すべきである。  
- **管理と承認フローの煩雑化**  
  参加者が多いマルチパーティーでは、全員にとって想定されるパターンを事前にテンプレート化する必要があり、スクリプトサイズも増え得る。

---

## 4. まとめ

OP_CTVは、将来のトランザクションをテンプレートという形で厳密に固定し、セキュリティや改ざん防止を大きく強化する。一方で、複雑なロジックや高度な条件分岐には向かない。したがって、Vaultのような限定された用途には最適であるが、汎用的な拡張には別のアプローチも検討すべきである。提示コードが示すように、出力や各種フィールドをハッシュ化して照合する一連の手順によって、シンプルかつ強力なCovenant機能を実現できる。

OP_CHECKTEMPLATEVERIFY（以下、OP_CTV）は「**あらかじめ定義した特定のトランザクション形式（テンプレート）にしか支払いを許可しない**」という性質を持つ新しいOPコード案（BIP-119）です。ここでは提示されたコード片（`get_default_check_template_precomputed_data`や`get_default_check_template_hash` など）を例に、OP_CTV（BIP-119）の仕組みと「どこまで柔軟性があるか」について解説します。
