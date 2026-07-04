import pytest
import sys
import os
import importlib.util

spec = importlib.util.spec_from_file_location("comfyui_string_tools", os.path.join(os.path.dirname(__file__), "..", "__init__.py"))
comfy_module = importlib.util.module_from_spec(spec)
sys.modules["comfyui_string_tools"] = comfy_module
spec.loader.exec_module(comfy_module)

get_node = comfy_module.get_node
# Will add count_node_occurrences later

def test_workflow_traversal():
    workflow = {
        "nodes": [
            {
                "id": 1,
                "type": "StringToolsString",
                "inputs": [{"name": "text"}],
                "widgets_values": ["Apple"]
            },
            {
                "id": 2,
                "type": "StringToolsString",
                "widgets_values": ["Banana"]
            },
            {
                "id": 10,
                "type": "StringToolsBalancedChoiceList",
                "inputs": [
                    {"name": "text_list", "type": "STRING", "link": 100}
                ]
            },
            {
                "id": 20,
                "type": "MockListCreator",
                "inputs": [
                     {"name": "text_0", "link": 1}
                ]
            }
        ],
        "links": [
            [1, 1, 0, 20, 0, "STRING"]
        ]
    }
    kwargs = {
        "text_list": ["Apple"],
        "extra_pnginfo": {"workflow": workflow},
        "unique_id": "10"
    }
    
    node = get_node(kwargs)
    assert node["id"] == 10
