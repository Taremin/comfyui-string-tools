import pytest
import time
import json
import urllib.request
from playwright.sync_api import Page, expect

def get_latest_history(base_url: str):
    """ComfyUIのAPIから最新の実行履歴を取得する"""
    req = urllib.request.Request(f"{base_url}/history", method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if not data:
                return None
            latest_id = list(data.keys())[-1]
            return data[latest_id]
    except Exception as e:
        print(f"Failed to fetch history: {e}")
        return None

def run_prompt_and_wait(page: Page, comfyui_server: str, timeout=30):
    """
    app.graphToPrompt() を取得し、requests で POST して実行完了を待機する。
    """
    import requests
    # graphToPrompt を取得
    prompt_data = page.evaluate('''async () => {
        const p = await app.graphToPrompt();
        return { output: p.output, workflow: p.workflow };
    }''')
    
    # POST
    resp = requests.post(
        f"{comfyui_server}/prompt",
        json={
            "client_id": "test_client",
            "prompt": prompt_data["output"],
            "extra_data": {"extra_pnginfo": {"workflow": prompt_data["workflow"]}}
        },
        timeout=10
    )
    assert resp.status_code == 200, f"Prompt failed: {resp.text}"
        
    prompt_id = resp.json().get("prompt_id")
    assert prompt_id, "No prompt_id returned"
    
    # 完了待機
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(f"{comfyui_server}/history", timeout=5).json()
            if prompt_id in resp:
                return resp[prompt_id]
        except: pass
        time.sleep(0.5)
    
    raise TimeoutError("Prompt execution timed out")

def test_concat_no_separator_success(page: Page, comfyui_server: str, wait_for_comfyui):
    """
    StringToolsConcat ノードの separator が未接続の場合、エラーにならずに実行でき、空文字で結合されることを確認。
    """
    page.goto(comfyui_server)
    wait_for_comfyui(page)

    page.evaluate('''() => {
        app.graph.clear();
        const strA = LiteGraph.createNode("StringToolsString");
        app.graph.add(strA);
        strA.widgets[0].value = "Hello";
        
        const strB = LiteGraph.createNode("StringToolsString");
        app.graph.add(strB);
        strB.widgets[0].value = "World";
        
        const concat = LiteGraph.createNode("StringToolsConcat");
        app.graph.add(concat);
        
        // separator(Slot 0) は接続しない
        strA.connect(0, concat, 1);
        if (concat.onConnectionsChange) {
             concat.onConnectionsChange(1, 1, true, null, concat.inputs[1]);
        }
        strB.connect(0, concat, 2);
        if (concat.onConnectionsChange) {
             concat.onConnectionsChange(1, 2, true, null, concat.inputs[2]);
        }
        
        let preview = LiteGraph.createNode("PreviewAny");
        app.graph.add(preview);
        concat.connect(0, preview, 0);
        
        window.concatNodeId = concat.id;
        window.tgtNodeId = preview.id;
    }''')
    
    history = run_prompt_and_wait(page, comfyui_server)
    assert history is not None
    
    tgt_id = page.evaluate("window.tgtNodeId")
    outputs = history.get("outputs", {})
    assert str(tgt_id) in outputs
    
    output = outputs[str(tgt_id)]
    # PreviewAny の出力形式に合わせて text を取得
    out_str = str(output.get("text", output[0] if isinstance(output, list) else output))
    print(f"Concat No Separator Output: {out_str}")
    
    # デフォルトは空文字なので HelloWorld になるはず
    assert "HelloWorld" in out_str

def test_concat_list_no_separator_success(page: Page, comfyui_server: str, wait_for_comfyui):
    """
    StringToolsConcatList ノードの separator が未接続の場合、エラーにならずに実行でき、改行で結合されることを確認。
    """
    page.goto(comfyui_server)
    wait_for_comfyui(page)

    page.evaluate('''() => {
        if (!LiteGraph.getNodeType("StringToolsMockStringList")) {
            class MockStringList extends LiteGraph.LGraphNode {
                constructor() {
                    super();
                    this.addInput("str1", "STRING");
                    this.addInput("str2", "STRING");
                    this.addOutput("list", "STRING");
                    this.comfyClass = "StringToolsMockStringList";
                }
            }
            MockStringList.title = "MockStringList";
            MockStringList.comfyClass = "StringToolsMockStringList";
            LiteGraph.registerNodeType("StringToolsMockStringList", MockStringList);
        }
        app.graph.clear();
        
        const s1 = LiteGraph.createNode("StringToolsString");
        app.graph.add(s1);
        s1.widgets[0].value = "ABC";
        const s2 = LiteGraph.createNode("StringToolsString");
        app.graph.add(s2);
        s2.widgets[0].value = "DEF";
        
        const mock = LiteGraph.createNode("StringToolsMockStringList");
        app.graph.add(mock);
        s1.connect(0, mock, 0);
        s2.connect(0, mock, 1);
        
        const concatList = LiteGraph.createNode("StringToolsConcatList");
        app.graph.add(concatList);
        
        mock.connect(0, concatList, 0); // text_list
        // separator(Slot 1) は接続しない
        
        const preview = LiteGraph.createNode("PreviewAny");
        app.graph.add(preview);
        concatList.connect(0, preview, 0);
        
        window.tgtNodeId = preview.id;
    }''')
    
    history = run_prompt_and_wait(page, comfyui_server)
    assert history is not None
    
    tgt_id = page.evaluate("window.tgtNodeId")
    outputs = history.get("outputs", {})
    assert str(tgt_id) in outputs
    
    output = outputs[str(tgt_id)]
    out_str = str(output.get("text", output[0] if isinstance(output, list) else output))
    print(f"ConcatList No Separator Output: {out_str}")
    
    # デフォルトは改行なので ABC\nDEF になるはず
    assert "ABC" in out_str and "DEF" in out_str
    # ABCDEF ではなく改行を挟んでいるか
    assert "ABC" in out_str and "DEF" in out_str and "ABCDEF" not in out_str
