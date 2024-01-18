import { app } from "/scripts/app.js"
import { setWidgetConfig } from "/extensions/core/widgetInputs.js"


function createCallback(nodename: string, basename: string, inputType: string) {
    return async function(nodeType:any, nodeData:any, app:any) {
        if (nodeData.name !== nodename) {
            return
        }

        const getInputBasename = function(input: any) {
            return input.name.split('_')[0]
        }

        const updateInputs = function(this: any) {
            // remove empty inputs
            for (let index = this.inputs.length; index--; ) {
                const input = this.inputs[index]
                if (getInputBasename(input) === basename && input.link === null) {
                    console.log("Remove:", input)
                    this.removeInput(index)
                    const widgetIndex = (this.widgets as any[]).findIndex((value) => value.name === input.name)
                    if (widgetIndex != -1) {
                        this.widgets.splice(widgetIndex)
                    }
                }
            }

            // rename
            let j = 0
            for (let i = 0, il = this.inputs.length; i < il; ++i) {
                const input = this.inputs[i]
                if (getInputBasename(input) === basename) {
                    this.inputs[i].name = [basename, j++].join('_')
                }
            }
            // create empty input
            this.addInput([basename, j].join('_'), inputType)

            if (!this.widgets) {
                this.widgets = []
            }
            for (let i = 0, il = this.inputs.length; i < il; ++i) {
                const input = this.inputs[i]

                if (input.widget) {
                    continue
                }

                // setup widget
                input.widget = {
                    name: input.name,
                    computeSize: () => [0, -4], // widgetsInputs.js -> hideWidgets
                }
                setWidgetConfig(input, [inputType, {forceInput: true}]);
                this.widgets.push(input.widget)
            }
        }

        const onNodeCreatedOriginal = nodeType.prototype.onNodeCreated
        nodeType.prototype.onNodeCreated = function() {
            if (onNodeCreatedOriginal) {
                const tmp = app.configuringGraph
                app.configuringGraph = false
                onNodeCreatedOriginal.call(this)
                app.configuringGraph = tmp 
            }

            const onConnectionsChange = this.onConnectionsChange
            this.onConnectionsChange = function(
                type: number, //(0: ?, 1:input, 2: output )
                slotIndex: number,
                isConnected: boolean,
                link: any,//LLink,
                ioSlot: any,//(INodeOutputSlot | INodeInputSlot)
            ) {
                if (onConnectionsChange) {
                    onConnectionsChange.apply(this, arguments)
                }
                if (type !== 1) {
                    return
                }

                updateInputs.call(this)
            }

            this.onAdded = function(graph: any) {
                this.tmpWidgets = this.widgets
                if (app.configuringGraph) {
                    this.widgets = []
                    this.widgets_values = []
                } else {
                    updateInputs.call(this)
                }
            }

            // デフォルトの onGraphConfigured は動的なソケットを破壊するので使用しない
            const onGraphConfiguredOriginal = this.onGraphConfigured
            this.onGraphConfigured = function() {
                if (this.tmpWidgets) {
                    this.widgets = this.tmpWidgets.concat(this.widgets)
                    delete this.tmpWidgets
                }
                if (this.widgets_values) {
                    for (let i = 0, il = this.widgets_values.length; i < il; ++i) {
                        const value = this.widgets_values[i]
                        if (value === null || value === void 0) {
                            continue
                        }
                        this.widgets[i].value = value
                    }
                }

                this.setSize(this.computeSize())
                this.setDirtyCanvas(true, true)

                if (app.configuringGraph) {
                    updateInputs.call(this)
                }
            }

            // init inputs
            if (!this.inputs) {
                this.inputs = []
            }
        }
    }
}

app.registerExtension({
    name: "Taremin.StringToolsConcat",
    beforeRegisterNodeDef: createCallback("StringToolsConcat", "text", "STRING"),
})

app.registerExtension({
    name: "Taremin.StringToolsRandomChoice",
    beforeRegisterNodeDef: createCallback("StringToolsRandomChoice", "text", "STRING"),
})
