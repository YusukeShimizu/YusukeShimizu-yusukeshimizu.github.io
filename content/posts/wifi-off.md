---
date: '2025-03-21T08:56:49+09:00'
title: 'Wifi Off'
---

Wi-Fiを強制的にオフにすべきである。ネットからの通知やチャットへの意識を一掃し、思考を乱す要因を遮断できるからである。プログラミングや文章作成など、深い集中が必要な作業では特に有効である。

Wi-Fiを切る前に必要資料をあらかじめ開いておくことが望ましい。ネット接続が必要な箇所は作業後にまとめて調べるべきである。スクリプトを用いれば、一定時間オフにしたまま強制的に待機できる。たとえばmacOSでは、以下のワンライナーが使える。

```bash
networksetup -setairportpower en0 off && sleep 1800 && \
networksetup -setairportpower en0 on && \
osascript -e 'display notification "WiFiが復活しました" with title "通知"'
```

資料を読み込み、作業に没頭し、後で必要部分のみ確認すればよい。緊急の連絡が想定される場合は注意が必要だが、そうでないならオフラインで集中すべきである。この手法によってフロー状態を維持しやすくなり、結果的に作業効率が上がると断言できる。

または、私の実装したcliを使えば、より高度に設定することができる  
https://github.com/YusukeShimizu/rust-pomo

```sh
rust-pomo --focus 1200 --break-time 600 --cycles 2
=== Cycle 1/2: Focus time ===
Setting WiFi off
Starting timer for 1200 seconds...
[####################--------------------] 594s / 1200s                                                                                                 
```