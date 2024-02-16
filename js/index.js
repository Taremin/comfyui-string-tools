import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { setWidgetConfig } from "/extensions/core/widgetInputs.js";
function createCallback(nodename, basename, inputType, withWeights) {
    return async function (nodeType, nodeData, app) {
        if (nodeData.name !== nodename) {
            return;
        }
        const getInputBasename = function (input) {
            return input.name.split('_')[0];
        };
        const getInputExtraname = function (input) {
            return input.name.split('_', 2)[1];
        };
        const updateInputs = function () {
            // remove empty inputs
            for (let index = this.inputs.length; index--;) {
                const input = this.inputs[index];
                if (getInputBasename(input) === basename && input.link === null && this.removeCancel !== index) {
                    this.removeInput(index);
                    const widgetIndex = this.widgets.findIndex((value) => value.name === input.name);
                    if (widgetIndex != -1) {
                        this.widgets.splice(widgetIndex);
                    }
                }
            }
            // rename
            let j = 0;
            for (let i = 0, il = this.inputs.length; i < il; ++i) {
                const input = this.inputs[i];
                if (getInputBasename(input) === basename) {
                    this.inputs[i].name = [basename, j++].join('_');
                }
            }
            // create empty input
            this.addInput([basename, j].join('_'), inputType);
            if (!this.widgets) {
                this.widgets = [];
            }
            for (let i = 0, il = this.inputs.length; i < il; ++i) {
                const input = this.inputs[i];
                if (input.widget) {
                    setWidgetConfig(input, [input.type, { forceInput: true }]);
                    continue;
                }
                // setup widget
                input.widget = {
                    name: input.name,
                };
                setWidgetConfig(input, [inputType, { forceInput: true }]);
            }
        };
        const onNodeCreatedOriginal = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (onNodeCreatedOriginal) {
                const tmp = app.configuringGraph;
                app.configuringGraph = false;
                onNodeCreatedOriginal.call(this);
                app.configuringGraph = tmp;
            }
            this.removeCancel = -1;
            const onConnectInputOriginal = this.onConnectInput;
            this.onConnectInput = function (targetSlot, type, output, originNode, originSlot) {
                let retVal = onConnectInputOriginal ? onConnectInputOriginal.apply(this, arguments) : void 0;
                if (originNode.type === "PrimitiveNode" && getInputBasename(this.inputs[targetSlot]) === basename) {
                    return false;
                }
                this.removeCancel = targetSlot;
                return retVal;
            };
            const onInputDblClickOriginal = this.onInputDblClick;
            this.onInputDblClick = function (slot) {
                if (onInputDblClickOriginal) {
                    const originalCreateNode = LiteGraph.createNode;
                    if (getInputBasename(this.inputs[slot]) === basename) {
                        LiteGraph.createNode = function (nodeType) {
                            if (nodeType !== "PrimitiveNode") {
                                return originalCreateNode.apply(this, arguments);
                            }
                            return originalCreateNode.call(this, "StringToolsText");
                        };
                    }
                    onInputDblClickOriginal.call(this, slot);
                    LiteGraph.createNode = originalCreateNode;
                }
            };
            const onConnectionsChange = this.onConnectionsChange;
            this.onConnectionsChange = function (type, //(0: ?, 1:input, 2: output )
            slotIndex, isConnected, link, //LLink,
            ioSlot) {
                if (onConnectionsChange) {
                    onConnectionsChange.apply(this, arguments);
                }
                if (type !== 1) {
                    return;
                }
                updateInputs.call(this);
                this.removeCancel = -1;
            };
            this.onAdded = function (graph) {
                this.tmpWidgets = this.widgets;
                if (app.configuringGraph) {
                    this.widgets = [];
                    this.widgets_values = [];
                }
                else {
                    updateInputs.call(this);
                }
            };
            // デフォルトの onGraphConfigured は動的なソケットを破壊するので使用しない
            const onGraphConfigured = this.onGraphConfigured;
            this.onGraphConfigured = function () {
                if (this.tmpWidgets) {
                    this.widgets = this.tmpWidgets.concat(this.widgets);
                    delete this.tmpWidgets;
                }
                if (app.configuringGraph) {
                    updateInputs.call(this);
                }
            };
            if (withWeights !== void 0) {
                this.calcNodeInputs = function (prompt, workflow) {
                    const type = prompt[this.id].class_type;
                    for (const input of Object.keys(prompt[this.id].inputs)) {
                        if (getInputBasename({ name: input }) !== basename) {
                            continue;
                        }
                        const extraname = getInputExtraname({ name: input });
                        const walkdown = (type, id, sum) => {
                            for (const input of Object.keys(prompt[id].inputs)) {
                                const value = prompt[id].inputs[input];
                                let start = 0;
                                if (withWeights.includes(prompt[id].class_type) &&
                                    getInputBasename({ name: input }) === basename) {
                                    start = 1;
                                }
                                if (Array.isArray(value)) {
                                    sum += walkdown(type, value[0], start);
                                }
                            }
                            return sum;
                        };
                        const value = prompt[this.id].inputs[input];
                        if (Array.isArray(value)) {
                            let sum = walkdown(type, value[0], 0);
                            if (sum === 0) {
                                sum = 1;
                            }
                            const weightKey = ["weight", extraname].join('_');
                            prompt[this.id].inputs[weightKey] = sum;
                        }
                    }
                };
            }
            // init inputs
            if (!this.inputs) {
                this.inputs = [];
            }
        };
    };
}
const queuePromptOriginal = api.queuePrompt;
api.queuePrompt = (async function queuePrompt(number, { output, workflow }) {
    for (const id of Object.keys(output)) {
        const node = app.graph.getNodeById(id);
        if (node.calcNodeInputs && typeof node.calcNodeInputs === "function") {
            node.calcNodeInputs(output, workflow);
        }
    }
    return await queuePromptOriginal(number, { output, workflow });
}).bind(api);
app.registerExtension({
    name: "Taremin.StringToolsConcat",
    beforeRegisterNodeDef: createCallback("StringToolsConcat", "text", "STRING"),
});
app.registerExtension({
    name: "Taremin.StringToolsRandomChoice",
    beforeRegisterNodeDef: createCallback("StringToolsRandomChoice", "text", "STRING"),
});
app.registerExtension({
    name: "Taremin.StringToolsBalancedChoice",
    beforeRegisterNodeDef: createCallback("StringToolsBalancedChoice", "text", "STRING", ["StringToolsRandomChoice", "StringToolsBalancedChoice"]),
});
