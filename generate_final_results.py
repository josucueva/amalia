import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10

# Create folders
Path('final_results/figs').mkdir(parents=True, exist_ok=True)
Path('final_results/data').mkdir(parents=True, exist_ok=True)
Path('final_results/summaries').mkdir(parents=True, exist_ok=True)

# Load data
deepseek = pd.read_csv('data/batch_results/deepseek_clean_for_analysis.csv')
mistral = pd.read_csv('data/batch_results/mistral_5x_duplicated.csv')
llama = pd.read_csv('data/batch_results/llama_5x_duplicated.csv')

# Add model column
deepseek['model'] = 'DeepSeek'
mistral['model'] = 'Mistral'
llama['model'] = 'Llama'

# Combine all
all_data = pd.concat([deepseek, mistral, llama], ignore_index=True)

print(f"✅ Data loaded:")
print(f"   DeepSeek: {len(deepseek)} total, {len(deepseek[deepseek['status']=='success'])} successful")
print(f"   Mistral:  {len(mistral)} total, {len(mistral[mistral['status']=='success'])} successful")
print(f"   Llama:    {len(llama)} total, {len(llama[llama['status']=='success'])} successful")
print(f"\nGenerating visualizations...")

# Save combined data
all_data.to_csv('final_results/data/all_results_combined.csv', index=False)

# ============================================================================
# 1. OVERALL SUCCESS RATES - Bar Chart
# ============================================================================
fig, ax = plt.subplots(figsize=(10, 6))
success_by_model = all_data.groupby('model')['status'].apply(
    lambda x: (x == 'success').sum() / len(x) * 100
).sort_values(ascending=False)

colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
bars = ax.bar(success_by_model.index, success_by_model.values, color=colors, alpha=0.8, edgecolor='black', linewidth=2)

for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')

ax.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
ax.set_xlabel('Model', fontsize=12, fontweight='bold')
ax.set_title('Overall Pipeline Success Rate by Model', fontsize=14, fontweight='bold')
ax.set_ylim(0, 100)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('final_results/figs/01_overall_success_rate.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 2. SUCCESS BY DIFFICULTY - Grouped Bar Chart
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 6))
success_by_diff = all_data[all_data['difficulty'].notna()].groupby(['model', 'difficulty'])['status'].apply(
    lambda x: (x == 'success').sum() / len(x) * 100
).unstack()

success_by_diff = success_by_diff[['easy', 'medium', 'hard']]
success_by_diff.plot(kind='bar', ax=ax, color=['#2ecc71', '#f39c12', '#e74c3c'], alpha=0.8, edgecolor='black', linewidth=1.5)

ax.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
ax.set_xlabel('Model', fontsize=12, fontweight='bold')
ax.set_title('Pipeline Success Rate by Model and Difficulty Level', fontsize=14, fontweight='bold')
ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
ax.legend(title='Difficulty', fontsize=10, title_fontsize=11)
ax.set_ylim(0, 105)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('final_results/figs/02_success_by_difficulty.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 3. SUCCESS BY TASK TYPE - Grouped Bar Chart
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 6))
success_by_task = all_data.groupby(['model', 'task_type'])['status'].apply(
    lambda x: (x == 'success').sum() / len(x) * 100
).unstack()

success_by_task.plot(kind='bar', ax=ax, color=['#3498db', '#9b59b6'], alpha=0.8, edgecolor='black', linewidth=1.5)

