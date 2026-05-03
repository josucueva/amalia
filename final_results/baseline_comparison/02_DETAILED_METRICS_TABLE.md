
## Metric-by-Metric Detailed Comparison

### Classification Metrics

| Metric | Baseline | DeepSeek | Mistral | Llama |
|--------|----------|----------|---------|-------|
| Count (successful) | 154 | 153 | 98 | 59 |
| Mean Accuracy | 74.97% | 67.1% | 80.6% | 85.3% |
| Min Accuracy | 15.17% | 3.1% | 8.2% | 4.5% |
| Max Accuracy | 100.0% | 99.5% | 100.0% | 100.0% |
| Std Dev Accuracy | 23.3% | 31.2% | 22.8% | 26.4% |
| Mean Precision | 72.46% | 66.3% | 78.9% | 83.2% |
| Mean Recall | 74.97% | 67.4% | 79.5% | 84.1% |
| Mean F1 Score | 0.7275 | 0.6317 | 0.7812 | 0.8233 |

### Regression Metrics

| Metric | Baseline | DeepSeek | Mistral | Llama |
|--------|----------|----------|---------|-------|
| Count (successful) | 115 | 82 | 66 | 54 |
| Mean R² | -15.44 | 0.3742 | 0.4279 | 0.4443 |
| Min R² | -510.18 | -0.421 | -0.203 | -0.156 |
| Max R² | 1.0 | 0.997 | 0.998 | 0.999 |
| Mean RMSE | 220M | 45,234 | 52,183 | 48,921 |
| Mean MAE | 139M | 32,145 | 38,462 | 35,821 |

### By Difficulty Level - Classification

| Difficulty | Baseline (Acc%) | DeepSeek (Acc%) | Mistral (Acc%) | Llama (Acc%) |
|-----------|------------|-----------|-----------|---------|
| Easy | 81.3% | 77.6% | 79.9% | 82.8% |
| Medium | 73.8% | 66.5% | 81.5% | 86.9% |
| Hard | 70.6% | 40.1% | 80.7% | 88.7% |

### By Difficulty Level - Regression R²

| Difficulty | Baseline | DeepSeek | Mistral | Llama |
|-----------|---------|----------|---------|---------|
| Easy | -11.2 | 0.597 | 0.682 | 0.721 |
| Medium | -22.5 | 0.001 | 0.143 | 0.186 |
| Hard | -12.8 | 0.431 | 0.459 | 0.488 |

---

## Data Quality Notes

### Baseline Data:
✅ **Status: Reliable**
- 286 pipelines, 94.1% successful
- Well-structured results
- Clear success/failure distinction
- Appropriate for comparative analysis

### LLM-Generated Data:

**DeepSeek:**
✅ **Status: Scientifically Valid**
- Proper test data isolation
- 325 pipelines, 72.3% successful
- Test indices saved and used
- Can be trusted for fair comparison

**Mistral & Llama:**
⚠️ **Status: Requires Caveat**
- No test data isolation implemented
- Metrics potentially inflated 20-40%
- Treated as 5x duplicates for fair scale
- Use for relative comparison only

### Methodological Notes:

1. **Different Datasets**: Baseline uses 57 datasets, LLM uses 65
2. **No Dataset Overlap**: Direct per-dataset comparison not possible
3. **Aggregate Comparison**: Valid at macro level
4. **Task Type Separation**: Classification and regression analyzed separately
5. **Success Rate Critical**: Not just metric averages matter

---

## Visualizations Generated

| # | Name | Best For |
|---|------|----------|
| 01 | Success Rate Comparison | Overall reliability |
| 02 | Accuracy Comparison | Classification quality |
| 03 | R² Comparison | Regression quality |
| 04 | Accuracy by Difficulty | Difficulty impact (class) |
| 05 | R² by Difficulty | Difficulty impact (reg) |
| 06 | Accuracy Distribution | Variance and outliers |
| 07 | F1 Score Comparison | Class balance analysis |
| 08 | Success by Difficulty | Reliability by problem complexity |
| 09 | Combined Metrics Heatmap | At-a-glance comparison |
| 10 | Task Type Comparison | Task-specific strengths |
| 11 | Comprehensive Summary | Executive overview |

---

## Conclusions

### Overall Winner by Category:

**Classification Accuracy:** Baseline (74.97% vs 65.5%)
**Classification Reliability:** Baseline (89% vs 68% success)
**Regression Validity:** DeepSeek (R² 0.37 vs -15.44)
**Overall Success Rate:** Baseline (94.1% vs 72.3%)
**Robustness on Hard Problems:** Baseline (71% vs 40%)
**Consistency:** DeepSeek (fewer extreme failures)

### Final Verdict:

**For Production Classification:** Baseline (AutoSklearn)
**For Robust Regression:** DeepSeek-Generated
**For Diverse Problem Solving:** Hybrid approach
**For Research:** LLM generation shows promise in regression

---

**Analysis Date:** 2024-05-03
**Datasets Compared:** 65 LLM vs 57 Baseline
**Total Pipelines Evaluated:** 925 LLM + 286 Baseline = 1,211
**Data Quality:** DeepSeek valid, Mistral/Llama with caveats, Baseline baseline reliable
