# Recommendations for Research Annexes

## Overview
This document suggests high-value content for appendices in your research paper or presentation.

## Recommended Annexes

### ANNEX A: Detailed Results Tables
**Location:** `final_results/summaries/`

Include the following CSV files in appendix:

1. **01_overall_summary.csv**
   - Overview statistics for each model
   - Use case: Quick reference for readers
   - Format: Simple 7-column table

2. **02_difficulty_analysis.csv**
   - Success rates and metrics by difficulty level
   - Use case: Justify medium difficulty findings
   - Format: Detailed breakdown by model × difficulty

3. **03_task_type_analysis.csv**
   - Classification vs regression performance
   - Use case: Task-specific insights
   - Format: Complete metrics table

4. **04_comparative_ranking.csv**
   - Ranked comparison across categories
   - Use case: Quick comparison visualization
   - Format: Ranked tables

5. **05_performance_gaps.csv**
   - Percentage point differences between models
   - Use case: Statistical significance evidence
   - Format: Gap analysis table

6. **06_dataset_distribution.csv**
   - Pipeline counts by difficulty and task
   - Use case: Explain sample sizes
   - Format: Distribution breakdown

### ANNEX B: Complete Visualization Suite
**Location:** `final_results/figs/`

Recommended subset for paper appendix (select 6-8 most impactful):

**Essential (must include):**
- `02_success_by_difficulty.png` - Main finding visualization
- `06_heatmap_model_vs_difficulty.png` - Comprehensive breakdown
- `09_mean_metrics_by_model.png` - Metric comparison

**Strongly Recommended (high-value add):**
- `11_mean_accuracy_by_difficulty_line.png` - Trend analysis
- `10_metrics_heatmap_all_models.png` - All metrics overview
- `12_failure_analysis_pie_charts.png` - Failure distribution

**Optional (additional detail):**
- `04_accuracy_distribution_violin.png` - Statistical distributions
- `14_cumulative_distribution_accuracy.png` - Robustness analysis
- `15_3d_heatmap_difficulty_task_success.png` - Multi-dimensional view

### ANNEX C: Data Leakage Fix Documentation
**Create new file:** `ANNEX_C_DATA_LEAKAGE_EXPLANATION.md`

Content should include:
- What data leakage is and why it matters
- How it was discovered (perfect results on spam detection)
- Quantitative impact (metrics inflated 13-42pp)
- Solution implementation details
- Verification that fix was successful

### ANNEX D: Mistral/Llama Data Quality Caveats
**Create new file:** `ANNEX_D_DATA_QUALITY_ASSESSMENT.md`

Content should explain:
- DeepSeek has test_indices files (scientifically valid)
- Mistral/Llama don't have test_indices (not fixed)
- Estimated metric inflation 20-40% for Mistral/Llama
- Implications for comparison
- Recommendation to re-execute or discount their metrics

### ANNEX E: Pipeline Generation Strategy
**Create new file:** `ANNEX_E_GENERATION_STRATEGY.md`

Content should describe:
- Why generate 5 pipelines per dataset
- How diversity improves robustness
- Success rate of 5 vs 1 pipeline per dataset
- Example pipelines (best and worst performers)
- LLM prompting strategy used

### ANNEX F: Failure Analysis
**Create new file:** `ANNEX_F_FAILURE_ANALYSIS.md`

Content should analyze:
- Common failure patterns by model
- Task types most prone to failure
- Difficulty level failure rates
- Examples of failed pipelines
- Recommendations to improve success rate

### ANNEX G: Example Pipelines
**Create new file:** `ANNEX_G_EXAMPLE_PIPELINES.md`

Content should include:
- **Best Performer:** Example of top-scoring pipeline
- **Average Performer:** Typical successful pipeline
- **Failed Pipeline:** Example of unsuccessful generation
- **Format:** Show actual pipeline structure and steps

## Supporting Materials to Create

### Create Summary Statistics Sheet
**File:** `final_results/summaries/STATISTICS_SHEET.csv`

```
Statistic,DeepSeek,Mistral,Llama
Total Pipelines,325,300,300
Successful,235,164,113
Success Rate,72.3%,54.7%,37.7%
Mean Accuracy (Classification),65.5%,60.4%,58.2%
Mean R² (Regression),0.547,0.482,0.391
...
```

### Create Executive Brief
**File:** `final_results/summaries/EXECUTIVE_BRIEF.txt`

One-page summary:
- 3-4 key findings
- 2-3 visualizations recommended
- Concrete recommendations
- Data quality notes

## Integration Guide

### For Master's Thesis
**Recommended structure:**
- Main text: Findings + top 3 visualizations
- Annex A: Detailed results tables
- Annex B: Complete visualization suite
- Annex C: Data leakage explanation
- Annex D: Data quality assessment

### For Conference Paper
**Recommended structure:**
- Main text: Key findings + 2-3 critical visualizations
- Appendix A: Summary statistics
- Appendix B: Heatmaps (6 and 7)
- Appendix C: Data quality notes
- Appendix D: Failure analysis

### For Technical Report
**Recommended structure:**
- Executive Summary: 1 page
- Main Findings: 3-4 pages with visualizations
- Data Quality: 1 page
- Detailed Results: Appendix with all tables
- Visualizations: Appendix with all 15 charts
- Methodology: Annex with full details

## Visualization Selection Guide

**For showing DeepSeek superiority:**
- Use: `02_success_by_difficulty.png` (shows 24pp gap at medium)
- Why: Clearest evidence of meaningful difference

**For showing robustness:**
- Use: `11_mean_accuracy_by_difficulty_line.png` (trend lines)
- Why: Shows predictable degradation pattern

**For comprehensive overview:**
- Use: `06_heatmap_model_vs_difficulty.png` (heatmap)
- Why: Single visualization shows all key information

**For statistical detail:**
- Use: `09_mean_metrics_by_model.png` (accuracy, F1, R²)
- Why: Shows multiple metrics in one view

**For failure analysis:**
- Use: `12_failure_analysis_pie_charts.png` (success/failure)
- Why: Contextualizes success rates

## Recommendations for Text Integration

### Key Statistics to Highlight
- 72.3% success rate for DeepSeek vs 54.7% for Mistral
- 24pp advantage at medium difficulty (KEY FINDING)
- 92% → 72% → 48% graceful degradation pattern
- 325 vs 300 pipelines tested per model

### Key Insights to Emphasize
1. Medium difficulty is the critical differentiator
2. DeepSeek shows predictable performance degradation
3. Mistral/Llama metrics may be inflated (caveat)
4. Hard problems remain challenging for all models (48% max)

### Common Questions to Preempt
- Q: Why is DeepSeek better? A: Superior reasoning → better pipeline generation
- Q: Are metrics reliable? A: DeepSeek yes, Mistral/Llama caveat needed
- Q: Why did you test 65 datasets? A: Diverse coverage, representative sample
- Q: Can we trust these results? A: Data leakage fix ensures scientific validity

---

**Recommended Execution:**
1. Create all ANNEX files as separate markdown documents
2. Organize in `final_results/annexes/` folder
3. Create comprehensive index/TOC
4. Reference these in main paper/presentation
5. Include data quality assessment prominently
