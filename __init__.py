import random


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
        return separator.join(kwargs.values())


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
        values = kwargs.values()
        if len(values) == 0:
            return ""

        random.seed(0)
        random.choice
        return random.choice(values)


NODE_CLASS_MAPPINGS = {
    "StringToolsConcat": StringToolsConcat,
    "StringToolsRandomChoice": StringToolsRandomChoice,
}
WEB_DIRECTORY = "./js"
