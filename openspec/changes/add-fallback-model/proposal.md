# Proposal: Add Fallback Model Configuration

## Description
Introduces a configuration option to specify a fallback translation model, constrained to the same API gateway as the default model. This model will be used when the default model fails or encounters structural errors requiring controlled retry.

## Motivation
Translation tasks easily fail due to LLM timeouts on massive parameter models or output formatting issues. Utilizing a separate, potentially more stable fallback model exclusively for retries (while staying within the same API gateway to reuse keys and endpoint URLs) significantly improves overall task success rates and system robustness without adding complex multi-vendor secret management.
