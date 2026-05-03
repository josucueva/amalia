# Final Results Repository - Complete Index

## 📊 Folder Structure

```
final_results/
├── figs/                          (15 visualizations)
├── summaries/                     (6 CSV files + 3 markdown documents)
├── data/
│   └── all_results_combined.csv  (Combined results from all 3 models)
└── README.md                      (This file)
```

## 📈 Visualizations (15 PNG files)

### Overview & Comparison Charts
1. **01_overall_success_rate.png** - Bar chart comparing success rates across models
2. **02_success_by_difficulty.png** - Grouped bars: Easy/Medium/Hard by model
3. **03_success_by_task_type.png** - Grouped bars: Classification/Regression by model
4. **12_failure_analysis_pie_charts.png** - Success vs failure distribution

### Statistical Distributions
5. **04_accuracy_distribution_violin.png** - Violin plots of accuracy scores
6. **05_r2_distribution_boxplot.png** - Box plots of R² scores  
8. **08_accuracy_by_difficulty_boxplot.png** - Accuracy distribution by difficulty

### Heatmaps & Dense Visualizations
6. **06_heatmap_model_vs_difficulty.png** - Success rate heatmap
7. **07_heatmap_model_vs_task.png** - Success rate by task type heatmap
10. **10_metrics_heatmap_all_models.png** - Combined metrics (Accuracy, R², F1)
15. **15_3d_heatmap_difficulty_task_success.png** - Multi-dimensional breakdown

### Metric & Correlation Analysis
9. **09_mean_metrics_by_model.png** - Mean Accuracy, F1, R² bar charts
11. **11_mean_accuracy_by_difficulty_line.png** - Trend lines by difficulty
13. **13_accuracy_vs_f1_scatter.png** - Accuracy vs F1 scatter plot
14. **14_cumulative_distribution_accuracy.png** - CDF of accuracy scores

## 📋 Data Files

### Summary Tables (CSV format)
**Location:** `final_results/summaries/`

1. **01_overall_summary.csv**
   - Overall statistics by model
   - Columns: Model, Total Pipelines, Successful, Success Rate, Mean Accuracy, Mean F1, Mean R²

2. **02_difficulty_analysis.csv**
   - Success rates and metrics by difficulty level
   - Columns: Model, Difficulty, Total, Successful, Success Rate, Mean Accuracy, Mean R²

3. **03_task_type_analysis.csv**
   - Classification vs regression metrics
   - Columns: Model, Task Type, Total, Successful, Success Rate, metrics

4. **04_comparative_ranking.csv**
   - Ranked comparison across categories
   - Columns: Rank, Model, Category, Value

5. **05_performance_gaps.csv**
   - Percentage point differences between models
   - Shows gap analysis across all categories

6. **06_dataset_distribution.csv**
   - Pipeline counts by difficulty and task type
   - Columns: Model, Difficulty, Task Type, Pipeline Count

### Combined Data
7. **data/all_results_combined.csv**
   - Complete results from all 3 models (925 pipelines)
   - Raw data for custom analysis

## 📄 Markdown Documents

### Main Research Documents
1. **01_MAIN_RESEARCH_SUMMARY.md**
   - Executive overview of all findings
   - Key findings by difficulty and task type
   - Statistical significance analysis
   - Visualization guide and presentation order
   - Key messages for research

2. **02_METHODOLOGY_AND_DATA_QUALITY.md**
   - Complete methodology explanation
   - Data quality assessment for each model
   - Issues and resolutions
   - Limitations and recommendations
   - Statistical methods used

3. **03_RECOMMENDED_ANNEXES.md**
   - Suggestions for appendices in research paper
   - Recommended content for different document types
   - Visualization selection guide
   - Text integration recommendations

## 🎯 Key Findings Summary

### Overall Success Rates
| Model | Success Rate | Pipelines |
|-------|-------------|-----------|
| DeepSeek | 72.3% | 325 |
| Mistral | 54.7% | 300 |
| Llama | 37.7% | 300 |

### By Difficulty Level
| Difficulty | DeepSeek | Mistral | Llama | Gap |
|-----------|----------|---------|-------|-----|
| **Easy** | 92.0% | 75.0% | 47.0% | 17pp |
| **Medium** | 72.0% | 48.0% | 43.0% | 24pp ⭐ |
| **Hard** | 48.0% | 41.0% | 23.0% | 7pp |

### Performance Metrics (Successful Pipelines Only)
| Model | Accuracy | F1 Score | R² |
|-------|----------|----------|-----|
| DeepSeek | 65.5% | 0.635 | 0.547 |
| Mistral | 60.4% | 0.591 | 0.482 |
| Llama | 58.2% | 0.569 | 0.391 |

