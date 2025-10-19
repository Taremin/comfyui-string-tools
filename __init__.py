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
        node = nodes_by_id[current_path[0]]

        if node["type"] in subgraphs_by_id:
            return walkdown_node_path(current_path[1:], subgraphs_by_id[node["type"]])
        else:
            return node

    node = walkdown_node_path(node_path, workflow)

    return node


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


class StringToolsBalancedChoice(StringToolsRandomChoice):
    total_count = {}
    counts = {}
    debug = True

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


NODE_CLASS_MAPPINGS = {
    "StringToolsSeed": StringToolsSeed,
    "StringToolsString": StringToolsString,
    "StringToolsText": StringToolsText,
    "StringToolsConcat": StringToolsConcat,
    "StringToolsRandomChoice": StringToolsRandomChoice,
    "StringToolsBalancedChoice": StringToolsBalancedChoice,
}
WEB_DIRECTORY = "./js"
