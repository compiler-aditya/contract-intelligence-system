#!/usr/bin/env python3
"""
Q&A Evaluation Script for Contract Intelligence System

This script evaluates the RAG system's performance on a set of questions
and calculates accuracy metrics.
"""

import json
import asyncio
import httpx
from typing import List, Dict, Any
from pathlib import Path
import sys
from datetime import datetime


class QAEvaluator:
    """Evaluates Q&A system performance"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    def calculate_keyword_match_score(
        self, answer: str, expected_keywords: List[str]
    ) -> float:
        """
        Calculate score based on keyword presence
        Returns percentage of expected keywords found in answer
        """
        if not expected_keywords:
            return 1.0

        answer_lower = answer.lower()
        matches = sum(
            1 for keyword in expected_keywords if keyword.lower() in answer_lower
        )
        return matches / len(expected_keywords)

    def calculate_semantic_similarity(
        self, answer: str, expected_answer: str
    ) -> float:
        """
        Calculate semantic similarity (simplified version)
        In production, use sentence transformers for better accuracy
        """
        # Simple word overlap approach
        answer_words = set(answer.lower().split())
        expected_words = set(expected_answer.lower().split())

        if not expected_words:
            return 1.0

        overlap = answer_words.intersection(expected_words)
        return len(overlap) / len(expected_words)

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        expected_answer: str,
        expected_keywords: List[str],
    ) -> Dict[str, Any]:
        """Evaluate a single answer"""
        keyword_score = self.calculate_keyword_match_score(answer, expected_keywords)
        similarity_score = self.calculate_semantic_similarity(answer, expected_answer)

        # Combined score (weighted average)
        combined_score = (keyword_score * 0.6) + (similarity_score * 0.4)

        return {
            "keyword_match_score": keyword_score,
            "semantic_similarity_score": similarity_score,
            "combined_score": combined_score,
            "passed": combined_score >= 0.5,  # Pass threshold
        }

    async def ask_question(
        self, question: str, document_ids: List[str]
    ) -> Dict[str, Any]:
        """Ask a question via API"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/ask",
                json={"question": question, "document_ids": document_ids},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "answer": ""}

    async def run_evaluation(
        self, eval_set_path: str, document_ids: List[str]
    ) -> Dict[str, Any]:
        """Run evaluation on entire eval set"""
        # Load evaluation set
        with open(eval_set_path, "r") as f:
            eval_set = json.load(f)

        results = []
        total_score = 0.0

        print(f"\n{'=' * 80}")
        print(f"Running Q&A Evaluation - {len(eval_set)} questions")
        print(f"{'=' * 80}\n")

        for i, item in enumerate(eval_set, 1):
            print(f"[{i}/{len(eval_set)}] {item['question']}")

            # Get answer from API
            response = await self.ask_question(item["question"], document_ids)

            if "error" in response:
                print(f"  ❌ ERROR: {response['error']}\n")
                results.append(
                    {
                        **item,
                        "actual_answer": "",
                        "error": response["error"],
                        "scores": {
                            "keyword_match_score": 0.0,
                            "semantic_similarity_score": 0.0,
                            "combined_score": 0.0,
                            "passed": False,
                        },
                    }
                )
                continue

            actual_answer = response.get("answer", "")

            # Evaluate answer
            scores = self.evaluate_answer(
                item["question"],
                actual_answer,
                item["expected_answer"],
                item["expected_keywords"],
            )

            # Store result
            result = {
                **item,
                "actual_answer": actual_answer,
                "scores": scores,
            }
            results.append(result)

            # Print result
            status = "✅ PASS" if scores["passed"] else "❌ FAIL"
            print(f"  {status} (score: {scores['combined_score']:.2f})")
            print(f"  Expected: {item['expected_answer'][:100]}...")
            print(f"  Got: {actual_answer[:100]}...")
            print()

            total_score += scores["combined_score"]

        # Calculate overall metrics
        passed_count = sum(1 for r in results if r["scores"]["passed"])
        avg_score = total_score / len(eval_set) if eval_set else 0
        pass_rate = passed_count / len(eval_set) if eval_set else 0

        # Print summary
        print(f"\n{'=' * 80}")
        print("EVALUATION SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total Questions: {len(eval_set)}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {len(eval_set) - passed_count}")
        print(f"Pass Rate: {pass_rate * 100:.1f}%")
        print(f"Average Score: {avg_score:.2f}")
        print(f"{'=' * 80}\n")

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_questions": len(eval_set),
            "passed": passed_count,
            "failed": len(eval_set) - passed_count,
            "pass_rate": pass_rate,
            "average_score": avg_score,
            "results": results,
        }

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


async def main():
    """Main evaluation function"""
    # Configuration
    BASE_URL = "http://localhost:8000"
    EVAL_SET_PATH = "eval/qa_eval_set.json"
    OUTPUT_PATH = "eval/eval_results.json"

    # Check if eval set exists
    if not Path(EVAL_SET_PATH).exists():
        print(f"Error: Evaluation set not found at {EVAL_SET_PATH}")
        sys.exit(1)

    # Get document IDs from command line or use defaults
    if len(sys.argv) > 1:
        document_ids = sys.argv[1:]
    else:
        print(
            "Usage: python run_evaluation.py <document_id1> <document_id2> ..."
        )
        print("Note: Make sure documents are ingested before running evaluation")
        print("\nRunning with empty document IDs (will likely fail)...")
        document_ids = []

    # Run evaluation
    evaluator = QAEvaluator(BASE_URL)
    try:
        results = await evaluator.run_evaluation(EVAL_SET_PATH, document_ids)

        # Save results
        with open(OUTPUT_PATH, "w") as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to: {OUTPUT_PATH}")

        # Print one-line summary
        summary = (
            f"EVAL SCORE: {results['average_score']:.2f} | "
            f"PASS RATE: {results['pass_rate']*100:.1f}% | "
            f"PASSED: {results['passed']}/{results['total_questions']}"
        )
        print(f"\n{summary}\n")

        # Save one-line summary
        with open("eval/SCORE.txt", "w") as f:
            f.write(summary)

        return results

    finally:
        await evaluator.close()


if __name__ == "__main__":
    asyncio.run(main())
