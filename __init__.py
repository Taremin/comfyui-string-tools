import random
import re

# 真の動的入力を実現するための辞書クラス
class StringToolsOptionalDict(dict):
    def __contains__(self, key: object) -> bool:
        # text_NN 形式のキーなら常に存在するとみなす
        if isinstance(key, str) and re.match(r"text_\d+", key):
            return True
        return super().__contains__(key)

    def __getitem__(self, key):
        if isinstance(key, str) and re.match(r"text_\d+", key):
            return super().get(key, ("STRING", {"forceInput": True}))
        return super().__getitem__(key)

    def get(self, key, default=None):
        if isinstance(key, str) and re.match(r"text_\d+", key):
            return super().get(key, ("STRING", {"forceInput": True}))
        return super().get(key, default)


def sort_kwargs_value(basename, kwargs):
    basename_dict = {}
    for key, value in kwargs.items():
        if key.startswith(basename) and value is not None:
            parts = key.split("_")
            if len(parts) > 1 and parts[1].isdigit():
                # value がリストの場合は最初の要素を取り出し、そうでなければそのまま文字列化
                if isinstance(value, list):
                    basename_dict[int(parts[1])] = str(value[0]) if value else ""
                else:
                    basename_dict[int(parts[1])] = str(value)

    sorted_basename_dict = sorted(basename_dict.items())
    return list(map(lambda kv: kv[1], sorted_basename_dict))


def get_node(kwargs):
    extra_pnginfo = kwargs.get("extra_pnginfo", None)
    unique_id = kwargs.get("unique_id", None)

    if isinstance(extra_pnginfo, list):
        extra_pnginfo = extra_pnginfo[0] if extra_pnginfo else None
    if isinstance(unique_id, list):
        unique_id = unique_id[0] if unique_id else None

    if extra_pnginfo is None or unique_id is None:
        return None

    workflow = extra_pnginfo.get("workflow", None)
    if workflow is None:
        return None

    node_path = [unique_id]

    def walkdown_node_path(current_path, workflow):
        if not current_path: return None
        node_id = current_path[0]
        node = None
        for n in workflow.get("nodes", []):
            if str(n["id"]) == str(node_id):
                node = n
                break

        if node is None:
            return None

        if node["type"] == "Subgraph" or "subgraph" in node:
            subgraphs_by_id = workflow.get("definitions", {})
            if node["type"] in subgraphs_by_id:
                return walkdown_node_path(current_path[1:], subgraphs_by_id[node["type"]])
        
        return node

    node = walkdown_node_path(node_path, workflow)
    return node


def calculate_weights_from_prompt(prompt, target_node_id, with_weights_classes, weight_prefix="text"):
    # JS 実装 (index.ts) と同様に ID をフラット化してマッチングするための前処理
    # 末尾の数値IDをキーにしたマップを作成する
    flatten_prompt = {}
    for k, v in prompt.items():
        flatten_id = str(k).split(':')[-1]
        flatten_prompt[flatten_id] = v

    # ターゲットIDも同様に正規化
    target_id_str = str(target_node_id).split(':')[-1]

    # 再帰的にリーフノードの合計数を数える内部関数
    def count_leaves(current_id):
        curr_id_str = str(current_id).split(':')[-1]
        if not curr_id_str or curr_id_str not in flatten_prompt:
            return 1
        
        node_info = flatten_prompt[curr_id_str]
        class_type = node_info.get("class_type")
        
        # ターゲットクラスの場合
        if class_type in with_weights_classes:
            node_inputs = node_info.get("inputs", {})
            total = 0
            for key, value in node_inputs.items():
                if key.startswith(weight_prefix):
                    if isinstance(value, list) and len(value) >= 2:
                        total += count_leaves(value[0])
                    else:
                        total += 1
                elif key == "text_list":
                    if isinstance(value, list) and len(value) >= 2:
                        total += count_leaves(value[0])
                    else:
                        total += 1
            return max(1, total)
        
        # 中間ノードの場合は全入力を再帰探索
        node_inputs = node_info.get("inputs", {})
        total = 0
        has_connections = False
        for key, value in node_inputs.items():
            if isinstance(value, list) and len(value) >= 2:
                has_connections = True
                total += count_leaves(value[0])
        
        if not has_connections:
            return 1
        return max(1, total)

    weights = {}
    main_node = flatten_prompt.get(target_id_str)
    if not main_node:
        return weights

    main_inputs = main_node.get("inputs", {})
    for key, value in main_inputs.items():
        if key.startswith(weight_prefix) or key == "text_list":
            if isinstance(value, list) and len(value) >= 2:
                weights[key] = count_leaves(value[0])
            else:
                weights[key] = 1
    
    return weights


