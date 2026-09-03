# OpenAI Responses API adapter

## Purpose

`OpenAIResponsesAgent` connects the Authorization Decay Surface to the Responses API while preserving the benchmark's local safety boundary. It translates the ordered trajectory, attaches the exact authority ledger, exposes thirteen synthetic controlled tools, executes requested calls locally, and returns each result to the model until the model produces a final response.

## Install

```bash
python -m pip install -e ".[dev,openai]"
export OPENAI_API_KEY="your-project-key"
```

The adapter uses the standard OpenAI client credential environment. API keys are never accepted as command-line arguments or written to run artifacts.

## Run one registered arm

Baseline example:

```bash
boundarybench stress \
  --provider openai \
  --model gpt-5.6-luna \
  --reasoning-effort medium \
  --max-output-tokens 1500 \
  --max-tool-rounds 8 \
  --trials 10 \
  --seed 20260903 \
  --output-root runs/gpt-5.6-luna/baseline \
  --summary results/gpt-5.6-luna-baseline.json
```

Authority-checkpoint example:

```bash
boundarybench stress \
  --provider openai \
  --model gpt-5.6-luna \
  --reasoning-effort medium \
  --max-output-tokens 1500 \
  --max-tool-rounds 8 \
  --mitigation authority-checkpoint \
  --trials 10 \
  --seed 20260903 \
  --output-root runs/gpt-5.6-luna/authority-checkpoint \
  --summary results/gpt-5.6-luna-authority-checkpoint.json
```

Run the six model and arm blocks in the order recorded by the compiled study plan. Each command uses the study seed, so its internal SHA256 order matches the corresponding locked block. The individual commands above show the exact adapter configuration.

After both arms for one model complete, generate the registered comparison directly from their durable run records:

```bash
boundarybench compare-mitigation \
  runs/gpt-5.6-luna/baseline \
  runs/gpt-5.6-luna/authority-checkpoint \
  --seed 20260903 \
  --summary results/gpt-5.6-luna-mitigation-comparison.json
```

The command requires identical scenario, control, trial, and condition keys in both arms. It also requires one shared model and provider, distinct mitigation settings, matching manifests and results, and valid trajectory metadata. It reports both arm fingerprints before the matched mitigation estimands.

## Safety invariants

| Boundary | Enforcement |
| --- | --- |
| Provider state | Every response sets `store=False` |
| Model tools | Only the thirteen BoundaryBench function schemas are supplied |
| Network | No web search, computer use, or model-selected endpoint is available |
| Filesystem | Paths resolve inside a fresh synthetic sandbox |
| Commands | Only exact scenario allowlist entries can execute |
| Secrets | Synthetic-secret guards inspect tool inputs and outputs |
| Admin actions | Visibility, membership, and pin operations are denied local stubs |
| Tool errors | Denials return structured results so the model can recover |
| Telemetry | Response IDs, cumulative token use, rounds, and calls enter the manifest |

The adapter requests encrypted reasoning items for stateless tool continuation, as documented by the Responses API, while leaving response storage disabled. It runs tool calls sequentially to preserve a complete order for audit.

## Translation contract

The policy message becomes a developer message and contains the canonical authority ledger. User, context, and neutral checkpoint messages retain their original order. Visible provenance fields are rendered directly above the associated content. Flattened conditions include the same content without source or trust labels.

The authority-checkpoint mitigation adds one sentence to each neutral checkpoint. It does not change the ledger, scenario task, attack content, available tools, fixture, or oracle.

## Verification

The automated suite injects a deterministic Responses client and verifies multi-round tool execution, absolute-path normalization, denial recovery, cumulative token accounting, provider metadata, mitigation rendering, and an end-to-end deterministic scenario oracle. The same adapter class is used for API collection.

The implementation follows the official [Responses API reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create) and current [model catalog](https://developers.openai.com/api/docs/models).
