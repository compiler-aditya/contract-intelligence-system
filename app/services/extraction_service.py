"""Service for extracting structured data from contracts"""
import json
import re
from typing import Dict, Optional, List
from openai import OpenAI
from app.core.config import settings


class ExtractionService:
    """Extract structured fields from contract text"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.use_llm = bool(settings.OPENAI_API_KEY)

    def extract_with_llm(self, text: str) -> Dict:
        """
        Extract contract data using LLM (GPT-4)

        Args:
            text: Contract text to extract from

        Returns:
            Dictionary with extracted fields
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured")

        # Load extraction prompt
        prompt = """You are a legal document analysis AI. Extract structured information from the provided contract text.

Extract the following fields:
1. parties: List of all parties involved in the contract (organizations/individuals)
2. effective_date: When the contract becomes effective
3. term: Duration/term of the contract
4. governing_law: Which jurisdiction/law governs this contract
5. payment_terms: Payment conditions, amounts, schedules
6. termination: Termination conditions and notice periods
7. auto_renewal: Auto-renewal clauses and notice requirements
8. confidentiality: Confidentiality and NDA provisions
9. indemnity: Indemnification clauses
10. liability_cap_amount: Liability limitation amount (numeric value only)
11. liability_cap_currency: Currency for liability cap (e.g., USD, EUR)
12. signatories: List of signatories as array of objects with 'name' and 'title' keys

Return ONLY valid JSON. Use null for missing fields. Do not include any explanation.

Contract text:
"""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a legal contract analysis expert. Extract data and return only valid JSON."},
                    {"role": "user", "content": f"{prompt}\n\n{text[:8000]}"}  # Limit text to avoid token limits
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Normalize the output
            return self._normalize_extraction(result)

        except Exception as e:
            raise ValueError(f"LLM extraction failed: {str(e)}")

    def extract_with_rules(self, text: str) -> Dict:
        """
        Extract contract data using rule-based patterns (fallback)

        Args:
            text: Contract text to extract from

        Returns:
            Dictionary with extracted fields
        """
        result = {
            "parties": self._extract_parties_rule(text),
            "effective_date": self._extract_date_rule(text, "effective"),
            "term": self._extract_term_rule(text),
            "governing_law": self._extract_governing_law_rule(text),
            "payment_terms": self._extract_payment_terms_rule(text),
            "termination": self._extract_termination_rule(text),
            "auto_renewal": self._extract_auto_renewal_rule(text),
            "confidentiality": self._extract_confidentiality_rule(text),
            "indemnity": self._extract_indemnity_rule(text),
            "liability_cap_amount": None,
            "liability_cap_currency": None,
            "signatories": []
        }

        # Extract liability cap
        liability = self._extract_liability_cap_rule(text)
        if liability:
            result["liability_cap_amount"] = liability.get("amount")
            result["liability_cap_currency"] = liability.get("currency")

        return result

    def _extract_parties_rule(self, text: str) -> List[str]:
        """Extract parties using regex patterns"""
        parties = []

        # Pattern: "between X and Y"
        between_pattern = r"between\s+([A-Z][^,\n]+?)\s+(?:and|&)\s+([A-Z][^,\n]+?)(?:\s*\(|,|\.)"
        matches = re.findall(between_pattern, text, re.IGNORECASE)
        for match in matches:
            parties.extend([m.strip() for m in match])

        # Pattern: "Party: X" or "Parties: X, Y"
        party_pattern = r"(?:Party|Parties):\s*([^\n]+)"
        matches = re.findall(party_pattern, text, re.IGNORECASE)
        for match in matches:
            parties.extend([p.strip() for p in match.split(',')])

        return list(set(parties[:10]))  # Limit to 10 unique parties

    def _extract_date_rule(self, text: str, date_type: str = "effective") -> Optional[str]:
        """Extract dates using patterns"""
        patterns = [
            rf"{date_type}\s+date[:\s]+([A-Za-z]+\s+\d{{1,2}},?\s+\d{{4}})",
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"([A-Za-z]+\s+\d{1,2},?\s+\d{4})"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_term_rule(self, text: str) -> Optional[str]:
        """Extract contract term"""
        patterns = [
            r"term[:\s]+(\d+\s+(?:year|month|day)s?)",
            r"period of\s+(\d+\s+(?:year|month|day)s?)",
            r"duration[:\s]+(\d+\s+(?:year|month|day)s?)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_governing_law_rule(self, text: str) -> Optional[str]:
        """Extract governing law"""
        pattern = r"governing\s+law[:\s]+([^\n\.]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_payment_terms_rule(self, text: str) -> Optional[str]:
        """Extract payment terms"""
        pattern = r"payment\s+terms?[:\s]+([^\n]+(?:\n[^\n]+){0,2})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_termination_rule(self, text: str) -> Optional[str]:
        """Extract termination clause"""
        pattern = r"termination[:\s]+([^\n]+(?:\n[^\n]+){0,3})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_auto_renewal_rule(self, text: str) -> Optional[str]:
        """Extract auto-renewal clause"""
        pattern = r"(?:auto-?renew|automatic renewal)[:\s]+([^\n]+(?:\n[^\n]+){0,2})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_confidentiality_rule(self, text: str) -> Optional[str]:
        """Extract confidentiality clause"""
        pattern = r"confidentialit(?:y|ies)[:\s]+([^\n]+(?:\n[^\n]+){0,3})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_indemnity_rule(self, text: str) -> Optional[str]:
        """Extract indemnity clause"""
        pattern = r"indemni(?:ty|fication)[:\s]+([^\n]+(?:\n[^\n]+){0,3})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_liability_cap_rule(self, text: str) -> Optional[Dict]:
        """Extract liability cap"""
        pattern = r"liability.*?(?:limit|cap).*?(\$|USD|EUR|GBP)?\s*([\d,]+(?:\.\d{2})?)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            currency = match.group(1) or "USD"
            amount_str = match.group(2).replace(',', '')
            try:
                amount = float(amount_str)
                return {"amount": amount, "currency": currency}
            except ValueError:
                pass
        return None

    def _normalize_extraction(self, data: Dict) -> Dict:
        """Normalize extracted data to standard format"""
        normalized = {
            "parties": data.get("parties") or [],
            "effective_date": data.get("effective_date"),
            "term": data.get("term"),
            "governing_law": data.get("governing_law"),
            "payment_terms": data.get("payment_terms"),
            "termination": data.get("termination"),
            "auto_renewal": data.get("auto_renewal"),
            "confidentiality": data.get("confidentiality"),
            "indemnity": data.get("indemnity"),
            "liability_cap_amount": data.get("liability_cap_amount"),
            "liability_cap_currency": data.get("liability_cap_currency"),
            "signatories": data.get("signatories") or []
        }

        # Ensure parties is a list
        if isinstance(normalized["parties"], str):
            normalized["parties"] = [normalized["parties"]]

        # Ensure signatories is a list of dicts
        if normalized["signatories"] and isinstance(normalized["signatories"][0], str):
            normalized["signatories"] = [{"name": s, "title": "Unknown"} for s in normalized["signatories"]]

        return normalized

    def extract(self, text: str, use_llm: bool = True) -> Dict:
        """
        Extract structured data from contract text

        Args:
            text: Contract text
            use_llm: Whether to use LLM (True) or rule-based extraction (False)

        Returns:
            Dictionary with extracted fields
        """
        if use_llm and self.use_llm:
            try:
                return self.extract_with_llm(text)
            except Exception as e:
                print(f"LLM extraction failed, falling back to rules: {str(e)}")
                return self.extract_with_rules(text)
        else:
            return self.extract_with_rules(text)
