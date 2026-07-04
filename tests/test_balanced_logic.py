import pytest
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from __init__ import calculate_weights_from_prompt, StringToolsBalancedChoice, StringToolsBalancedChoiceList

@pytest.fixture
def reset_balanced_choice_state():
    """テストごとに内部状態をリセットするフィクスチャ"""
    StringToolsBalancedChoice.counts = {}
    StringToolsBalancedChoice.total_count = {}
    StringToolsBalancedChoiceList.counts = {}
    StringToolsBalancedChoiceList.total_count = {}
    yield

def test_calculate_weights_hell_nesting(reset_balanced_choice_state):
    """
    真に複雑な「地獄のネスト」構造のテスト。
    構造:
    Main (BalancedChoice)
      - text_0: StringToolsStringsToList (中間ノード)
          - text_0: RandomChoice
              - text_0: Leaf A
              - text_1: Leaf B
          - text_1: BalancedChoice
              - text_0: Leaf C
              - text_1: Leaf D
              - text_2: Leaf E
      - text_1: BalancedChoiceList
          - text_list: [接続なし、または外部からの単一値想定] -> 重み 1
      - text_2: StringToolsString (Leaf F)
    
    期待値計算:
      - text_0 branch: (RandomChoice: 2) + (BalancedChoice: 3) = 5
      - text_1 branch: BalancedChoiceList (単体) = 1
      - text_2 branch: StringToolsString (単体) = 1
    合計リーフ数 = 7
    Mainノードの重み = {"text_0": 5, "text_1": 1, "text_2": 1}
    """
    classes = ["StringToolsRandomChoice", "StringToolsBalancedChoice", "StringToolsRandomChoiceList", "StringToolsBalancedChoiceList"]
    
    prompt = {
        "main": {
            "class_type": "StringToolsBalancedChoice",
            "inputs": {
                "text_0": ["to_list", 0],
                "text_1": ["bc_list", 0],
                "text_2": ["leaf_f", 0]
            }
        },
        "to_list": {
            "class_type": "StringToolsStringsToList",
            "inputs": {
                "text_0": ["rc_abc", 0],
                "text_1": ["bc_de", 0]
            }
        },
        "rc_abc": {
            "class_type": "StringToolsRandomChoice",
            "inputs": {
                "text_0": ["leaf_a", 0],
                "text_1": ["leaf_b", 0]
            }
        },
        "bc_de": {
            "class_type": "StringToolsBalancedChoice",
            "inputs": {
                "text_0": ["leaf_c", 0],
                "text_1": ["leaf_d", 0],
                "text_2": ["leaf_e", 0]
            }
        },
        "bc_list": {
            "class_type": "StringToolsBalancedChoiceList",
            "inputs": {
                "text_list": "some_external_list" # 接続なし、リテラル入力
            }
        },
        "leaf_a": {"class_type": "StringToolsString", "inputs": {"string": "A"}},
        "leaf_b": {"class_type": "StringToolsString", "inputs": {"string": "B"}},
        "leaf_c": {"class_type": "StringToolsString", "inputs": {"string": "C"}},
        "leaf_d": {"class_type": "StringToolsString", "inputs": {"string": "D"}},
        "leaf_e": {"class_type": "StringToolsString", "inputs": {"string": "E"}},
        "leaf_f": {"class_type": "StringToolsString", "inputs": {"string": "F"}},
    }

    # Mainノードの検証 (5:1:1)
    weights_main = calculate_weights_from_prompt(prompt, "main", classes, "text")
    assert weights_main == {"text_0": 5, "text_1": 1, "text_2": 1}

    # 中間ノード (bc_de) の検証 (1:1:1)
    weights_bc_de = calculate_weights_from_prompt(prompt, "bc_de", classes, "text")
    assert weights_bc_de == {"text_0": 1, "text_1": 1, "text_2": 1}

    # 中間ノード (bc_list) の検証 (1)
    weights_bc_list = calculate_weights_from_prompt(prompt, "bc_list", classes, "text")
    assert weights_bc_list == {"text_list": 1}

