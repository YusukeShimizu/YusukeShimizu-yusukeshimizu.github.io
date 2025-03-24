---
date: '2025-03-22T08:56:49+09:00'
title: 'bip-0119'
---

BIP 119の日本語訳をおいておく。

この記事は、llmにより翻訳されたものであり、内容に誤りがある可能性はある。  
BIP 119は、新しいオペコード OP_CHECKTEMPLATEVERIFY を有効化することを提案しており、このブログを書いた段階で、有力な選択肢となっている。  
[Developer Consensus May Be Converging on a Bitcoin Soft Fork Proposal: Blockspace](https://www.coindesk.com/tech/2025/03/17/developer-consensus-may-be-converging-on-a-bitcoin-soft-fork-proposal-blockspace)

なお、この記事は、commit hash[88c0fb9b5b7c3ed73386224c8c4ae0fd4fc3537f](https://github.com/bitcoin/bips/blob/88c0fb9b5b7c3ed73386224c8c4ae0fd4fc3537f/bip-0119.mediawiki) 時点のものとなっている。

- [Abstract](#abstract)
- [Summary](#summary)
- [Motivation](#motivation)
- [Detailed Specification](#detailed-specification)
- [デプロイ](#デプロイ)
- [参考実装](#参考実装)
- [根拠](#根拠)
    - [The DefaultCheckTemplateVerifyHash of the transaction at the current input index matches the top of the stack](#the-defaultchecktemplateverifyhash-of-the-transaction-at-the-current-input-index-matches-the-top-of-the-stack)
      - [Committing to the version and locktime](#committing-to-the-version-and-locktime)
      - [Committing to the ScriptSigs Hash](#committing-to-the-scriptsigs-hash)
      - [インプット数へのコミット](#インプット数へのコミット)
      - [シーケンスハッシュへのコミット](#シーケンスハッシュへのコミット)
      - [アウトプット数へのコミット](#アウトプット数へのコミット)
      - [アウトプットハッシュへのコミット](#アウトプットハッシュへのコミット)
      - [現在のインプットのインデックスへのコミット](#現在のインプットのインデックスへのコミット)
      - [Committing to Values by Hash](#committing-to-values-by-hash)
      - [Using SHA256](#using-sha256)
      - [Using Non-Tagged Hashes](#using-non-tagged-hashes)
      - [The Ordering of Fields](#the-ordering-of-fields)
  - [設計上のトレードオフとリスク](#設計上のトレードオフとリスク)
    - [Denial of Service and Validation Costs](#denial-of-service-and-validation-costs)
    - [永久に使用できない出力](#永久に使用できない出力)
    - [転送アドレス](#転送アドレス)
    - [NOP-Default and Recommended Standardness Rules](#nop-default-and-recommended-standardness-rules)
    - [機能の冗長性](#機能の冗長性)
    - [将来的なアップグレード](#将来的なアップグレード)
      - [CHECKTEMPLATEVERIFY バージョン](#checktemplateverify-バージョン)
      - [OP\_CHECKSIGFROMSTACKVERIFY](#op_checksigfromstackverify)
      - [OP\_AMOUNTVERIFY](#op_amountverify)
      - [OP\_CAT/OP\_SHA256STREAM](#op_catop_sha256stream)
- [Backwards Compatibility](#backwards-compatibility)
- [スクリプト互換性](#スクリプト互換性)
- [References](#references)
  - [類似した代替案について](#類似した代替案について)
- [著作権](#著作権)


---

BIP: 119  
Layer: Consensus (soft fork)  
Title: CHECKTEMPLATEVERIFY  
Author: Jeremy Rubin <j@rubin.io>  
Comments-URI: https://github.com/bitcoin/bips/wiki/Comments:BIP-0119  
Status: Draft  
Type: Standards Track  
Created: 2020-01-06  
License: BSD-3-Clause

## Abstract

この BIP は、新しいオペコード OP_CHECKTEMPLATEVERIFY を有効化することを提案しており、OP_NOP4 のセマンティクスを変更する形で適用されます。

## Summary

OP_CHECKTEMPLATEVERIFY は、オペコード OP_NOP4 (0xb3) をソフトフォークによるアップグレードとして使用します。

OP_CHECKTEMPLATEVERIFY は次のような処理を行います：

- スタック上に少なくとも 1 つの要素がある。ない場合は失敗。  
- スタック上の要素が 32 バイト長である。そうでなければ NOP。  
- 現在の入力インデックスにあるトランザクションの DefaultCheckTemplateVerifyHash がスタック上の要素と等しい。そうでなければ失敗。

DefaultCheckTemplateVerifyHash はシリアライズされたバージョン、locktime、scriptSigs ハッシュ (もし非 null の scriptSigs がある場合)、インプット数、sequences ハッシュ、アウトプット数、アウトプット ハッシュ、そして現在実行中の入力インデックスにコミットします。

推奨される標準性ルールとしてさらに：

- 32 バイト以外は SCRIPT_ERR_DISCOURAGE_UPGRADABLE_NOPS として拒否。

## Motivation

この BIP は、トランザクションテンプレートを導入します。これは、ハッシュ化されたトランザクション仕様に対してパターンマッチすることで簡易的な支出制限を実現するものです。OP_CHECKTEMPLATEVERIFY は、アプリケーションで事前署名を使用する際に内在する信頼・対話性・ストレージ要件を大きく削減します。アプリケーションの詳細についてはリファレンスを参照してください。

## Detailed Specification

以下のコードは、CHECKTEMPLATEVERIFY を検証するメインロジックを示したもので、Python 風の擬似コードで記述しています。OP_CHECKTEMPLATEVERIFY の仕様としての正準的な定義は、Bitcoin Core の文脈で C++ で実装されたリファレンス実装を参照してください。

The execution of the opcode is as follows:

```python
def execute_bip_119(self):
    # Before soft-fork activation / failed activation
    # continue to treat as NOP4
    if not self.flags.script_verify_default_check_template_verify_hash:
        # Potentially set for node-local policy to discourage premature use
        if self.flags.script_verify_discourage_upgradable_nops:
            return self.errors_with(errors.script_err_discourage_upgradable_nops)
        return self.return_as_nop()

    # CTV always requires at least one stack argument
    if len(self.stack) < 1:
        return self.errors_with(errors.script_err_invalid_stack_operation)

    # CTV only verifies the hash against a 32 byte argument
    if len(self.stack[-1]) == 32:
        # Ensure the precomputed data required for anti-DoS is available,
        # or cache it on first use
        if self.context.precomputed_ctv_data == None:
            self.context.precomputed_ctv_data = self.context.tx.get_default_check_template_precomputed_data()

        # If the hashes do not match, return error
        if stack[-1] != self.context.tx.get_default_check_template_hash(self.context.nIn, self.context.precomputed_ctv_data):
            return self.errors_with(errors.script_err_template_mismatch)

        return self.return_as_nop()

    # future upgrade can add semantics for this opcode with different length args
    # so discourage use when applicable
    if self.flags.script_verify_discourage_upgradable_nops:
        return self.errors_with(errors.script_err_discourage_upgradable_nops)
    else:
        return self.return_as_nop()
```

このハッシュの計算は、以下に示すように実装できます (ここで self はトランザクション型を指します)。どのような検証コンテキストでも、事前計算されたデータが初期化されていないとサービス妨害攻撃を招く可能性があるため注意が必要です。任意の実装は、二次元的なハッシュ計算による DoS を回避するために、これらのハッシュ計算部分をキャッシュしなければなりません。scriptsig、sequence、アウトプットなど可変長のすべての計算は事前計算を行う必要があります。詳細は「Denial of Service and Validation Costs」を参照してください。これは性能最適化ではありません。

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

# parameter precomputed must be passed in for DoS resistance
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

A PayToBareDefaultCheckTemplateVerifyHash output matches the following template:

```python
# Extra-fast test for pay-to-basic-standard-template CScripts:
def is_pay_to_bare_default_check_template_verify_hash(self):
    return len(self) == 34 and self[0] == 0x20 and self[-1] == OP_CHECKTEMPLATEVERIFY
```

## デプロイ

この BIP からはアクティベーションロジックが省略されており、より適切な場所で議論されることが望ましいです。

BIP-119 が ACTIVE 状態に到達し、かつ SCRIPT_VERIFY_DEFAULT_CHECK_TEMPLATE_VERIFY_HASH フラグが施行されるまでは、ノード実装は （推奨される場合）NOP4 を実行するとして SCRIPT_ERR_DISCOURAGE_UPGRADABLE_NOPS (to deny entry to the mempool) によるポリシーを適用し、コンセンサス (during block validation). では NOP として評価されなければなりません。

CHECKTEMPLATEVERIFY を利用しやすくするため、a の一般的なケースとして scriptSig データを持たない PayToBareDefaultCheckTemplateVerifyHash が （推奨） スタンダード化されてリレーを許可するかもしれません。将来的にベアスクリプトは実装者の方針によるポリシー変更で標準化される可能性があります。

## 参考実装

リファレンス実装とテストはこちらの Bitcoin Core への PR で利用できます  
<https://github.com/bitcoin/bitcoin/pull/21702>。

PR へのリンクはリベースや変更が行われる可能性があるため理想的ではありませんが、現在の実装や他者のレビューコメントを見つけるには最適な場所です。テストやベクタを含む最近のコミットハッシュはこちらにあります  
<https://github.com/jeremyrubin/bitcoin/commit/3109df5616796282786706738994a5b97b8a5a38>。PR がマージされたら、この BIP はリリースされたコードを指すように更新すべきです。

テストベクタは \[/bip-0119/vectors the bip-0119/vectors directory\] にあり、リファレンス実装や BIP との互換性チェックに使用できます。

## 根拠

OP_CHECKTEMPLATEVERIFY の設計はコードの変更点が少なく、解析が容易です。より複雑で安全性が実証可能なユースケースが必要になった場合に、新しいテンプレートタイプとの互換性もあります。

以下ではルールを一つずつ説明します。

#### The DefaultCheckTemplateVerifyHash of the transaction at the current input index matches the top of the stack

コミットされるデータの集合は、トランザクションの TXID に影響を与える可能性があるデータのスーパーセットで、入力以外も含みます。これは、既知の入力がある場合に TXID をあらかじめ把握できるようにするためです。そうでなければ、CHECKTEMPLATEVERIFY はバッチ処理によるチャネル作成の構造では使用できません。これは、リデンプションの TXID が改変されて、事前署名されたトランザクションが無効化されてしまうからです。ただし、チャネルが LN-Symmetry のようなプロトコルで構築されている場合は別です。

ここで注意すべきは、事前署名されたコントラクトには、LN-Symmetry のようなものを利用できる場合と利用できない場合があることです。したがって、TXID を予測可能にしておくことで CTV は任意のサブプロトコルとより柔軟に組み合わせられるようになります。

##### Committing to the version and locktime

これらの値がコミットされていない場合、出力を恣意的に遅らせることが可能になるほか、TXID を変更することも可能になります。

これらの値を特定の値に制限するのではなくコミットすることは、CHECKTEMPLATEVERIFY の利用者がバージョンとロックタイムを自由に設定できるため、より柔軟です。

##### Committing to the ScriptSigs Hash

segwit トランザクションの scriptsig は完全に空でなければいけません。ただし、P2SH segwit トランザクションの場合は、正確な redeemscript のみ含んでいなければいけません。P2SH は (P2SH ハッシュが破られていない限り) CHECKTEMPLATEVERIFY とは互換性がありません。なぜならテンプレートハッシュが ScriptSig にコミットする必要があり、そこに含まれる redeemscript がハッシュサイクルとなるためです。

segwit インプットを使用しない場合のマリアビリティを防ぐためにも、scriptsig にコミットします。これによりレガシーの事前署名済み支出を 2 インプットの CHECKTEMPLATEVERIFY で使うことが可能になりますが、それにはレガシー出力の正確な scriptsig をコミットしておく必要があります。これは単に CHECKTEMPLATEVERIFY で設定する任意の scriptSig を不許可にするよりも堅牢です。

トランザクションに scriptSig が設定されていない場合、そのデータをハッシュしたり DefaultCheckTemplateVerifyHash に含めたりする意味はないため、省略します。segwit はマリアビリティを回避するために scriptSig を空にする必要があるので、scriptSig が設定されないことは一般的であると考えられます。

私たちは値そのものではなくハッシュにコミットしますが、これはすでに各トランザクションに対して事前に計算されており、SIGHASH_ALL シグネチャを最適化するためです。

さらに、ハッシュにコミットすることで、DefaultCheckTemplateVerifyHash をスクリプトから安全かつ明確に構築しやすくなります。

##### インプット数へのコミット

トランザクションで複数のインプットが使われることを許可すると、同じ出力のセットに対して 2 つの出力が支払いを要求できてしまい、意図した支払いの半分が破棄されてしまう「half-spend」問題が生じます。

さらに、どのインプットを同時に消費できるかの制限は、安定した TXID が必須となるペイメントチャネル構造において非常に重要です (アップデート時にはインプットのあらゆる組み合わせに署名する必要があります)。

しかし、複数のインプットを許可することには正当なユースケースもあります。例えば：

スクリプトパス：  
```
Path A: <+24 hours> OP_CHECKSEQUENCEVERIFY OP_CHECKTEMPLATEVERIFY <Pay Alice 1 Bitcoin (1 input) nLockTime for +24 hours>
Path B: OP_CHECKTEMPLATEVERIFY <Pay Bob 2 Bitcoin (2 inputs)>
```

この場合、出力には 24 時間があり、第二の出力を追加することで、Bob に 2 BTC を支払うことができます。もし 24 時間が経過した場合、Alice は契約から 1 BTC をリデームできます。どちらのインプット UTXO も同じ Path B を使用することも、片方のみが使用することも可能です。

これらの構成における問題は、インプットが並べられる順序が N! 通り存在し、その並び順を一般的な方法で制限することができない点です。

CHECKTEMPLATEVERIFY は、ユーザが消費されるインプットの正確な数を保証できるようにします。一般的に、CHECKTEMPLATEVERIFY を複数のインプットで使用するのは難しく、微妙な問題を引き起こす可能性があるため、特定のアプリケーション以外では複数インプットは使うべきではありません。

原則として、下記の Sequences Hash にコミットすることで、間接的にインプット数にもコミットされ、このフィールドは厳密には冗長になります。しかし、この数を個別にコミットすることで、スクリプトから DefaultCheckTemplateVerifyHash を構築しやすくなります。

私たちはインプットの数を `uint32_t` として扱いますが、これは Bitcoin のコンセンサスのデコードロジックがベクターを `MAX_SIZE=33554432` に制限しており、これは `uint16_t` より大きく、`uint32_t` より小さい値です。32 ビットは Bitcoin の現在の算術オペコードで操作するのにも適しています。もし `OP_CAT` が追加されればそれも可能です。なお、ブロック内の最大インプット数はブロックサイズによって約 25,000 に制限されており、`uint16_t` に収まりますが、それは不要な抽象化の漏洩です。

##### シーケンスハッシュへのコミット

シーケンスにコミットしない場合、TXID が改ざんされる可能性があります。これにより、相対的なシーケンスロックを OP_CSV を使用せずに適用できます。OP_CSV だけでは不十分です。なぜなら、OP_CSV はリテラルな値ではなく、nSequence の最小値を強制するだけだからです。

私たちは値そのものではなくハッシュにコミットします。これは各トランザクションごとに SIGHASH_ALL シグネチャを最適化するためにあらかじめ計算されているからです。ハッシュにコミットすることで、スクリプトから DefaultCheckTemplateVerifyHash を安全かつ明確に構築しやすくなります。

##### アウトプット数へのコミット

原則として、Outputs Hash (below) にコミットすることはアウトプット数にも暗黙的にコミットすることになり、このフィールドを厳密には冗長にします。しかし、この数に個別にコミットすると、スクリプトから DefaultCheckTemplateVerifyHash を構築しやすくなります。

アウトプットの数は `COutpoint` のインデックスが `uint32_t` であるため、`uint32_t` として扱います。さらに、Bitcoin のコンセンサスのデコードロジックではベクターを `MAX_SIZE=33554432` に制限しており、これは `uint16_t` より大きく、`uint32_t` より小さい値です。32 ビットはまた、Bitcoin の現在の数値オペコードを使用した操作にも適しており、`OP_CAT` が追加された場合にも対応しやすいです。

##### アウトプットハッシュへのコミット

これにより、UTXO を使用するときに要求されたとおりのアウトプットを確実に作成できるようになります。

私たちは、値そのものではなくハッシュにコミットします。これは、各トランザクションであらかじめ計算されており、SIGHASH_ALL シグネチャを最適化するために利用できるからです。ハッシュにコミットすることで、スクリプトから DefaultCheckTemplateVerifyHash を安全かつ明確に構築しやすくなります。

##### 現在のインプットのインデックスへのコミット

現在実行中のインプットのインデックスにコミットすることは、厳密には改ざん耐性のために必要というわけではありません。しかし、これによってインプットの順序が制限され、プロトコル設計者にとっての改ざん可能性の要因を排除できます。

しかし、インデックスにコミットすることでハーフスペンド問題におけるキー再利用の脆弱性がなくなります。CHECKTEMPLATEVERIFY スクリプトは特定のインデックスで使用されるようコミットされるため、これらのスクリプトを再利用しても同じインデックスでは使用できません。つまり、同じトランザクションで使用することはできないことになります。これにより、ハーフスペンドの脆弱性がないウォレットボルト契約を設計しやすくなります。

現在のインデックスにコミットしても、複数のインデックスで使用可能な CHECKTEMPLATEVERIFY を表現することは妨げません。現在のスクリプトでは、CHECKTEMPLATEVERIFY オペレーションは各インデックスに対して OP_IF (または将来的には Tapscript のブランチ) でラップすることができます。もし OP_CAT または OP_SHA256STREAM が Bitcoin に追加される場合は、インデックスはハッシュ化の前に witness によって単純に渡される可能性があります。

##### Committing to Values by Hash

値をハッシュでコミットすることにより、スクリプトから DefaultCheckTemplateVerifyHash を構築することがより簡単かつ効率的になります。設定する予定のないフィールドは、再ハッシュの際に O(n) のオーバーヘッドが発生することなく、ハッシュでコミットすることができます。

さらに、将来的に OP_SHA256STREAM が追加される場合、スクリプト上でハッシュのミッドステートにコミットすることで、O(n) のオーバーヘッドを発生させずに単一の出力を出力のリストに追加できるスクリプトを書くことが可能になるかもしれません。

##### Using SHA256

SHA256 は 32 バイトのハッシュで、Bitcoin のセキュリティ標準を満たしており、テンプレートプログラムをプログラム的に作成するためにすでに Bitcoin Script 内で利用できます。

RIPEMD160 は 20 バイトのハッシュで、一部の文脈では有効なハッシュとなり得るだけでなく、いくつかの利点があります。手数料の効率面では、RIPEMD160 は 12 バイトを節約できます。しかし、RIPEMD160 は BIP-119 のためには選ばれませんでした。これは、サードパーティによって作成されるプログラムの検証に、トランザクションのプリイメージに対する [birthday-attack <https://bitcoin.stackexchange.com/questions/54841/birthday-attack-on-p2sh>] のリスクをもたらすためです。

##### Using Non-Tagged Hashes

Taproot/Schnorr BIPs は Tagged Hashes ( `SHA256(SHA256(tag)||SHA256(tag)||msg)` ) を使用します。これは、taproot のリーフ、ブランチ、ツイーク、および署名が重複してセキュリティ上の [vulnerability <https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2018-June/016091.html>] を引き起こすのを防ぐためです。

OP_CHECKTEMPLATEVERIFY はこの種の脆弱性の影響を受けません。これらのハッシュは事実上外部でタグ付けされているので、つまり、OP_CHECKTEMPLATEVERIFY 自体によってタグが付与されているため、別のハッシュと混同されることはありません。

それをタグ付きハッシュにすることは、慎重な設計上の判断になるでしょう。たとえ明白な利点やコストがなかったとしてもです。しかし、将来的に OP_CAT が Bitcoin に導入された場合、動的に OP_CHECKTEMPLATEVERIFY ハッシュを組み立てるプログラムは空間効率が悪くなるでしょう。そのため、BIP-119 ではタグなしのハッシュが使われています。

##### The Ordering of Fields

厳密にいえば、フィールドの順序は重要ではありません。しかし、注意して選択された順序を用いることで、将来のスクリプト (e.g., OP_CAT や OP_SHA256STREAM を使うもの) の効率が向上する可能性があります (as described in the Future Upgrades section).

特に、この順序は変更される可能性が低いものから高いものへと並ぶように選択されています。

1. nVersion  
2. nLockTime  
3. scriptSig hash (maybe!)  
4. input count  
5. sequences hash  
6. output count  
7. outputs hash  
8. input index  

いくつかのフィールドはめったに変更されないです。nVersion はめったに変更されないはずです。nLockTime は通常 0 に固定するべきです (in the case of a payment tree, only the *first* lock time is needed to prevent fee-sniping the root)。scriptSig hash は通常まったく設定しないほうがいいです。

与えられた input count に対して可能な sequences hash が多数存在するため、input count は sequences hash の前に置かれます。与えられた out count に対して可能な outputs hash が多数存在するため、output count は outputs hash の前に置かれます。

通常、単一の入力から複数の出力を行う設計を使用しているため、inputs ハッシュよりも outputs ハッシュを変更する可能性が高いです。CHECKTEMPLATEVERIFY script では通常、入力が 1 つだけなので、input index を最後のフィールドにするのは意味がないように思えるかもしれません。しかし、「don't care」インデックスを簡単に表現できることの有用性 (e.g., for decentralized kickstarter-type transactions) を考えると、この値は最後に配置されています。

### 設計上のトレードオフとリスク

CHECKTEMPLATEVERIFY の設計はスクリプトの作成者を比較的厳密なテンプレート マッチングに制限します。CHECKTEMPLATEVERIFY テンプレートの構造は、入力を除いて、トランザクションの詳細の大部分を構築時に正確に把握しておく必要があります。

CHECKTEMPLATEVERIFY は入れ子にできます――つまり、あるトランザクションは created by spending an output with a `<H> OP_CHECKTEMPLATEVERIFY` の制限がかかったアウトプットを使って支払うことで作成されると、`<X> OP_CHECKTEMPLATEVERIFY` の制限がかかったアウトプットを新たに作成できます。

この拡張は本質的に有限です。なぜなら、`<H>` のハッシュを含むスクリプトを備えたアウトプットを、`<H>` のハッシュを持つアウトプットを使用して支払うトランザクションから再生成すると、ハッシュ サイクルが生じるからです。これは、各テンプレート ハッシュ `<H>` が、途切れなく続く可能性のある `OP_CHECKTEMPLATEVERIFY` 検証トランザクションの最も長い連鎖に対応する「path height」を持ち、その path height が厳密に減少する、と捉えられます。

さらに、テンプレートは特定の数のインプットとしてのみ支払えるように制限され、特定のインプット インデックスでのみ使用できるため、意図しない『half spend』問題の導入を防ぎます。

これほど制限されているテンプレートにも、いくつかのリスクが伴います。

#### Denial of Service and Validation Costs

CTV は DoS を発生させることなく非常に低コストで検証できるように設計されています。これは、あらかじめ計算されたハッシュをチェックするか、(some of which may be cached from more expensive computations) 固定長の引数をハッシュ化することで実現できます。

特に、CTV はクライアントがハッシュの計算をキャッシュすることを要求します。すべての scriptSig、sequence、および output に対して計算されるハッシュです。CTV 以前は、scriptSig のハッシュは必須ではありませんでした。CTV は非空の scriptSig をハッシュ化する必要がありますが、これは scriptSig のハッシュ処理の一部として扱うことができます。

したがって、コンセンサス中に CTV のハッシュを評価する場合のコストは、常に O(1) です。これはキャッシュが利用できる場合に限り成立する計算です。これらのキャッシュは通常、CHECKSIG の動作に関連する類似の問題のために必要となります。キャッシュの計算は O(T) (the size of the transaction) です。

キャッシュを行わない場合に DoS 問題が発生する可能性があるスクリプトの例は以下のとおりです：

```
CTV CTV CTV... CTV
```

このようなスクリプトによって、インタープリタは (supposing N CTV's) の場合に O(N*T) のデータに対してハッシュを計算することになります。もし scriptSigs の非ヌル性がキャッシュされていない場合は、O(T) のトランザクションが O(N) 回走査される可能性もあります (although cheaper than hashing, still a DoS)。したがって、CTV はハッシュをキャッシュします。そしてトランザクション内のすべての可変長フィールドに対する計算結果もキャッシュします。

CTV（CheckTemplateVerify）において、サービス拒否（DoS）のリスクと検証コストは比較的明確です。実装者は、既存のキャッシュを活用し、CTVに新たに導入されるscriptSig上での計算をキャッシュするよう適切にコードを書く必要があります。より柔軟な提案では、より複雑なテンプレート計算がキャッシュしにくく、二乗的なハッシュ計算の問題を引き起こす可能性があるため、DoS問題への対処がより難しくなるでしょう。これは、柔軟性を犠牲にして低コストかつ安全な検証を優先するというCTVのトレードオフです。たとえば、もしCTVでビットマスクを利用して一部の出力のみをハッシュできるようにした場合、すべての出力パターンをキャッシュすることは不可能となり、二乗的ハッシュ計算によるDoSの脆弱性を引き起こすでしょう。

#### 永久に使用できない出力

CHECKTEMPLATEVERIFY に渡されるプレイメージ引数は、不明であるか、または満たせない可能性があります。しかし、アドレスが使用可能であるという知識を要求するのは、送信者が任意のアドレス (特に OP_RETURN) に支払える能力と両立しません。もし送信者がテンプレートが送信前に使用可能かどうかを知る必要がある場合は、CHECKTEMPLATEVERIFY ツリーのリーフから、非トランザクションであることが証明可能なチャレンジ文字列への署名を要求できます。

#### 転送アドレス

CHECKTEMPLATEVERIFY によるキーの再利用は、「forwarding address contract」の一形態として利用できます。転送アドレスとは、あらかじめ定義された方法で自動的に実行されるアドレスです。たとえば、ある取引所のホットウォレットは、そのアドレスを用いて、相対的なタイムアウト後にコールドストレージアドレスへ自動的に資金を移動できるようにすることができます。

この方法でアドレスを再利用すると資金を失う可能性があるという問題があります。1 BTC をコールドストレージに転送するテンプレートアドレスを作成すると仮定します。コールドストレージに転送するとします。このアドレスに 1 BTC 未満を送ろうとすると永久に凍結されます。1 BTC を超える金額を支払った場合、1 BTC を超える分は大きなマイナー手数料として支払われます。

CHECKTEMPLATEVERIFY は、入力によって提供される正確な bitcoin の額にコミットすることができるはずですが、これは利用者の誤りであって可鍛性の問題ではないため行われていません。将来的なソフトフォークでは、どのテンプレートやスクリプトのブランチをトランザクションに利用可能な資金の額を調べて判断できるような opcode を導入できる可能性があります。

一般的なベストプラクティスとして、Bitcoin の利用者はそのアドレスが意図した支払いに適切であると確信できない限り、いかなるアドレスも再利用しないようにする必要があります。この制限とリスクは CHECKTEMPLATEVERIFY に特有のものではありません。たとえば、atomic swap スクリプトは単一使用で、ハッシュが公開されると一度しか使用できません。将来の Taproot スクリプトには、多くの論理ブランチが含まれる可能性があり、それらは複数回使用すると安全でない（例として、Hash Time Lock ブランチはユニークなハッシュでインスタンス化する必要があります）。SIGHASH_ANYPREVOUT に署名した鍵もまた、再利用が危険になる可能性があります。

CHECKTEMPLATEVERIFY は、現在消費されている入力のインデックスにコミットしているため、再利用された鍵は必ず別々のトランザクションで実行され、「half-spend」タイプの問題のリスクを低減します。

#### NOP-Default and Recommended Standardness Rules

引数の長さが正確に 32 でない場合、CHECKTEMPLATEVERIFY はこれをコンセンサス検証時には NOP として扱います。実装では非コンセンサスの中継やメモリプール検証において、そのような状況下では失敗するようにすることが推奨されます。特に、無効な長さの引数を失敗にすることで将来のソフトフォークのアップグレードが、より厳しい標準的な制限に依存しながら、安全に標準性に関する制限を緩和できるようにしつつ、アップグレードのルールによってコンセンサスをより強化できるよう支援します。

標準性ルールは、悪意のあるスクリプト開発者が合意形成（consensus）時により厳格な標準性ルールが適用されると誤認してしまう恐れがあります。そのような開発者が標準性の拒否をあてにしてトランザクションをネットワークに直接送信した場合、標準性の観点では無効である一方、合意形成の観点では有効なトランザクションが作られ、資金を失うリスクにつながる可能性があります。

#### 機能の冗長性

There are other opcodes that, if implemented, could make the CHECKTEMPLATEVERIFY の機能を冗長にする可能性があります。しかし、CHECKTEMPLATEVERIFY はシンプルな意味論とオンチェーンコストの低さから、たとえほかの機能と重複しても依然として好まれる可能性が高いです。

また、OP_VAULTやOP_CHECKCONTRACTVERIFY、OP_TXHASHなどのオペコードの場合、OP_CHECKTEMPLATEVERIFYは提案されている現在の実装の一部となっています。

より強力なオペコードとして、MES16で提案されているOP_COVやOP_TXHASHなどが挙げられます。これらは、外部的なchild-pays-for-parentやトランザクションスポンサーなどの手数料支払いメカニズムに依存するのではなく、内生的に手数料を支払う能力を高めるという点でいくつかの利点をもたらします。しかし、これらの機能は大幅に複雑性を増大させ、アプリケーション開発者が想定していない振る舞いが生じる可能性があります。

あるいは、SIGHASH_ANYPREVOUTANYSCRIPTを使用して、以下のようにscriptPubKeyを設定することでテンプレートに類似したものを実装することが可能です:  
```
<sig of desired TX with PK and fixed nonce R || SIGHASH_ANYPREVOUTANYSCRIPT <PK with public SK>> OP_CHECKSIG
```

上記のSIGHASH_ANYPREVOUTANYSCRIPTの機能はCHECKTEMPLATEVERIFYが提供するものに近いです。大きな違いとして、OP_CHECKTEMPLATEVERIFYは追加入力の数を制限し、動的に決定されるおつりの出力を認めない一方で、SIGHASH_ANYPREVOUTANYSCRIPTはSIGHASH_SINGLEやSIGHASH_ANYONECANPAYと組み合わせることができます。

さらに、OP_CHECKTEMPLATEVERIFYはscriptsigやsequenceにもコミットできるため、特定のP2SHスクリプト（またはsegwit v0 P2SH）を指定することができ、いくつかのユースケースで役立ちます。

加えて、CHECKTEMPLATEVERIFYにはスクリプトサイズの面での利点があります。（PKの選択にもよりますが、SIGHASH_ANYPREVOUTANYSCRIPTでは約2倍から3倍のバイト数を使用する場合があります。）また、署名操作ではなくハッシュ計算のみで済むため、検証速度の点でも有利です。これは大規模なペイメントツリーやプログラム的なコンパイルを構築する際に重要となる場合があります。さらに、CHECKTEMPLATEVERIFYには、将来的なテンプレートのアップグレードに対応する堅牢な道筋を提供するという機能的メリットもあり、これはOP_TXHASHでも提案されています。

OP_CHECKSIGFROMSTACKVERIFY と OP_CAT は、CHECKTEMPLATEVERIFY をエミュレートするためにも使用できます。しかし、そのような構成はアプリケーションスクリプトでの実装がCHECKTEMPLATEVERIFY よりも複雑になり、CHECKTEMPLATEVERIFY には存在しない追加の検証オーバーヘッドを伴います。

このアプローチは実装や分析が容易ですし、ユーザアプリケーションで得られるメリットもあるため、CHECKTEMPLATEVERIFY の単一テンプレートベースのアプローチは、スクリプトでトランザクションを指定するための汎用的なシステムの代わりに提案されています。

#### 将来的なアップグレード

このセクションでは、将来的に考えられる OP_CHECKTEMPLATEVERIFY へのアップデートおよび、他の可能なアップグレードとのシナジーについて説明します。

##### CHECKTEMPLATEVERIFY バージョン

OP_CHECKTEMPLATEVERIFY は現在、32 バイトの引数の特性のみを検証します。将来的には、他の長さの引数にも意味を持たせることができます。たとえば、33 バイトの引数では、最後のバイトだけをコントロールプログラムとして利用できます。その場合、DefaultCheckTemplateVerifyHash はフラグバイトが CTVHASH_ALL に設定されている場合に計算されます。他のプログラムもSIGHASH_TYPE と同様に追加できます。たとえば、CTVHASH_GROUP はSIGHASH_GROUP との互換性のために Taproot Annex からデータを読み取り、どのインデックスがバンドルのためにハッシュされるかを動的に変更できるようにするなど、可能にします。

OP_TXHASH のプレ BIP で行われた作業は、OP_CHECKTEMPLATEVERIFY のセマンティクスを拡張するための 1 つのアプローチの詳細が示されています。

##### OP_CHECKSIGFROMSTACKVERIFY

OP_CHECKTEMPLATEVERIFY と OP_CHECKSIGFROMSTACKVERIFY の両方が Bitcoin に追加された場合、LN-Symmetry のフローティングトランザクションのバリアントを次のスクリプトで実装できるようになります:
```
witness(S+n): <sig> <H(tx with nLockTime S+n paying to program(S+n))>
program(S): OP_CHECKTEMPLATEVERIFY <musig_key(pk_update_a, pk_update_b)> OP_CHECKSIGFROMSTACKVERIFY <S+1> OP_CHECKLOCKTIMEVERIFY
```

SIGHASH_ANYPREVOUTANYSCRIPT と比較すると、OP_CHECKTEMPLATEVERIFY は SIGHASH_ANYONECANPAY や SIGHASH_SINGLE に類する機能を許可していないため、プロトコル実装者は手数料を支払うため、Ephemeral Anchors や追加の Inputs を使ってトランザクションに署名するか、あるいはトランザクションスポンサーなどを検討するかもしれません。

##### OP_AMOUNTVERIFY

トランザクションで消費される正確な金額や、手数料として支払われる金額、特定の出力で使用可能になる金額を検証するオペコードは、より安全な OP_CHECKTEMPLATEVERIFY アドレスを実現するために利用できる可能性があります。たとえば、OP_CHECKTEMPLATEVERIFY のプログラム P がちょうど S satoshi を想定している場合、S-1 satoshi を送ると UTXO が凍結され、S+n satoshi を送ると n satoshi が手数料として支払われます。範囲チェックを行うことで、特定の値にのみプログラムを適用し、それ以外の場合はキー経路にフォールバックするように制限できるかもしれません。例：

```
IF OP_AMOUNTVERIFY <N> OP_GREATER <PK> CHECKSIG
ELSE <H> OP_CHECKTEMPLATEVERIFY
```

##### OP_CAT/OP_SHA256STREAM

OP_CHECKTEMPLATEVERIFY は (as described in the Ordering of Fields section) Bitcoin が拡張されたデータ操作オペコードを得た場合に、スクリプトからトランザクションを動的に指定するために効率的です。

たとえば、以下のコードは入力インデックスの引数をチェックし、それをテンプレートに連結して、トランザクションがテンプレートに合致しているかを確認します。

```
OP_SIZE 4 OP_EQUALVERIFY
<nVersion || nLockTime || input count || sequences hash || output count || outputs hash>
OP_SWAP OP_CAT OP_SHA256 OP_CHECKTEMPLATEVERIFY
```

なお、OP_CAT に例えば 520 バイトのサイズ制限が導入された場合、スクリプトの種類にもよりますが、12 個の入力と 12 個の出力を持つトランザクションを検査することしかできなくなります。

## Backwards Compatibility

OP_CHECKTEMPLATEVERIFY は、より厳格な検証セマンティクスをもつ形で OP_NOP4 を置き換えます。そのため、以前は有効だったスクリプトは、この変更によって無効になる場合があります。OP_NOP に対してより厳格な検証セマンティクスを導入することはソフトフォークであり、既存のソフトウェアはマイニングやブロック検証を除いてアップグレードなしでも完全に機能します。OP_CHECKSEQUENCEVERIFY と OP_CHECKLOCKTIMEVERIFY (see BIP-0065 と BIP-0112) も同様に、互換性の問題を起こすことなく OP_NOP のセマンティクスを変更してきました。

これまでのフォークとは対照的に、OP_CHECKTEMPLATEVERIFY のリファレンス実装では、それを使用する支出スクリプトを含むトランザクションが 新しいルールがアクティブになるまで標準ポリシーの下でメモリプールに受理されたり中継されたりしません。他の実装にもこのルールに従うことが推奨されていますが、必須ではありません。

古いウォレットソフトウェアは、OP_CHECKTEMPLATEVERIFY アウトプットからの支払いを受け付けられますが、確定済みの先祖を持つ PayToBareDefaultCheckTemplateVerifyHash チェーンを「信頼済み」(つまり、トランザクションが承認される前に支出可能 であるもの)として扱うにはアップグレードが必要になります。

OP_CHECKTEMPLATEVERIFY のバックポートは (リファレンス実装を参照) 古いノードバージョン向けに簡単に用意できますが、それらはパッチ適用はできても新しいメジャーリリースへのアップグレードはできません。

## スクリプト互換性

OP_CHECKTEMPLATEVERIFY はすべてのスクリプトバージョンで利用可能です。アプリケーション開発者は、scriptSig でプログラムが露出する P2SH および P2SH Segwit では、scriptSig 内でプログラムが公開されるこれらの場合、プログラム内で`<H> CTV` のようなフラグメントを使用できません。scriptSig のコミットメントがハッシュサイクルを引き起こすためです。

## References

- [utxos.org 情報サイト](https://utxos.org)  
- [covenants.info 情報サイト](https://covenants.info)  
- [Sapio ビットコイン スマートコントラクト言語](https://learn.sapio-lang.org)  
- [27 Blog Posts on building smart contracts with Sapio and CTV, including examples described here.](https://rubin.io/advent21)  
- [Scaling Bitcoin Presentation](https://www.youtube.com/watch?v=YxsjdIl0034&t=2451)  
- [Optech Newsletter Covering OP_CHECKOUTPUTSHASHVERIFY](https://bitcoinops.org/en/newsletters/2019/05/29/)  
- [Structuring Multi Transaction Contracts in Bitcoin](https://cyber.stanford.edu/sites/g/files/sbiybj9936/f/jeremyrubin.pdf)  
- [Lazuli Notes (ECDSA based N-of-N Signatures for Certified Post-Dated UTXOs)](https://github.com/jeremyrubin/lazuli)  
- [Bitcoin Covenants](https://fc16.ifca.ai/bitcoin/papers/MES16.pdf)  
- [CoinCovenants using SCIP signatures, an amusingly bad idea.](https://bitcointalk.org/index.php?topic=278122.0)  
- [Enhancing Bitcoin Transactions with Covenants](https://fc17.ifca.ai/bitcoin/papers/bitcoin17-final28.pdf)  
- [Simple CTV Vaults](https://github.com/jamesob/simple-ctv-vault)  
- [Python Vaults](https://github.com/kanzure/python-vaults)  
- [CTV Dramatically Improves DLCs](https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2022-January/019808.html)  
- [Calculus of Covenants](https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2022-April/020225.html)  
- [Payment Pools with CTV](https://rubin.io/bitcoin/2021/12/10/advent-13/)  
- [Channels with CTV](https://rubin.io/bitcoin/2021/12/11/advent-14/)  
- [Congestion Control with CTV](https://rubin.io/bitcoin/2021/12/09/advent-12/)  
- [Building Vaults on Bitcoin](https://rubin.io/bitcoin/2021/12/07/advent-10/)  
- [(Ark Labs) Ark Documentation](https://arkdev.info/)  
- [(Second) Ark Documentation](https://docs.second.tech/protocol/intro/)  
- [SpookChains](https://rubin.io/bitcoin/2022/09/14/drivechain-apo/)  
- [OP_TXHASH](https://github.com/bitcoin/bips/pull/1500)

### 類似した代替案について

CHECKTEMPLATEVERIFY の以前のバージョンである CHECKOUTPUTSHASHVERIFY は CHECKTEMPLATEVERIFY を優先するために取り下げられました。CHECKOUTPUTSHASHVERIFY はバージョンやロックタイムにコミットしていなかったため、安全ではありませんでした。

CHECKTEMPLATEVERIFY は Taproot への拡張として実装することも可能で、これまでもこの方法で提案されていました。ただし、特定のアプリケーションは bare legacy スクリプトで OP_CHECKTEMPLATEVERIFY を使用して効率を最大化したい場合があります。

CHECKTEMPLATEVERIFY は以前に次の名称でも呼ばれていました OP_SECURETHEBAG として言及されており、ここではこの BIP に関する検索や議論を参照するのに役立てるために記載しています。

## 著作権

このドキュメントは 3-clause BSD license の下でライセンスされています。
