"""
Investment Narrative Engine - LLM-Powered Investment Thesis Generation

Transforms quantitative agent scores into human-readable narratives:
- Investment thesis (2-3 paragraphs)
- Key strengths (3-5 bullet points)
- Key risks (3-5 bullet points)
- Professional-grade reports

Supports multiple LLM providers:
- Google Gemini (default, free tier)
- OpenAI GPT-4 (optional)
- Anthropic Claude (optional)
- Rule-based fallback (if LLM fails)
"""

import os
import logging
from typing import Dict, Optional, List
import json

logger = logging.getLogger(__name__)


class InvestmentNarrativeEngine:
    """
    Investment Narrative Engine

    Generates professional investment analysis narratives from agent scores.
    Supports multiple LLM providers with graceful fallback.
    """

    # LLM provider configurations
    PROVIDERS = {
        'gemini': {
            'name': 'Google Gemini',
            'model': 'gemini-1.5-flash',
            'env_var': 'GEMINI_API_KEY',
            'timeout': 30
        },
        'openai': {
            'name': 'OpenAI GPT-4',
            'model': 'gpt-4',
            'env_var': 'OPENAI_API_KEY',
            'timeout': 30
        },
        'anthropic': {
            'name': 'Anthropic Claude',
            'model': 'claude-3-sonnet-20240229',
            'env_var': 'ANTHROPIC_API_KEY',
            'timeout': 30
        }
    }

    def __init__(
        self,
        llm_provider: str = 'gemini',
        enable_llm: bool = True,
        fallback_to_rules: bool = True
    ):
        """
        Initialize Narrative Engine

        Args:
            llm_provider: LLM provider to use ('gemini', 'openai', 'anthropic')
            enable_llm: Enable LLM-powered narratives (default: True)
            fallback_to_rules: Fall back to rule-based if LLM fails (default: True)
        """
        self.llm_provider = llm_provider.lower()
        self.enable_llm = enable_llm
        self.fallback_to_rules = fallback_to_rules

        # Initialize LLM client
        self.llm_client = None
        if self.enable_llm:
            self._initialize_llm_client()

        logger.info(f"Narrative Engine initialized (provider: {llm_provider}, enabled: {enable_llm})")

    def _initialize_llm_client(self):
        """Initialize LLM client based on provider"""
        if self.llm_provider not in self.PROVIDERS:
            logger.warning(f"Unknown provider '{self.llm_provider}', using rule-based fallback")
            self.enable_llm = False
            return

        provider_config = self.PROVIDERS[self.llm_provider]
        api_key = os.getenv(provider_config['env_var'])

        if not api_key:
            logger.warning(
                f"{provider_config['env_var']} not found. "
                f"LLM narratives disabled. Set environment variable to enable."
            )
            self.enable_llm = False
            return

        try:
            if self.llm_provider == 'gemini':
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.llm_client = genai.GenerativeModel(provider_config['model'])
                logger.info(f"✅ Gemini client initialized")

            elif self.llm_provider == 'openai':
                from openai import OpenAI
                self.llm_client = OpenAI(api_key=api_key)
                logger.info(f"✅ OpenAI client initialized")

            elif self.llm_provider == 'anthropic':
                from anthropic import Anthropic
                self.llm_client = Anthropic(api_key=api_key)
                logger.info(f"✅ Anthropic client initialized")

        except ImportError as e:
            logger.warning(f"Failed to import {self.llm_provider} library: {e}")
            self.enable_llm = False
        except Exception as e:
            logger.error(f"Failed to initialize {self.llm_provider} client: {e}")
            self.enable_llm = False

    def generate_narrative(
        self,
        symbol: str,
        agent_scores: Dict,
        composite_score: float,
        recommendation: str,
        stock_info: Optional[Dict] = None
    ) -> Dict:
        """
        Generate investment narrative

        Args:
            symbol: Stock symbol
            agent_scores: Results from all 5 agents
            composite_score: Final weighted score
            recommendation: Investment recommendation
            stock_info: Additional stock information

        Returns:
            {
                'investment_thesis': str,
                'key_strengths': List[str],
                'key_risks': List[str],
                'summary': str,
                'generated_by': str
            }
        """
        logger.info(f"Generating narrative for {symbol} (score: {composite_score:.1f})")

        try:
            if self.enable_llm and self.llm_client:
                # Try LLM-powered generation
                return self._generate_llm_narrative(
                    symbol, agent_scores, composite_score, recommendation, stock_info
                )
            else:
                # Use rule-based generation
                return self._generate_rule_based_narrative(
                    symbol, agent_scores, composite_score, recommendation, stock_info
                )

        except Exception as e:
            logger.error(f"Narrative generation failed: {e}", exc_info=True)

            if self.fallback_to_rules:
                logger.info("Falling back to rule-based narrative")
                return self._generate_rule_based_narrative(
                    symbol, agent_scores, composite_score, recommendation, stock_info
                )
            else:
                return {
                    'investment_thesis': f"Analysis complete for {symbol}. Score: {composite_score:.1f}/100. Recommendation: {recommendation}.",
                    'key_strengths': ['Quantitative analysis available'],
                    'key_risks': ['Limited narrative available'],
                    'summary': f"{recommendation}: {composite_score:.1f}/100",
                    'generated_by': 'error_fallback',
                    'error': str(e)
                }

    def _generate_llm_narrative(
        self,
        symbol: str,
        agent_scores: Dict,
        composite_score: float,
        recommendation: str,
        stock_info: Optional[Dict]
    ) -> Dict:
        """Generate narrative using LLM"""
        logger.info(f"Generating LLM narrative using {self.llm_provider}...")

        # Prepare prompt
        prompt = self._create_llm_prompt(
            symbol, agent_scores, composite_score, recommendation, stock_info
        )

        try:
            # Call LLM based on provider
            if self.llm_provider == 'gemini':
                response = self.llm_client.generate_content(prompt)
                narrative_text = response.text

            elif self.llm_provider == 'openai':
                response = self.llm_client.chat.completions.create(
                    model=self.PROVIDERS['openai']['model'],
                    messages=[
                        {"role": "system", "content": "You are a professional stock analyst generating investment theses."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                narrative_text = response.choices[0].message.content

            elif self.llm_provider == 'anthropic':
                response = self.llm_client.messages.create(
                    model=self.PROVIDERS['anthropic']['model'],
                    max_tokens=1000,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                narrative_text = response.content[0].text

            # Parse LLM response
            parsed = self._parse_llm_response(narrative_text, symbol, composite_score, recommendation)
            parsed['generated_by'] = self.llm_provider
            logger.info(f"✅ LLM narrative generated successfully")

            return parsed

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    def _create_llm_prompt(
        self,
        symbol: str,
        agent_scores: Dict,
        composite_score: float,
        recommendation: str,
        stock_info: Optional[Dict]
    ) -> str:
        """Create detailed prompt for LLM"""
        company_name = stock_info.get('company_name', symbol) if stock_info else symbol
        sector = stock_info.get('sector', 'Unknown') if stock_info else 'Unknown'

        # Extract agent scores and key metrics
        fund_score = agent_scores.get('fundamentals', {}).get('score', 50)
        fund_reasoning = agent_scores.get('fundamentals', {}).get('reasoning', '')
        fund_metrics = agent_scores.get('fundamentals', {}).get('metrics', {})

        mom_score = agent_scores.get('momentum', {}).get('score', 50)
        mom_reasoning = agent_scores.get('momentum', {}).get('reasoning', '')

        qual_score = agent_scores.get('quality', {}).get('score', 50)
        qual_reasoning = agent_scores.get('quality', {}).get('reasoning', '')

        sent_score = agent_scores.get('sentiment', {}).get('score', 50)
        sent_reasoning = agent_scores.get('sentiment', {}).get('reasoning', '')

        flow_score = agent_scores.get('institutional_flow', {}).get('score', 50)
        flow_reasoning = agent_scores.get('institutional_flow', {}).get('reasoning', '')

        prompt = f"""Generate a professional investment analysis for {company_name} ({symbol}), an Indian stock in the {sector} sector.

QUANTITATIVE ANALYSIS RESULTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Score: {composite_score:.1f}/100
Recommendation: {recommendation}

AGENT BREAKDOWN (5 specialized AI agents):

1. FUNDAMENTALS AGENT (36% weight): {fund_score}/100
   {fund_reasoning}
   Key Metrics: ROE: {fund_metrics.get('roe', 'N/A')}, P/E: {fund_metrics.get('pe_ratio', 'N/A')}, Revenue Growth: {fund_metrics.get('revenue_growth', 'N/A')}%

2. MOMENTUM AGENT (27% weight): {mom_score}/100
   {mom_reasoning}

3. QUALITY AGENT (18% weight): {qual_score}/100
   {qual_reasoning}

4. SENTIMENT AGENT (9% weight): {sent_score}/100
   {sent_reasoning}

5. INSTITUTIONAL FLOW AGENT (10% weight): {flow_score}/100
   {flow_reasoning}

TASK:
Generate a professional investment thesis with the following structure:

**INVESTMENT THESIS** (2-3 paragraphs):
[Provide a comprehensive, data-driven investment thesis that synthesizes all agent insights. Write in a professional, analytical tone suitable for institutional investors.]

**KEY STRENGTHS** (3-5 bullet points):
- [Strength 1]
- [Strength 2]
- [Strength 3]
[Add 1-2 more if applicable]

**KEY RISKS** (3-5 bullet points):
- [Risk 1]
- [Risk 2]
- [Risk 3]
[Add 1-2 more if applicable]

**SUMMARY** (1 sentence):
[Concise one-line summary of the investment case]

Guidelines:
- Focus on quantitative insights from the agent analysis
- Be specific about numerical metrics when mentioned
- Maintain objectivity - don't oversell or be overly pessimistic
- Use professional financial terminology
- For Indian stocks, consider market context (NSE/BSE)
- Keep it factual and data-driven"""

        return prompt

    def _parse_llm_response(
        self,
        response_text: str,
        symbol: str,
        composite_score: float,
        recommendation: str
    ) -> Dict:
        """Parse LLM response into structured format"""
        # Simple parsing - extract sections
        thesis = ""
        strengths = []
        risks = []
        summary = ""

        # Split by sections
        sections = response_text.split('**')

        for i, section in enumerate(sections):
            section_lower = section.lower()

            if 'investment thesis' in section_lower:
                # Get content after this header
                if i + 1 < len(sections):
                    thesis = sections[i + 1].strip()
                    # Clean up
                    thesis = thesis.split('**')[0].strip()

            elif 'key strengths' in section_lower:
                if i + 1 < len(sections):
                    strengths_text = sections[i + 1].strip().split('**')[0]
                    strengths = self._extract_bullet_points(strengths_text)

            elif 'key risks' in section_lower:
                if i + 1 < len(sections):
                    risks_text = sections[i + 1].strip().split('**')[0]
                    risks = self._extract_bullet_points(risks_text)

            elif 'summary' in section_lower:
                if i + 1 < len(sections):
                    summary = sections[i + 1].strip().split('**')[0].strip()

        # Fallback to simple extraction if parsing failed
        if not thesis:
            thesis = response_text[:500] + "..." if len(response_text) > 500 else response_text

        if not summary:
            summary = f"{recommendation}: {symbol} scores {composite_score:.1f}/100 based on quantitative analysis."

        return {
            'investment_thesis': thesis,
            'key_strengths': strengths[:5],  # Max 5
            'key_risks': risks[:5],  # Max 5
            'summary': summary
        }

    def _extract_bullet_points(self, text: str) -> List[str]:
        """Extract bullet points from text"""
        points = []
        for line in text.split('\n'):
            line = line.strip()
            # Remove bullet markers
            for marker in ['-', '•', '*', '→']:
                if line.startswith(marker):
                    line = line[1:].strip()
                    break
            if line and len(line) > 10:  # Minimum length
                points.append(line)
        return points

    def _generate_rule_based_narrative(
        self,
        symbol: str,
        agent_scores: Dict,
        composite_score: float,
        recommendation: str,
        stock_info: Optional[Dict]
    ) -> Dict:
        """Generate narrative using rules (fallback)"""
        logger.info("Generating rule-based narrative...")

        company_name = stock_info.get('company_name', symbol) if stock_info else symbol

        # Generate thesis
        thesis = self._create_rule_based_thesis(
            company_name, agent_scores, composite_score, recommendation
        )

        # Extract strengths and risks
        strengths = self._extract_strengths(agent_scores)
        risks = self._extract_risks(agent_scores)

        # Generate summary
        summary = f"{recommendation}: {company_name} ({symbol}) scores {composite_score:.1f}/100 based on comprehensive quantitative analysis."

        return {
            'investment_thesis': thesis,
            'key_strengths': strengths,
            'key_risks': risks,
            'summary': summary,
            'generated_by': 'rule_based'
        }

    def _create_rule_based_thesis(
        self,
        company_name: str,
        agent_scores: Dict,
        composite_score: float,
        recommendation: str
    ) -> str:
        """Create rule-based investment thesis"""
        fund_score = agent_scores.get('fundamentals', {}).get('score', 50)
        mom_score = agent_scores.get('momentum', {}).get('score', 50)
        qual_score = agent_scores.get('quality', {}).get('score', 50)

        # Determine overall assessment
        if composite_score >= 70:
            assessment = "presents a compelling investment opportunity"
        elif composite_score >= 60:
            assessment = "shows positive investment characteristics"
        elif composite_score >= 50:
            assessment = "presents a balanced risk-reward profile"
        else:
            assessment = "faces notable investment challenges"

        # Build thesis
        thesis = f"{company_name} {assessment} with a composite score of {composite_score:.1f}/100. "

        # Add fundamentals commentary
        if fund_score >= 70:
            thesis += "The company demonstrates strong fundamental metrics with solid profitability and attractive valuation. "
        elif fund_score >= 50:
            thesis += "Fundamental analysis reveals mixed signals with both strengths and areas of concern. "
        else:
            thesis += "Fundamental metrics indicate challenges in profitability or valuation. "

        # Add momentum commentary
        if mom_score >= 70:
            thesis += "Technical momentum indicators are positive, suggesting favorable price trends. "
        elif mom_score >= 50:
            thesis += "Technical indicators show neutral momentum with balanced risk. "
        else:
            thesis += "Technical analysis reveals weak momentum and adverse price trends. "

        # Add quality commentary
        if qual_score >= 70:
            thesis += "The stock exhibits high quality characteristics with stable performance and manageable risk."
        elif qual_score >= 50:
            thesis += "Quality metrics are adequate with moderate volatility and acceptable stability."
        else:
            thesis += "Quality assessment indicates elevated volatility and inconsistent performance."

        return thesis

    def _extract_strengths(self, agent_scores: Dict) -> List[str]:
        """Extract key strengths from agent scores"""
        strengths = []

        # Check each agent for strengths
        for agent_name, result in agent_scores.items():
            score = result.get('score', 50)
            if score >= 65:  # Strong performance
                reasoning = result.get('reasoning', '')
                if reasoning:
                    strengths.append(f"{agent_name.replace('_', ' ').title()}: {reasoning}")

        # If no strengths, add generic ones
        if not strengths:
            strengths = ["Comprehensive quantitative analysis completed"]

        return strengths[:5]

    def _extract_risks(self, agent_scores: Dict) -> List[str]:
        """Extract key risks from agent scores"""
        risks = []

        # Check each agent for risks
        for agent_name, result in agent_scores.items():
            score = result.get('score', 50)
            if score <= 40:  # Weak performance
                reasoning = result.get('reasoning', '')
                if reasoning:
                    risks.append(f"{agent_name.replace('_', ' ').title()}: {reasoning}")

        # If no specific risks, add generic ones
        if not risks:
            risks = ["Market volatility and general investment risks apply"]

        return risks[:5]


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize narrative engine
    engine = InvestmentNarrativeEngine(
        llm_provider='gemini',
        enable_llm=False,  # Set to True if you have API key
        fallback_to_rules=True
    )

    # Sample agent scores
    sample_agent_scores = {
        'fundamentals': {
            'score': 75,
            'confidence': 0.85,
            'reasoning': 'Strong ROE: 16.2% | Undervalued P/E: 14.3 | High growth: 22.1%',
            'metrics': {'roe': 16.2, 'pe_ratio': 14.3, 'revenue_growth': 22.1}
        },
        'momentum': {
            'score': 68,
            'confidence': 0.90,
            'reasoning': 'Strong RSI: 58.5 | Uptrend | Strong 3M return: +12.3%'
        },
        'quality': {
            'score': 72,
            'confidence': 0.80,
            'reasoning': 'Low volatility: 18.5% | Strong 1Y return: +15.2%'
        },
        'sentiment': {
            'score': 65,
            'confidence': 0.70,
            'reasoning': 'Buy consensus (2.1) | Medium upside: +12.5%'
        },
        'institutional_flow': {
            'score': 70,
            'confidence': 0.85,
            'reasoning': 'Accumulation (OBV) | Strong buying (MFI: 65.5)'
        }
    }

    # Generate narrative
    narrative = engine.generate_narrative(
        symbol='TCS',
        agent_scores=sample_agent_scores,
        composite_score=71.5,
        recommendation='STRONG BUY',
        stock_info={'company_name': 'Tata Consultancy Services', 'sector': 'Technology'}
    )

    # Display results
    print("\n" + "="*60)
    print("Investment Narrative")
    print("="*60)
    print(f"\nGenerated by: {narrative['generated_by']}")
    print(f"\n{narrative['investment_thesis']}")
    print(f"\nKey Strengths:")
    for i, strength in enumerate(narrative['key_strengths'], 1):
        print(f"  {i}. {strength}")
    print(f"\nKey Risks:")
    for i, risk in enumerate(narrative['key_risks'], 1):
        print(f"  {i}. {risk}")
    print(f"\nSummary: {narrative['summary']}")
