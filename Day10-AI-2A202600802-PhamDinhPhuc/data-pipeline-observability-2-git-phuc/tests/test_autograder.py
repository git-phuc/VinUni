"""
==============================================================
VinUni Day 10 - Autograding Tests
==============================================================
DO NOT MODIFY THIS FILE.
These tests are run automatically by GitHub Classroom.

Rubric (100 points):
  test_script_runs        - 20 pts (ETL Functional)
  test_validation         - 10 pts (ETL Validation)
  test_transformation     - 10 pts (ETL Transformation)
  test_logging            - 10 pts (Observability: Status Reporting)
  test_timestamp          - 10 pts (Observability: Timestamps)
  test_report_exists      - 10 pts (Stress Test: Completion)
  test_report_analysis    - 10 pts (Stress Test: Critical Thinking)
  test_structure          - 10 pts (GitHub: File Structure)
  test_readme             - 10 pts (GitHub: README Quality)
==============================================================
"""

import subprocess
import sys
import os
import re

# Ensure pandas is available
try:
    import pandas as pd
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "-q"])
    import pandas as pd


# ============================================================
# MODULE 1: ETL Script (40 points)
# ============================================================

class TestETLFunctional:
    """Test 1a: Script runs without crashing and produces CSV (20 pts)"""

    def test_script_runs(self):
        """solution.py runs successfully and creates processed_data.csv"""
        # Clean up any existing output
        if os.path.exists("processed_data.csv"):
            os.remove("processed_data.csv")

        result = subprocess.run(
            [sys.executable, "solution.py"],
            capture_output=True,
            timeout=30,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        assert result.returncode == 0, (
            f"Script crashed with exit code {result.returncode}.\n"
            f"stderr: {result.stderr[:300]}"
        )

        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "processed_data.csv"
        )
        assert os.path.exists(csv_path), (
            "Script ran successfully but did not create processed_data.csv. "
            "Make sure your load() function saves the DataFrame to CSV."
        )


class TestETLValidation:
    """Test 1b: Invalid records are removed (10 pts)"""

    def test_validation(self):
        """No records with price <= 0 or empty category in output"""
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "processed_data.csv"
        )
        if not os.path.exists(csv_path):
            # Run the script first
            subprocess.run(
                [sys.executable, "solution.py"],
                capture_output=True, timeout=30, text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )

        assert os.path.exists(csv_path), "processed_data.csv not found"
        df = pd.read_csv(csv_path)

        # Check: no negative/zero price
        assert 'price' in df.columns, "Missing 'price' column in CSV"
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        bad_prices = df[df['price'] <= 0]
        assert bad_prices.empty, (
            f"Found {len(bad_prices)} records with price <= 0. "
            f"Your validate() should drop these records."
        )

        # Check: no empty category
        assert 'category' in df.columns, "Missing 'category' column in CSV"
        empty_cats = df[df['category'].isna() | (df['category'].astype(str).str.strip() == '')]
        assert empty_cats.empty, (
            f"Found {len(empty_cats)} records with empty category. "
            f"Your validate() should drop these records."
        )


class TestETLTransformation:
    """Test 1c: Transformation logic is correct (10 pts)"""

    def test_transformation(self):
        """discounted_price = price * 0.9 and category is Title Case"""
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "processed_data.csv"
        )
        assert os.path.exists(csv_path), "processed_data.csv not found"
        df = pd.read_csv(csv_path)

        # Check discounted_price exists
        assert 'discounted_price' in df.columns, (
            "Missing 'discounted_price' column. "
            "Add: df['discounted_price'] = df['price'] * 0.9"
        )

        # Check discounted_price values
        expected = df['price'] * 0.9
        diff = abs(df['discounted_price'] - expected)
        assert all(diff < 0.01), (
            "discounted_price values are incorrect. "
            "Expected: price * 0.9 (10% discount)"
        )

        # Check Title Case
        assert 'category' in df.columns, "Missing 'category' column"
        not_title = df[df['category'].astype(str) != df['category'].astype(str).str.title()]
        assert not_title.empty, (
            f"Categories not in Title Case: {not_title['category'].tolist()}. "
            f"Add: df['category'] = df['category'].str.title()"
        )


# ============================================================
# MODULE 2: Observability (20 points)
# ============================================================

