# Instruction-Following Robustness Dataset Generation (Arabic--English)

**Author:** Obie Mohammed\
**Course:** NLP / Foundation Models\
**Type:** Individual Project Summary

------------------------------------------------------------------------

## Objective

The goal of this project was to generate a high-quality synthetic
dataset for preference tuning of large language models (LLMs), focusing
on **language consistency and instruction-following robustness**.\
Arabic prompts are expected to produce Arabic answers, while English
outputs represent failure cases (rejected samples).\
The dataset follows the HuggingFace TRL conversational format.

------------------------------------------------------------------------

## Dataset Design

Each data sample contains: - **Prompt:** User instruction written in
Arabic. - **Chosen:** A valid Arabic response. - **Rejected:** An
English or language-violating response.

Prompts are automatically generated using diverse templates: -
Daily-life and general knowledge questions. - Technical terms written
using Arabic letters (e.g., الديناميك). - Mixed Arabic--English
triggers. - Comparisons, lists, summaries, and explanations.

These patterns intentionally increase the probability of language
confusion.

------------------------------------------------------------------------

## Generation Pipeline (Algorithm Summary)

1.  **Prompt Generation**\
    Thousands of Arabic prompts are generated using randomized templates
    and stored in JSONL format.

2.  **First LLM Call (Natural Behavior)**\
    The LLM answers the prompt without enforcing language constraints.

3.  **Language Validation**\
    Character-ratio heuristics classify the output as Arabic-dominant or
    English-dominant.

4.  **Hybrid Labeling Strategy**

    -   If the first answer is Arabic → it becomes the **chosen**
        sample.
    -   If the first answer is English → it becomes the **rejected**
        sample (natural failure case).

5.  **Fallback Completion**

    -   If **chosen** is missing → regenerate with Arabic-only
        constraint.
    -   If **rejected** is missing → generate by rewriting the Arabic
        answer into English.

6.  **Optional Quality Check** A lightweight additional LLM call
    periodically verifies that the Arabic answer actually addresses the
    prompt.

7.  **Checkpointing and Recovery** Each accepted triple is written
    immediately to disk with progress tracking, allowing safe recovery
    after connection failures.


------------------------------------------------------------------------

## Outcome

The result is a scalable synthetic dataset suitable for supervised or
preference fine-tuning of multilingual LLMs, emphasizing robustness
against language drift and instruction violations.
