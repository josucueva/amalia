#!/usr/bin/env python3
"""
Re-execute Mistral and Llama pipelines with proper test_indices isolation.
This corrects the data leakage issue where evaluation was done on 100% of data instead of 20% test set.
"""

import json
import subprocess
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

def main():
    project_root = Path("/home/joshua/Code/ai_projects/amalia")
    backend_dir = project_root / "backend"
    
    # Load current Mistral/Llama data to extract datasets
    print("=" * 80)
    print("RE-EXECUTING MISTRAL AND LLAMA PIPELINES WITH TEST_INDICES")
    print("=" * 80)
    print()
    
    mistral_old = pd.read_csv(project_root / "data/batch_results/mistral_5x_duplicated.csv")
    llama_old = pd.read_csv(project_root / "data/batch_results/llama_5x_duplicated.csv")
    
    # Get unique datasets
    mistral_datasets = sorted(mistral_old['dataset_id'].unique())
    llama_datasets = sorted(llama_old['dataset_id'].unique())
    
    print(f"📊 Mistral: {len(mistral_datasets)} datasets, currently {len(mistral_old)} pipelines")
    print(f"   - Mean accuracy (OLD): {mistral_old['accuracy'].mean():.2%}")
    print(f"   - Mean f1_score (OLD): {mistral_old['f1_score'].mean():.2%}")
    
    print(f"\n📊 Llama: {len(llama_datasets)} datasets, currently {len(llama_old)} pipelines")
    print(f"   - Mean accuracy (OLD): {llama_old['accuracy'].mean():.2%}")
    print(f"   - Mean f1_score (OLD): {llama_old['f1_score'].mean():.2%}")
    
    print("\n" + "=" * 80)
    print("STEP 1: RE-EXECUTE MISTRAL PIPELINES")
    print("=" * 80)
    
    # Re-execute Mistral
    mistral_command = [
        sys.executable,
        str(backend_dir / "scripts/execute_batch_pipelines.py"),
        "--model", "mistral",
        "--datasets", ",".join(mistral_datasets),
        "--output", str(project_root / "data/batch_results/mistral_reexecuted"),
        "--verbose"
    ]
    
    print(f"\n🚀 Command: {' '.join(mistral_command[:6])} ...")
    print("\nExecuting Mistral...")
    
    result_mistral = subprocess.run(mistral_command, cwd=project_root)
    
    if result_mistral.returncode != 0:
        print("❌ Mistral execution failed!")
        return False
    
    print("\n✅ Mistral re-execution completed!")
    
    print("\n" + "=" * 80)
    print("STEP 2: RE-EXECUTE LLAMA PIPELINES")
    print("=" * 80)
    
    # Re-execute Llama
    llama_command = [
        sys.executable,
        str(backend_dir / "scripts/execute_batch_pipelines.py"),
        "--model", "llama",
        "--datasets", ",".join(llama_datasets),
        "--output", str(project_root / "data/batch_results/llama_reexecuted"),
        "--verbose"
    ]
    
    print(f"\n🚀 Command: {' '.join(llama_command[:6])} ...")
    print("\nExecuting Llama...")
    
    result_llama = subprocess.run(llama_command, cwd=project_root)
    
    if result_llama.returncode != 0:
        print("❌ Llama execution failed!")
        return False
    
    print("\n✅ Llama re-execution completed!")
    
    print("\n" + "=" * 80)
    print("STEP 3: COMPARE OLD vs NEW RESULTS")
    print("=" * 80)
    
    # Load new results
    mistral_new_path = project_root / "data/batch_results/mistral_reexecuted/pipeline_results.csv"
    llama_new_path = project_root / "data/batch_results/llama_reexecuted/pipeline_results.csv"
    
    if mistral_new_path.exists():
        mistral_new = pd.read_csv(mistral_new_path)
        print(f"\n📊 MISTRAL NEW RESULTS:")
        print(f"   - Pipelines: {len(mistral_new)}")
        print(f"   - Mean accuracy (NEW): {mistral_new['accuracy'].mean():.2%}")
        print(f"   - Mean f1_score (NEW): {mistral_new['f1_score'].mean():.2%}")
        print(f"   - Success rate: {(mistral_new['status'] == 'success').sum() / len(mistral_new):.1%}")
        print(f"\n   ✅ IMPROVEMENT: {(mistral_old['accuracy'].mean() - mistral_new['accuracy'].mean()):.2%} correction applied")
    else:
        print(f"⚠️  Mistral results not found at {mistral_new_path}")
    
    if llama_new_path.exists():
        llama_new = pd.read_csv(llama_new_path)
        print(f"\n📊 LLAMA NEW RESULTS:")
        print(f"   - Pipelines: {len(llama_new)}")
        print(f"   - Mean accuracy (NEW): {llama_new['accuracy'].mean():.2%}")
        print(f"   - Mean f1_score (NEW): {llama_new['f1_score'].mean():.2%}")
        print(f"   - Success rate: {(llama_new['status'] == 'success').sum() / len(llama_new):.1%}")
        print(f"\n   ✅ IMPROVEMENT: {(llama_old['accuracy'].mean() - llama_new['accuracy'].mean()):.2%} correction applied")
    else:
        print(f"⚠️  Llama results not found at {llama_new_path}")
    
    print("\n" + "=" * 80)
    print("RE-EXECUTION COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Review new results in:")
    print(f"   - {mistral_new_path}")
    print(f"   - {llama_new_path}")
    print("2. Regenerate all visualizations with corrected data")
    print("3. Update comparative analysis")
    
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
