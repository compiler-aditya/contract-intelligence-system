# Q&A Evaluation

This directory contains the evaluation framework for the Contract Intelligence RAG system.

## Files

- `qa_eval_set.json` - Evaluation dataset with 20 questions across different contract types
- `run_evaluation.py` - Evaluation script that tests the system and calculates scores
- `eval_results.json` - Detailed evaluation results (generated)
- `SCORE.txt` - One-line score summary (generated)

## Running the Evaluation

### 1. Start the Application

```bash
make up
```

### 2. Ingest Sample Contracts

```bash
# Ingest your test contracts
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "files=@sample_contracts/contract1.pdf" \
  -F "files=@sample_contracts/contract2.pdf"

# Save the document_ids from the response
```

### 3. Run Evaluation

```bash
python eval/run_evaluation.py <document_id_1> <document_id_2> ...
```

Example:
```bash
python eval/run_evaluation.py \
  123e4567-e89b-12d3-a456-426614174000 \
  123e4567-e89b-12d3-a456-426614174001
```

## Evaluation Metrics

The script calculates:

1. **Keyword Match Score** (60% weight)
   - Percentage of expected keywords found in the answer
   - Tests factual accuracy

2. **Semantic Similarity Score** (40% weight)
   - Word overlap between actual and expected answer
   - Tests overall answer quality

3. **Combined Score**
   - Weighted average of the above
   - Pass threshold: ≥ 0.5

4. **Pass Rate**
   - Percentage of questions that passed the threshold

## Evaluation Dataset

The evaluation set includes 20 questions across 5 contract types:

- **MSA (Master Service Agreement)**: 10 questions
  - Payment terms, parties, term, liability, etc.

- **NDA (Non-Disclosure Agreement)**: 2 questions
  - Confidentiality duration and scope

- **SaaS Agreement**: 2 questions
  - Subscription fees, SLA commitments

- **Consulting Agreement**: 2 questions
  - IP ownership, rates

- **Employment Agreement**: 2 questions
  - Compensation, termination

- **General**: 2 questions
  - Dispute resolution, amendments

## Expected Score

Target score: **≥ 0.70** (70%)

- **0.80-1.00**: Excellent
- **0.70-0.79**: Good
- **0.50-0.69**: Acceptable
- **< 0.50**: Needs improvement

## Interpreting Results

The detailed results in `eval_results.json` include:

```json
{
  "timestamp": "2024-01-24T12:00:00",
  "total_questions": 20,
  "passed": 16,
  "failed": 4,
  "pass_rate": 0.80,
  "average_score": 0.75,
  "results": [
    {
      "id": "q1",
      "question": "...",
      "expected_answer": "...",
      "actual_answer": "...",
      "scores": {
        "keyword_match_score": 0.8,
        "semantic_similarity_score": 0.7,
        "combined_score": 0.76,
        "passed": true
      }
    }
  ]
}
```

## Customizing the Evaluation

### Add New Questions

Edit `qa_eval_set.json`:

```json
{
  "id": "q21",
  "document_type": "MSA",
  "question": "Your question here?",
  "expected_answer": "Expected answer",
  "expected_keywords": ["keyword1", "keyword2"],
  "category": "category_name"
}
```

### Adjust Pass Threshold

Edit `run_evaluation.py`:

```python
"passed": combined_score >= 0.5,  # Change threshold here
```

### Change Score Weights

Edit the `evaluate_answer` method:

```python
combined_score = (keyword_score * 0.6) + (similarity_score * 0.4)
# Adjust weights as needed
```

## Troubleshooting

### "Error: Evaluation set not found"
- Make sure you're running from the project root directory
- Check that `eval/qa_eval_set.json` exists

### "No documents found"
- Ensure you've ingested documents first
- Verify document IDs are correct UUIDs
- Check that documents were processed successfully

### Low Scores
- Verify documents contain the expected information
- Check that the RAG system has proper context
- Review the detailed results to see which questions failed
- Consider adjusting chunking parameters or prompts

## CI/CD Integration

To integrate with CI/CD:

```bash
#!/bin/bash
# Example CI script

# Start services
docker-compose up -d

# Wait for services
sleep 10

# Ingest test contracts
DOC_IDS=$(python scripts/ingest_test_contracts.py)

# Run evaluation
python eval/run_evaluation.py $DOC_IDS

# Check score
SCORE=$(cat eval/SCORE.txt)
echo "Evaluation: $SCORE"

# Fail if score < 0.70
if [ $(python -c "import json; print(json.load(open('eval/eval_results.json'))['average_score'] >= 0.70)") != "True" ]; then
  echo "Score too low!"
  exit 1
fi
```
