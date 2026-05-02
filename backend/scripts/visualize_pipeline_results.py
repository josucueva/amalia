#!/usr/bin/env python3
"""
Pipeline Results Visualization Script
Generates comprehensive visualizations for AMALIA pipeline execution results.

Usage:
    python visualize_pipeline_results.py [output_dir]
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import Counter
import warnings

warnings.filterwarnings('ignore')

# Configure plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class PipelineVisualizer:
    """Handles all visualization of pipeline results."""
    
    def __init__(self, results_dir, output_dir=None):
        """Initialize visualizer with results directory."""
        self.results_dir = Path(results_dir)
        self.output_dir = Path(output_dir) if output_dir else self.results_dir / 'visualizations'
        self.output_dir.mkdir(exist_ok=True)
        
        # Load data
        self.results_csv = self.results_dir / 'pipeline_results.csv'
        self.best_csv = self.results_dir / 'best_pipelines_per_dataset.csv'
        
        print(f"📂 Results Directory: {self.results_dir}")
        print(f"📊 Output Directory: {self.output_dir}")
        
        self.df_results = pd.read_csv(self.results_csv)
        self.df_best = pd.read_csv(self.best_csv)
        
        # Process data
        self._process_data()
        print("✅ Data loaded and processed\n")
    
    def _process_data(self):
        """Process and clean data."""
        # Extract variant number from artifact file
        self.df_results['variant'] = self.df_results['artifact_file'].str.extract(
            r'variant_(\d+)_of_\d+', expand=False
        )
        
        # Extract difficulty from dataset_id
        self.df_results['difficulty'] = self.df_results['dataset_id'].str.extract(
            r'(easy|mid|hard)', expand=False
        )
        
        # Count successes
        self.df_results['is_success'] = (self.df_results['status'] == 'success').astype(int)
        
        # Fill NaN metrics with 0 for failed pipelines
        metric_cols = ['accuracy', 'r2_score', 'f1_score', 'precision', 'recall']
        for col in metric_cols:
            self.df_results[col] = self.df_results[col].fillna(0)
    
    def generate_all(self):
        """Generate all visualizations."""
        print("🎨 Generating visualizations...\n")
        
        self.plot_success_rate()
        self.plot_metric_distribution()
        self.plot_model_frequency()
        self.plot_variant_performance()
        self.plot_task_type_comparison()
        self.plot_difficulty_vs_success()
        self.plot_model_by_task_type()
        self.plot_metric_by_model()
        self.plot_variant_distribution()
        self.plot_top_models()
        self.plot_success_by_difficulty()
        self.plot_model_success_rates()
        
        print("\n✅ All visualizations generated!")
        print(f"📁 Saved to: {self.output_dir}\n")
    
    def plot_success_rate(self):
        """Plot overall success vs failure rates."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        success_counts = self.df_results['status'].value_counts()
        colors = ['#2ecc71', '#e74c3c']
        
        wedges, texts, autotexts = ax.pie(
            success_counts.values,
            labels=success_counts.index,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90,
            textprops={'fontsize': 12, 'weight': 'bold'}
        )
        
        total = len(self.df_results)
        ax.set_title(
            f'Pipeline Execution Success Rate\nTotal Pipelines: {total}',
            fontsize=14, weight='bold', pad=20
        )
        
        # Add legend with counts
        legend_labels = [f'{status}: {count}' for status, count in success_counts.items()]
        ax.legend(legend_labels, loc='upper right', fontsize=11)
        
        plt.tight_layout()
        self._save_fig('01_success_rate')
        plt.close()
    
    def plot_metric_distribution(self):
        """Plot distribution of metrics for successful pipelines."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Classification metrics (accuracy)
        classification = self.df_results[
            (self.df_results['task_type'] == 'classification') & 
            (self.df_results['accuracy'] > 0)
        ]['accuracy']
        
        # Regression metrics (R2)
        regression = self.df_results[
            (self.df_results['task_type'] == 'regression') & 
            (self.df_results['r2_score'] > -10)
        ]['r2_score']
        
        # Classification histogram
        axes[0].hist(classification, bins=20, color='#3498db', edgecolor='black', alpha=0.7)
        axes[0].set_xlabel('Accuracy', fontsize=11, weight='bold')
        axes[0].set_ylabel('Frequency', fontsize=11, weight='bold')
        axes[0].set_title(f'Classification Accuracy Distribution\n(n={len(classification)})', fontsize=12, weight='bold')
        axes[0].axvline(classification.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {classification.mean():.3f}')
        axes[0].legend()
        axes[0].grid(axis='y', alpha=0.3)
        
        # Regression histogram
        axes[1].hist(regression, bins=20, color='#e74c3c', edgecolor='black', alpha=0.7)
        axes[1].set_xlabel('R² Score', fontsize=11, weight='bold')
        axes[1].set_ylabel('Frequency', fontsize=11, weight='bold')
        axes[1].set_title(f'Regression R² Distribution\n(n={len(regression)})', fontsize=12, weight='bold')
        axes[1].axvline(regression.mean(), color='blue', linestyle='--', linewidth=2, label=f'Mean: {regression.mean():.3f}')
        axes[1].legend()
        axes[1].grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        self._save_fig('02_metric_distribution')
        plt.close()
    
    def plot_model_frequency(self):
        """Plot most frequently used models."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        model_counts = self.df_results['model_type'].value_counts().head(10)
        colors = sns.color_palette("husl", len(model_counts))
        
        bars = ax.barh(range(len(model_counts)), model_counts.values, color=colors)
        ax.set_yticks(range(len(model_counts)))
        ax.set_yticklabels(model_counts.index, fontsize=11)
        ax.set_xlabel('Count', fontsize=11, weight='bold')
        ax.set_title('Top 10 Most Used Models (All Pipelines)', fontsize=13, weight='bold', pad=15)
        ax.invert_yaxis()
        
        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, model_counts.values)):
            ax.text(val + 0.5, i, str(int(val)), va='center', fontsize=10, weight='bold')
        
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        self._save_fig('03_model_frequency')
        plt.close()
    
    def plot_variant_performance(self):
        """Plot success rate by variant."""
        fig, ax = plt.subplots(figsize=(11, 6))
        
        variant_success = self.df_results.groupby('variant').agg({
            'is_success': ['sum', 'count']
        }).round(3)
        
        variant_success.columns = ['success', 'total']
        variant_success['success_rate'] = (
            variant_success['success'] / variant_success['total'] * 100
        ).round(1)
        variant_success = variant_success.sort_index()
        
        colors = ['#2ecc71' if x > 70 else '#f39c12' if x > 60 else '#e74c3c' 
                  for x in variant_success['success_rate']]
        
        bars = ax.bar(
            [f'Variant {v}' for v in variant_success.index],
            variant_success['success_rate'],
            color=colors,
            edgecolor='black',
            linewidth=1.5
        )
        
        ax.set_ylabel('Success Rate (%)', fontsize=11, weight='bold')
        ax.set_title('Pipeline Success Rate by Variant', fontsize=13, weight='bold', pad=15)
        ax.set_ylim(0, 100)
        ax.axhline(y=70, color='gray', linestyle='--', alpha=0.5, label='70% threshold')
        ax.legend()
        
        # Add value labels
        for bar, val in zip(bars, variant_success['success_rate']):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{val:.1f}%', ha='center', va='bottom', fontsize=10, weight='bold')
        
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        self._save_fig('04_variant_performance')
        plt.close()
    
    def plot_task_type_comparison(self):
        """Compare classification vs regression results."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Success rates
        task_success = self.df_results.groupby('task_type')['is_success'].agg(['sum', 'count'])
        task_success['rate'] = (task_success['sum'] / task_success['count'] * 100).round(1)
        
        colors_task = ['#3498db', '#e74c3c']
        axes[0].bar(task_success.index, task_success['rate'], color=colors_task, edgecolor='black', linewidth=1.5)
        axes[0].set_ylabel('Success Rate (%)', fontsize=11, weight='bold')
        axes[0].set_title('Success Rate: Classification vs Regression', fontsize=12, weight='bold')
        axes[0].set_ylim(0, 100)
        
        for i, (idx, val) in enumerate(zip(task_success.index, task_success['rate'])):
            axes[0].text(i, val + 2, f'{val:.1f}%', ha='center', fontsize=11, weight='bold')
        
        # Average metrics
        avg_accuracy = self.df_results[
            self.df_results['task_type'] == 'classification'
        ]['accuracy'].mean()
        
        avg_r2 = self.df_results[
            self.df_results['task_type'] == 'regression'
        ]['r2_score'].mean()
        
        metrics = ['Classification\nAvg Accuracy', 'Regression\nAvg R²']
        values = [avg_accuracy, avg_r2]
        
        axes[1].bar(metrics, values, color=colors_task, edgecolor='black', linewidth=1.5)
        axes[1].set_ylabel('Metric Value', fontsize=11, weight='bold')
        axes[1].set_title('Average Metric: Classification vs Regression', fontsize=12, weight='bold')
        axes[1].set_ylim(0, 1)
        
        for i, val in enumerate(values):
            axes[1].text(i, val + 0.03, f'{val:.3f}', ha='center', fontsize=11, weight='bold')
        
        plt.tight_layout()
        self._save_fig('05_task_type_comparison')
        plt.close()
    
    def plot_difficulty_vs_success(self):
        """Plot success rate by dataset difficulty."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        difficulty_order = ['easy', 'mid', 'hard']
        difficulty_success = self.df_results.groupby('difficulty')['is_success'].agg(['sum', 'count'])
        difficulty_success['rate'] = (
            difficulty_success['sum'] / difficulty_success['count'] * 100
        ).round(1)
        difficulty_success = difficulty_success.reindex(difficulty_order)
        
        colors_diff = ['#2ecc71', '#f39c12', '#e74c3c']
        bars = ax.bar(
            [f'{d.capitalize()}\n(n={int(difficulty_success.loc[d, "count"])})' 
             for d in difficulty_order],
            difficulty_success['rate'],
            color=colors_diff,
            edgecolor='black',
            linewidth=1.5
        )
        
        ax.set_ylabel('Success Rate (%)', fontsize=11, weight='bold')
        ax.set_title('Pipeline Success Rate by Dataset Difficulty', fontsize=13, weight='bold', pad=15)
        ax.set_ylim(0, 100)
        
        for bar, val in zip(bars, difficulty_success['rate']):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{val:.1f}%', ha='center', va='bottom', fontsize=11, weight='bold')
        
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        self._save_fig('06_difficulty_vs_success')
        plt.close()
    
    def plot_model_by_task_type(self):
        """Show top models used in each task type."""
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        for idx, task_type in enumerate(['classification', 'regression']):
            top_models = self.df_results[
                self.df_results['task_type'] == task_type
            ]['model_type'].value_counts().head(8)
            
            colors = sns.color_palette("husl", len(top_models))
            axes[idx].barh(range(len(top_models)), top_models.values, color=colors, edgecolor='black', linewidth=1)
            axes[idx].set_yticks(range(len(top_models)))
            axes[idx].set_yticklabels(top_models.index, fontsize=10)
            axes[idx].set_xlabel('Count', fontsize=10, weight='bold')
            axes[idx].set_title(f'Top Models in {task_type.capitalize()}', fontsize=11, weight='bold')
            axes[idx].invert_yaxis()
            
            for i, val in enumerate(top_models.values):
                axes[idx].text(val + 0.3, i, str(int(val)), va='center', fontsize=9, weight='bold')
            
            axes[idx].grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        self._save_fig('07_model_by_task_type')
        plt.close()
    
    def plot_metric_by_model(self):
        """Box plot of metrics by top models."""
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        # Classification: top models by accuracy
        class_data = self.df_results[
            (self.df_results['task_type'] == 'classification') & 
            (self.df_results['accuracy'] > 0)
        ]
        top_models_class = class_data['model_type'].value_counts().head(8).index
        
        class_filtered = class_data[class_data['model_type'].isin(top_models_class)]
        sns.boxplot(data=class_filtered, y='model_type', x='accuracy', ax=axes[0], palette='Set2')
        axes[0].set_xlabel('Accuracy', fontsize=11, weight='bold')
        axes[0].set_ylabel('Model', fontsize=11, weight='bold')
        axes[0].set_title('Classification Accuracy by Model', fontsize=12, weight='bold')
        axes[0].grid(axis='x', alpha=0.3)
        
        # Regression: top models by R2
        reg_data = self.df_results[
            (self.df_results['task_type'] == 'regression') & 
            (self.df_results['r2_score'] > -10)
        ]
        top_models_reg = reg_data['model_type'].value_counts().head(8).index
        
        reg_filtered = reg_data[reg_data['model_type'].isin(top_models_reg)]
        sns.boxplot(data=reg_filtered, y='model_type', x='r2_score', ax=axes[1], palette='Set3')
        axes[1].set_xlabel('R² Score', fontsize=11, weight='bold')
        axes[1].set_ylabel('Model', fontsize=11, weight='bold')
        axes[1].set_title('Regression R² Score by Model', fontsize=12, weight='bold')
        axes[1].grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        self._save_fig('08_metric_by_model')
        plt.close()
    
    def plot_variant_distribution(self):
        """Distribution of variants in best pipelines per dataset."""
        fig, ax = plt.subplots(figsize=(11, 6))
        
        variant_dist = self.df_best['Best Variant'].value_counts().sort_index()
        colors = sns.color_palette("husl", len(variant_dist))
        
        wedges, texts, autotexts = ax.pie(
            variant_dist.values,
            labels=[f'Variant {v.split("_")[0]}' for v in variant_dist.index],
            autopct='%1.1f%%',
            colors=colors,
            startangle=45,
            textprops={'fontsize': 11, 'weight': 'bold'}
        )
        
        ax.set_title(
            'Distribution of Best Variants (per Dataset)\nTop Pipeline for Each of 65 Datasets',
            fontsize=13, weight='bold', pad=20
        )
        
        # Add legend with counts
        legend_labels = [f'Variant {v.split("_")[0]}: {count}' 
                        for v, count in variant_dist.items()]
        ax.legend(legend_labels, loc='upper right', fontsize=10)
        
        plt.tight_layout()
        self._save_fig('09_variant_distribution')
        plt.close()
    
    def plot_top_models(self):
        """Show top models in best pipelines per dataset."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        top_models = self.df_best['Model'].value_counts().head(10)
        colors = sns.color_palette("husl", len(top_models))
        
        bars = ax.barh(range(len(top_models)), top_models.values, color=colors, edgecolor='black', linewidth=1.5)
        ax.set_yticks(range(len(top_models)))
        ax.set_yticklabels(top_models.index, fontsize=11)
        ax.set_xlabel('Count', fontsize=11, weight='bold')
        ax.set_title('Top 10 Models in Best Pipelines per Dataset', fontsize=13, weight='bold', pad=15)
        ax.invert_yaxis()
        
        for i, (bar, val) in enumerate(zip(bars, top_models.values)):
            pct = (val / len(self.df_best) * 100)
            ax.text(val + 0.2, i, f'{int(val)} ({pct:.0f}%)', va='center', fontsize=10, weight='bold')
        
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        self._save_fig('10_top_models_best')
        plt.close()
    
    def plot_success_by_difficulty(self):
        """Stacked bar chart of success/failure by difficulty."""
        fig, ax = plt.subplots(figsize=(11, 6))
        
        difficulty_order = ['easy', 'mid', 'hard']
        stats = []
        
        for diff in difficulty_order:
            diff_data = self.df_results[self.df_results['difficulty'] == diff]
            success = (diff_data['is_success'] == 1).sum()
            failed = (diff_data['is_success'] == 0).sum()
            stats.append((success, failed))
        
        success_counts = [s[0] for s in stats]
        failed_counts = [s[1] for s in stats]
        
        x = np.arange(len(difficulty_order))
        width = 0.6
        
        bars1 = ax.bar(x, success_counts, width, label='Success', color='#2ecc71', edgecolor='black', linewidth=1.5)
        bars2 = ax.bar(x, failed_counts, width, bottom=success_counts, label='Failed', color='#e74c3c', edgecolor='black', linewidth=1.5)
        
        ax.set_ylabel('Number of Pipelines', fontsize=11, weight='bold')
        ax.set_title('Success vs Failure Distribution by Dataset Difficulty', fontsize=13, weight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels([d.capitalize() for d in difficulty_order], fontsize=11)
        ax.legend(fontsize=10)
        
        # Add value labels
        for i, (s, f) in enumerate(stats):
            total = s + f
            s_pct = (s / total * 100)
            f_pct = (f / total * 100)
            ax.text(i, s/2, f'{int(s)}', ha='center', va='center', fontsize=10, weight='bold', color='white')
            ax.text(i, s + f/2, f'{int(f)}', ha='center', va='center', fontsize=10, weight='bold', color='white')
        
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        self._save_fig('11_success_by_difficulty_stacked')
        plt.close()
    
    def plot_model_success_rates(self):
        """Success rate for top 10 models."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        top_models = self.df_results['model_type'].value_counts().head(10).index
        model_stats = []
        
        for model in top_models:
            model_data = self.df_results[self.df_results['model_type'] == model]
            success_rate = (model_data['is_success'].sum() / len(model_data) * 100)
            model_stats.append((model, success_rate, len(model_data)))
        
        models, rates, counts = zip(*sorted(model_stats, key=lambda x: x[1], reverse=True))
        colors = ['#2ecc71' if r > 70 else '#f39c12' if r > 60 else '#e74c3c' for r in rates]
        
        bars = ax.barh(range(len(models)), rates, color=colors, edgecolor='black', linewidth=1.5)
        ax.set_yticks(range(len(models)))
        ax.set_yticklabels(models, fontsize=11)
        ax.set_xlabel('Success Rate (%)', fontsize=11, weight='bold')
        ax.set_title('Success Rate by Model (Top 10 Models)', fontsize=13, weight='bold', pad=15)
        ax.set_xlim(0, 100)
        ax.invert_yaxis()
        
        for i, (bar, rate, count) in enumerate(zip(bars, rates, counts)):
            ax.text(rate + 2, i, f'{rate:.1f}% (n={int(count)})', va='center', fontsize=10, weight='bold')
        
        ax.axvline(x=70.7, color='gray', linestyle='--', alpha=0.5, label='Overall avg (70.7%)')
        ax.legend(fontsize=10)
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        self._save_fig('12_model_success_rates')
        plt.close()
    
    def _save_fig(self, name):
        """Save figure to output directory."""
        filepath = self.output_dir / f'{name}.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"  ✅ {filepath.name}")


def main():
    """Main execution."""
    # Results directory
    results_dir = Path(__file__).parent.parent.parent / 'data' / 'batch_results' / 'resilient_execution'
    
    # Optional custom output directory
    output_dir = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not results_dir.exists():
        print(f"❌ Results directory not found: {results_dir}")
        sys.exit(1)
    
    visualizer = PipelineVisualizer(results_dir, output_dir)
    visualizer.generate_all()


if __name__ == '__main__':
    main()
