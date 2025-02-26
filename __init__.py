import random


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
            separator = ""
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

        values = sort_kwargs_value("text", kwargs)
        weights = sort_kwargs_value("weight", kwargs)
        random.seed(seed)
        choice = random.choices(values, weights=weights)[0]
        return (choice,)


NODE_CLASS_MAPPINGS = {
    "StringToolsString": StringToolsString,
    "StringToolsText": StringToolsText,
    "StringToolsConcat": StringToolsConcat,
    "StringToolsRandomChoice": StringToolsRandomChoice,
    "StringToolsBalancedChoice": StringToolsBalancedChoice,
}
WEB_DIRECTORY = "./js"
