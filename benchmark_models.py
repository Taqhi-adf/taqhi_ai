import time
import pandas as pd
import ollama

# 1. Define models to compare
MODELS = ["qwen2.5:7b", "llama3.2:3b"]

# 2. Test Prompts (Accuracy / Reasoning / Code Execution)
TEST_PROMPTS = [
    {
        "category": "Reasoning & Math",
        "prompt": "If 5 cats catch 5 mice in 5 minutes, how long does it take 100 cats to catch 100 mice? Explain step-by-step.",
    },
    {
        "category": "SQL Generation",
        "prompt": "Write an ANSI SQL query to find the 3rd highest salary from an 'employees' table. Output only valid SQL.",
    },
    {
        "category": "Extraction",
        "prompt": "Extract the phone number and email from this text: 'Contact us at support@example.com or call +1-800-555-0199.' Format as JSON.",
    },
]


def evaluate_model(model_name, prompt):
    print(f"Running {model_name}...")
    start_time = time.time()

    # Send request to local Ollama API
    response = ollama.chat(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
    )

    elapsed_time = round(time.time() - start_time, 2)

    # Extract metrics from Ollama metadata
    eval_count = response.get("eval_count", 0)  # Total tokens generated
    eval_duration = response.get("eval_duration", 1) / 1e9  # Convert ns to sec
    prompt_eval_count = response.get("prompt_eval_count", 0)  # Input tokens

    tokens_per_second = round(eval_count / eval_duration, 2) if eval_duration > 0 else 0

    return {
        "Model": model_name,
        "Total Output Tokens": eval_count,
        "Input Tokens": prompt_eval_count,
        "Latency (s)": elapsed_time,
        "Tokens/Sec": tokens_per_second,
        "Response": response["message"]["content"],
    }


# 3. Run Benchmark
results = []
for test in TEST_PROMPTS:
    print(f"\n--- Category: {test['category']} ---")
    for model in MODELS:
        res = evaluate_model(model, test["prompt"])
        res["Category"] = test["category"]
        results.append(res)

# 4. Process and Display Results
df = pd.DataFrame(results)

# Print Performance Metrics Summary
print("\n" + "=" * 80)
print("BENCHMARK METRICS SUMMARY")
print("=" * 80)
metrics_df = df[[
    "Category",
    "Model",
    "Tokens/Sec",
    "Latency (s)",
    "Total Output Tokens",
    "Input Tokens",
]]
print(metrics_df.to_string(index=False))

# Print Output Quality for Review
print("\n" + "=" * 80)
print("ACCURACY & OUTPUT COMPARISON")
print("=" * 80)
for test in TEST_PROMPTS:
    cat = test["category"]
    print(f"\nPROMPT [{cat}]: {test['prompt']}")
    print("-" * 60)
    for model in MODELS:
        resp = df[(df["Category"] == cat) & (df["Model"] == model)][
            "Response"
        ].values[0]
        print(f"[{model.upper()}]:\n{resp}\n")