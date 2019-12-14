# 設定モジュールブロック

## 概要

Blocklyに記述したくない、パスワードのような設定情報を別のMicroPythonスクリプトに切り出して管理するためのブロック

## 使い方

1. `mycfg.template.py`を`mycfg.py`としてコピーします。
2. mycfg.pyのトップレベルに管理したい設定値を変数として定義します。
3. mycfg.pyをUI FlowのResource Managerでデバイスにダウンロードします。
4. UI FlowのCustom (beta)の下にある`open *.m5b file`から、myconfig.m5bを開きます。
5. Setupの直後くらいに`Load MyConfig`ブロックを起きます。
6. mycfg.pyに定義した設定値を使いたい部分に、`MyConfig value`ブロックを置いて、`name`パラメータに設定値の名前を指定します。

