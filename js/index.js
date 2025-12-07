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
            this.widgets = [];
            // remove empty inputs
            for (let index = this.inputs.length; index--;) {
                const input = this.inputs[index];
                if (getInputBasename(input) === basename && input.link === null && this.removeCancel !== index) {
                    this.removeInput(index);
                }
            }
            // current version
            if (typeof this.layoutSlot !== "function") {
                // rename
                let j = 0;
                for (let i = 0, il = this.inputs.length; i < il; ++i) {
                    const input = this.inputs[i];
                    if (getInputBasename(input) === basename) {
                        this.inputs[i].name = [basename, j++].join('_');
                        this.inputs[i].widget = void 0;
                    }
                }
                // create empty input
                this.addInput([basename, j].join('_'), inputType);
            }
            // legacy version
            else {
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
                for (let i = 0, il = this.inputs.length; i < il; ++i) {
                    const input = this.inputs[i];
                    // setup widget
                    input.widget = {
                        name: input.name,
                    };
                    setWidgetConfig(input, [input.type, { forceInput: true }]);
                }
                for (const [idx, slot] of this.inputs.entries()) {
                    if (!slot._layoutElement) {
                        this.layoutSlot(slot, { slotIndex: idx });
                    }
                }
            }
        };
        const onNodeCreatedOriginal = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            if (onNodeCreatedOriginal) {
                onNodeCreatedOriginal.call(this);
            }
            this.removeCancel = -1;
            const onConnectInputOriginal = this.onConnectInput;
            this.onConnectInput = function (targetSlot, type, output, originNode, originSlot) {
                let retVal = onConnectInputOriginal ? onConnectInputOriginal.apply(this, arguments) : void 0;
                if (originNode.type === "PrimitiveNode") {
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
                    const flattenPrompt = {};
                    for (const [key, value] of Object.entries(prompt)) {
                        const flattenId = key.split(':').at(-1);
                        flattenPrompt[flattenId] = value;
                    }
                    const node = flattenPrompt[this.id];
                    const type = node.class_type;
                    for (const input of Object.keys(node.inputs)) {
                        if (getInputBasename({ name: input }) !== basename) {
                            continue;
                        }
                        const extraname = getInputExtraname({ name: input });
                        const walkdown = (type, id, sum) => {
                            const node = flattenPrompt[id.split(':').at(-1)];
                            for (const input of Object.keys(node.inputs)) {
                                const value = node.inputs[input];
                                let start = 0;
                                if (withWeights.includes(node.class_type) &&
                                    getInputBasename({ name: input }) === basename) {
                                    start = 1;
                                }
                                if (Array.isArray(value)) {
                                    sum += walkdown(type, value[0], start);
                                }
                            }
                            return sum;
                        };
                        const value = node.inputs[input];
                        if (Array.isArray(value)) {
                            let sum = walkdown(type, value[0], 0);
                            if (sum === 0) {
                                sum = 1;
                            }
                            const weightKey = ["weight", extraname].join('_');
                            node.inputs[weightKey] = sum;
                            node.inputs["title"] = this.title;
                            node.inputs["id"] = this.id;
                            node.inputs["debug"] = app.extensionManager.setting.get("StringTools.StringToolsBalancedChoice.debug");
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
    for (const idPath of Object.keys(output)) {
        const path = idPath.split(":");
        let node;
        if (path.length === 1) {
            const id = path[0];
            node = app.graph.getNodeById(id);
        }
        else {
            const nodePath = app.graph.resolveSubgraphIdPath(path.slice(0, -1));
            const id = path.at(-1);
            const subgraphNode = nodePath.at(-1);
            if (subgraphNode.isSubgraphNode()) {
                node = subgraphNode.subgraph.getNodeById(id);
            }
            else {
                console.error("last nodePath is not subgraph");
            }
        }
        if (!node) {
            console.error("output node not found:", idPath);
            continue;
        }
        if (node.calcNodeInputs && typeof node.calcNodeInputs === "function") {
            node.calcNodeInputs(output, workflow);
        }
    }
    return await queuePromptOriginal.call(api, number, { output, workflow });
}).bind(api);
app.registerExtension({
    name: "Taremin.StringToolsConcat",
    beforeRegisterNodeDef: createCallback("StringToolsConcat", "text", "STRING"),
});
app.registerExtension({
    name: "Taremin.StringToolsRandomChoice",
    beforeRegisterNodeDef: createCallback("StringToolsRandomChoice", "text", "STRING", ["StringToolsRandomChoice"]),
});
app.registerExtension({
    name: "Taremin.StringToolsBalancedChoice",
    settings: [
        {
            id: "StringTools.StringToolsBalancedChoice.debug",
            name: "Debug",
            type: "boolean",
            defaultValue: false,
        }
    ],
    beforeRegisterNodeDef: createCallback("StringToolsBalancedChoice", "text", "STRING", ["StringToolsRandomChoice", "StringToolsBalancedChoice"]),
});
