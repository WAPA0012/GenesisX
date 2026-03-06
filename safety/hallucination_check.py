"""
Hallucination Checker: Detect Model Hallucinations

Implements:
- Factual consistency checking
- Source attribution verification
- Confidence-based filtering

References:
- 代码大纲架构 safety/hallucination_check.py
- Hallucination detection research
"""

from typing import Dict, Any, List
import re


class HallucinationScore:
    """Hallucination detection result"""

    def __init__(
        self,
        is_hallucination: bool,
        confidence: float,
        evidence: str,
        category: str,
    ):
        self.is_hallucination = is_hallucination
        self.confidence = confidence  # [0, 1]
        self.evidence = evidence
        self.category = category


class HallucinationChecker:
    """
    Detect and mitigate model hallucinations.

    Methods:
    - Factual consistency checking
    - Source citation verification
    - Uncertainty quantification
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Hallucination thresholds
        self.confidence_threshold = config.get("confidence_threshold", 0.7)

        # Patterns indicating uncertainty
        self.uncertainty_patterns = [
            r"I think",
            r"maybe",
            r"possibly",
            r"might be",
            r"could be",
            r"not sure",
            r"uncertain",
        ]

        # Patterns indicating hallucination
        self.hallucination_indicators = [
            r"as far as I know",
            r"if I recall correctly",
            r"I believe",
            r"I'm pretty sure",
        ]

    def check_response(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> HallucinationScore:
        """
        Check response for hallucinations.

        Args:
            response: Model response text
            context: Context dict with sources, facts, etc.

        Returns:
            HallucinationScore
        """
        # Check for uncertainty language
        uncertainty_score = self._check_uncertainty_language(response)

        # Check for unsupported claims
        unsupported_score = self._check_unsupported_claims(response, context)

        # Check for source attribution
        attribution_score = self._check_source_attribution(response, context)

        # Combine scores
        hallucination_score = max(uncertainty_score, unsupported_score, attribution_score)

        is_hallucination = hallucination_score > self.confidence_threshold

        category = self._categorize_hallucination(
            uncertainty_score,
            unsupported_score,
            attribution_score
        )

        return HallucinationScore(
            is_hallucination=is_hallucination,
            confidence=hallucination_score,
            evidence=f"Uncertainty: {uncertainty_score:.2f}, Unsupported: {unsupported_score:.2f}, Attribution: {attribution_score:.2f}",
            category=category,
        )

    def _check_uncertainty_language(self, text: str) -> float:
        """
        Check for uncertainty language patterns.

        Args:
            text: Response text

        Returns:
            Uncertainty score [0, 1]
        """
        text_lower = text.lower()

        matches = 0
        for pattern in self.uncertainty_patterns:
            if re.search(pattern, text_lower):
                matches += 1

        # Normalize by text length
        words = len(text.split())
        # 修复: 当 words 为 0 时，使用 1 作为分母
        uncertainty_score = min(1.0, matches / max(1, words) * 50)

        return uncertainty_score

    def _check_unsupported_claims(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> float:
        """
        Check for claims not supported by context.

        Args:
            text: Response text
            context: Context dict

        Returns:
            Unsupported claim score [0, 1]
        """
        # Extract factual claims (simplified)
        claims = self._extract_claims(text)

        # If no claims were extracted, no risk of unsupported claims
        if not claims:
            return 0.0

        # Check if claims are supported by context
        sources = context.get("sources", [])

        if not sources:
            # No sources provided, assume some risk
            return 0.3

        unsupported_count = 0
        for claim in claims:
            if not self._is_claim_supported(claim, sources):
                unsupported_count += 1

        unsupported_ratio = unsupported_count / len(claims)

        return unsupported_ratio

    def _check_source_attribution(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> float:
        """
        Check if sources are properly attributed.

        Args:
            text: Response text
            context: Context dict

        Returns:
            Attribution score [0, 1] (higher = worse)
        """
        sources = context.get("sources", [])

        if not sources:
            return 0.0

        # Check for citation patterns
        citation_patterns = [
            r"\[(\d+)\]",           # [1]
            r"according to",
            r"source:",
            r"from (.+?),",
        ]

        has_citations = False
        for pattern in citation_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                has_citations = True
                break

        # If sources provided but no citations, potential hallucination
        if not has_citations:
            return 0.5

        return 0.0

    def _extract_claims(self, text: str) -> List[str]:
        """
        Extract factual claims from text.

        Simple implementation: split by sentences.

        Args:
            text: Input text

        Returns:
            List of claim strings
        """
        # Split by sentence
        sentences = re.split(r'[.!?]+', text)

        # Filter out short sentences and questions
        claims = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and not sentence.endswith('?'):
                claims.append(sentence)

        return claims

    def _is_claim_supported(self, claim: str, sources: List[str]) -> bool:
        """
        Check if claim is supported by sources.

        Simple keyword overlap check.

        Args:
            claim: Claim text
            sources: List of source texts

        Returns:
            True if supported
        """
        claim_words = set(claim.lower().split())

        for source in sources:
            source_words = set(source.lower().split())
            overlap = claim_words & source_words

            # If >50% of claim words in source, consider supported
            if len(overlap) > len(claim_words) * 0.5:
                return True

        return False

    def _categorize_hallucination(
        self,
        uncertainty: float,
        unsupported: float,
        attribution: float
    ) -> str:
        """
        Categorize hallucination type.

        Args:
            uncertainty: Uncertainty score
            unsupported: Unsupported claims score
            attribution: Attribution score

        Returns:
            Category string
        """
        if uncertainty > 0.7:
            return "high_uncertainty"
        elif unsupported > 0.7:
            return "unsupported_claims"
        elif attribution > 0.5:
            return "missing_attribution"
        elif max(uncertainty, unsupported, attribution) > 0.5:
            return "moderate_risk"
        else:
            return "low_risk"

    def should_filter(self, score: HallucinationScore) -> bool:
        """
        Determine if response should be filtered.

        Args:
            score: Hallucination score

        Returns:
            True if should be filtered
        """
        return score.is_hallucination and score.confidence > 0.8
