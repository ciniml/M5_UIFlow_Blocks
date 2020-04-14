# SORACOM 3G ブロック

## 概要

SORACOMコンソールから購入できる [M5Stack用 3G拡張ボード](https://soracom.jp/products/kit/3g_module_m5stack/) をUI Flowから使用するカスタム･ブロック (非公式)

ソラコムおよびスイッチサイエンス `非公式` ブロックですので、ソラコムやスイッチサイエンスに問い合わせたりしないでください。

## 使い方

1. `gsm.mpy` をUI FlowのResource Managerからデバイスにダウンロードします。
2. UI FlowのCustom (beta)の下にある`open *.m5b file`から、soracom3g.m5bを開きます。
3. ブロックを使います。

## ブロックの説明

### 3G startブロック

3G拡張ボードを初期化して、通信処理を開始します。


### 3G wait connectionブロック

3G拡張ボードがネットワークに接続するまで待ちます。

### 3G disconnect WLAN

3G通信を使ってインターネット接続を行うため、無線LANを無効化します。

### 3G IP address

3G回線に割り当てられたIPアドレスを取得します。

### 3G ifconfig

3G回線に割り当てられたネットワーク情報を取得します。
`(ip, netmask, gateway, dns)` の4-pleを返します。

## サンプル

[examples/3g](../../examples/3g) が3G拡張ボード用のサンプルコードです。

## ライセンス
gsm.pyはBoost Software Licenseですので、ソースコード上にライセンス表記が残ってさえ居ればコピーして使って構いません。
