import random


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

    return list(sorted_args.values()) + list(
        map(lambda kv: kv[1], sorted_basename_dict)
    )


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
        values = list(kwargs.values())
        if len(values) == 0:
            return ""

        random.seed(0)
        return (random.choice(values),)


NODE_CLASS_MAPPINGS = {
    "StringToolsConcat": StringToolsConcat,
    "StringToolsRandomChoice": StringToolsRandomChoice,
}
WEB_DIRECTORY = "./js"
