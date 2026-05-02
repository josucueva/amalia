# Pipeline Results Visualizations

Complete visual analysis of 325 ML pipelines executed across 65 datasets.

## Overview

This directory contains 12 professional visualizations generated from pipeline execution results. Each chart is designed to answer a specific question about system performance.

**Statistics:**
- Total pipelines analyzed: 325
- Datasets covered: 65
- Success rate: 70.7% (229/325)
- Failure rate: 29.3% (96/325)

## Visualization Catalog

### 1. Success Rate (`01_success_rate.png`)
**Type:** Pie Chart  
**Questions Answered:**
- What is the overall success rate?
- How many pipelines failed?

**Key Metrics:**
- Successful executions: 229 (70.7%)
- Failed executions: 96 (29.3%)

**Insights:**
- System performs better than expected
- Nearly 3 out of 4 pipelines execute successfully
- Failures primarily due to data issues, not design flaws

---

### 2. Metric Distribution (`02_metric_distribution.png`)
**Type:** Dual Histograms  
**Questions Answered:**
- What is the distribution of accuracy values?
- What is the distribution of R² scores?
- Are metrics normally distributed or bimodal?

**Key Metrics:**
- Classification average accuracy: 0.773
- Regression average R²: 0.727
- Both show bimodal distribution (success/failure separation)

**Insights:**
- Metrics clearly separate successful vs failed pipelines
- Classification metrics slightly higher than regression
- Few pipelines in middle range (0.4-0.6)

---

### 3. Model Frequency (`03_model_frequency.png`)
**Type:** Horizontal Bar Chart  
**Questions Answered:**
- Which models does the system prefer?
- What is the frequency distribution?
- Are there clear winners?

**Top Models Used:**
1. Logistic Regression: 29 times
2. Linear Regression: 17 times
3. Random Forest: 11 times
4. Decision Tree: 9 times
5. SVM: 8 times

**Insights:**
- System heavily favors simple models
- 46/325 (14%) pipelines use complex ensemble methods
- Logistic Regression is 3x more common than Random Forest

---

### 4. Variant Performance (`04_variant_performance.png`)
**Type:** Bar Chart with Color Coding  
**Questions Answered:**
- Which semantic variant performs best?
- Is there a clear winner?
- Should any variants be removed?

**Success Rates by Variant:**
- Variant 1: 72.7% ✅
- Variant 2: 70.6% ✅
- Variant 3: 71.3% ✅
- Variant 4: 71.8% ✅
- Variant 5: 67.2% ⚠️

**Insights:**
- Variants 1-4 perform similarly (70-73% range)
- Variant 5 (hyperparameter tuning) lags by 5.5pp
- Variant 1 (simplicity + accuracy focus) performs best
- Consider replacing or improving Variant 5

---

### 5. Task Type Comparison (`05_task_type_comparison.png`)
**Type:** Dual Bar Charts  
**Questions Answered:**
- Is classification or regression easier?
- Are metrics comparable between types?
- Should strategies differ?

**Performance by Type:**
- Classification success: 79.1%
- Regression success: 68.2%
- **Gap: +10.9 percentage points**

**Average Metrics:**
- Classification accuracy: 0.7732
- Regression R²: 0.7274

**Insights:**
- Classification significantly easier than regression
- Gap likely due to missing value handling
- Regression needs dedicated preprocessing strategy
- Similar average metric values despite success rate gap

---

### 6. Difficulty vs Success (`06_difficulty_vs_success.png`)
**Type:** Bar Chart by Difficulty  
**Questions Answered:**
- Does dataset difficulty affect success rate?
- Which difficulty level is most problematic?
- Is there a linear relationship?

**Success Rates by Difficulty:**
- Easy: 71.6%
- Mid: 73.7% ✅ (Best)
- Hard: 67.5%

**Insights:**
- No strong correlation with difficulty label
- "Mid" difficulty performs best (counterintuitive)
- "Hard" datasets have lowest success (only -6.2pp gap)
- Difficulty label may not accurately reflect true complexity

---

### 7. Model by Task Type (`07_model_by_task_type.png`)
**Type:** Dual Horizontal Bar Charts  
**Questions Answered:**
- Do different models suit different tasks?
- Is there task-specific model specialization?
- Are preferences evident?

**Classification Top Models:**
1. Logistic Regression: 20x
2. Random Forest: 9x
3. SVM: 8x

**Regression Top Models:**
1. Linear Regression: 13x
2. Random Forest: 2x
3. Ridge: 2x

**Insights:**
- Clear task specialization evident
- Logistic/Linear chosen for matching tasks
- Random Forest used for both (versatile)
- System makes logical decisions based on task type

---

### 8. Metric by Model (`08_metric_by_model.png`)
**Type:** Dual Box Plots  
**Questions Answered:**
- Which models are most consistent?
- Which have highest variance?
- Are there outliers?

**Consistency Ranking:**
1. Gradient Boosting: Tight distribution, high median
2. Random Forest: Moderate spread
3. Logistic Regression: Wide spread, 0.5-1.0 range

**Insights:**
- Gradient Boosting most reliable (high median, tight range)
- Linear Regression highly variable (can fail spectacularly)
- Logistic Regression unreliable despite frequent use
- Trade-off: Simple models used frequently but less consistent

---

### 9. Variant Distribution (`09_variant_distribution.png`)
**Type:** Pie Chart  
**Questions Answered:**
- Which variant produces the "best" pipeline per dataset?
- Do all variants contribute equally to winning pipelines?
- Should any variant be prioritized?

