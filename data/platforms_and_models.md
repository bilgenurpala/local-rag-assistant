Foundry Local supports Windows, macOS on Apple silicon, and Linux. On Windows, the SDK integrates with the Windows ML runtime, which provides the same API surface with a wider breadth of hardware acceleration.

Foundry Local provides a curated catalog of high-quality models optimized for on-device use across a wide range of consumer hardware. The catalog covers chat completion models such as GPT OSS, Qwen, DeepSeek, Mistral, and Phi, as well as audio transcription models such as Whisper.

Every model in the Foundry Local catalog goes through extensive quantization and compression to deliver the best balance of quality and performance on consumer devices. Models are versioned, so an application can pin to a specific version or automatically receive updates.

The Foundry Local model catalog is intentionally curated rather than open-ended, because the product is designed for shipping production applications, not for general-purpose model experimentation. Models are tested across a range of consumer hardware and kept small enough to distribute to end users, which ensures reliable performance when embedded in an application.

Foundry Local is optimized for hardware-constrained devices where a single user accesses the model at a time. It is not designed as a server inference stack for many concurrent users; server-oriented runtimes such as vLLM or Triton Inference Server are built for that scenario instead.