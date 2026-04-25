# Hardware Specs — MacBook Pro M5 (14-inch, 2025)

## System

| Field | Value |
|-------|-------|
| Model | MacBook Pro 14-inch (M5, 2025) |
| Chip | Apple M5 |
| CPU | 10-core (4 performance + 6 efficiency) |
| GPU | 10-core (with Neural Accelerators per core) |
| Neural Engine | 16-core |
| Unified Memory | 32 GB (LPDDR5X) |
| Memory Bandwidth | 153.6 GB/s |
| Storage | 1 TB SSD |
| OS | macOS 26.4.1 (Darwin 25.4.0) |
| Ollama | 0.21.2 (ggml-Metal engine) |

## Model: `gemma4:26b` (MoE, ~4B active parameters)

- **Quantisation:** Q4_K_M (~16–17 GB weights)
- **Layers:** 31, all loaded on Metal GPU
- **Available GPU memory:** 26.8 GB (`recommendedMaxWorkingSetSize`) — model fits with ~10 GB headroom
- **Active parameters:** ~4B, so inference is closer in cost to a 4B dense model
- **Context window:** 65,536 tokens (64k)

## Ollama environment (`~/.zprofile`)

```zsh
export OLLAMA_CONTEXT_LENGTH=65536   # 64k context window for gemma4:26b
export OLLAMA_FLASH_ATTENTION=1      # reduces KV cache memory, improves throughput
export OLLAMA_NUM_PARALLEL=1         # single-user app; avoids doubling KV cache cost
export OLLAMA_KV_CACHE_TYPE=q8_0    # halves KV cache memory vs f16; negligible quality loss at 64k context
```

Reload after any change: `source ~/.zprofile`, then restart Ollama.

### What each setting does

| Setting | Effect | Why it matters here |
|---------|--------|---------------------|
| `OLLAMA_CONTEXT_LENGTH=65536` | Sets KV cache size to 64k tokens | Without it Ollama defaults to 4k–8k; matches `CONTEXT_WINDOW` in `config.py` |
| `OLLAMA_FLASH_ATTENTION=1` | Enables flash attention kernel | Reduces KV cache memory ~40%; confirmed active in log |
| `OLLAMA_NUM_PARALLEL=1` | One request at a time | Prevents a second KV cache being allocated; 32 GB leaves no room for two |
| `OLLAMA_KV_CACHE_TYPE=q8_0` | Quantises KV cache to 8-bit | Halves KV cache memory vs f16 default; frees ~1–2 GB at 64k — negligible perplexity impact |

## What the server log reveals

```
GPULayers:31[ID:0 Layers:31(0..30)]   ← all layers on Metal GPU ✓
FlashAttention:Enabled                 ← active ✓
KvSize:65536                           ← correct ✓
KvCacheType:                           ← was empty (f16 default) → now q8_0
Parallel:1                             ← correct ✓
```

### Known limitation: M5 Neural Accelerators not active

```
ggml_metal_device_init: testing tensor API for f16 support
ggml_metal_library_init_from_source: error compiling source
ggml_metal_device_init: - the tensor API is not supported in this environment - disabling
ggml_metal_device_init: has tensor = false
```

The M5 GPU has per-core Neural Accelerators that Apple advertises as giving up to 4× AI speedup over M4. Ollama 0.21.2's Metal shaders do not yet compile correctly against the M5's tensor API (`MTLGPUFamilyMetal4 / Apple10`). It falls back to standard Metal kernels. This is **not a configuration issue** — it is a known gap in the current Ollama build. Watch for a fix in a future Ollama release; when it lands, decode speed should jump significantly.

### MLX backend not active (3 blockers)

Ollama does offer an MLX preview backend (introduced in 0.19), but it is not available for this setup:

| Requirement | Needed | Yours |
|-------------|--------|-------|
| Unified memory | **> 32 GB** | 32 GB (at the boundary — not above it) |
| Chip | M5 Pro / Max | M5 base |
| Model | `qwen3.5:35b-a3b-coding-nvfp4` | `gemma4:26b` (unsupported) |

Nothing to configure — this is a hardware + model availability gap. When Ollama expands MLX to base M5 and adds gemma4 support, the current config will take advantage of it automatically.

## Summary: what's working, what's not

| Feature | Status |
|---------|--------|
| All layers on GPU (Metal) | ✓ Active |
| Flash attention | ✓ Active |
| 64k context window | ✓ Active |
| Q4_K_M quantisation | ✓ Active |
| q8_0 KV cache | ✓ Set (takes effect on next Ollama restart) |
| Single-parallel mode | ✓ Active |
| M5 Neural Accelerators (tensor API) | ✗ Not supported by Ollama 0.21.2 |
| MLX backend | ✗ Requires >32 GB RAM, M5 Pro/Max, and supported model |

## Thermal

MacBook Pro has active cooling — sustains full Metal load indefinitely.
Expect ~85 °C under continuous generation; normal and within spec.