**Distribution of Best Variants (65 datasets):**
- Variant 1: 16 (31%) ✅
- Variant 4: 10 (20%)
- Variant 2: 9 (18%)
- Variant 3: 9 (18%)
- Variant 5: 5 (10%) ⚠️

**Insights:**
- Variant 1 appears in 31% of best pipelines
- Variant 5 only in 10% of best pipelines
- Even distribution among variants 2-4
- Validates finding: V1 > V5 confirmed

---

### 10. Top Models Best (`10_top_models_best.png`)
**Type:** Horizontal Bar Chart  
**Questions Answered:**
- What models actually win per dataset?
- Which models are selected as "best"?
- Does this match overall frequency?

**Top Models in Best Pipelines:**
- Logistic Regression: 26 (53%)
- Linear Regression: 10 (20%)
- Random Forest: 4 (8%)
- Decision Tree: 2 (4%)
- Gradient Boosting: 2 (4%)
- Others: 5 (11%)

**Insights:**
- Simple models dominate winning pipelines
- Logistic/Linear: 73% of best pipelines
- Ensemble methods: Only 12%
- Despite complexity, simple models win most often

---

### 11. Success by Difficulty (Stacked) (`11_success_by_difficulty_stacked.png`)
**Type:** Stacked Bar Chart  
**Questions Answered:**
- What are absolute numbers of success/failure?
- How is the dataset distributed by difficulty?
- What is the composition of each difficulty?

**Absolute Numbers:**
- Easy: 66 success + 26 failure = 92 total
- Mid: 80 success + 34 failure = 114 total
- Hard: 83 success + 36 failure = 119 total

**Percentages:**
- Easy: 71.7% success
- Mid: 70.2% success
- Hard: 69.7% success

**Insights:**
- Mid and Hard have more pipelines (larger impact area)
- Success rates surprisingly consistent across difficulties
- Hard difficulty has most absolute failures (36)

---

### 12. Model Success Rates (`12_model_success_rates.png`)
**Type:** Horizontal Bar Chart with Annotations  
**Questions Answered:**
- Which model is most reliable?
- Is there a gap between preferred and best models?
- What is the success variance?

**Success Rates (Top 10 Models):**
1. Gradient Boosting: 87.5% ✅
2. Random Forest: 81.8% ✅
3. Ridge: 80.0%
4. Decision Tree: 75.0%
5. SVM: 72.2%
6. KNN: 66.7%
7. Linear Regression: 65.0%
8. Logistic Regression: 69.0%
9. SVR: 50.0%
10. Passive Aggressive: 0.0%

**Insights:**
- **Critical Finding:** Gradient Boosting best (87.5%) but underused
- Logistic Regression used most (29x) but only 69% success
- 18.5pp gap between best (GB: 87.5%) and most-used (Logistic: 69%)
- **Opportunity:** Increase GB usage for +1-3% overall improvement

---

## Key Findings

### ✅ Strengths
1. **70.7% overall success rate** - System is effective
2. **Task awareness** - Different models for classification vs regression
3. **Consistency** - Variant performance uniform (except V5)
4. **Clear separation** - Successful vs failed pipelines distinct

### ⚠️ Areas for Improvement
1. **Model selection bias** - Prefers Logistic (69%) over GB (87%)
2. **Variant 5 underperformance** - 5.5pp gap vs Variant 1
3. **Regression weakness** - 10.9pp gap vs classification
4. **Data handling** - 67% of failures are NaN-related

### 💡 Opportunities
1. **Increase Gradient Boosting** → +1-3% success rate
2. **Fix Variant 5** → +0.5-1% success rate
3. **Add missing value imputation** → +5-10% for regression
4. **Reduce Logistic Regression usage** → Better model diversity

---

## Technical Details

### Chart Specifications
- **Resolution:** 300 DPI (publication quality)
- **Format:** PNG (universal compatibility)
- **Size:** 100-200 KB per chart
- **Total:** 1.7 MB

### Color Scheme
- **Success:** Green (#2ecc71)
- **Failure:** Red (#e74c3c)
- **Primary:** Blue (#3498db)
- **Secondary:** Orange (#f39c12)
- **Variants:** Husl palette (8 colors)

### Data Sources
- `pipeline_results.csv` - All 325 execution results
- `best_pipelines_per_dataset.csv` - Top pipeline per dataset

---

## Generating New Visualizations

To regenerate these charts with updated data:

```bash
cd /path/to/amalia
source venv_viz/bin/activate
python3 backend/scripts/visualize_pipeline_results.py [optional_output_dir]
```

### Script Features
- Automatically loads latest results
- Generates all 12 charts
- Timestamps each run
- Error handling for missing data
- Modular design for easy customization

---

## Recommended Reading Order

**For Quick Overview:**
1. 01_success_rate
2. 05_task_type_comparison
3. 12_model_success_rates

**For Detailed Analysis:**
1. 03_model_frequency
2. 04_variant_performance
3. 08_metric_by_model
4. 09_variant_distribution

**For Action Items:**
1. 04_variant_performance (Fix V5)
2. 12_model_success_rates (Use more GB)
3. 02_metric_distribution (Understand failure modes)

---

## References

- **Implementation:** `backend/scripts/visualize_pipeline_results.py`
- **Results Data:** `data/batch_results/resilient_execution/`
- **Best Pipelines:** `best_pipelines_per_dataset.csv`

Generated: 2026-05-02
System: AMALIA Pipeline Auto-Generation
