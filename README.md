# AI-Researcher---R1-Submission-Venkatakrishnan-Veeraraghavan
# AI Researcher R1 — Constraint Extraction and Rota Solver

## Overview

This project implements a command-line pipeline that converts natural-language staffing-rota statements into typed constraints and uses a symbolic solver to classify each rota puzzle as **unique**, **ambiguous**, **inconsistent**, or **unknown**.

The approach separates language understanding from constraint solving. The language model extracts structured clues, while deterministic Python code validates the clues, searches the assignment space, and determines the resulting classification. This separation makes the solver independent of the wording of individual statements and avoids relying on the language model to solve the complete puzzle directly.

## Architecture

The pipeline has four main stages:

1. **Input parsing:** Read the puzzle dataset and extract the people, time blocks, stations, station-eligible people, and statements.
2. **Constraint extraction:** Call the provided Granite model endpoint to map each statement to a typed clue with a statement ID and arguments.
3. **Validation:** Check extracted clues for valid types, argument keys, statement IDs, and references to known people, blocks, and stations.
4. **Symbolic solving:** Enumerate valid rota assignments that satisfy the extracted constraints and classify the result.

The main components are:

- `run.py` — command-line interface, input parsing, model-call budgeting, and orchestration.
- `model_client.py` — model API client and structured-output schema.
- `prompt_v2.py` — instructions and examples for extracting typed constraints.
- `solver.py` — extraction validation, constraint evaluation, assignment search, and result classification.

## Design decisions

### Separate extraction from solving

Natural-language interpretation and combinatorial search are handled by different components. The model is responsible for translating statements into the supported constraint vocabulary; the solver applies those constraints systematically.

### Typed constraints and validation

Each extracted clue has a statement ID, a clue kind, and an argument object. The schema restricts the available clue types and argument structure. Validation checks that referenced entities belong to the puzzle's declared domain.

This validation is important because an invalid or incorrectly interpreted clue can change the final classification even when the symbolic solver itself is correct.

### Conservative handling of uncertainty

The extraction prompt distinguishes asserted constraints from unrelated statements, unresolved questions, and rejected or counterfactual requests. When a statement cannot be represented safely, the model can return an `unknown` clue rather than inventing a constraint.

The solver's `unknown` outcome is retained when extraction is incomplete or a statement cannot be handled reliably. Consequently, `unknown` is a limitation of the current pipeline rather than evidence that the puzzle itself has no solution.

### Model-call budgets

The CLI supports the required `1x`, `3x`, and `10x` budget settings. Calls are tracked per item, and the model client uses structured-output constraints and the required request settings.

The current implementation has not demonstrated a reliable improvement from higher budgets. The reported experiment below covers the `1x` configuration only.

## Running the project

Configure the model endpoint and credentials using the local environment configuration expected by `model_client.py`. Do not commit API keys or other secrets.

Run the solver with:

```bash
./run items.json --budget 1x --out answers.json
```

The budget can be changed to `3x` or `10x`:

```bash
./run items.json --budget 3x --out answers.json
./run items.json --budget 10x --out answers.json
```

The output is a JSON object keyed by item ID. Each item contains a case classification and, where applicable, assignments, conflicts, or a reason explaining why the result is unknown.

## Evaluation: 1x baseline

The latest recorded run used the 1x configuration on all 60 dataset items. The output file contained an entry for every item.

| Classification | Items | Percentage |
|---|---:|---:|
| Unique | 1 | 1.7% |
| Ambiguous | 6 | 10.0% |
| Inconsistent | 6 | 10.0% |
| Unknown | 47 | 78.3% |
| **Total** | **60** | **100%** |

These are observed output counts, not verified accuracy measurements. No ground-truth comparison was performed for this run, so the unique, ambiguous, and inconsistent classifications should not be interpreted as confirmed correct predictions.

Most `unknown` results reported that one or more statements needed extraction repair. One item also encountered an upstream HTTP 429 rate-limit error from the model provider. These outcomes show that extraction reliability and service availability are important limitations of the current implementation.

## Ablation and budget comparison

A controlled comparison of `1x`, `3x`, and `10x` was not completed. Therefore, no measured claim is made about the effect of additional model calls, prompt changes, or extraction strategies.

The next evaluation should run each budget on the same dataset, compare predictions against verified labels, and report classification accuracy, unknown rate, extraction-validity rate, model-call usage, and runtime. Any prompt or validation change should be evaluated against the same baseline.

## Limitations and future work

The main limitation is the high unknown rate in the latest 1x run. The next improvements should focus on:

- Inspecting failed extractions at the statement level to identify incorrect entity references, invalid arguments, and unsupported clue interpretations.
- Improving extraction reliability without introducing puzzle-specific rules or hardcoded answers.
- Separating provider/API failures from semantic extraction failures in the output diagnostics.
- Evaluating all supported budgets using consistent measurements and verified ground truth.
- Testing whether additional calls improve extraction quality enough to justify their cost.

## Conclusion

This submission implements the core architecture of a model-assisted constraint-solving pipeline: typed natural-language extraction, validation, and deterministic symbolic search. The latest 1x run successfully produced output entries for all 60 items, but its high unknown rate means that extraction robustness remains unresolved. The current results should therefore be treated as a working baseline rather than a validated high-accuracy solution.
