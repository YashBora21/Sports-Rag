# RAGAS Temperature Parameter Fix

## Problem
The RAGAS evaluation script was failing with:
```
TypeError(GenerativeServiceClient.generate_content() got an unexpected keyword argument 'temperature')
```

This occurred because of a version incompatibility between:
- **RAGAS 0.1.21** - which passes `temperature` directly as a keyword argument
- **google-generativeai 0.7.2** - which no longer accepts `temperature` directly in `generate_content()`

## Root Cause
In google-generativeai 0.6.0+, the API changed to use `generation_config` parameter with a `GenerationConfig` object instead of passing parameters like `temperature` directly to the method.

RAGAS 0.1.21 (released before this breaking change) still uses the old API pattern, causing the error.

## Solution
Downgraded `google-generativeai` from **0.7.2** to **0.4.1** in `requirements.txt`.

Version 0.4.1 still supports the direct `temperature` parameter pattern that RAGAS 0.1.21 expects.

## Changes Made
- **requirements.txt**: Changed `google-generativeai==0.7.2` → `google-generativeai==0.4.1`

## Installation
To apply this fix, reinstall the dependencies:
```bash
pip install -r requirements.txt
```

Or specifically update google-generativeai:
```bash
pip install google-generativeai==0.4.1
```

## Alternative Solutions
If you need the newer google-generativeai features:
1. **Upgrade RAGAS** to version 0.2.8+ (which supports the new API)
2. **Use a different LLM provider** for RAGAS evaluation (e.g., OpenAI's ChatGPT via langchain_openai)

## Verification
After applying the fix, run:
```bash
python scripts/run_ragas_eval.py
```

The evaluation should progress without the temperature-related TypeError.
