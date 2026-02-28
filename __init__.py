import random
import re


class StringToolsOptionalDict(dict):
    getitem_default_callback = None

    def __init__(self, *args, get_default_callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.getitem_default_callback = get_default_callback

    def __contains__(self, key: object) -> bool:
        return True

    def __getitem__(self, key):
        if callable(self.getitem_default_callback):
            return super().get(key, self.getitem_default_callback(key))
        else:
            return super().get(key, None)


def sort_kwargs_value(basename, kwargs, separator="_"):
    sorted_args = {}
    basename_dict = {}

    for key, value in kwargs.items():
        if separator.join(key.split(separator)[:-1]) != basename:
            sorted_args[key] = value
        else:
            basename_dict[key] = value

    sorted_basename_dict = sorted(
        basename_dict.items(), key=lambda kv: int(kv[0].split(separator)[-1])
    )

    return list(map(lambda kv: kv[1], sorted_basename_dict))


def get_node(kwargs):
    extra_pnginfo = kwargs.get("extra_pnginfo", None)
    unique_id = kwargs.get("unique_id", None)

    # INPUT_IS_LIST = True のノードではhidden入力もリストにラップされるためアンラップ
    if isinstance(extra_pnginfo, list):
        extra_pnginfo = extra_pnginfo[0]
    if isinstance(unique_id, list):
        unique_id = unique_id[0]

    if extra_pnginfo is None or unique_id is None:
        print(
            re.sub(
                pattern="^\s*> ",
                repl="",
                string="""
                > "extra_pnginfo" or "unique_id" not found in kwargs.
                > please add to INPUT_TYPES:
                >     "hidden": {
                >        "extra_pnginfo": "EXTRA_PNGINFO",
                >        "unique_id": "UNIQUE_ID",
                >     }
                """,
                flags=re.MULTILINE,
            )
        )
        return None

    workflow = extra_pnginfo["workflow"]
    node_path = [int(p) for p in unique_id.split(":")]

    subgraphs = workflow["definitions"]["subgraphs"] if "definitions" in workflow and "subgraphs" in workflow["definitions"] else []
    subgraphs_by_id = {}
    for subgraph in subgraphs:
        subgraphs_by_id[subgraph["id"]] = subgraph

    def walkdown_node_path(current_path, graph):
        nodes_by_id = {}
        for n in graph["nodes"]:
            nodes_by_id[n["id"]] = n
        node = nodes_by_id.get(current_path[0])
        if node is None:
            return None

        if node["type"] in subgraphs_by_id:
            return walkdown_node_path(current_path[1:], subgraphs_by_id[node["type"]])
        else:
            return node

    node = walkdown_node_path(node_path, workflow)

    return node


def get_input_basename(input_name):
    return input_name.split('_')[0]

def get_input_extraname(input_name):
    parts = input_name.split('_', 1)
    return parts[1] if len(parts) > 1 else ""

def calculate_weights_from_prompt(prompt, target_node_id, with_weights_classes, basename="text"):
    flatten_prompt = {}
    for key, value in prompt.items():
        flatten_id = key.split(':')[-1]
        flatten_prompt[flatten_id] = value

    if str(target_node_id) not in flatten_prompt:
        return {}

    node = flatten_prompt[str(target_node_id)]
    weights_result = {}

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


def format(num):
    return "{:6.2f}".format(num)


class StringToolsSeed:
    RETURN_TYPES = ("INT",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xffffffffffffffff,
                    }
                ),
            }
        }

    def process(self, seed):
        return (seed,)


class StringToolsString:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "dynamicPrompts": False,
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, text):
        return (text,)


class StringToolsText:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": False,
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, text):
        return (text,)


class StringToolsConcat:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {},
            "optional": {
                "separator": (
                    "STRING",
                    {"forceInput": True},
                ),
            },
            "hidden": {
                "text": (
                    "STRING",
                    {"forceInput": True},
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, *args, **kwargs):
        if "separator" in kwargs:
            separator = kwargs["separator"]
            del kwargs["separator"]
        else:
            separator = "\n"
        return (separator.join(sort_kwargs_value("text", kwargs)),)

class StringToolsConcatList:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text_list": (
                    "STRING",
                    {"forceInput": True},
                ),
            },
            "optional": {
                "separator": (
                    "STRING",
                    {"forceInput": True},
                ),
            },
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, text_list, separator=None):
        sep = "\n" if separator is None or len(separator) == 0 else separator[0]
        return (sep.join(text_list),)


class StringToolsRandomChoice:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "forceInput": True,
                    },
                ),
            },
            "hidden": {
                "text": (
                    "STRING",
                    {"forceInput": True},
                ),
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, *args, **kwargs):
        seed = 0
        if "seed" in kwargs:
            seed = kwargs["seed"]
            del kwargs["seed"]

        values = sort_kwargs_value("text", kwargs)
        random.seed(seed)
        choice = random.choice(values)
        return (choice,)


class StringToolsRandomChoiceList:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text_list": (
                    "STRING",
                    {"forceInput": True},
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "forceInput": True,
                    },
                ),
            },
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, text_list, seed):
        if not text_list:
            return ("",)
        s = seed[0] if isinstance(seed, list) else seed
        random.seed(s)
        choice = random.choice(text_list)
        return (choice,)


