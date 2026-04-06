"""
Investment Narrative Engine - Investment Thesis Generation

Transforms quantitative agent scores into human-readable narratives:
- Investment thesis (2-3 paragraphs)
- Key strengths (3-5 bullet points)
- Key risks (3-5 bullet points)
- Professional-grade reports

Supports multiple LLM providers:
- Groq (FREE — Llama 3, no credit card, sign up at console.groq.com)
- Google Gemini (free tier — 15 RPM)
- OpenAI GPT-4 (optional, paid)
- Anthropic Claude (optional, paid)
- Rule-based fallback (no API key needed — uses actual metrics)
"""

import os
import logging
from typing import Dict, Optional, List
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from utils.circuit_breaker import CircuitBreaker, CircuitBreakerError

logger = logging.getLogger(__name__)


class InvestmentNarrativeEngine:
    """
    Investment Narrative Engine

    Generates professional investment analysis narratives from agent scores.
    Supports multiple LLM providers with graceful fallback.
    """

    # LLM provider configurations
    PROVIDERS = {
        'groq': {
            'name': 'Groq (Llama 3) — FREE',
            'model': 'llama3-8b-8192',
            'env_var': 'GROQ_API_KEY',
            'timeout': 20
        },
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
        self._llm_circuit_breaker = CircuitBreaker(
            failure_threshold=int(os.getenv('LLM_CIRCUIT_BREAKER_THRESHOLD', '5')),
            recovery_timeout=int(os.getenv('LLM_CIRCUIT_BREAKER_TIMEOUT', '120')),
            name='llm_narrative'
        )
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
            if self.llm_provider == 'groq':
                from groq import Groq
                self.llm_client = Groq(api_key=api_key)
                logger.info("✅ Groq client initialized (free tier)")

            elif self.llm_provider == 'gemini':
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

        timeout_secs = self.PROVIDERS.get(self.llm_provider, {}).get('timeout', 30)

        def _call_llm():
            """Blocking LLM call — executed in a thread to enforce timeout."""
            if self.llm_provider == 'groq':
                response = self.llm_client.chat.completions.create(
                    model=self.PROVIDERS['groq']['model'],
                    messages=[
                        {"role": "system", "content": "You are a professional stock analyst for Indian equity markets. Generate concise, data-driven investment theses."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                return response.choices[0].message.content

            elif self.llm_provider == 'gemini':
                return self.llm_client.generate_content(prompt).text

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
                return response.choices[0].message.content

            elif self.llm_provider == 'anthropic':
                response = self.llm_client.messages.create(
                    model=self.PROVIDERS['anthropic']['model'],
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

            else:
                raise ValueError(f"Unknown LLM provider: {self.llm_provider}")

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._llm_circuit_breaker.call, _call_llm)
                narrative_text = future.result(timeout=timeout_secs)

            # Parse LLM response
            parsed = self._parse_llm_response(narrative_text, symbol, composite_score, recommendation)
            parsed['generated_by'] = self.llm_provider
            logger.info("✅ LLM narrative generated successfully")
            return parsed

        except FuturesTimeoutError:
            logger.warning(f"LLM call timed out after {timeout_secs}s for {symbol}")
            raise TimeoutError(f"LLM provider {self.llm_provider} timed out after {timeout_secs}s")
        except CircuitBreakerError as e:
            logger.warning(f"LLM circuit breaker blocked call for {symbol}: {e}")
            raise
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
        """Generate metric-driven narrative using rules (no API key needed)"""
        logger.info("Generating rule-based narrative...")

        company_name = stock_info.get('company_name', symbol) if stock_info else symbol
        sector = stock_info.get('sector', '') if stock_info else ''
        current_price = stock_info.get('current_price') if stock_info else None
        market_cap = stock_info.get('market_cap') if stock_info else None

        fund_data = agent_scores.get('fundamentals', {})
        mom_data = agent_scores.get('momentum', {})
        qual_data = agent_scores.get('quality', {})
        sent_data = agent_scores.get('sentiment', {})
        flow_data = agent_scores.get('institutional_flow', {})

        strengths = self._extract_strengths_from_metrics(
            fund_data, mom_data, qual_data, sent_data, flow_data
        )
        risks = self._extract_risks_from_metrics(
            fund_data, mom_data, qual_data, sent_data, flow_data
        )
        thesis = self._build_thesis(
            company_name, symbol, sector, composite_score, recommendation,
            fund_data, mom_data, qual_data, sent_data, flow_data,
            current_price, market_cap
        )
        summary = self._build_summary(
            company_name, symbol, composite_score, recommendation,
            fund_data, mom_data, qual_data
        )

        return {
            'investment_thesis': thesis,
            'key_strengths': strengths,
            'key_risks': risks,
            'summary': summary,
            'generated_by': 'rule_based'
        }

    def _build_thesis(
        self,
        company_name: str,
        symbol: str,
        sector: str,
        composite_score: float,
        recommendation: str,
        fund_data: Dict,
        mom_data: Dict,
        qual_data: Dict,
        sent_data: Dict,
        flow_data: Dict,
        current_price,
        market_cap
    ) -> str:
        """Build a detailed, metric-specific investment thesis."""
        fund_score = fund_data.get('score', 50)
        mom_score = mom_data.get('score', 50)
        qual_score = qual_data.get('score', 50)
        sent_score = sent_data.get('score', 50)
        flow_score = flow_data.get('score', 50)

        fund_metrics = fund_data.get('metrics', {})
        mom_metrics = mom_data.get('metrics', {})
        qual_metrics = qual_data.get('metrics', {})
        sent_metrics = sent_data.get('metrics', {})
        flow_metrics = flow_data.get('metrics', {})

        sector_str = f" in the {sector} sector" if sector else ""
        price_str = f" trading at ₹{current_price:,.2f}" if current_price else ""

        # --- Paragraph 1: Overall verdict with key numbers ---
        if composite_score >= 68:
            verdict = "presents a compelling investment opportunity"
        elif composite_score >= 58:
            verdict = "shows a favourable risk-reward profile"
        elif composite_score >= 48:
            verdict = "warrants a cautious, selective approach"
        else:
            verdict = "carries meaningful downside risks at current levels"

        para1 = (
            f"{company_name} ({symbol}){sector_str}{price_str} "
            f"{verdict}, scoring {composite_score:.1f}/100 on our five-agent quantitative framework "
            f"with a {recommendation} recommendation. "
        )

        # Add agent summary line
        agent_summary = []
        if fund_score >= 60:
            agent_summary.append(f"fundamentals ({fund_score:.0f}/100)")
        if mom_score >= 60:
            agent_summary.append(f"momentum ({mom_score:.0f}/100)")
        if qual_score >= 60:
            agent_summary.append(f"quality ({qual_score:.0f}/100)")
        if sent_score >= 60:
            agent_summary.append(f"sentiment ({sent_score:.0f}/100)")
        if flow_score >= 60:
            agent_summary.append(f"institutional flow ({flow_score:.0f}/100)")

        weak_agents = []
        if fund_score < 45:
            weak_agents.append(f"fundamentals ({fund_score:.0f}/100)")
        if mom_score < 45:
            weak_agents.append(f"momentum ({mom_score:.0f}/100)")
        if qual_score < 45:
            weak_agents.append(f"quality ({qual_score:.0f}/100)")

        if agent_summary:
            para1 += f"The stock scores well on {', '.join(agent_summary)}. "
        if weak_agents:
            para1 += f"Weakness is evident in {', '.join(weak_agents)}. "

        # --- Paragraph 2: Fundamentals deep-dive ---
        para2_parts = []
        roe = fund_metrics.get('roe')
        pe = fund_metrics.get('pe_ratio')
        pb = fund_metrics.get('pb_ratio')
        de = fund_metrics.get('debt_to_equity')
        rev_growth = fund_metrics.get('revenue_growth')
        promoter = fund_metrics.get('promoter_holding')

        if roe is not None:
            if roe >= 18:
                para2_parts.append(f"ROE of {roe:.1f}% signals high capital efficiency")
            elif roe >= 12:
                para2_parts.append(f"ROE of {roe:.1f}% is adequate")
            else:
                para2_parts.append(f"ROE of {roe:.1f}% is below par, raising profitability concerns")

        if pe is not None and pe > 0:
            if pe < 15:
                para2_parts.append(f"P/E of {pe:.1f}x appears undervalued")
            elif pe < 25:
                para2_parts.append(f"P/E of {pe:.1f}x is fairly valued")
            else:
                para2_parts.append(f"P/E of {pe:.1f}x prices in significant growth expectations")

        if rev_growth is not None:
            if rev_growth >= 20:
                para2_parts.append(f"strong revenue growth of {rev_growth:.1f}%")
            elif rev_growth >= 10:
                para2_parts.append(f"steady revenue growth of {rev_growth:.1f}%")
            elif rev_growth < 0:
                para2_parts.append(f"revenue contraction of {rev_growth:.1f}% is a concern")

        if de is not None:
            if de < 0.3:
                para2_parts.append(f"near-zero leverage (D/E: {de:.2f})")
            elif de < 1.0:
                para2_parts.append(f"manageable debt (D/E: {de:.2f})")
            else:
                para2_parts.append(f"elevated leverage (D/E: {de:.2f}) warrants monitoring")

        if promoter is not None:
            if promoter >= 60:
                para2_parts.append(f"high promoter confidence at {promoter:.1f}% holding")
            elif promoter < 30:
                para2_parts.append(f"low promoter holding of {promoter:.1f}%")

        para2 = ""
        if para2_parts:
            para2 = "On the fundamentals front, " + "; ".join(para2_parts) + ". "

        # --- Paragraph 3: Technical & flow ---
        para3_parts = []
        rsi = mom_metrics.get('rsi')
        trend = mom_metrics.get('trend', '')
        ret_3m = mom_metrics.get('3m_return')
        ret_1y = mom_metrics.get('1y_return')
        volatility = qual_metrics.get('volatility')
        max_dd = qual_metrics.get('max_drawdown')
        analyst_rec = sent_metrics.get('recommendation_mean')
        upside = sent_metrics.get('upside_percent')
        fii_net = flow_metrics.get('fii_net_30d')
        fii_trend = flow_metrics.get('fii_trend', '')

        if rsi is not None:
            if rsi < 35:
                para3_parts.append(f"RSI of {rsi:.0f} indicates oversold conditions")
            elif rsi > 70:
                para3_parts.append(f"RSI of {rsi:.0f} signals overbought territory")
            else:
                para3_parts.append(f"RSI of {rsi:.0f} is in neutral territory")

        if trend:
            para3_parts.append(f"price trend is {trend.lower()}")

        if ret_3m is not None:
            sign = "+" if ret_3m >= 0 else ""
            para3_parts.append(f"3M return of {sign}{ret_3m:.1f}%")

        if ret_1y is not None:
            sign = "+" if ret_1y >= 0 else ""
            para3_parts.append(f"1Y return of {sign}{ret_1y:.1f}%")

        if volatility is not None:
            if volatility < 20:
                para3_parts.append(f"low volatility of {volatility:.1f}%")
            elif volatility > 40:
                para3_parts.append(f"high volatility of {volatility:.1f}%")

        if max_dd is not None and max_dd < -15:
            para3_parts.append(f"max drawdown of {max_dd:.1f}%")

        if upside is not None and upside > 5:
            para3_parts.append(f"analyst consensus implies {upside:.1f}% upside")

        if fii_net is not None and fii_net != 0:
            direction = "net buying" if fii_net > 0 else "net selling"
            para3_parts.append(f"FII {direction} of ₹{abs(fii_net):,.0f}Cr over 30 days")
        elif fii_trend == 'buying':
            para3_parts.append("FIIs have been accumulating in recent sessions")
        elif fii_trend == 'selling':
            para3_parts.append("FIIs have been distributing in recent sessions")

        para3 = ""
        if para3_parts:
            para3 = "Technically, " + "; ".join(para3_parts) + "."

        return (para1 + para2 + para3).strip()

    def _extract_strengths_from_metrics(
        self,
        fund_data: Dict,
        mom_data: Dict,
        qual_data: Dict,
        sent_data: Dict,
        flow_data: Dict
    ) -> List[str]:
        """Extract specific, metric-backed strengths."""
        strengths = []

        fund_metrics = fund_data.get('metrics', {})
        mom_metrics = mom_data.get('metrics', {})
        qual_metrics = qual_data.get('metrics', {})
        sent_metrics = sent_data.get('metrics', {})
        flow_metrics = flow_data.get('metrics', {})

        # Fundamentals strengths
        roe = fund_metrics.get('roe')
        if roe is not None and roe >= 15:
            strengths.append(f"Strong return on equity ({roe:.1f}%) indicates efficient capital deployment")

        pe = fund_metrics.get('pe_ratio')
        if pe is not None and 0 < pe < 18:
            strengths.append(f"Attractive valuation at P/E of {pe:.1f}x — potential margin of safety")

        rev_growth = fund_metrics.get('revenue_growth')
        if rev_growth is not None and rev_growth >= 15:
            strengths.append(f"Robust revenue growth of {rev_growth:.1f}% reflects strong business momentum")

        de = fund_metrics.get('debt_to_equity')
        if de is not None and de < 0.4:
            strengths.append(f"Clean balance sheet with low leverage (D/E: {de:.2f})")

        promoter = fund_metrics.get('promoter_holding')
        if promoter is not None and promoter >= 55:
            strengths.append(f"High promoter confidence — {promoter:.1f}% holding signals alignment with minority shareholders")

        # Momentum strengths
        rsi = mom_metrics.get('rsi')
        if rsi is not None and 40 <= rsi <= 65:
            strengths.append(f"RSI of {rsi:.0f} — healthy momentum without being overbought")

        ret_3m = mom_metrics.get('3m_return')
        if ret_3m is not None and ret_3m >= 10:
            strengths.append(f"Strong 3-month price performance of +{ret_3m:.1f}%, outpacing broader market")

        # Quality strengths
        volatility = qual_metrics.get('volatility')
        if volatility is not None and volatility < 22:
            strengths.append(f"Low annualised volatility of {volatility:.1f}% — suitable for risk-conscious investors")

        max_dd = qual_metrics.get('max_drawdown')
        if max_dd is not None and max_dd > -15:
            strengths.append(f"Limited max drawdown of {max_dd:.1f}% demonstrates price resilience")

        # Sentiment strengths
        upside = sent_metrics.get('upside_percent')
        if upside is not None and upside >= 15:
            strengths.append(f"Analyst consensus target implies {upside:.1f}% upside from current levels")

        analyst_count = sent_metrics.get('number_of_analyst_opinions')
        if analyst_count is not None and analyst_count >= 8:
            strengths.append(f"Well-covered by {analyst_count} analysts, indicating strong institutional interest")

        # Institutional flow strengths
        fii_net = flow_metrics.get('fii_net_30d')
        if fii_net is not None and fii_net > 2000:
            strengths.append(f"FII net buying of ₹{fii_net:,.0f}Cr over 30 days signals foreign institutional accumulation")

        mfi = flow_metrics.get('mfi')
        if mfi is not None and mfi > 60:
            strengths.append(f"Money Flow Index of {mfi:.0f} indicates sustained buying pressure")

        # Fallback if nothing specific found
        if not strengths:
            for agent_name, data in [('Fundamentals', fund_data), ('Momentum', mom_data),
                                      ('Quality', qual_data), ('Sentiment', sent_data),
                                      ('Institutional Flow', flow_data)]:
                if data.get('score', 50) >= 60:
                    strengths.append(f"{agent_name} score of {data['score']:.0f}/100 — above-average performance")

        return strengths[:5]

    def _extract_risks_from_metrics(
        self,
        fund_data: Dict,
        mom_data: Dict,
        qual_data: Dict,
        sent_data: Dict,
        flow_data: Dict
    ) -> List[str]:
        """Extract specific, metric-backed risks."""
        risks = []

        fund_metrics = fund_data.get('metrics', {})
        mom_metrics = mom_data.get('metrics', {})
        qual_metrics = qual_data.get('metrics', {})
        sent_metrics = sent_data.get('metrics', {})
        flow_metrics = flow_data.get('metrics', {})

        # Fundamentals risks
        roe = fund_metrics.get('roe')
        if roe is not None and roe < 10:
            risks.append(f"Weak ROE of {roe:.1f}% raises questions about management's capital efficiency")

        pe = fund_metrics.get('pe_ratio')
        if pe is not None and pe > 40:
            risks.append(f"Elevated P/E of {pe:.1f}x leaves little room for earnings disappointment")

        de = fund_metrics.get('debt_to_equity')
        if de is not None and de > 1.5:
            risks.append(f"High leverage (D/E: {de:.2f}) increases vulnerability in rising rate environment")

        rev_growth = fund_metrics.get('revenue_growth')
        if rev_growth is not None and rev_growth < 0:
            risks.append(f"Revenue contraction of {rev_growth:.1f}% signals deteriorating business fundamentals")

        # Momentum risks
        rsi = mom_metrics.get('rsi')
        if rsi is not None and rsi > 72:
            risks.append(f"Overbought RSI of {rsi:.0f} — short-term pullback risk is elevated")
        elif rsi is not None and rsi < 30:
            risks.append(f"RSI of {rsi:.0f} in oversold territory; trend reversal yet to materialise")

        ret_3m = mom_metrics.get('3m_return')
        if ret_3m is not None and ret_3m < -10:
            risks.append(f"3-month decline of {ret_3m:.1f}% indicates sustained selling pressure")

        # Quality risks
        volatility = qual_metrics.get('volatility')
        if volatility is not None and volatility > 40:
            risks.append(f"High annualised volatility of {volatility:.1f}% — significant price swings likely")

        max_dd = qual_metrics.get('max_drawdown')
        if max_dd is not None and max_dd < -30:
            risks.append(f"Historical max drawdown of {max_dd:.1f}% highlights downside risk in adverse conditions")

        current_dd = qual_metrics.get('current_drawdown')
        if current_dd is not None and current_dd < -20:
            risks.append(f"Currently {current_dd:.1f}% below its recent peak — recovery timeline uncertain")

        # Sentiment risks
        upside = sent_metrics.get('upside_percent')
        if upside is not None and upside < -5:
            risks.append(f"Analyst consensus implies {upside:.1f}% downside — sell-side is negative")

        # Flow risks
        fii_net = flow_metrics.get('fii_net_30d')
        if fii_net is not None and fii_net < -5000:
            risks.append(f"FII net selling of ₹{abs(fii_net):,.0f}Cr over 30 days — foreign outflows pose headwind")

        fii_trend = flow_metrics.get('fii_trend', '')
        dii_trend = flow_metrics.get('dii_trend', '')
        if fii_trend == 'selling' and dii_trend == 'selling':
            risks.append("Both FII and DII have been net sellers recently — broad institutional distribution signal")

        # Fallback
        if not risks:
            risks.append("General market risks apply; position sizing should reflect portfolio risk tolerance")
            for agent_name, data in [('Fundamentals', fund_data), ('Momentum', mom_data),
                                      ('Quality', qual_data)]:
                if data.get('score', 50) < 45:
                    risks.append(f"{agent_name} score of {data['score']:.0f}/100 below threshold — warrants caution")
                    break

        return risks[:5]

    def _build_summary(
        self,
        company_name: str,
        symbol: str,
        composite_score: float,
        recommendation: str,
        fund_data: Dict,
        mom_data: Dict,
        qual_data: Dict
    ) -> str:
        """Build a one-sentence summary with the most relevant data point."""
        fund_metrics = fund_data.get('metrics', {})
        mom_metrics = mom_data.get('metrics', {})

        pe = fund_metrics.get('pe_ratio')
        rsi = mom_metrics.get('rsi')
        ret_3m = mom_metrics.get('3m_return')

        detail = ""
        if pe is not None and 0 < pe < 50:
            detail = f" (P/E: {pe:.1f}x"
            if rsi is not None:
                detail += f", RSI: {rsi:.0f}"
            detail += ")"
        elif ret_3m is not None:
            sign = "+" if ret_3m >= 0 else ""
            detail = f" (3M return: {sign}{ret_3m:.1f}%)"

        return (
            f"{recommendation}: {company_name} ({symbol}) scores {composite_score:.1f}/100{detail} — "
            f"generated by rule-based analysis across five quantitative agents."
        )


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
