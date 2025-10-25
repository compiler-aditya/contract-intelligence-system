"""Service for auditing contracts and detecting risky clauses"""
import json
import re
from typing import List, Dict
from app.core.config import settings
from app.models.document import SeverityLevel

# Import LLM clients based on provider
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class AuditService:
    """Audit contracts for risky clauses"""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER

        if self.provider == "gemini" and settings.GEMINI_API_KEY:
            if genai:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.client = genai.GenerativeModel(settings.GEMINI_MODEL)
                self.use_llm = True
            else:
                self.client = None
                self.use_llm = False
        elif self.provider == "openai" and settings.OPENAI_API_KEY:
            if OpenAI:
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
                self.use_llm = True
            else:
                self.client = None
                self.use_llm = False
        else:
            self.client = None
            self.use_llm = False

    def audit_with_llm(self, text: str) -> List[Dict]:
        """
        Audit contract using LLM

        Args:
            text: Contract text to audit

        Returns:
            List of findings
        """
        if not self.client:
            raise ValueError(f"{self.provider.upper()} API key not configured")

        prompt = """You are a contract risk analyzer. Analyze the provided contract text and identify risky clauses.

Focus on detecting these risk types:
1. auto_renewal_short_notice: Auto-renewal with less than 30 days notice
2. unlimited_liability: No liability cap or unlimited liability exposure
3. broad_indemnity: Overly broad indemnification obligations
4. unilateral_termination: One-sided termination rights
5. unfavorable_jurisdiction: Jurisdiction clause favoring the other party
6. automatic_price_increase: Automatic price increases without caps
7. data_retention_risk: Unclear or excessive data retention
8. ip_transfer: Intellectual property transfer or assignment clauses
9. non_compete_overreach: Overly restrictive non-compete clauses
10. force_majeure_imbalance: One-sided force majeure protections

For each finding, return JSON with:
- finding_type: Type of risk from the list above
- description: Clear description of the risk
- severity: "low", "medium", "high", or "critical"
- evidence_text: Exact text from contract showing the risk (max 200 chars)
- recommendation: Suggestion to mitigate the risk

Return JSON with a "findings" array. Return empty array if no risks found.

Contract text:
"""

        try:
            if self.provider == "gemini":
                # Gemini API call
                full_prompt = f"{prompt}\n\n{text[:10000]}"
                response = self.client.generate_content(full_prompt)
                result_text = response.text

                # Extract JSON from response (Gemini might wrap it in markdown)
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                result = json.loads(result_text)
            else:
                # OpenAI API call
                response = self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a contract risk analyzer. Return only valid JSON."},
                        {"role": "user", "content": f"{prompt}\n\n{text[:10000]}"}
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
                result = json.loads(response.choices[0].message.content)

            findings = result.get("findings", [])

            # Normalize findings
            return [self._normalize_finding(f) for f in findings]

        except Exception as e:
            raise ValueError(f"LLM audit failed: {str(e)}")

    def audit_with_rules(self, text: str) -> List[Dict]:
        """
        Audit contract using rule-based patterns

        Args:
            text: Contract text to audit

        Returns:
            List of findings
        """
        findings = []

        # Check for auto-renewal with short notice
        auto_renewal_findings = self._check_auto_renewal(text)
        findings.extend(auto_renewal_findings)

        # Check for unlimited liability
        liability_findings = self._check_unlimited_liability(text)
        findings.extend(liability_findings)

        # Check for broad indemnity
        indemnity_findings = self._check_broad_indemnity(text)
        findings.extend(indemnity_findings)

        # Check for unilateral termination
        termination_findings = self._check_unilateral_termination(text)
        findings.extend(termination_findings)

        # Check for automatic price increases
        price_findings = self._check_price_increases(text)
        findings.extend(price_findings)

        return findings

    def _check_auto_renewal(self, text: str) -> List[Dict]:
        """Check for auto-renewal with short notice"""
        findings = []

        # Pattern: auto-renewal with notice period
        patterns = [
            r"(auto(?:matic)?(?:ally)?\s+renew.{0,100}?(\d+)\s+days?)",
            r"(renew(?:s|al)?\s+automatic.{0,100}?(\d+)\s+days?)"
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                evidence = match.group(1)
                try:
                    days = int(match.group(2))
                    if days < 30:
                        findings.append({
                            "finding_type": "auto_renewal_short_notice",
                            "description": f"Auto-renewal clause with only {days} days notice (less than 30 days recommended)",
                            "severity": "high" if days < 15 else "medium",
                            "evidence_text": evidence[:200],
                            "recommendation": "Negotiate for at least 30-60 days notice period for auto-renewal"
                        })
                except (ValueError, IndexError):
                    pass

        return findings

    def _check_unlimited_liability(self, text: str) -> List[Dict]:
        """Check for unlimited liability"""
        findings = []

        # Check if there's a liability cap
        cap_pattern = r"liability.{0,200}?(?:limit|cap).{0,100}?(?:\$|USD|EUR)?\s*[\d,]+"
        has_cap = bool(re.search(cap_pattern, text, re.IGNORECASE))

        # Check for unlimited liability language
        unlimited_patterns = [
            r"(unlimited\s+liability)",
            r"(no\s+limit\s+on\s+liability)",
            r"(liability.{0,50}?without\s+limit)"
        ]

        for pattern in unlimited_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                findings.append({
                    "finding_type": "unlimited_liability",
                    "description": "Contract contains unlimited liability exposure",
                    "severity": "critical",
                    "evidence_text": match.group(1)[:200],
                    "recommendation": "Negotiate a liability cap (e.g., fees paid in last 12 months)"
                })
                break

        # If no cap mentioned at all, flag it
        if not has_cap and not findings:
            if re.search(r"liability", text, re.IGNORECASE):
                findings.append({
                    "finding_type": "unlimited_liability",
                    "description": "No liability cap found in contract",
                    "severity": "high",
                    "evidence_text": "No liability limitation clause identified",
                    "recommendation": "Add a liability cap to limit exposure"
                })

        return findings

    def _check_broad_indemnity(self, text: str) -> List[Dict]:
        """Check for overly broad indemnification"""
        findings = []

        broad_patterns = [
            r"(indemnif.{0,100}?(?:any|all)\s+(?:claims|losses|damages|liabilities))",
            r"(indemnif.{0,100}?(?:defend|hold harmless).{0,100}?any)"
        ]

        for pattern in broad_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                findings.append({
                    "finding_type": "broad_indemnity",
                    "description": "Indemnification clause is overly broad and may expose to excessive liability",
                    "severity": "medium",
                    "evidence_text": match.group(1)[:200],
                    "recommendation": "Limit indemnification to claims arising from your acts or omissions, exclude third-party claims"
                })
                break

        return findings

    def _check_unilateral_termination(self, text: str) -> List[Dict]:
        """Check for one-sided termination rights"""
        findings = []

        # This is complex to detect with rules, so we keep it simple
        patterns = [
            r"(\[Other Party\].{0,100}?may terminate.{0,100}?at any time)",
            r"(terminate\s+this\s+agreement\s+at\s+any\s+time\s+(?:with|without)\s+cause)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                findings.append({
                    "finding_type": "unilateral_termination",
                    "description": "Contract allows termination without cause, creating uncertainty",
                    "severity": "medium",
                    "evidence_text": match.group(1)[:200],
                    "recommendation": "Negotiate for mutual termination rights or require cause for termination"
                })
                break

        return findings

    def _check_price_increases(self, text: str) -> List[Dict]:
        """Check for automatic price increases"""
        findings = []

        patterns = [
            r"(price.{0,100}?(?:increase|escalat).{0,100}?automatic)",
            r"(automatic.{0,100}?price.{0,100}?increase)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Check if there's a cap
                has_cap = bool(re.search(r"(?:not\s+(?:to\s+)?exceed|maximum|cap).{0,50}?\d+%", text, re.IGNORECASE))

                severity = "low" if has_cap else "medium"
                findings.append({
                    "finding_type": "automatic_price_increase",
                    "description": "Contract allows automatic price increases" + (" without clear cap" if not has_cap else ""),
                    "severity": severity,
                    "evidence_text": match.group(1)[:200],
                    "recommendation": "Cap automatic increases (e.g., CPI or 5% annually, whichever is lower)"
                })
                break

        return findings

    def _normalize_finding(self, finding: Dict) -> Dict:
        """Normalize finding to standard format"""
        return {
            "finding_type": finding.get("finding_type", "unknown"),
            "description": finding.get("description", ""),
            "severity": finding.get("severity", "medium"),
            "evidence_text": finding.get("evidence_text", "")[:500],
            "recommendation": finding.get("recommendation", "")
        }

    def audit(self, text: str, use_llm: bool = True) -> List[Dict]:
        """
        Audit contract for risky clauses

        Args:
            text: Contract text
            use_llm: Whether to use LLM (True) or rule-based (False)

        Returns:
            List of findings
        """
        if use_llm and self.use_llm:
            try:
                return self.audit_with_llm(text)
            except Exception as e:
                print(f"LLM audit failed, falling back to rules: {str(e)}")
                return self.audit_with_rules(text)
        else:
            return self.audit_with_rules(text)

    def calculate_risk_score(self, findings: List[Dict]) -> float:
        """
        Calculate overall risk score from findings

        Args:
            findings: List of audit findings

        Returns:
            Risk score from 0-100
        """
        if not findings:
            return 0.0

        severity_weights = {
            "low": 10,
            "medium": 25,
            "high": 50,
            "critical": 100
        }

        total_score = sum(severity_weights.get(f.get("severity", "low"), 10) for f in findings)

        # Cap at 100
        return min(total_score, 100.0)
