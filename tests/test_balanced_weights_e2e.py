import pytest
import time
import json
import requests
import sys
import os
from playwright.sync_api import Page, expect

# プロジェクトルートをパスに追加して __init__.py の関数をインポート可能にする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from __init__ import calculate_weights_from_prompt

def get_prompt_json(page: Page):
    """ブラウザ上の現在のグラフからプロンプトJSONを取得する"""
    return page.evaluate('''async () => {
        const p = await app.graphToPrompt();
        return p.output;
    }''')

def test_balanced_weights_hell_nesting_e2e(page: Page, comfyui_server: str, wait_for_comfyui):
    """
    真に複雑な「地獄のネスト」をUIで構築し、重み計算ロジックを統合検証する。
    構造:
    Main (BalancedChoice)
      - text_0: StringsToList (中間ノード)
          - text_0: RandomChoice [Leaf1, Leaf2] -> 計2
          - text_1: BalancedChoice [Leaf3, Leaf4, Leaf5] -> 計3
          - 合計: 5
      - text_1: BalancedChoiceList (text_list接続、Leaf6相当) -> 計1
      - text_2: String (Leaf7) -> 計1
    理論値: text_0: 5, text_1: 1, text_2: 1
    """
    page.goto(comfyui_server)
    wait_for_comfyui(page)

    page.evaluate('''() => {
        app.graph.clear();
        
        const createNode = (type, title = null) => {
            const node = LiteGraph.createNode(type);
            app.graph.add(node);
            if (title) node.title = title;
            return node;
        };

        const connect = (fromNode, fromSlot, toNode, toSlot) => {
            fromNode.connect(fromSlot, toNode, toSlot);
            if (toNode.onConnectionsChange) {
                // slotIndex は数値、isConnected は bool
                toNode.onConnectionsChange(1, toSlot, true, null, toNode.inputs[toSlot]);
            }
        };

        // --- Branch 0 (Weight 5) ---
        const toList = createNode("StringToolsStringsToList", "IntermediateList");
        
        const rc12 = createNode("StringToolsRandomChoice", "RC_12");
        const seedRC = createNode("StringToolsSeed");
        seedRC.widgets[0].value = 123;
        connect(seedRC, 0, rc12, 0);

        const l1 = createNode("StringToolsString", "L1");
        const l2 = createNode("StringToolsString", "L2");
        connect(l1, 0, rc12, 1);
        connect(l2, 0, rc12, 2);
        
        const bc345 = createNode("StringToolsBalancedChoice", "BC_345");
        const seedBC = createNode("StringToolsSeed");
        seedBC.widgets[0].value = 456;
        connect(seedBC, 0, bc345, 0);

        const l3 = createNode("StringToolsString", "L3");
        const l4 = createNode("StringToolsString", "L4");
        const l5 = createNode("StringToolsString", "L5");
        connect(l3, 0, bc345, 1);
        connect(l4, 0, bc345, 2);
        connect(l5, 0, bc345, 3);
        
        // StringsToList への接続 (text_0, text_1)
        connect(rc12, 0, toList, 0);
        connect(bc345, 0, toList, 1);
        window.bc345Id = bc345.id;

        // --- Branch 1 (Weight 1) ---
        const bcList = createNode("StringToolsBalancedChoiceList", "BC_List_Branch");
        window.bcListId = bcList.id;
        const seedList = createNode("StringToolsSeed");
        seedList.widgets[0].value = 789;
        connect(seedList, 0, bcList, 0);

        const l6 = createNode("StringToolsString", "L6");
        // BalancedChoiceList は text_list ポートを持つ (slot 1)
        connect(l6, 0, bcList, 1);

        // --- Branch 2 (Weight 1) ---
        const l7 = createNode("StringToolsString", "L7");

        // --- Main Choice ---
        const main = createNode("StringToolsBalancedChoice", "MainChoice");
        const seedMain = createNode("StringToolsSeed");
        seedMain.widgets[0].value = 999;
        connect(seedMain, 0, main, 0);
        
        // text_0, text_1, text_2 に接続
        connect(toList, 0, main, 1);
        connect(bcList, 0, main, 2);
        connect(l7, 0, main, 3);

        // Preview
        const preview = createNode("PreviewAny");
        connect(main, 0, preview, 0);

        window.mainNodeId = main.id;
        app.graph.setDirtyCanvas(true, true);
    }''')

    # UIが生成したプロンプトJSONを抽出
    prompt_json = get_prompt_json(page)
    main_node_id = str(page.evaluate("window.mainNodeId"))
    bc345_node_id = str(page.evaluate("window.bc345Id"))
    bclist_node_id = str(page.evaluate("window.bcListId"))
    
    # サーバー側のロジックにこのJSONを流し込む
    classes = ["StringToolsRandomChoice", "StringToolsBalancedChoice", "StringToolsRandomChoiceList", "StringToolsBalancedChoiceList"]
    
    # Mainノードの検証
    weights_main = calculate_weights_from_prompt(prompt_json, main_node_id, classes, "text")
    print(f"Main Weights: {weights_main}")
    assert weights_main == {"text_0": 5, "text_1": 1, "text_2": 1}

    # 中間ノード (BC_345) の検証
    weights_bc345 = calculate_weights_from_prompt(prompt_json, bc345_node_id, classes, "text")
    print(f"BC_345 Weights: {weights_bc345}")
    assert weights_bc345 == {"text_0": 1, "text_1": 1, "text_2": 1}

    # 中間ノード (BC_List_Branch) の検証
    weights_bclist = calculate_weights_from_prompt(prompt_json, bclist_node_id, classes, "text")
    print(f"BC_List Weights: {weights_bclist}")
    assert weights_bclist == {"text_list": 1}
    
    # 実際に応答が返ることも確認
    resp = requests.post(
        f"{comfyui_server}/prompt",
        json={
            "client_id": "test_client",
            "prompt": prompt_json
        },
        timeout=10
    )
    assert resp.status_code == 200
    print("E2E Hell Nesting Test Passed.")
