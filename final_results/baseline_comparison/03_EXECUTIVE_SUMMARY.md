# Baseline vs LLM-Generated: Executive Summary

## Quick Facts

- **Baseline Success Rate:** 94.1% (269/286 pipelines)
- **LLM Success Rate:** 55.4% (512/925 pipelines)
- **DeepSeek Success Rate:** 72.3% (235/325 pipelines)

- **Classification Accuracy (Baseline):** 75.0%
- **Classification Accuracy (DeepSeek):** 65.5%
- **Gap:** -9.5 percentage points

- **Regression R² (Baseline):** -15.44 ⚠️ (BROKEN!)
- **Regression R² (DeepSeek):** 0.374 ✅ (VALID)
- **Advantage:** DeepSeek +15.8 points

## Key Takeaway: Different Strengths

| Task | Winner | Reason |
|------|--------|--------|
| **Classification** | Baseline | 75% accuracy vs 65% |
| **Regression** | DeepSeek | Valid models vs negative R² |
| **Success Rate** | Baseline | 94% vs 72% |
| **Hard Problems** | Baseline | 71% vs 40% |
| **Robustness** | Baseline | More stable |

## When to Use Each:

**Use Baseline if:** Classification task, need high accuracy, want stability
**Use DeepSeek if:** Regression task, baseline fails, need diverse approach
**Use Hybrid if:** Unsure, want best of both approaches

## Visualizations Summary

11 comprehensive visualizations generated showing:
- Success rate comparisons
- Metric comparisons (accuracy, F1, R²)
- Difficulty level analysis
- Task type breakdown
- Distribution analysis
- Heatmap comparisons

See `figs/` folder for all visualizations.
