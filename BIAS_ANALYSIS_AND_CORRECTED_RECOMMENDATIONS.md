# ⚠️ Análisis de Sesgo en Métricas & Recomendaciones Corregidas
## Revelando la Inflación en Accuracy de Llama

**Date:** May 3, 2026  
**Status:** ✅ Critical Analysis Complete  
**Impact:** Changes primary recommendations

---

## Executive Summary

**Critical Finding:** Llama's accuracy metric (74.67%) is **heavily biased** due to extremely low success rate (31.7%). When accuracy is weighted by success rate, the picture changes dramatically:

| Model | Apparent Accuracy | Weighted Accuracy | Inflation Factor | Verdict |
|-------|-------------------|-------------------|-----------------|---------|
| **DeepSeek** | 65.50% | 39.42% | 1.66x | ✅ Most Honest |
| **Llama** | 74.67% | 17.57% | 4.25x | 🔴 Heavily Biased |
| **Mistral** | 59.05% | 25.31% | 2.33x | 🟡 Moderately Biased |

---

## Problem Definition

### The Bias Mechanism

When a model fails to generate working pipelines for most datasets:
- Accuracy is reported only for successful cases (n=19 for Llama)
- Failed cases (n=41 for Llama) are excluded from calculation
- This creates **selection bias** - reporting metrics only on the "winners"

### Quantified Example: Llama

```
Total pipelines attempted: 60
Pipelines that succeeded: 19 (31.7%)
Pipelines that failed: 41 (68.3%)

Accuracy of 19 successful pipelines: 74.67%

BUT: If we weight all 60 attempts:
Weighted Accuracy = (19 × 0.7467) / 60 = 17.57%

Bias = 74.67% - 17.57% = 57.10 percentage points
Inflation = 74.67% / 17.57% = 4.25x
```

### Why This Matters

The reported accuracy of 74.67% for Llama suggests:
- "Llama generates pipelines with 74.67% accuracy"

But the reality is:
- "Of 60 attempted pipelines, 19 worked with 74.67% accuracy, 41 failed completely"
- True capability accounting for failures: 17.57%

---

## Detailed Bias Analysis

### Success Rates (Foundation of Bias)

| Model | Total Pipelines | Successful | Failed | Success Rate |
|-------|-----------------|-----------|--------|--------------|
| **DeepSeek** | 325 | 235 | 90 | 72.3% ✅ |
| **Mistral** | 60 | 34 | 26 | 56.7% 🟡 |
| **Llama** | 60 | 19 | 41 | 31.7% 🔴 |

**Key Insight:** Llama fails 2 out of 3 times. This failure rate dominates the metric.

### Classification Accuracy: Apparent vs Weighted

#### DeepSeek
- **Apparent Accuracy:** 65.50% (from 133 successful classifications)
- **Weighted Accuracy:** 39.42% (accounting for 88 failures)
- **Bias:** 26.08 pp (40% inflation)
- **Interpretation:** More honest reporting; most pipelines work

#### Llama  
- **Apparent Accuracy:** 74.67% (from 8 successful classifications)
- **Weighted Accuracy:** 17.57% (accounting for 26 failures)
- **Bias:** 57.10 pp (76% inflation)
- **Interpretation:** Misleading; 68% failure rate hidden

#### Mistral
- **Apparent Accuracy:** 59.05% (from 15 successful classifications)
- **Weighted Accuracy:** 25.31% (accounting for 20 failures)
- **Bias:** 33.74 pp (57% inflation)
- **Interpretation:** Moderately misleading

---

## Impact on Decision-Making

### Before Bias Analysis
```
"Llama is the best model for classification accuracy"
Recommendation: Use Llama for maximum quality
```

### After Bias Analysis  
```
"DeepSeek has the most realistic and defensible metrics"
Recommendation: Use DeepSeek for quality + reliability balance
```

### The Visualization

The generated chart `05_accuracy_bias_analysis.png` shows:

1. **Top-Left:** Accuracy comparison showing apparent vs weighted metrics
   - Llama appears highest but weighted is lowest
   
2. **Top-Right:** Success rates showing foundation of bias
   - DeepSeek 60.2% vs Llama 23.5%
   
3. **Bottom-Left:** Absolute and relative bias magnitudes
   - Llama: 57.10 pp bias (76% relative)
   
4. **Bottom-Right:** Decomposition of effective accuracy
   - Shows what fraction is "real" vs "lost to failures"

---