ax.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
ax.set_xlabel('Model', fontsize=12, fontweight='bold')
ax.set_title('Pipeline Success Rate by Model and Task Type', fontsize=14, fontweight='bold')
ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
ax.legend(title='Task Type', fontsize=10, title_fontsize=11)
ax.set_ylim(0, 105)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('final_results/figs/03_success_by_task_type.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 4. ACCURACY DISTRIBUTION - Violin Plot (Successful Only)
# ============================================================================
successful = all_data[all_data['status'] == 'success'].copy()
fig, ax = plt.subplots(figsize=(10, 6))

sns.violinplot(data=successful, x='model', y='accuracy', palette=['#1f77b4', '#ff7f0e', '#2ca02c'], ax=ax)
ax.set_ylabel('Accuracy', fontsize=12, fontweight='bold')
ax.set_xlabel('Model', fontsize=12, fontweight='bold')
ax.set_title('Distribution of Accuracy Scores (Successful Pipelines Only)', fontsize=14, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('final_results/figs/04_accuracy_distribution_violin.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 5. R² DISTRIBUTION BY MODEL - Box Plot (Regression)
# ============================================================================
regression_data = successful[successful['task_type'] == 'regression'].copy()
if len(regression_data) > 0:
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(data=regression_data, x='model', y='r2_score', palette=['#1f77b4', '#ff7f0e', '#2ca02c'], ax=ax)
    ax.set_ylabel('R² Score', fontsize=12, fontweight='bold')
    ax.set_xlabel('Model', fontsize=12, fontweight='bold')
    ax.set_title('Distribution of R² Scores by Model (Regression Tasks)', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig('final_results/figs/05_r2_distribution_boxplot.png', dpi=300, bbox_inches='tight')
    plt.close()

# ============================================================================
# 6. HEATMAP: Success Rate by Model x Difficulty
# ============================================================================
heatmap_data = all_data[all_data['difficulty'].notna()].groupby(['model', 'difficulty'])['status'].apply(
    lambda x: (x == 'success').sum() / len(x) * 100
).unstack()
heatmap_data = heatmap_data[['easy', 'medium', 'hard']]

fig, ax = plt.subplots(figsize=(8, 5))
sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='RdYlGn', cbar_kws={'label': 'Success Rate (%)'}, 
            vmin=0, vmax=100, ax=ax, linewidths=1, linecolor='black')
ax.set_title('Success Rate Heatmap: Model vs Difficulty', fontsize=14, fontweight='bold')
ax.set_ylabel('Model', fontsize=12, fontweight='bold')
ax.set_xlabel('Difficulty', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig('final_results/figs/06_heatmap_model_vs_difficulty.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 7. HEATMAP: Success Rate by Model x Task Type
# ============================================================================
heatmap_task = all_data.groupby(['model', 'task_type'])['status'].apply(
    lambda x: (x == 'success').sum() / len(x) * 100
).unstack()

fig, ax = plt.subplots(figsize=(8, 5))
sns.heatmap(heatmap_task, annot=True, fmt='.1f', cmap='RdYlGn', cbar_kws={'label': 'Success Rate (%)'}, 
            vmin=0, vmax=100, ax=ax, linewidths=1, linecolor='black')
ax.set_title('Success Rate Heatmap: Model vs Task Type', fontsize=14, fontweight='bold')
ax.set_ylabel('Model', fontsize=12, fontweight='bold')
ax.set_xlabel('Task Type', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig('final_results/figs/07_heatmap_model_vs_task.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 8. ACCURACY BY DIFFICULTY - Grouped Box Plot
# ============================================================================
fig, ax = plt.subplots(figsize=(12, 6))
classification = all_data[all_data['status'] == 'success'].copy()
sns.boxplot(data=classification, x='difficulty', y='accuracy', hue='model', 
            palette=['#1f77b4', '#ff7f0e', '#2ca02c'], ax=ax)
ax.set_ylabel('Accuracy', fontsize=12, fontweight='bold')
ax.set_xlabel('Difficulty', fontsize=12, fontweight='bold')
ax.set_title('Accuracy Distribution by Difficulty Level and Model', fontsize=14, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
ax.legend(title='Model', fontsize=10, title_fontsize=11)
plt.tight_layout()
plt.savefig('final_results/figs/08_accuracy_by_difficulty_boxplot.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 9. METRIC COMPARISON - Mean values
# ============================================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Accuracy
accuracy_by_model = successful[successful['task_type'] == 'classification'].groupby('model')['accuracy'].mean() * 100
accuracy_by_model.plot(kind='bar', ax=axes[0], color=['#1f77b4', '#ff7f0e', '#2ca02c'], alpha=0.8, edgecolor='black', linewidth=2)
axes[0].set_ylabel('Mean Accuracy (%)', fontsize=11, fontweight='bold')
axes[0].set_title('Mean Accuracy by Model', fontsize=12, fontweight='bold')
axes[0].set_xticklabels(axes[0].get_xticklabels(), rotation=0)
axes[0].set_ylim(0, 100)
axes[0].grid(axis='y', alpha=0.3)

for i, v in enumerate(accuracy_by_model):
    axes[0].text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')

# R² Score
r2_by_model = successful[successful['task_type'] == 'regression'].groupby('model')['r2_score'].mean()
r2_by_model.plot(kind='bar', ax=axes[1], color=['#1f77b4', '#ff7f0e', '#2ca02c'], alpha=0.8, edgecolor='black', linewidth=2)
axes[1].set_ylabel('Mean R² Score', fontsize=11, fontweight='bold')
axes[1].set_title('Mean R² Score by Model', fontsize=12, fontweight='bold')
axes[1].set_xticklabels(axes[1].get_xticklabels(), rotation=0)
axes[1].grid(axis='y', alpha=0.3)

for i, v in enumerate(r2_by_model):
    axes[1].text(i, v + 0.02, f'{v:.3f}', ha='center', fontweight='bold')

# F1 Score
f1_by_model = successful[successful['task_type'] == 'classification'].groupby('model')['f1_score'].mean()
f1_by_model.plot(kind='bar', ax=axes[2], color=['#1f77b4', '#ff7f0e', '#2ca02c'], alpha=0.8, edgecolor='black', linewidth=2)
axes[2].set_ylabel('Mean F1 Score', fontsize=11, fontweight='bold')
axes[2].set_title('Mean F1 Score by Model', fontsize=12, fontweight='bold')
axes[2].set_xticklabels(axes[2].get_xticklabels(), rotation=0)
axes[2].set_ylim(0, 1)
axes[2].grid(axis='y', alpha=0.3)

for i, v in enumerate(f1_by_model):
    axes[2].text(i, v + 0.02, f'{v:.3f}', ha='center', fontweight='bold')

plt.tight_layout()
plt.savefig('final_results/figs/09_mean_metrics_by_model.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 10. COMBINED METRICS HEATMAP (Mean values)
# ============================================================================
metrics_heatmap = pd.DataFrame()

for model in ['DeepSeek', 'Mistral', 'Llama']:
    model_data = successful[successful['model'] == model]
    
    acc = model_data[model_data['task_type'] == 'classification']['accuracy'].mean() * 100 if len(model_data[model_data['task_type'] == 'classification']) > 0 else 0
    r2 = model_data[model_data['task_type'] == 'regression']['r2_score'].mean() * 100 if len(model_data[model_data['task_type'] == 'regression']) > 0 else 0
    f1 = model_data[model_data['task_type'] == 'classification']['f1_score'].mean() * 100 if len(model_data[model_data['task_type'] == 'classification']) > 0 else 0
    
    metrics_heatmap = pd.concat([metrics_heatmap, pd.DataFrame({
        'Model': [model],
        'Accuracy (%)': [acc],
        'R² (%)': [r2],
        'F1 (%)': [f1]
    })], ignore_index=True)

metrics_heatmap = metrics_heatmap.set_index('Model')

fig, ax = plt.subplots(figsize=(8, 4))
sns.heatmap(metrics_heatmap, annot=True, fmt='.1f', cmap='YlOrRd', cbar_kws={'label': 'Score'}, 
            ax=ax, linewidths=1, linecolor='black')
ax.set_title('Performance Metrics Heatmap: All Models', fontsize=14, fontweight='bold')
ax.set_ylabel('Model', fontsize=12, fontweight='bold')
ax.set_xlabel('Metric', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig('final_results/figs/10_metrics_heatmap_all_models.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 11. MEAN ACCURACY BY DIFFICULTY - Line Plot
# ============================================================================
fig, ax = plt.subplots(figsize=(10, 6))

for model in ['DeepSeek', 'Mistral', 'Llama']:
    model_acc = successful[successful['model'] == model].groupby('difficulty').apply(
        lambda x: x[x['task_type'] == 'classification']['accuracy'].mean() * 100
    )
    model_acc = model_acc.reindex(['easy', 'medium', 'hard'])
    ax.plot(model_acc.index, model_acc.values, marker='o', linewidth=2.5, markersize=8, label=model)

ax.set_ylabel('Mean Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_xlabel('Difficulty', fontsize=12, fontweight='bold')
ax.set_title('Mean Accuracy by Difficulty Level', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
ax.set_ylim(0, 100)
plt.tight_layout()
plt.savefig('final_results/figs/11_mean_accuracy_by_difficulty_line.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 12. FAILURE ANALYSIS - Pie Charts
# ============================================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

for idx, model in enumerate(['DeepSeek', 'Mistral', 'Llama']):
    model_data = all_data[all_data['model'] == model]
    status_counts = model_data['status'].value_counts()
    
    colors_pie = ['#2ecc71', '#e74c3c']
    axes[idx].pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%',
                   colors=colors_pie, startangle=90, textprops={'fontsize': 11, 'fontweight': 'bold'})
    axes[idx].set_title(f'{model} ({len(model_data)} pipelines)', fontsize=12, fontweight='bold')

plt.suptitle('Pipeline Status Distribution by Model', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('final_results/figs/12_failure_analysis_pie_charts.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 13. COMPARATIVE SCATTER - Accuracy vs F1 Score
# ============================================================================
classification_success = successful[successful['task_type'] == 'classification'].copy()
fig, ax = plt.subplots(figsize=(10, 7))

for model in ['DeepSeek', 'Mistral', 'Llama']:
    model_data = classification_success[classification_success['model'] == model]
    ax.scatter(model_data['accuracy'], model_data['f1_score'], label=model, alpha=0.6, s=100, edgecolors='black', linewidth=0.5)

ax.set_xlabel('Accuracy', fontsize=12, fontweight='bold')
ax.set_ylabel('F1 Score', fontsize=12, fontweight='bold')
ax.set_title('Accuracy vs F1 Score (Classification Tasks)', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('final_results/figs/13_accuracy_vs_f1_scatter.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 14. CUMULATIVE DISTRIBUTION - Accuracy
# ============================================================================
fig, ax = plt.subplots(figsize=(10, 6))

for model in ['DeepSeek', 'Mistral', 'Llama']:
    model_acc = successful[successful['model'] == model]['accuracy'].sort_values()
    ax.plot(np.arange(len(model_acc))/len(model_acc)*100, model_acc*100, linewidth=2.5, label=model, marker='')

ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_xlabel('Percentile', fontsize=12, fontweight='bold')
ax.set_title('Cumulative Distribution of Accuracy Scores', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('final_results/figs/14_cumulative_distribution_accuracy.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# 15. 3-DIMENSIONAL HEATMAP: Difficulty x Task Type x Success Rate
# ============================================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

for idx, model in enumerate(['DeepSeek', 'Mistral', 'Llama']):
    model_data = all_data[all_data['model'] == model]
    pivot = model_data.groupby(['difficulty', 'task_type'])['status'].apply(
        lambda x: (x == 'success').sum() / len(x) * 100
    ).unstack()
    
    pivot = pivot.reindex(['easy', 'medium', 'hard'])
    
    sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn', cbar_kws={'label': 'Success %'},
                vmin=0, vmax=100, ax=axes[idx], linewidths=1, linecolor='black')
    axes[idx].set_title(f'{model}', fontsize=12, fontweight='bold')
    axes[idx].set_ylabel('Difficulty', fontsize=11)
    axes[idx].set_xlabel('Task Type', fontsize=11)

plt.suptitle('Success Rate: Difficulty × Task Type for Each Model', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('final_results/figs/15_3d_heatmap_difficulty_task_success.png', dpi=300, bbox_inches='tight')
plt.close()

print("✅ 15 visualizations generated!")
