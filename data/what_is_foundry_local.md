Foundry Local is an end-to-end local AI solution for shipping applications that run entirely on the user's device. It provides an easy-to-use SDK for C#, JavaScript, Rust, and Python, a curated catalog of optimized models, and automatic hardware acceleration, all in a lightweight package.

With Foundry Local, user data never leaves the device, responses start immediately with zero network latency, and applications keep working offline. There are no per-token costs and no backend infrastructure to maintain.

Foundry Local runs inference through ONNX Runtime. ONNX Runtime is the
inference runtime that executes every model in Foundry Local, and it adds
approximately 20 MB to the application package, which makes it practical to
embed AI directly into applications where size matters.

Foundry Local downloads models automatically on first use and caches them
locally for instant subsequent launches, selecting the best-performing variant
for the user's specific hardware.

Foundry Local detects the available hardware on the user's device and selects the best execution provider. It accelerates inference on GPUs and NPUs when available and falls back to CPU seamlessly, with no hardware detection code required.

Foundry Local supports OpenAI-compatible request and response formats. Applications that already use the OpenAI SDK can point to a Foundry Local endpoint with minimal code changes. An optional local web server is also available for serving models to multiple processes or experimenting through REST calls.

Foundry Local is ideal for applications that need to keep sensitive data on the user's device, operate in limited-connectivity or offline environments, reduce per-token cloud inference costs, or deliver low-latency AI responses for real-time interactions.