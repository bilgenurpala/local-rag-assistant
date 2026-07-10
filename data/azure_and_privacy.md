Foundry Local does not require an Azure subscription. It runs entirely on local hardware, and no cloud account of any kind is needed to download models or run inference.

Foundry Local runs inference entirely on the device. When an application sends prompts to a Foundry Local endpoint, the prompts and the model outputs are processed locally and are not sent to Microsoft.

Foundry Local can still use the network for two purposes: downloading model files and execution providers the first time a model runs, and optional diagnostics if a user chooses to share logs when reporting a problem. Regular inference traffic never leaves the device.

Foundry Local is one of two options for running AI models locally. Foundry Local itself is for embedding AI in client applications on end-user devices, with data staying on the device and no Azure subscription required. A separate product, Foundry Local on Azure Local, targets enterprise-scale inference on Arc-enabled Kubernetes clusters and is managed through Azure.