# Evaluation and Testing

How to measure whether your context engineering is working and systematically improve it.

---

## Measuring Context Quality

### Output Quality Dimensions

| Dimension | What It Measures | How to Assess |
|---|---|---|
| Accuracy | Are facts and code correct? | Compare against ground truth, run tests |
| Completeness | Does the response address the full request? | Checklist against requirements |
| Consistency | Are responses stable across similar inputs? | Run same prompt 5-10 times, compare |
| Relevance | Is the response focused on what was asked? | Check for tangential content |
| Efficiency | Minimal tokens for maximum value? | Measure response length vs info density |
| Format Compliance | Does output match specified format? | Validate against schema/template |

Score each dimension independently on a 1-5 scale. A single aggregate score hides problems — a response can be accurate but verbose, or well-formatted but incomplete.

### Context Quality Signals

When outputs are poor, the cause is often in the context, not the model.

| Signal | Indicates | Action |
|---|---|---|
| Model ignores late instructions | Position bias, context too long | Move instructions to start, add XML structure |
| Hallucinated function names | Missing code context | Improve retrieval, add relevant files |
| Generic responses | System prompt too high altitude | Lower altitude with more specific guidance |
| Overly rigid responses | System prompt too low altitude | Raise altitude to principles |
| Wrong tool selected | Ambiguous tool descriptions | Rewrite descriptions, reduce tool count |
| Repeated similar answers | Context rot | Compress conversation, add diversity cues |
| Contradicting earlier responses | Compaction lost key info | Improve compaction strategy, preserve decisions |

---

## A/B Testing Prompts

### The Process
1. **Baseline**: Run current prompt on 20-50 test cases, record outputs
2. **Variant**: Modify one aspect of the prompt (not multiple changes at once)
3. **Evaluate**: Score both sets on the quality dimensions above
4. **Compare**: Statistical comparison (is the improvement consistent?)
5. **Iterate**: Keep winner, test next hypothesis

### What to A/B Test
- System prompt wording (altitude changes)
- Example selection (different multishot examples)
- Output format instructions
- XML structure vs plain text instructions
- Tool descriptions
- Context selection (which documents to include)
- Compaction strategies

### Single Variable Testing

Change ONE thing at a time. If you change both the system prompt AND the examples, you can't attribute improvement to either change.

| Round | Change | Measure |
|---|---|---|
| 1 | Add XML structure to prompt | Consistency, format compliance |
| 2 | Add 3 multishot examples | Accuracy, edge case handling |
| 3 | Raise system prompt altitude | Generalization, brevity |
| 4 | Add retrieval for context | Accuracy, completeness |

**Sample size matters.** Test on 20+ inputs to distinguish real improvement from noise. Record results for each round:

```
Round: 3
Change: Replaced step-by-step instructions with principles
Baseline: Accuracy 4.2, Completeness 3.8, Relevance 3.5
Variant:  Accuracy 4.0, Completeness 3.6, Relevance 4.1
Decision: Keep — relevance improved; add examples to recover completeness
```

---

## Memory Metrics

### Precision and Recall
- **Precision**: Of the memories retrieved, how many were actually relevant?
  - Low precision = noisy retrieval, irrelevant context injected
  - Fix: Better embedding model, stricter similarity thresholds, re-ranking

- **Recall**: Of the relevant memories that exist, how many were retrieved?
  - Low recall = useful memories missed
  - Fix: Better query formulation, lower similarity thresholds, multiple search strategies

### Recall@K
- Of the relevant memories, how many appear in the top K results?
- Recall@5 is most important — agents rarely use more than 5 retrieved items effectively
- Target: Recall@5 > 0.7 for your most common query types

### Memory Quality Indicators

| Metric | Healthy Range | Warning Sign |
|---|---|---|
| Active observations | Growing slowly | Explosive growth (>50/week) = low quality |
| Resolution rate | 10-20% per month | 0% = never maintaining, >50% = storing too much trivia |
| Retrieval relevance | >70% relevant in top 5 | <50% = classification or embedding problems |
| Memory types distribution | Mix of all types | 90%+ one type = narrow capture |
| Duplicate rate | <5% | >10% = not searching before storing |

---

## Iterative Improvement Workflow

### The Feedback Loop

```
1. Identify a failure mode (wrong output, missed info, hallucination)
   |
   v
2. Diagnose root cause (bad prompt? missing context? wrong retrieval?)
   |
   v
3. Hypothesize fix (raise altitude? add examples? improve retrieval?)
   |
   v
4. Apply ONE change
   |
   v
5. Test on the original failure case + 5-10 similar cases
   |
   v
6. Did it improve without regressing other cases?
   |-- Yes -> Keep change, go to step 1 with next failure mode
   |-- No  -> Revert change, try different hypothesis (step 3)
```

### Failure Mode to Root Cause Mapping

| Failure Mode | Likely Root Cause | First Fix to Try |
|---|---|---|
| Model ignores instructions | Context too long, instructions buried | Compress context, move instructions to system prompt start |
| Inconsistent output format | No examples of expected format | Add 3 multishot examples with exact output format |
| Hallucinated information | Model lacking context it needs | Add retrieval (RAG) for the missing knowledge |
| Correct but verbose | No conciseness instruction | Add explicit length/brevity constraint |
| Handles common cases, fails edge cases | Examples only show happy path | Add edge case examples (2-3 tricky inputs) |
| Works for simple queries, fails complex | Single-shot overload | Chain into multiple steps, add CoT |
| Uses wrong tool | Tool descriptions overlap | Rewrite descriptions to be mutually exclusive |
| Starts strong, degrades over time | Context rot | Add compaction at 60% capacity, repeat key instructions |
| Different result each time | Underdetermined prompt | Add more constraints, examples, or structured output format |

Prioritize fixes by **frequency** (how often it occurs), **severity** (how bad the outcome is), and **fixability** (can you address the root cause?). Fix high-frequency, high-severity issues first.

---

## Common Failure Modes

| Failure Mode | Symptom | Category | Remedy |
|---|---|---|---|
| Prompt injection | Model ignores system prompt | Security | Input sanitization, separate user/system context |
| Context overflow | Truncated or missing information | Capacity | Compress, isolate, select less |
| Stale retrieval | Outdated information surfaces | Memory | Resolve/supersede old observations, refresh index |
| Over-retrieval | Too many results injected | Selection | Stricter top-K, re-ranking |
| Under-retrieval | Relevant information not found | Selection | Better embeddings, query expansion |
| Goal drift | Agent forgets original task | Session | Goal scratchpad, periodic restatement |
| Tool abuse | Model calls tools unnecessarily | Selection | Fewer tools, clearer descriptions |
| Format drift | Output format degrades over conversation | Compression | Repeat format instructions after compaction |
| Anchor bias | First example dominates outputs | Examples | Diverse examples, put the "typical" case second |
| Sycophancy | Model agrees with incorrect user statements | System prompt | Add "push back when the user is wrong" instruction |

---

## Testing Checklist

Before deploying a prompt/context configuration:

- [ ] Tested on 10+ diverse inputs (not just the examples used in the prompt)
- [ ] Edge cases covered: empty input, very long input, ambiguous input, off-topic input
- [ ] Output format consistent across all test cases
- [ ] No hallucinated information in any test output
- [ ] Performance acceptable within token/cost budget
- [ ] Compaction tested: still works after 20+ turns of conversation
- [ ] Retrieval tested: correct memories/documents surface for test queries
- [ ] Negative testing: model correctly refuses out-of-scope requests