def test_calculate_weights_unconnected_and_unknown(reset_balanced_choice_state):
    """未接続ポートや未知のノードが混在する場合の検証"""
    classes = ["StringToolsRandomChoice", "StringToolsBalancedChoice"]
    prompt = {
        "node1": {
            "class_type": "StringToolsBalancedChoice",
            "inputs": {
                "text_0": ["unknown_node", 0], # 未知のクラス
                "text_1": None,                # 未接続
                "text_2": ["valid_bc", 0]
            }
        },
        "unknown_node": {"class_type": "SomeOtherNode", "inputs": {}},
        "valid_bc": {
            "class_type": "StringToolsBalancedChoice",
            "inputs": {
                "text_0": ["leaf1", 0],
                "text_1": ["leaf2", 0]
            }
        },
        "leaf1": {"class_type": "StringToolsString", "inputs": {}},
        "leaf2": {"class_type": "StringToolsString", "inputs": {}},
    }
    # weights: text_0(unknown)=1, text_1(unconnected)=1, text_2(valid_bc=2) = 2
    # 合計 4
    weights = calculate_weights_from_prompt(prompt, "node1", classes, "text")
    assert weights == {"text_0": 1, "text_1": 1, "text_2": 2}

def test_calculate_weights_subgraph_support(reset_balanced_choice_state):
    """
    サブグラフ環境（IDプレフィックス付き）における重み計算の検証。
    prompt のキーや接続先に ":" が含まれている状況を模擬。
    """
    classes = ["StringToolsRandomChoice", "StringToolsBalancedChoice"]
    prompt = {
        # サブグラフ A 内のターゲットノード
        "A:10": {
            "class_type": "StringToolsBalancedChoice",
            "inputs": {
                "text_0": ["A:20", 0], # サブグラフ内のノードへの接続
                "text_1": ["30", 0],   # サブグラフ外（メイン）のノードへの接続
            }
        },
        # サブグラフ A 内のリーフノード(2リーフ)
        "A:20": {
            "class_type": "StringToolsRandomChoice",
            "inputs": {
                "text_0": ["A:leaf1", 0],
                "text_1": ["A:leaf2", 0]
            }
        },
        # メイングラフのリーフノード(1リーフ)
        "30": {
            "class_type": "StringToolsString",
            "inputs": {"string": "X"}
        },
        "A:leaf1": {"class_type": "StringToolsString", "inputs": {}},
        "A:leaf2": {"class_type": "StringToolsString", "inputs": {}},
    }

    # 1. フル ID ("A:10") での検証 -> text_0(2) + text_1(1)
    weights_full = calculate_weights_from_prompt(prompt, "A:10", classes, "text")
    assert weights_full == {"text_0": 2, "text_1": 1}

    # 2. フラット ID ("10") での検証 (フォールバック) -> 同上の結果を期待
    weights_flat = calculate_weights_from_prompt(prompt, "10", classes, "text")
    assert weights_flat == {"text_0": 2, "text_1": 1}

    # 3. 再帰探索中にプレフィックスが混在していても正しく辿れることの確認
    # (A:20) は A:leaf1 と A:leaf2 に繋がっている
    weights_recursive = calculate_weights_from_prompt(prompt, "20", classes, "text")
    assert weights_recursive == {"text_0": 1, "text_1": 1}

def test_balanced_choice_list_statistics_update(reset_balanced_choice_state):
    """BalancedChoiceList の統計情報が正しく更新されることを検証"""
    node = StringToolsBalancedChoiceList()
    text_list = ["A", "B", "C"]
    
    # 1回目の実行
    node.process(seed=42, text_list=text_list, unique_id="test_list_node", prompt={}, extra_pnginfo={"workflow": {"nodes": [{"id": "test_list_node", "type": "StringToolsBalancedChoiceList"}]}})
    
    assert StringToolsBalancedChoiceList.total_count["test_list_node"] == 1
    # 選択されたインデックスのカウンタが 1 になっているはず
    counts = StringToolsBalancedChoiceList.counts["test_list_node"]
    assert sum(counts.values()) == 1

    # 2回目の実行
    node.process(seed=43, text_list=text_list, unique_id="test_list_node", prompt={}, extra_pnginfo={"workflow": {"nodes": [{"id": "test_list_node", "type": "StringToolsBalancedChoiceList"}]}})
    assert StringToolsBalancedChoiceList.total_count["test_list_node"] == 2
    assert sum(counts.values()) == 2

