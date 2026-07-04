import pytest
import sys
import os
import importlib.util

spec = importlib.util.spec_from_file_location("comfyui_string_tools", os.path.join(os.path.dirname(__file__), "..", "__init__.py"))
comfy_module = importlib.util.module_from_spec(spec)
sys.modules["comfyui_string_tools"] = comfy_module
spec.loader.exec_module(comfy_module)

def calculate_weights_from_prompt(prompt, target_node_id, with_weights_classes, basename="text"):
    flatten_prompt = {}
    for key, value in prompt.items():
        flatten_id = key.split(':')[-1]
        flatten_prompt[flatten_id] = value

    if str(target_node_id) not in flatten_prompt:
        return {}

    node = flatten_prompt[str(target_node_id)]
    weights_result = {}

    def get_input_basename(input_name):
        return input_name.split('_')[0]

    def get_input_extraname(input_name):
        parts = input_name.split('_', 1)
        return parts[1] if len(parts) > 1 else ""

    def walkdown(type_name, id_str, current_sum):
        target_node = flatten_prompt.get(str(id_str.split(':')[-1]))
        if not target_node:
            return current_sum
        
        for input_name, value in target_node.get("inputs", {}).items():
            if get_input_basename(input_name) != basename:
                continue

            start = 0
            if target_node.get("class_type") in with_weights_classes:
                start = 1
            if isinstance(value, list) and len(value) > 0:
                current_sum += walkdown(target_node.get("class_type"), value[0], start)
        return current_sum

    for input_name, value in node.get("inputs", {}).items():
        if get_input_basename(input_name) != basename:
            continue
        
        extraname = get_input_extraname(input_name)
        if isinstance(value, list) and len(value) > 0:
            total_sum = walkdown(node.get("class_type"), value[0], 0)
            if total_sum == 0:
                total_sum = 1
            weights_result[f"weight_{extraname}"] = total_sum

    return weights_result

def test_calculate_weights():
    prompt = {
        "1": {
            "class_type": "StringToolsString",
            "inputs": {"text": "A"}
        },
        "2": {
            "class_type": "StringToolsString",
            "inputs": {"text": "B"}
        },
        "3": {
            "class_type": "StringToolsRandomChoice",
            "inputs": {
                "text_0": ["1", 0],
                "text_1": ["2", 0]
            }
        },
        "4": {
            "class_type": "StringToolsBalancedChoice",
            "inputs": {
                "text_0": ["1", 0],
                "text_1": ["3", 0]
            }
        }
    }
    
    weights = calculate_weights_from_prompt(
        prompt, 
        target_node_id=4, 
        with_weights_classes=["StringToolsRandomChoice", "StringToolsBalancedChoice"],
        basename="text"
    )
    
    assert weights == {
        "weight_0": 1,
        "weight_1": 2
    }
