# ComfyUI String Tools

これは [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 用のカスタムノードです。
単純な文字列ノードである `StringToolsString` ノードと複数行の文字列ノードである `StringToolsText`、
複数のテキストを結合する `StringToolsConcat` ノードと、複数のテキストからランダムにひとつを選択する `StringToolsRandomChoice` ノードを提供します。

## なぜ単純なテキストノードをこのカスタムノードで提供しているのか

`StringToolsConcat` ノードと `StringToolsRandomChoice` ノードは文字列を受け付けますが、現状 `PrimitiveNode` は受け付けられません。
そこで単純な文字列ノードである `StringToolsString` と `StringToolsText` ノードを提供しています。

## 機能

### StringToolsConcat 

`separator` で `text_*` を結合します。
これらの入力はWidgetに変更することができません。

### StringToolsRandomChoice

`seed` で `text_*` の中からひとつ選択します。
これらの入力はWidgetに変更することができません。

## ライセンス

[MIT](./LICENSE)
