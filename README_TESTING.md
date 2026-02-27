# E2Eテスト環境のセットアップと実行手順

本プロジェクトでは、`pytest` と `Playwright` を使用してE2Eテストを実行します。
テスト実行時には、指定したローカルのComfyUI環境を自動的に起動してテストを行います。

## 1. 動作環境の準備

テストの実行には、以下のPythonパッケージが必要です。
プロジェクトの仮想環境（または使用するPython環境）でインストールしてください。

```bash
pip install pytest pytest-playwright pytest-asyncio
playwright install chromium
```

## 2. テスト設定ファイルの作成

`tests/test_settings.json.example` をコピーして、同ディレクトリ内に `test_settings.json` を作成してください。
（※ `test_settings.json` はGitの管理対象外として設定されています。）

ご自身の環境に合わせて、以下のパスを絶対パスまたは相対パスで指定してください。

```json
{
    "comfyui_path": "C:/path/to/your/ComfyUI",
    "python_executable": "C:/path/to/your/ComfyUI/python_embeded/python.exe",
    "test_port": 9876
}
```

- **comfyui_path**: ComfyUI本体（`main.py` があるディレクトリ）へのパス。
- **python_executable**: ComfyUIを実行するためのPythonのパス（Stability Matrix等を利用している場合は、その内包Pythonのパス）。

## 3. テストの実行

ターミナルを開き、プロジェクトのルートディレクトリ（`f:\ComfyUI_custom_nodes\comfyui-string-tools`）で以下のコマンドを実行します。

```bash
# 基本的な実行
pytest tests/

# 動作を目視確認しながら実行する場合 (Playwrightのブラウザを表示)
pytest tests/ --headed

# 特定のファイルだけ実行する場合
pytest tests/test_string_tools.py
```
