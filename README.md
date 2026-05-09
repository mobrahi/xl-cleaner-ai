# 🧹 AI-Powered Spreadsheet Cleaner

Automatically clean messy spreadsheets using local LLMs (Ollama) + Pandas. Fix headers, correct typos, and remove duplicates without sending your data to the cloud.

## ✨ Features

- **Smart Header Normalization** - Convert messy column names to clean, standardized formats
- **Intelligent Typo Correction** - Fix misspellings using fuzzy matching + LLM
- **Duplicate Removal** - Remove both exact and semantic duplicates
- **Fully Local** - Runs on your machine with Ollama (no API costs, private)
- **Multiple Formats** - Supports CSV, Excel (.xlsx, .xls)

## 🚀 Quick Start

### Prerequisites

```bash
# Install Ollama (Mac/Linux/Windows)
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (choose one based on your hardware)
ollama pull qwen2.5-coder:3b     # Fast, ~3GB RAM (good for 8GB Macs)
ollama pull llama3.2:3b          # Balanced
ollama pull mistral:7b           # Better quality, needs 16GB+ RAM
```

### Installation

```bash
# Clone or download the script
git clone <your-repo-url>
cd spreadsheet-cleaner

# Install Python dependencies
pip install pandas ollama typer openpyxl rapidfuzz
```

### Basic Usage

```bash
# Clean a CSV file
python cleaner.py clean messy_data.csv

# Clean an Excel file
python cleaner.py clean messy_data.xlsx

# Specify output file
python cleaner.py clean data.csv --output-path clean_data.csv
```

## 📖 Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `input_path` | Path to your messy file | Required |
| `--output-path` | Output file path | `cleaned_output.csv` |
| `--model` | Ollama model to use | `qwen2.5-coder:3b` |
| `--fix-typos` | Enable typo correction | `True` |
| `--semantic-dedup-cols` | Columns for semantic dedup (comma-separated) | None |
| `--known-terms-file` | Text file with correct terms for fuzzy matching | None |
| `--output-format` | `csv` or `excel` | `csv` |

### Examples

```bash
# Clean with semantic deduplication on specific columns
python cleaner.py clean sales.xlsx --semantic-dedup-cols "customer_name,email,phone"

# Use a different model for better accuracy
python cleaner.py clean data.csv --model mistral:7b

# Provide known correct terms for better typo fixing
python cleaner.py clean products.csv --known-terms-file valid_cities.txt

# Skip typo fixing (faster for large files)
python cleaner.py clean huge_file.csv --fix-typos False

# Save as Excel
python cleaner.py clean data.csv --output-format excel --output-path cleaned.xlsx
```

## 🖥️ Hardware Recommendations

| Model | RAM Usage | Speed | Best For |
|-------|-----------|-------|----------|
| `qwen2.5-coder:3b` | ~3GB | Fast | 8GB MacBooks, laptops |
| `llama3.2:3b` | ~3.5GB | Fast | Most computers |
| `phi3:mini` | ~4GB | Medium | Balanced quality/speed |
| `mistral:7b` | ~7GB | Slow | High accuracy, 16GB+ RAM |

## 📊 What It Cleaned Example

**Before:**
```
Emp. Name    | DOB        | Addres      | City
-------------|------------|-------------|----------
John Doe     | 1990-01-15 | 123 Main St | New Yrok
J. Doe       | 1990-01-15 | 123 Main St | NYC
```

**After:**
```
employee_name | date_of_birth | address      | city
--------------|---------------|--------------|---------
John Doe      | 1990-01-15    | 123 Main St  | New York
```

## 🔧 Troubleshooting

### "Ollama is not running"

```bash
# Start Ollama
ollama serve

# In another terminal, verify it's working
ollama list
```

### "Model not found"

```bash
# Pull the model first
ollama pull qwen2.5-coder:3b
```

### Memory issues on 8GB Mac

Try these optimizations:

```bash
# Use smaller model
python cleaner.py clean data.csv --model qwen2.5-coder:3b

# Disable typo fixing (most memory-intensive)
python cleaner.py clean data.csv --fix-typos False

# Process files in chunks (for very large files >50MB)
# Open the script and reduce MAX_BATCH_SIZE to 10
```

### Slow performance

- Use CSV instead of Excel (faster loading)
- Disable typo fixing for files >10,000 rows
- Use `qwen2.5-coder:3b` or `llama3.2:3b` for fastest speed

## 📁 Creating a Known Terms File

Create a text file with one correct term per line:

```text
# valid_products.txt
New York
Los Angeles
Chicago
Houston
Phoenix
```

## 🧪 Testing Your Setup

```bash
# Test if Ollama is working
python cleaner.py test-ollama

# Run benchmark on your machine
python cleaner.py benchmark
```

## 📈 Performance Expectations

On MacBook M2 8GB with `qwen2.5-coder:3b`:

| File Size | Operation | Time | Memory |
|-----------|-----------|------|--------|
| 1,000 rows | Full cleaning | 30-60 sec | ~500MB |
| 5,000 rows | Full cleaning | 2-3 min | ~700MB |
| 10,000 rows | Headers + dedup only | 20-30 sec | ~400MB |
| 50,000 rows | Headers only | 5 sec | ~300MB |

## 🛠️ Project Structure

```
spreadsheet-cleaner/
├── cleaner.py          # Main script
├── README.md           # This file
├── requirements.txt    # Python dependencies
└── examples/
    ├── messy_data.csv  # Example input
    └── valid_terms.txt # Example known terms file
```

## 📦 Dependencies

- `pandas` - Data manipulation
- `ollama` - Local LLM interface
- `typer` - CLI interface
- `openpyxl` - Excel file support
- `rapidfuzz` - Fast fuzzy matching

Install all at once:
```bash
pip install -r requirements.txt
```

Create `requirements.txt`:
```txt
pandas>=2.0.0
ollama>=0.1.0
typer>=0.9.0
openpyxl>=3.1.0
rapidfuzz>=3.5.0
```

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Add support for Google Sheets
- Implement progress bars for long operations
- Add interactive mode (review changes before saving)
- Support for more file formats (JSON, Parquet)

## 📝 License

MIT License - Free for personal and commercial use

## ⚠️ Disclaimer

- Always backup your original files before cleaning
- LLM corrections are suggestions - review critical data manually
- Performance varies based on hardware and file complexity

## 🙏 Acknowledgments

- [Ollama](https://ollama.com/) for making local LLMs easy
- [Pandas](https://pandas.pydata.org/) for data processing power
- [RapidFuzz](https://github.com/maxbachmann/RapidFuzz) for fast string matching

---

**Made with 🧠 for clean data**
