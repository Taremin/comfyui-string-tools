import pytest
import time
from playwright.sync_api import Page, expect

def test_list_nodes_do_not_have_dynamic_text_sockets(page: Page, comfyui_server: str, wait_for_comfyui):
    """
    List系ノード（ConcateList, RandomChoiceList, BalancedChoiceList）において、
    接続後も text_0, text_1 といった不要な動的ソケットが生成されないことを検証する。
    """
    page.goto(comfyui_server)
    wait_for_comfyui(page)

    nodes_to_test = [
        "StringToolsConcatList",
        "StringToolsRandomChoiceList",
        "StringToolsBalancedChoiceList"
    ]

    for node_type in nodes_to_test:
        print(f"Testing node type: {node_type}")
        input_count = page.evaluate(f'''(type) => {{
            app.graph.clear();
            const node = LiteGraph.createNode(type);
            app.graph.add(node);
            
            const stringNode = LiteGraph.createNode("StringToolsString");
            app.graph.add(stringNode);
            
            // ポート接続を試みる（BalancedChoiceListの場合は slot 0: seed, slot 1: text_list）
            // ポート名を検索して接続する
            let targetSlot = -1;
            for(let i=0; i < node.inputs.length; i++) {{
                if(node.inputs[i].name === "text_list") {{
                    targetSlot = i;
                    break;
                }}
            }}
            
            if (targetSlot === -1) throw new Error("text_list input not found for " + type);

            stringNode.connect(0, node, targetSlot);
            
            // onConnectionsChange を明示的に呼んでJS側のフックをトリガーする
            if (node.onConnectionsChange) {{
                node.onConnectionsChange(1, targetSlot, true, null, node.inputs[targetSlot]);
            }}

            // 入力ポートの一覧を返す
            return node.inputs.map(i => i.name);
        }}''', node_type)

        print(f"Inputs for {node_type}: {input_count}")
        
        # text_0 や text_1 が含まれていないことを確認
        assert "text_0" not in input_count, f"Node {node_type} should not have text_0 socket"
        assert "text_1" not in input_count, f"Node {node_type} should not have text_1 socket"
        # かつ、text_list が維持されていることを確認
        assert "text_list" in input_count, f"Node {node_type} should maintain text_list socket"

if __name__ == "__main__":
    # 手動実行用
    pass
