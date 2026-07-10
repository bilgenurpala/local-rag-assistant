To get started with Foundry Local in Python, you need Python 3.11 or later. On Windows, install the SDK with pip using the package name foundry-local-sdk-winml, which integrates with the Windows ML runtime for wider hardware acceleration. On other platforms, the cross-platform package foundry-local-sdk is used instead.

A Foundry Local application starts by initializing the SDK. In Python, you create a Configuration object with an application name, call FoundryLocalManager.initialize with that configuration, and then access the shared FoundryLocalManager.instance singleton to interact with the runtime.

Before running inference, Foundry Local can download and register execution providers for the user's hardware. Execution provider packages include dependencies and may be large, but they only need to be downloaded again when a new version is released.

To use a model with Foundry Local, you get it from the catalog by its alias, for example qwen2.5-0.5b. Calling the model's download method fetches the model files, and the download is skipped automatically if the model is already cached locally. The model is then loaded into memory with the load method.

After a model is loaded, Foundry Local provides a chat client through the model's get_chat_client method. The client can return a complete response or stream the answer token by token. When the application is done, the model is unloaded from memory with the unload method.