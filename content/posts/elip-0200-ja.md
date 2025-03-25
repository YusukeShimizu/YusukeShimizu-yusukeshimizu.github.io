---
date: '2025-03-24T16:56:49+09:00'
title: 'elip-0200'
---

ELIP 0200の日本語訳。Elements Improvement Proposals (ELIPs) は、BitcoinのBIPに相当するElementsプロジェクトの改善提案である。

この記事はllmによる機械翻訳に基づく。誤りの可能性がある点に留意すること。  
この内容はcommit hash  
[9f08b8168328691c1bff6e0261cebbe985f39ae4](https://github.com/ElementsProject/ELIPs/tree/9f08b8168328691c1bff6e0261cebbe985f39ae4)  
時点のリポジトリを参照している。

---

ELIP: 200  
Layer: Applications  
Title: Confidential Transactions の割引料金  
Author: Byron Hambly <bhambly@blockstream.com>  
Comments-Summary: まだコメントはない  
Comments-URI: https://github.com/ElementsProject/elips/wiki/Comments:ELIP-0200  
Status: Draft  
Type: Standards Track  
Created: 2024-06-19  
License: BSD-3-Clause  

## はじめに

### 概要

Confidential Transactions (CT) の取引手数料を割引する方法を提案する。これにより、ウォレットが割引手数料率を算出可能になり、ノードが割引されたCTをリレー・採掘するための要件を定義する。

### Copyright

本書は3条項BSDライセンスの下で公開している。

### Motivation

ElementsにおけるCTは、明示的な取引よりサイズが約10倍大きい。  
Pedersenコミットメントやアセットコミットメント、ECDHエフェメラルキーなどが追加され、さらにレンジプルーフとサージェクションプルーフを含むウィットネスデータが大きな要因である。  
サイズが大きいほど手数料が高くなるため、ユーザがCTによるプライバシーを犠牲にし、明示的な取引を選びやすくなる可能性がある。  
このELIPは、ElementsでCTを割引料金で受け入れるポリシー変更を提案し、CTと明示的な取引を同等の手数料規模に近づけ、明示的取引優先の動機を下げる。

## Design

### Overview

新たに「discount virtual size (discountvsize)」を導入する。  
明示的な取引では通常のvsizeと実質同じ値となるが、CTでは秘密出力が含まれるたびに、各出力分の重みを仮想サイズ計算の前に減少させる。

ウォレットは、この割引計算を用いて手数料を推定し、ノードはメンプールへの受け入れやピアへのメッセージングでdiscountvsizeを利用する。これによってCT取引の中継と採掘が行われる。

### 欠点

ディスカウントを導入すると、実際のコストは表面上の手数料率より低くなる。  
既存のブロックアセンブラは先祖手数料率が高い取引から優先するため、割引CTは同じ「表面料金率」の明示的トランザクションなどより選択が遅れる。  
この状態を解消するには、ブロックアセンブラ側で割引された仮想サイズを基準に手数料率を扱うよう変更が必要だが、最大料金追求よりCTのプライバシー優先を許容するというトレードオフとなる。

### 仕様

#### ウォレット

ウォレットは通常の手順で取引を作成し、まずプレースホルダーの手数料出力を含める。  
ダミー署名を埋め込んだ後、BIP-0141[^1] に従い以下の式で重みを算出する:
  
Weight = (Base transaction size * 3) + Total transaction size

- Base transaction sizeはウィットネスを除いたサイズ  
- Total transaction sizeはBIP-0144[^2]に準拠し、ベースデータとウィットネスデータをすべて含むサイズ

次に、割引ウエイトを計算する。出力ウィットネスがある場合はウィットネスを差し引き、2ウエイト単位のみを残す形で計上する。さらに、金額がコミットメントの場合は33バイトと明示額の9バイト差を非ウィットデータとして4倍し、96単位を減算する。ノンスがコミットメントなら同じ要領で128単位を減算する。

最終的に:

discountvsize = (discount weight + 3) / 4

これを使い:

手数料出力額 = chosen fee rate * discountvsize

手数料出力自体は割引計算対象外とする。  

##### 計算例

LiquidV1[^3] のトランザクション例:  

- CT出力が2つ、手数料出力が1つ  
- 重み: 10536 WU  

以下のステップでディスカウント重みへ変換する:  
1. 1つ目の出力ウィットネス (4277) - 2 = 4275 を差し引く  
   10536 - 4275 = 6261  
2. 金額コミットメント 96 を差し引き  
   6261 - 96 = 6165  
3. ノンスコミットメント 128 を差し引き  
   6165 - 128 = 6037  
4. 2つ目の出力ウィットネス (4277) - 2 = 4275 を差し引く  
   6037 - 4275 = 1762  
5. 金額コミットメント 96 を差し引き  
   1762 - 96 = 1666  
6. ノンスコミットメント 128 を差し引き  
   1666 - 128 = 1538  

割引後の重み: 1538 WU    
discountvsize = (1538 + 3) / 4 = 385 vB  

#### ノード

ノードは新たなオプション "accept_discount_ct" を通して、ディスカウントCTのリレーを許可するかを決定する。  
有効化すると、ミンプールの受け入れ判断やピアのフィルタ料金率計算でvsizeの代わりにdiscountvsizeを使用する。  
さらにはブロックテンプレートアセンブラも、手数料率計算をdiscountvsizeベースに変更する必要がある。

## 後方互換性

LiquidV1では、任意の手数料率や手数料出力なし取引もコンセンサス的には有効である。  
既存のElementsの最低手数料率(0.1 sats/vb)下では、割引CTはアップグレードされていないノードのリレー基準を満たさない。  
ただし、アップグレード済みノード経由でマイナーノードへ到達できればブロックに取り込まれる。  
アップグレードノードが増えると、現実的にリレーが広がる。

## 参照実装

<https://github.com/ElementsProject/elements/pull/1317>

## 代替実装

<https://github.com/ElementsProject/rust-elements/pull/204>

## 参考文献

<references />

[^1]: BIP-0141  
    <https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki>  
    #Transaction_size_calculations

[^2]: BIP-0144  
    <https://github.com/bitcoin/bips/blob/master/bip-0144.mediawiki>  
    #user-content-Serialization

[^3]: <https://blockstream.info/liquid/tx/221c8a8bb81d1e33f3b6556ec9eb10815469ff02fd4bb4dd5127442eaa16d988>
