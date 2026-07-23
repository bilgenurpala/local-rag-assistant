Foundry Local has two official Python SDK packages with the same API surface. The `foundry-local-sdk-winml` package is recommended on Windows for Windows ML hardware acceleration. The `foundry-local-sdk` package is the cross-platform choice for macOS, Linux, or Windows without hardware acceleration. The two packages must not be installed together because their ONNX Runtime dependencies conflict.

Foundry Local model aliases are resolved through the model catalog. If an alias is not found, the catalog may need an internet connection to refresh, or the requested alias may no longer be available. The `foundry model list` command shows aliases available for the current hardware.

Foundry Local downloads model files and execution providers on first use and caches them. Once all required files are cached, ordinary inference can run offline. A network connection can still be needed later to refresh the model catalog or download a model or execution provider that is not already cached.

On Windows, the WinML backend requires physical DirectX 12-capable GPU hardware for GPU acceleration. A virtual machine without GPU passthrough may return empty model output. The cross-platform SDK can be used on Windows when Windows ML acceleration is not required.

Foundry Local selects an execution provider for the available hardware. When a supported GPU or NPU accelerator is unavailable, the runtime can fall back to CPU execution, which preserves functionality but may respond more slowly.
