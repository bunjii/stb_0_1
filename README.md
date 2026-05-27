# Structural Toolbox (Linux メモ)

## 今回の不具合の原因（要点）

- 症状は `vtkXOpenGLRenderWindow ... failed to get the converted tmp` と `BadWindow` で即終了。
- 本質的な原因は、wxGTK 環境で `wxVTKRenderWindowInteractor` が使う `GetHandle()` の値が、VTK が期待する X11 Window ID (XID) ではなかったこと。
- その結果、VTK 側でウィンドウ ID の解釈に失敗し、無効な Window に対して X11 操作が走ってクラッシュしていた。

## どう直したか

1. Wayland セッション上でも、VTK の埋め込み描画は X11 (XWayland) を使うようにした。
2. `GetHandle()` ではなく `GetGtkWidget()` から GTK/GDK 経由で実際の X11 XID を取得するパッチを適用した。
3. `main_frame.py` で Wayland セッション時に `GDK_BACKEND=x11` を強制セットした。

## 重要: Wayland をやめる必要はあるか？

**不要です。**

- デスクトップ環境全体を X11 セッションに戻す必要はありません。
- いまの修正は「Wayland セッションのまま、当該アプリだけ X11 バックエンドで動かす」方式です。
- つまり普段の Fedora/Wayland 利用を維持したまま、このアプリだけ安全に動かせます。

## 通常起動

```bash
cd /home/bunjii/Dropbox/98_codes/stb_0_1
.venv/bin/python main_frame.py
```

## デバッグ起動（必要なときだけ）

```bash
cd /home/bunjii/Dropbox/98_codes/stb_0_1
STB_WXVTK_DEBUG=1 .venv/bin/python main_frame.py
```

期待されるデバッグログ例:

- `[stb wxvtk] widget 0x...(wxPizza) -> XID 0xe...`

## 補足（切替オプション）

- 既定は Wayland セッション時に `GDK_BACKEND=x11` を強制。
- 明示的に Wayland のまま試したい場合のみ `STB_ALLOW_WAYLAND=1` を指定。
  （ただし埋め込み VTK は再び失敗する可能性が高い）