class TestLogging:
    """Test 2a: Script outputs processed/dropped counts (10 pts)"""

    def test_logging(self):
        """stdout contains processed count and dropped/error count"""
        result = subprocess.run(
            [sys.executable, "solution.py"],
            capture_output=True, timeout=30, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        stdout = result.stdout

        has_processed = bool(re.search(
            r'\d+\s*(?:record|kept|valid|processed|success|loaded)',
            stdout, re.IGNORECASE
        ))
        assert has_processed, (
            "Script output does not mention how many records were processed/valid. "
            "Add a print() showing the count, e.g.: "
            "print(f'Validation summary: {len(valid)} kept, {len(dropped)} dropped.')"
        )

        has_dropped = bool(re.search(
            r'\d+\s*(?:drop|error|fail|invalid|reject)',
            stdout, re.IGNORECASE
        ))
        assert has_dropped, (
            "Script output does not mention how many records were dropped/invalid. "
            "Add a print() showing errors found."
        )


class TestTimestamp:
    """Test 2b: Output CSV has processed_at column (10 pts)"""

    def test_timestamp(self):
        """processed_data.csv contains a 'processed_at' column"""
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "processed_data.csv"
        )
        assert os.path.exists(csv_path), "processed_data.csv not found"
        df = pd.read_csv(csv_path)

        assert 'processed_at' in df.columns, (
            "Missing 'processed_at' column in CSV. "
            "Add: df['processed_at'] = datetime.datetime.now().isoformat()"
        )


# ============================================================
# MODULE 3: Stress Test Report (20 points)
# ============================================================

class TestReportExists:
    """Test 3a: experiment_report.md exists with comparison table (10 pts)"""

    def test_report_exists(self):
        """experiment_report.md has a filled comparison table"""
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "experiment_report.md"
        )
        assert os.path.exists(report_path), (
            "experiment_report.md not found. "
            "Fill in the experiment report template."
        )

        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Must have a markdown table
        pipe_count = content.count('|')
        assert pipe_count >= 8, (
            f"No comparison table found in experiment_report.md "
            f"(found {pipe_count} pipe characters, need >= 8). "
            f"Fill in the results table."
        )

        # Must mention both scenarios
        has_clean = bool(re.search(r'clean', content, re.IGNORECASE))
        has_garbage = bool(re.search(r'garbage|poison', content, re.IGNORECASE))
        assert has_clean and has_garbage, (
            "Report should mention both 'Clean' and 'Garbage' data scenarios."
        )


class TestReportAnalysis:
    """Test 3b: Report has substantial analysis (10 pts)"""

    def test_report_analysis(self):
        """Analysis section has >= 50 words of student-written content"""
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "experiment_report.md"
        )
        assert os.path.exists(report_path), "experiment_report.md not found"

        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find analysis section
        match = re.search(
            r'(?:phan tich|tai sao|analysis|why|nhan xet).*?\n(.*)',
            content, re.IGNORECASE | re.DOTALL
        )
        assert match, (
            "No analysis section found. "
            "Write your analysis under the 'Phan tich' heading."
        )

        analysis_text = match.group(1)
        # Remove template/placeholder text
        clean_text = re.sub(r'[#*|>\-_`\[\]\(\)]', '', analysis_text)
        clean_text = re.sub(r'\(.*?ban.*?day\)', '', clean_text, flags=re.DOTALL)
        clean_text = re.sub(r'\(.*?Goi y.*?\)', '', clean_text, flags=re.DOTALL)
        clean_text = re.sub(r'\(.*?Hay phan tich.*?\)', '', clean_text, flags=re.DOTALL)
        clean_text = re.sub(r'\(.*?Dong y.*?\)', '', clean_text, flags=re.DOTALL)
        words = [w for w in clean_text.split() if len(w) > 1]

        assert len(words) >= 50, (
            f"Analysis is too short ({len(words)} words, need >= 50). "
            f"Write a detailed explanation of why the agent failed on garbage data."
        )


# ============================================================
# MODULE 4: GitHub Structure (20 points)
# ============================================================

class TestStructure:
    """Test 4a: Required files exist (10 pts)"""

    def test_structure(self):
        """All required files are present"""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        required = ["solution.py", "processed_data.csv", "experiment_report.md", "README.md"]
        missing = [f for f in required if not os.path.exists(os.path.join(base, f))]

        assert not missing, (
            f"Missing required files: {', '.join(missing)}. "
            f"Make sure all files are committed and pushed."
        )


class TestReadme:
    """Test 4b: README has substantial content (10 pts)"""

    def test_readme(self):
        """README.md has content, run instructions, and student ID"""
        readme_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "README.md"
        )
        assert os.path.exists(readme_path), "README.md not found"

        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check length
        assert len(content) >= 200, (
            f"README is too short ({len(content)} chars, need >= 200). "
            f"Add a description, run instructions, and your results."
        )

        # Check for run instructions
        has_instructions = bool(re.search(
            r'(?:how to run|pip|python|chay|install|setup)',
            content, re.IGNORECASE
        ))
        assert has_instructions, (
            "README does not contain run instructions. "
            "Add a section explaining how to run your pipeline."
        )

        
