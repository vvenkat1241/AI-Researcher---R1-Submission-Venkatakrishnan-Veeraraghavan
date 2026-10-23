# AI-Researcher---R1-Submission-Venkatakrishnan-Veeraraghavan
## AI Researcher - R1 Submission

### Overview

This project implements a command-line pipeline that attempts to classify natural-language staffing-rota puzzles as **unique**, **ambiguous**, **inconsistent**, or **unknown**.

The pipeline separates language-model-based constraint extraction from deterministic symbolic solving. The model is prompted to translate statements into structured clues, while Python code validates the extracted clues and searches for assignments satisfying them. The final classification depends on the correctness and completeness of the extracted constraints.

### Architecture

The pipeline has four main stages:

1. **Input parsing:** Read the puzzle dataset and extract the people, time blocks, stations, station-eligible people, and statements.
2. **Constraint extraction:** Call the provided Granite model endpoint to map statements to typed clues with statement IDs and arguments.
3. **Validation:** Check clue types, argument keys, statement IDs, and references to known people, blocks, and stations. These checks enforce structural consistency but do not guarantee that each clue correctly represents its original statement.
4. **Symbolic solving:** Search for assignments satisfying the extracted constraints and produce a classification based on the solver's results.

The main components are:

- `run.py` — command-line interface, input parsing, model-call budgeting, and orchestration.
- `model_client.py` — model API client and structured-output schema.
- `prompt.py` — instructions and examples for extracting typed constraints.
- `solver.py` — extraction validation, constraint evaluation, assignment search, and result classification.

### Design decisions

#### Separate extraction from solving

Natural-language interpretation and combinatorial search are handled by separate components. The model is responsible for translating statements into the supported constraint vocabulary, while the symbolic solver applies the extracted constraints systematically.

This separation makes the solving process deterministic for a given set of constraints, but it does not guarantee that the extracted constraints are semantically correct.

#### Typed constraints and validation

Each extracted clue contains a statement ID, a clue kind, and an argument object. Structured-output constraints restrict the expected clue types and argument structure. Validation checks statement IDs and entity references against the puzzle's declared domain.

These checks help identify malformed extractions, but validly structured clues can still misinterpret the original statements and affect the final classification.

#### Handling uncertainty

The extraction prompt distinguishes asserted constraints from unrelated statements, unresolved questions, and rejected or counterfactual requests. When a statement cannot be represented safely, the model can return an `unknown` clue instead of inventing a constraint.

The solver can return `unknown` when extraction is incomplete or cannot be handled reliably. In the latest 1x run, this outcome occurred frequently, making extraction reliability the primary limitation observed in the results.

#### Model-call budgets

The CLI exposes the `1x`, `3x`, and `10x` budget settings. Model calls are tracked per item, and the model client is configured to use structured-output constraints and the required request settings.

Only the 1x configuration is reported in the evaluation below. No controlled comparison was completed to establish whether higher budgets improve performance.

### Running the project

Configure the model endpoint and credentials using the local environment configuration expected by `model_client.py`. Do not commit API keys or other secrets.

Run the solver with:

```bash
./run items.json --budget 1x --out answers.json
```

The other available budget settings are:

```bash
./run items.json --budget 3x --out answers.json
./run items.json --budget 10x --out answers.json
```

The output is a JSON object keyed by item ID. Each item contains a case classification and, where applicable, assignments, conflicts, or a reason explaining why the result is unknown.

The presence of an output entry does not necessarily indicate successful extraction or a correct classification; entries may also represent failures recorded as `unknown`.

### Evaluation: 1x baseline

The latest recorded 1x run processed all 60 dataset items and produced an output entry for each item. However, the run encountered extraction-related failures and an upstream HTTP 429 rate-limit error. No full run completed without errors.

| Classification | Items | Percentage |
|---|---:|---:|
| Unique | 1 | 1.7% |
| Ambiguous | 6 | 10.0% |
| Inconsistent | 6 | 10.0% |
| Unknown | 47 | 78.3% |
| **Total** | **60** | **100%** |

These figures are observed output counts, not verified accuracy measurements. No ground-truth comparison was performed, so the unique, ambiguous, and inconsistent classifications have not been confirmed as correct.

Most `unknown` results reported that one or more statements needed extraction repair. The run also encountered an upstream model-provider rate-limit error. These results indicate that the pipeline produced outputs for the dataset, but did not achieve reliable, error-free execution.

### Ablation and budget comparison

A controlled comparison of `1x`, `3x`, and `10x` was not completed. No measured conclusions can therefore be drawn about the effect of additional model calls, prompt changes, or alternative extraction strategies.

A future evaluation would compare the same dataset and verified ground-truth labels across budgets, reporting classification accuracy, unknown rate, extraction-validity rate, model-call usage, and runtime.

### Limitations and future work

- Maximizing the performance of a relatively weak model within the available call budget.
- Keeping prompts concise and structured to avoid overwhelming the model's context window.
- Improving constraint extraction reliability while preserving the required output format.
- Evaluating whether prompt and budget changes improve results without increasing context pressure.

### Conclusion

- Implemented the model-assisted constraint extraction and symbolic solving pipeline.
- The latest 1x run produced output entries for all 60 items, but 47 were classified as `unknown`.
- Extraction validation failures and an upstream rate-limit error prevented error-free execution.
- The main challenge was extracting the best possible performance from a weak model while staying within its context window and call budget.
