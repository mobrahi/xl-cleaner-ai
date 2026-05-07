import pandas as pd
import ollama
from rapidfuzz import fuzz, process
import typer
from typing import Optional, List, Dict
import json
import re
from pathlib import Path
import time

app = typer.Typer()

# OPTIMIZED FOR MacBook M2 8GB + qwen2.5-coder:3b
MODEL_NAME = "qwen2.5-coder:3b"
MAX_BATCH_SIZE = 25  # Limit batch size for memory
REQUEST_DELAY = 0.5  # Small delay between LLM calls to prevent overload

# ---------- Enhanced LLM Call for qwen2.5-coder ----------
def ask_qwen(prompt: str, max_retries: int = 2) -> str:
    """Optimized for qwen2.5-coder:3b on M2 8GB."""
    for attempt in range(max_retries):
        try:
            # Clear any cached responses
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.1,  # Lower temp = more consistent for structured data
                    "num_predict": 400,   # Reduced from 500 for speed
                    "top_k": 20,          # Limit vocabulary for faster inference
                    "top_p": 0.9,
                }
            )
            return response["message"]["content"].strip()
        except Exception as e:
            print(f"⚠️  Ollama error (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retry
            else:
                return ""
    return ""

# ---------- Memory-Efficient Header Normalization ----------
def normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Headers are usually small - LLM can handle all at once."""
    print("\n📋 Step 1: Normalizing headers...")
    current_headers = list(df.columns)
    
    # Only call LLM if we have reasonable number of columns
    if len(current_headers) <= 50:
        prompt = f"""
You are cleaning spreadsheet headers. Convert these to clean names:
- lowercase, underscores instead of spaces
- remove special chars
- keep meaning

Headers: {current_headers}

Return ONLY JSON mapping original->clean.
Example: {{"Emp. Name": "employee_name"}}

JSON:
"""
        response = ask_qwen(prompt)
        
        try:
            # Extract JSON more robustly
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                mapping = json.loads(json_match.group())
                if isinstance(mapping, dict) and len(mapping) > 0:
                    df.rename(columns=mapping, inplace=True)
                    print(f"✅ Cleaned {len(mapping)} headers")
                    return df
        except:
            pass
    
    # Fallback to simple cleaning
    print("⚠️  Using fallback header cleaning")
    fallback_mapping = {}
    for col in current_headers:
        cleaned = str(col).lower()
        cleaned = re.sub(r'[^\w\s]', '', cleaned)
        cleaned = re.sub(r'\s+', '_', cleaned)
        cleaned = re.sub(r'_+', '_', cleaned)
        fallback_mapping[col] = cleaned.strip('_') if cleaned.strip('_') else 'column'
    
    df.rename(columns=fallback_mapping, inplace=True)
    return df

# ---------- Batch Typo Fixing ----------
def fix_typos_batch(df: pd.DataFrame, col: str, values_batch: List[str]) -> Dict:
    """Send a batch of values to LLM for correction."""
    if not values_batch:
        return {}
    
    prompt = f"""
Fix typos in these values from column '{col}'. 
Return JSON mapping wrong->correct.
Only fix obvious typos, keep legitimate variations.

Values: {values_batch}

Example: {{"Nwe York": "New York", "Micheal": "Michael"}}

JSON:
"""
    response = ask_qwen(prompt)
    try:
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            corrections = json.loads(json_match.group())
            return {k: v for k, v in corrections.items() if k in values_batch}
    except:
        pass
    return {}

def fix_typos_in_column(df: pd.DataFrame, col: str, known_terms: Optional[List[str]] = None) -> pd.DataFrame:
    """Memory-efficient typo fixing with batching."""
    if df[col].dtype != "object":
        return df
    
    unique_vals = df[col].dropna().unique()
    if len(unique_vals) < 2:
        return df
    
    corrections = {}
    
    # Stage 1: Fast fuzzy matching (no LLM)
    if known_terms:
        print(f"  🔍 Fuzzy matching '{col}'...")
        for val in unique_vals[:100]:  # Limit to first 100 to avoid slowdown
            if pd.isna(val) or len(str(val)) < 3:
                continue
            match, score, _ = process.extractOne(str(val), known_terms, scorer=fuzz.ratio)
            if score > 85:
                corrections[val] = match
        
        if corrections:
            df[col] = df[col].replace(corrections)
            print(f"    ✓ Fixed {len(corrections)} via fuzzy matching")
            unique_vals = df[col].dropna().unique()
    
    # Stage 2: LLM correction in small batches
    remaining = [v for v in unique_vals 
                if v not in corrections and len(str(v)) > 2 and len(str(v)) < 50]
    
    if remaining:
        print(f"  🤖 LLM correcting {len(remaining)} values in '{col}'...")
        
        # Process in small batches for memory efficiency
        batch_corrections = {}
        for i in range(0, len(remaining), MAX_BATCH_SIZE):
            batch = remaining[i:i+MAX_BATCH_SIZE]
            batch_result = fix_typos_batch(df, col, batch)
            batch_corrections.update(batch_result)
            time.sleep(REQUEST_DELAY)  # Small pause between batches
        
        if batch_corrections:
            df[col] = df[col].replace(batch_corrections)
            print(f"    ✓ LLM fixed {len(batch_corrections)} values")
    
    return df

# ---------- Simplified Deduplication ----------
def deduplicate_rows(df: pd.DataFrame, semantic_cols: Optional[List[str]] = None) -> pd.DataFrame:
    """Exact dedup only - semantic is memory heavy for 8GB."""
    print("\n🔄 Step 3: Deduplicating rows...")
    initial = len(df)
    
    # Exact duplicates (memory efficient)
    df = df.drop_duplicates()
    exact_removed = initial - len(df)
    print(f"  📊 Removed {exact_removed} exact duplicate rows")
    
    # Optional: Simple semantic dedup for small datasets only
    if semantic_cols and len(df) < 500:  # Only for smaller datasets
        print(f"  🧠 Checking near-duplicates on {len(df)} rows...")
        
        # Group by first 3 words of first semantic column (simple heuristic)
        first_col = semantic_cols[0]
        if first_col in df.columns:
            df['_group_key'] = df[first_col].astype(str).str[:30]
            
            to_remove = []
            for key, group in df.groupby('_group_key'):
                if len(group) > 1:
                    # Keep the first one, mark others for removal
                    to_remove.extend(group.index[1:].tolist())
            
            df.drop(index=to_remove, inplace=True)
            df.drop('_group_key', axis=1, inplace=True)
            print(f"  ✓ Removed {len(to_remove)} near-duplicates using heuristic")
    
    return df

# ---------- Performance Monitor ----------
def get_memory_usage():
    """Check available memory (simple version)."""
    import psutil
    mem = psutil.virtual_memory()
    return f"{mem.used/1e9:.1f}GB used / {mem.available/1e9:.1f}GB free"

# ---------- Main Command ----------
@app.command()
def clean(
    input_path: str,
    output_path: str = "cleaned_output.csv",
    fix_typos: bool = True,
    semantic_dedup_cols: Optional[str] = None,
    known_terms_file: Optional[str] = None,
    output_format: str = "csv"
):
    """Clean spreadsheet with qwen2.5-coder:3b on M2 Mac."""
    
    print(f"\n🚀 AI Cleaner - Optimized for MacBook M2 8GB")
    print(f"   Model: {MODEL_NAME}")
    print(f"   Memory: {get_memory_usage()}")
    
    # Test Ollama
    try:
        test_response = ollama.chat(model=MODEL_NAME, 
                                   messages=[{"role":"user","content":"OK"}],
                                   options={"num_predict": 5})
        print(f"✅ Ollama ready")
    except:
        print(f"❌ Ollama not running. Start with: ollama serve")
        print(f"   Then pull model: ollama pull {MODEL_NAME}")
        return
    
    # Load file
    file_ext = Path(input_path).suffix.lower()
    try:
        if file_ext == '.csv':
            df = pd.read_csv(input_path, low_memory=False)
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(input_path, engine='openpyxl')
        else:
            print(f"❌ Unsupported format: {file_ext}")
            return
    except Exception as e:
        print(f"❌ Load failed: {e}")
        return
    
    original_shape = df.shape
    print(f"✅ Loaded: {original_shape[0]:,} rows, {original_shape[1]} cols")
    
    # Step 1: Headers (always do this)
    df = normalize_headers(df)
    
    # Step 2: Typos (optional, can be slow)
    if fix_typos:
        print("\n🔧 Step 2: Fixing typos...")
        string_cols = df.select_dtypes(include=["object"]).columns
        for i, col in enumerate(string_cols[:5], 1):  # Limit to first 5 columns for speed
            print(f"  {i}/{min(5, len(string_cols))}: '{col}'")
            df = fix_typos_in_column(df, col, None)
            print(f"    Memory: {get_memory_usage()}")
    
    # Step 3: Deduplicate
    sem_cols = semantic_dedup_cols.split(",") if semantic_dedup_cols else None
    df = deduplicate_rows(df, semantic_cols=sem_cols)
    
    # Save
    try:
        if output_format == 'csv':
            df.to_csv(output_path, index=False)
        else:
            if not output_path.endswith('.xlsx'):
                output_path = output_path.replace('.csv', '.xlsx')
            df.to_excel(output_path, index=False)
        
        print(f"\n💾 Saved: {output_path}")
        print(f"   Final: {len(df):,} rows, {len(df.columns)} cols")
        print(f"   Memory: {get_memory_usage()}")
    except Exception as e:
        print(f"❌ Save failed: {e}")

@app.command()
def benchmark():
    """Test performance on your M2."""
    print("Running benchmark on MacBook M2 8GB...")
    
    import time
    test_prompts = [
        "Say 'test'",
        "Fix typo: 'New Yrok' ->",
        '{"wrong": "correct"}'
    ]
    
    for prompt in test_prompts:
        start = time.time()
        response = ask_qwen(prompt)
        elapsed = time.time() - start
        print(f"  {elapsed:.2f}s - {prompt[:30]}... -> {response[:50]}")

if __name__ == "__main__":
    app()