class StringToolsString:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": (
                    "STRING",
                    {"default": "", "multiline": False, "dynamicPrompts": False},
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, text):
        return (text,)


class StringToolsText:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": (
                    "STRING",
                    {"default": "", "multiline": True, "dynamicPrompts": False},
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, text):
        return (text,)


class StringToolsConcat:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
            },
            "optional": StringToolsOptionalDict({
                "separator": ("STRING", {"forceInput": True}),
            }),
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, **kwargs):
        separator = kwargs.get("separator", "")
        if isinstance(separator, list):
            separator = str(separator[0]) if separator else ""
            
        values = sort_kwargs_value("text", kwargs)
        return (separator.join(values),)


class StringToolsConcatList:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text_list": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "separator": ("STRING", {"forceInput": True}),
            },
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, text_list=None, separator=None):
        if not text_list: return ("",)
        
        if separator is None:
            sep = "\n"
        elif isinstance(separator, list):
            sep = separator[0] if separator else "\n"
        else:
            sep = str(separator)
        
        flat_list = []
        for x in text_list:
            if isinstance(x, list):
                flat_list.extend(map(str, x))
            else:
                flat_list.append(str(x))
        return (sep.join(flat_list),)


class StringToolsRandomChoice:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF, "forceInput": True}),
            },
            "optional": StringToolsOptionalDict(),
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, **kwargs):
        seed = kwargs.get("seed", 0)
        values = sort_kwargs_value("text", kwargs)
        if not values:
            return ("",)
        random.seed(seed)
        choice = random.choice(values)
        return (choice,)


class StringToolsRandomChoiceList:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF, "forceInput": True}),
                "text_list": ("STRING", {"forceInput": True}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, seed=0, text_list=None, **kwargs):
        if not text_list:
            return ("",)
        
        flat_list = []
        for x in text_list:
            if isinstance(x, list):
                flat_list.extend(x)
            else:
                flat_list.append(x)
                
        s = seed[0] if isinstance(seed, list) else seed
        random.seed(s)
        choice = random.choice(flat_list)
        return (choice,)


class StringToolsBalancedChoice(StringToolsRandomChoice):
    total_count = {}
    counts = {}
    debug = False

    @classmethod
    def INPUT_TYPES(s):
        return super().INPUT_TYPES()

    def process(self, **kwargs):
        seed = kwargs.get("seed", 0)
        node = get_node(kwargs)
        
        values = sort_kwargs_value("text", kwargs)
        if not values:
            return ("",)

        if node is None:
            random.seed(seed)
            return (random.choice(values),)
            
        unique_id = kwargs.get("unique_id", None)
        if isinstance(unique_id, list): unique_id = unique_id[0]
        id = str(unique_id) if unique_id is not None else str(node.get("id", ""))

        counts = self.counts.get(id, None)
        if counts is None:
            counts = self.counts[id] = {}
        total_count = self.total_count.get(id, None)
        if total_count is None:
            total_count = self.total_count[id] = 0

        title = node.get("title", node.get("type", None))
        
        prompt = kwargs.get("prompt", {})
        computed_weights = calculate_weights_from_prompt(
            prompt, id, ["StringToolsRandomChoice", "StringToolsBalancedChoice", "StringToolsRandomChoiceList", "StringToolsBalancedChoiceList"], "text"
        )
        if computed_weights:
            weights = [computed_weights.get(f"text_{i}", 1) for i in range(len(values))]
        else:
            weights = [1] * len(values)

        random.seed(seed)
        choice_idx = random.choices(range(len(values)), weights=weights)[0]
        choice_text = "_".join(["text", str(choice_idx)])
        counts[choice_text] = counts.get(choice_text, 0) + 1
        self.total_count[id] += 1
        total_weight = sum(weights)

        if self.debug or kwargs.get("debug", False):
            print(f"#{id} {title} (Seed:{seed}):")
            for idx in range(len(values)):
                text = "_".join(["text", str(idx)])
                count = counts.get(text, 0)
                print(f"\tInput:{text} Weight:{weights[idx]} ({weights[idx] / total_weight * 100}%) - Count:{count} ({count / self.total_count[id] * 100}%)")

        return (values[choice_idx],)