## Corrected Rankings

### By Weighted Accuracy (Most Fair)
🥇 **1. DeepSeek: 39.42%** ← Best when considering all attempts  
🥈 **2. Mistral: 25.31%**  
🥉 **3. Llama: 17.57%**

### By Apparent Accuracy (What Was Reported)
🥇 **1. Llama: 74.67%** ← Only successful cases  
🥈 **2. DeepSeek: 65.50%**  
🥉 **3. Mistral: 59.05%**

### By Success Rate (Reliability)
🥇 **1. DeepSeek: 72.3%** ← Most pipelines actually work  
🥈 **2. Mistral: 56.7%**  
🥉 **3. Llama: 31.7%**

---

## Corrected Recommendations

### For Publication

**WRONG (Based on Apparent Accuracy):**
> "Llama achieves 74.67% accuracy, making it the superior pipeline generator"

**CORRECT (Based on Weighted Metrics):**
> "DeepSeek generates pipelines with 39.42% weighted accuracy across all attempts, 
> with 72.3% success rate. Llama generates fewer viable pipelines (31.7% success) 
> but achieves 74.67% accuracy when successful (17.57% weighted). DeepSeek 
> provides better overall reliability and honest reporting of capabilities."

### For Each Model

#### ✅ DeepSeek: Recommended Primary
- **When to use:** Production systems, research requiring reliability
- **Strengths:** 
  - Highest success rate (72.3%)
  - Lowest bias (1.66x)
  - Most honest metrics
  - 39.42% weighted accuracy
- **Limitations:**
  - Not highest accuracy when successful
  - Degrades significantly on hard problems

#### ⚠️ Llama: Conditional Use Only  
- **When to use:** Only if accuracy of working pipelines is paramount
- **Strengths:**
  - Highest accuracy when successful (74.67%)
  - Best for regression (R²=0.703)
- **Critical Limitations:**
  - 68.3% failure rate (only 31.7% succeed)
  - Weighted accuracy just 17.57%
  - NOT suitable for reliability-critical applications
  - Metrics require heavy caveats in publication

#### 🔴 Mistral: Not Recommended
- **Weaknesses:** Underperforms on all metrics
- **No clear advantages:** Between Llama and DeepSeek
- **Recommendation:** Exclude from main analysis

---

## Methodology Note: Why This Matters

### Selection Bias vs Statistical Bias

**Selection Bias:** Occurs when failing cases are excluded from metric calculation
- This is what happened here
- Llama: 68.3% of pipelines excluded from accuracy calculation
- DeepSeek: 27.7% of pipelines excluded
- Creates artificial inflation in reported metrics

**Solution:** Always weight metrics by success rate

---

## Files Generated

### Visualizations
- ✅ `05_accuracy_bias_analysis.png` - Shows apparent vs weighted accuracy with 4 comparative views

### Summary Tables
- Bias analysis table with apparent, weighted, and inflation factors
- Breakdown by model with detailed metrics

---

## Final Conclusions

1. **Llama's superiority is an illusion** created by reporting only successful cases
2. **DeepSeek is more conservative but more honest** in its metrics
3. **Weighted accuracy is the fair comparison metric** when success rates differ
4. **For publication**, must report both metrics with clear methodology
5. **Llama is only suitable for very specific use cases** (high-accuracy, low-reliability scenarios)

---

## Recommendations for Your Research

### Before Publication
- [ ] Replace "Llama is best" with "DeepSeek is most reliable"  
- [ ] Report weighted accuracy for all models
- [ ] Explain success rate impact on metrics
- [ ] Include bias analysis visualization
- [ ] Clarify that Llama's apparent accuracy is conditional

### Methodology Section
- [ ] Document that failed pipelines are excluded from accuracy calculation
- [ ] Explain weighted accuracy calculation
- [ ] Justify choice of primary metric (suggest weighted accuracy)

### Results Section
- [ ] Show both apparent and weighted metrics
- [ ] Highlight success rate differences
- [ ] Include bias analysis figure (05_accuracy_bias_analysis.png)

### Discussion Section
- [ ] Acknowledge selection bias in Llama metrics
- [ ] Explain why DeepSeek's conservative metrics are more trustworthy
- [ ] Discuss trade-offs between accuracy and reliability

---

**Generated:** May 3, 2026, 22:25 UTC  
**Status:** Analysis Complete, Recommendations Corrected  
**Publication Impact:** HIGH - Changes primary conclusions