class StringToolsBalancedChoice(StringToolsRandomChoice):
    total_count = {}
    counts = {}
    debug = False

    @classmethod
    def INPUT_TYPES(s):
        input_types = super().INPUT_TYPES()
        input_types["optional"] = StringToolsOptionalDict(
            get_default_callback=lambda key: (
                ("INT") if key.startswith("weight_") else None,
            )
        )
        return input_types

    def process(self, *args, **kwargs):
        seed = 0
        if "seed" in kwargs:
            seed = kwargs["seed"]
            del kwargs["seed"]

        node = get_node(kwargs)
        title = node.get("title", node.get("type", None))
        values = sort_kwargs_value("text", kwargs)
        weights = sort_kwargs_value("weight", kwargs)
        random.seed(seed)

        id = node.get("id", None)
        counts = self.counts.get(id, None)
        if counts is None:
            counts = self.counts[id] = {}
        total_count = self.total_count.get(id, None)
        if total_count is None:
            total_count = self.total_count[id] = 0

        # weightsが空またはvaluesと長さが合わない場合は均等配分にフォールバック
        if not weights or len(weights) != len(values):
            weights = [1] * len(values)

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
                print(
                    f"\tInput:{text} Weight:{weights[idx]} ({format(weights[idx] / total_weight * 100)}%) - Count:{count} ({format(count / self.total_count[id] * 100)}%)"
                )

        return (values[choice_idx],)


class StringToolsBalancedChoiceList(StringToolsRandomChoiceList):
    total_count = {}
    counts = {}
    debug = False

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text_list": (
                    "STRING",
                    {"forceInput": True},
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "forceInput": True,
                    },
                ),
            },
            "optional": {
                "weight_list": (
                    "INT",
                    {"forceInput": True},
                )
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    def process(self, text_list, seed, weight_list=None, **kwargs):
        # INPUT_IS_LIST = True のため hidden 入力もリストにラップされる
        if isinstance(kwargs.get("prompt"), list):
            kwargs["prompt"] = kwargs["prompt"][0]
        if isinstance(kwargs.get("extra_pnginfo"), list):
            kwargs["extra_pnginfo"] = kwargs["extra_pnginfo"][0]
        if isinstance(kwargs.get("unique_id"), list):
            kwargs["unique_id"] = kwargs["unique_id"][0]

        if not text_list:
            return ("",)

        s = seed[0] if isinstance(seed, list) else seed
        random.seed(s)

        node = get_node(kwargs)
        if node is None:
            return (random.choice(text_list),)
            
        title = node.get("title", node.get("type", None))
        id = node.get("id", None)
        
        counts = self.counts.get(id, None)
        if counts is None:
            counts = self.counts[id] = {}
        total_count = self.total_count.get(id, None)
        if total_count is None:
            total_count = self.total_count[id] = 0

        weights = []
        if weight_list is not None and len(weight_list) == len(text_list):
            weights = weight_list
        else:
            prompt = kwargs.get("prompt", {})
            computed_weights = calculate_weights_from_prompt(
                prompt, id, ["StringToolsRandomChoice", "StringToolsBalancedChoice", "StringToolsRandomChoiceList", "StringToolsBalancedChoiceList"], "text_list"
            )
            # If input is connected to a list-generating node, text_list is a single connection.
            # Thus computed_weights might just have weight_list or weight_0.
            # For simplicity, if we don't have exactly per-element weights, uniform weight is used
            # Unless we are getting multiple input sources. List nodes usually receive 1 link for text_list.
            # To extract valid weights, we'd need the upstream node to supply a weight_list, 
            # Or assume uniform weights if not supplied. 
            
            # Reverting to basic equal weights if no weight_list is provided for List nodes logic,
            # or picking up from computed weights if applicable.
            weights = [1] * len(text_list)
            
            # If the upstream node passed exactly matching length weights via dict mapping
            if computed_weights and len(computed_weights) == len(text_list):
                 weights = [computed_weights[k] for k in sorted(computed_weights.keys())]

        choice_idx = random.choices(range(len(text_list)), weights=weights)[0]
        choice_text = "_".join(["text", str(choice_idx)])
        counts[choice_text] = counts.get(choice_text, 0) + 1
        self.total_count[id] += 1
        total_weight = sum(weights)

        if self.debug or kwargs.get("debug", False):
            print(f"#{id} {title} (Seed:{s}):")
            for idx in range(len(text_list)):
                text = "_".join(["text", str(idx)])
                count = counts.get(text, 0)
                print(
                    f"\tInput:{text} Weight:{weights[idx]} ({format(weights[idx] / total_weight * 100)}%) - Count:{count} ({format(count / self.total_count[id] * 100)}%)"
                )

        return (text_list[choice_idx],)


class MockStringList:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "str1": ("STRING", {"forceInput": True}),
                "str2": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("list",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "process"
    CATEGORY = "string-tools"

    def process(self, str1, str2):
        return ([str1, str2],)

NODE_CLASS_MAPPINGS = {
    "StringToolsSeed": StringToolsSeed,
    "StringToolsString": StringToolsString,
    "StringToolsText": StringToolsText,
    "StringToolsConcat": StringToolsConcat,
    "StringToolsRandomChoice": StringToolsRandomChoice,
    "StringToolsBalancedChoice": StringToolsBalancedChoice,
    "StringToolsConcatList": StringToolsConcatList,
    "StringToolsRandomChoiceList": StringToolsRandomChoiceList,
    "StringToolsBalancedChoiceList": StringToolsBalancedChoiceList,
    "string-tools/MockStringList": MockStringList,
}
WEB_DIRECTORY = "./js"