class StringToolsBalancedChoiceList(StringToolsRandomChoiceList):
    total_count = {}
    counts = {}
    debug = False

    @classmethod
    def INPUT_TYPES(s):
        input_types = super().INPUT_TYPES()
        input_types["optional"] = {
            "weight_list": ("INT", {"forceInput": True})
        }
        return input_types

    def process(self, seed=0, text_list=None, weight_list=None, **kwargs):
        if isinstance(kwargs.get("prompt"), list):
            kwargs["prompt"] = kwargs["prompt"][0]
        if isinstance(kwargs.get("extra_pnginfo"), list):
            kwargs["extra_pnginfo"] = kwargs["extra_pnginfo"][0]
        if isinstance(kwargs.get("unique_id"), list):
            kwargs["unique_id"] = kwargs["unique_id"][0]

        if not text_list:
            return ("",)

        flat_list = []
        for x in text_list:
            if isinstance(x, list):
                flat_list.extend(x)
            else:
                flat_list.append(x)

        s = seed[0] if isinstance(seed, list) else seed
        random.seed(s)

        node = get_node(kwargs)
        if node is None:
            return (random.choice(flat_list),)
            
        title = node.get("title", node.get("type", None))
        unique_id = kwargs.get("unique_id", None)
        if isinstance(unique_id, list): unique_id = unique_id[0]
        id = str(unique_id) if unique_id is not None else str(node.get("id", ""))
        
        counts = self.counts.get(id, None)
        if counts is None:
            counts = self.counts[id] = {}
        
        total_count = self.total_count.get(id, None)
        if total_count is None:
            total_count = self.total_count[id] = 0
        
        weights = []
        if weight_list is not None:
            # weight_list も平坦化が必要な可能性があるが、通常は 1つ
            flat_weights = []
            for w in weight_list:
                if isinstance(w, list): flat_weights.extend(w)
                else: flat_weights.append(w)
            
            if len(flat_weights) == len(flat_list):
                weights = flat_weights

        if not weights:
            prompt = kwargs.get("prompt", {})
            computed_weights = calculate_weights_from_prompt(
                prompt, id, ["StringToolsRandomChoice", "StringToolsBalancedChoice", "StringToolsRandomChoiceList", "StringToolsBalancedChoiceList"], "text_list"
            )
            if computed_weights:
                w = computed_weights.get("text_list", 1)
                weights = [w / len(flat_list)] * len(flat_list)
            else:
                weights = [1] * len(flat_list)

        choice_idx = random.choices(range(len(flat_list)), weights=weights)[0]
        choice_text = str(choice_idx)
        counts[choice_text] = counts.get(choice_text, 0) + 1
        self.total_count[id] += 1
        total_weight = sum(weights)

        if self.debug or kwargs.get("debug", False):
            print(f"#{id} {title} (Seed:{seed}):")
            for idx in range(len(flat_list)):
                count = counts.get(str(idx), 0)
                print(f"\tInput:{idx} Weight:{weights[idx]} ({weights[idx] / total_weight * 100 if total_weight > 0 else 0}%) - Count:{count} ({count / self.total_count[id] * 100}%)")

        return (flat_list[choice_idx],)


class StringToolsSeed:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seed": (
                    "INT",
                    {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF},
                ),
            }
        }

    RETURN_TYPES = ("INT",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, seed):
        return (seed,)


class StringToolsStringsToList:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {},
            "optional": StringToolsOptionalDict(),
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, **kwargs):
        values = sort_kwargs_value("text", kwargs)
        return (values,)


class StringToolsMockStringList:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "str1": ("STRING", {"forceInput": True}),
                "str2": ("STRING", {"forceInput": True}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "process"
    CATEGORY = "string-tools/test"

    def process(self, str1, str2):
        return ([str1, str2],)


NODE_CLASS_MAPPINGS = {
    "StringToolsString": StringToolsString,
    "StringToolsText": StringToolsText,
    "StringToolsConcat": StringToolsConcat,
    "StringToolsConcatList": StringToolsConcatList,
    "StringToolsRandomChoice": StringToolsRandomChoice,
    "StringToolsRandomChoiceList": StringToolsRandomChoiceList,
    "StringToolsBalancedChoice": StringToolsBalancedChoice,
    "StringToolsBalancedChoiceList": StringToolsBalancedChoiceList,
    "StringToolsSeed": StringToolsSeed,
    "StringToolsStringsToList": StringToolsStringsToList,
}

import os
if os.environ.get("COMFYUI_TEST_MODE") == "true" or os.environ.get("PYTEST_CURRENT_TEST"):
    NODE_CLASS_MAPPINGS["StringToolsMockStringList"] = StringToolsMockStringList

NODE_DISPLAY_NAME_MAPPINGS = {
    "StringToolsMockStringList": "StringTools [TEST ONLY] Mock String List"
}

WEB_DIRECTORY = "./js"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