## ⭐ Highlights

### Most Important Visualization
**Recommendation:** Use `02_success_by_difficulty.png`
- Shows DeepSeek's clear dominance
- Highlights 24pp gap at medium difficulty
- Best single chart to present findings

### Most Surprising Finding
**Medium Difficulty is Key Differentiator**
- DeepSeek: 72% success (strong)
- Mistral: 48% success (below 50%!)
- Llama: 43% success (struggles)

This 24pp gap reveals that DeepSeek's advantage isn't just on easy problems, 
but on moderately complex problems where most reasoning happens.

### Important Caveat
**Data Quality Note for Mistral/Llama:**
- DeepSeek: Test data properly isolated (scientifically valid)
- Mistral/Llama: No test isolation (potential 20-40% metric inflation)
- Recommendation: Results should include data quality disclaimer

## 📖 How to Use These Materials

### For Thesis or Paper
1. Start with `01_MAIN_RESEARCH_SUMMARY.md`
2. Include visualizations: 02, 06, 09, 11, 12
3. Add detailed tables from summaries/ folder
4. Reference `02_METHODOLOGY_AND_DATA_QUALITY.md` for methods section
5. Follow `03_RECOMMENDED_ANNEXES.md` for appendix structure

### For Presentation/Slides
**Slide 1 - Overview:** Use visualization #02 (success by difficulty)
**Slide 2 - Metrics:** Use visualization #10 (metrics heatmap)
**Slide 3 - Details:** Use visualization #06 (difficulty heatmap)
**Slide 4 - Data Quality:** Include caveat about Mistral/Llama

### For Research Proposal
1. Executive Brief: 1 page summary with #02 visualization
2. Background: `01_MAIN_RESEARCH_SUMMARY.md`
3. Methodology: `02_METHODOLOGY_AND_DATA_QUALITY.md`
4. Appendix: CSV summary tables

### For Quick Reference
- **Question:** "Which model is best?" → Show #02
- **Question:** "Are differences significant?" → Show #01 + #06
- **Question:** "What about hard problems?" → Show #06 + #15
- **Question:** "Are metrics reliable?" → Reference #02_METHODOLOGY

## 🔍 Data Quality Assessment

### ✅ DeepSeek: SCIENTIFICALLY VALID
- Test data properly isolated
- Test indices saved and used in evaluation
- No data leakage
- High confidence in results

### ⚠️ Mistral/Llama: REQUIRES CAVEAT
- No test data isolation
- Potential 20-40% metric inflation
- Use for relative comparison only
- Consider flagging in presentation

## 📊 Statistical Summary

### Sample Sizes
- **DeepSeek:** 325 pipelines (65 datasets × 5 variants)
- **Mistral:** 300 pipelines (60 datasets × 5 duplicates)
- **Llama:** 300 pipelines (60 datasets × 5 duplicates)

### Confidence
- **High:** DeepSeek metrics (proper methodology)
- **Medium:** Mistral/Llama relative performance (needs caveat)
- **Note:** No formal statistical testing applied

### Generalizability
- **Coverage:** 65 diverse datasets
- **Task Types:** Classification and regression
- **Difficulty Levels:** Easy, medium, hard
- **Limitation:** Single run per variant (no confidence intervals)

## 🚀 Recommended Next Steps

### For Improved Analysis
1. Re-execute Mistral/Llama with test_indices fix
2. Apply formal statistical testing (t-tests, ANOVA)
3. Generate confidence intervals
4. Expand to 100+ datasets for robustness

### For Paper/Presentation
1. Select 6-8 visualizations for inclusion
2. Create summary statistics sheet
3. Write data quality section (1-2 pages)
4. Develop executive brief (1 page)
5. Organize appendix materials

### For Future Research
1. Investigate why medium difficulty is hardest
2. Analyze failure cases systematically
3. Compare pipeline components across models
4. Study impact of dataset characteristics
5. Explore ensemble approaches

---

**Last Updated:** 2024-05-02
**Total Files:** 15 visualizations + 6 CSV tables + 3 markdown documents + 1 combined data file
**Status:** ✅ COMPLETE AND READY FOR RESEARCH USE

## Contact & Updates

For questions about these results:
1. Check `02_METHODOLOGY_AND_DATA_QUALITY.md` for methodological details
2. Review `03_RECOMMENDED_ANNEXES.md` for integration guidance
3. Reference specific visualization in `figs/` folder
4. Consult CSV files in `summaries/` for detailed statistics
