# Wi-SUNモジュール・サンプル

## 概要

Wi-SUNブロックとMyConfigブロックを使って部屋のスマートメーターから消費電力を取得して、画面表示とアップロードを行うサンプル

## 使い方

1. `myconfig.template.py` をコピーして `mycfg.py` を作ります。
2. mycfg.pyの各設定値をコメントに従って入力します。
3. mycfg.pyをUI FlowのResource Managerでデバイスにダウンロードします。
4. `wisun.mpy` をUIFlowのResource Managerでデバイスにダウンロードします。
5. UI FlowのCustom (beta)の下にある`open *.m5b file`から、`blocks/wisun/WiSUN.m5b`と`blocks/mycfg/myconfig.m5b` を開きます。
6. UI Flowでwisun.m5fをロードします。

これでサンプル・プログラムは読み込めたはずなので、あとはデバイスにプログラムを転送して実行します。
