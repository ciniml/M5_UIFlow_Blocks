# SORACOM 3G ブロック

## 概要

SORACOM 3GモジュールをUI Flowから使用するカスタム･ブロック (非公式)

ソラコムおよびスイッチサイエンス `非公式` ブロックですので、ソラコムやスイッチサイエンスに問い合わせたりしないでください。

## 使い方

1. `gsm.mpy` をUI FlowのResource Managerからデバイスにダウンロードします。
2. UI FlowのCustom (beta)の下にある`open *.m5b file`から、soracom3g.m5bを開きます。
3. ブロックを使います。

## ブロックの説明

### 3G startブロック

SORACOM 3Gモジュールを初期化して、通信処理を開始します。


### 3G wait connectionブロック

SORACOM 3Gモジュールがネットワークに接続するまで待ちます。

### 3G disconnect WLAN

3G通信を使ってインターネット接続を行うため、無線LANを無効化します。

### 3G IP address

3G回線に割り当てられたIPアドレスを取得します。

### 3G ifconfig

3G回線に割り当てられたネットワーク情報を取得します。
`(ip, netmask, gateway, dns)` の4-pleを返します。

## サンプル

[examples/3g](../../examples/3g) がSORACOM 3Gモジュール用のサンプルコードです。

## ライセンス
gsm.pyはBoost Software Licenseですので、ソースコード上にライセンス表記が残ってさえ居ればコピーして使って構いません。
