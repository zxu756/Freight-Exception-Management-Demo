"""
AI Decision Engine for generating solution options and recommendations.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

from schemas import DecisionOption
from risk_calculator import calculate_risk_score, categorize_risk


class DecisionEngine:
    """
    Core decision engine that generates solution options and recommendations.
    """

    def __init__(self):
        self.decision_history = []

    def generate_solutions(
        self,
        exception_type: str,
        shipment: Dict[str, Any],
        exception_data: Dict[str, Any]
    ) -> List[DecisionOption]:
        """
        Generate solution options based on exception type.

        Args:
            exception_type: Type of exception
            shipment: Shipment data dictionary
            exception_data: Exception details

        Returns:
            List of solution options
        """
        if exception_type == 'delay':
            return self._generate_delay_solutions(shipment, exception_data)
        elif exception_type == 'damage':
            return self._generate_damage_solutions(shipment, exception_data)
        elif exception_type == 'misroute':
            return self._generate_misroute_solutions(shipment, exception_data)
        else:
            return self._generate_default_solutions(shipment, exception_data)

    def _generate_delay_solutions(
        self,
        shipment: Dict[str, Any],
        exception_data: Dict[str, Any]
    ) -> List[DecisionOption]:
        """Generate solutions for delay exceptions."""
        options = []
        delayed_eta = exception_data.get('delayed_eta')
        delay_hours = exception_data.get('delay_hours', 2)

        # Option A: Wait/Continue with current plan
        options.append(DecisionOption(
            option_id='A',
            description='Continue with current plan',
            cost=0,
            new_eta=delayed_eta,
            sla_impact=self._calculate_sla_impact(delayed_eta, shipment['sla_deadline']),
            risk='low'
        ))

        # Option B: Expedite if possible
        if shipment['transport_mode'] in ['road', 'sea']:
            expedite_eta = delayed_eta - timedelta(hours=delay_hours * 0.5)
            expedite_cost = self._calculate_expedite_cost(shipment, delay_hours)

            options.append(DecisionOption(
                option_id='B',
                description='Expedite via faster transport',
                cost=expedite_cost,
                new_eta=expedite_eta,
                sla_impact=self._calculate_sla_impact(expedite_eta, shipment['sla_deadline']),
                risk='medium'
            ))

        # Option C: Reroute if alternate path exists
        if self._has_alternate_route(shipment):
            reroute_eta = delayed_eta - timedelta(hours=delay_hours * 0.3)
            reroute_cost = self._calculate_reroute_cost(shipment)

            options.append(DecisionOption(
                option_id='C',
                description='Reroute via alternate path',
                cost=reroute_cost,
                new_eta=reroute_eta,
                sla_impact=self._calculate_sla_impact(reroute_eta, shipment['sla_deadline']),
                risk='medium'
            ))

        return options

    def _generate_damage_solutions(
        self,
        shipment: Dict[str, Any],
        exception_data: Dict[str, Any]
    ) -> List[DecisionOption]:
        """Generate solutions for damage exceptions."""
        options = []

        # Option A: Assess and proceed if acceptable
        options.append(DecisionOption(
            option_id='A',
            description='Inspect cargo and deliver if acceptable',
            cost=0,
            new_eta=shipment['current_eta'],
            sla_impact='requires_inspection',
            risk='medium'
        ))

        # Option B: File insurance claim
        options.append(DecisionOption(
            option_id='B',
            description='File insurance claim and arrange replacement',
            cost=0,  # Insurance covers
            new_eta=shipment['current_eta'] + timedelta(days=3),
            sla_impact='breach_72h',
            risk='high'
        ))

        return options

    def _generate_misroute_solutions(
        self,
        shipment: Dict[str, Any],
        exception_data: Dict[str, Any]
    ) -> List[DecisionOption]:
        """Generate solutions for misroute exceptions."""
        options = []

        # Option A: Redirect from current location
        redirect_delay = 6  # hours
        options.append(DecisionOption(
            option_id='A',
            description='Redirect from current location',
            cost=350,
            new_eta=datetime.utcnow() + timedelta(hours=redirect_delay),
            sla_impact=self._calculate_sla_impact(
                datetime.utcnow() + timedelta(hours=redirect_delay),
                shipment['sla_deadline']
            ),
            risk='medium'
        ))

        return options

    def _generate_default_solutions(
        self,
        shipment: Dict[str, Any],
        exception_data: Dict[str, Any]
    ) -> List[DecisionOption]:
        """Generate default solutions."""
        return [
            DecisionOption(
                option_id='A',
                description='Continue monitoring and wait for resolution',
                cost=0,
                new_eta=shipment['current_eta'],
                sla_impact='monitoring',
                risk='low'
            )
        ]

    def rank_solutions(
        self,
        options: List[DecisionOption],
        shipment: Dict[str, Any],
        risk_score: int
    ) -> str:
        """
        Rank solutions and return the best option ID.

        Args:
            options: List of solution options
            shipment: Shipment data
            risk_score: Risk score

        Returns:
            Best option ID
        """
        for option in options:
            option.utility_score = self._calculate_utility(
                option,
                shipment['cargo_value'],
                shipment['customer_tier']
            )

        # Sort by utility score (higher is better)
        ranked = sorted(options, key=lambda x: x.utility_score, reverse=True)
        return ranked[0].option_id

    def _calculate_utility(
        self,
        option: DecisionOption,
        cargo_value: float,
        customer_tier: str
    ) -> float:
        """Calculate utility score for a solution option."""
        score = 100.0

        # Penalize cost (relative to cargo value)
        cost_ratio = option.cost / cargo_value if cargo_value > 0 else 0
        score -= cost_ratio * 50

        # Penalize SLA breaches
        if 'breach' in option.sla_impact:
            score -= 30
        elif option.sla_impact == 'minor_delay':
            score -= 10

        # Penalize risk
        risk_penalties = {'low': 0, 'medium': 10, 'high': 20}
        score -= risk_penalties.get(option.risk, 0)

        # Bonus for high-tier customers with better service
        if customer_tier in ['high', 'VIP'] and option.cost > 0:
            score += 15  # Willing to pay for better service

        return max(score, 0)

    def _calculate_sla_impact(self, new_eta: datetime, sla_deadline: datetime) -> str:
        """Calculate SLA impact description."""
        if new_eta <= sla_deadline:
            hours_early = (sla_deadline - new_eta).total_seconds() / 3600
            if hours_early > 2:
                return 'within_sla'
            else:
                return 'minor_delay_within_buffer'
        else:
            hours_late = (new_eta - sla_deadline).total_seconds() / 3600
            if hours_late <= 4:
                return f'breach_{int(hours_late)}h'
            else:
                return f'breach_{int(hours_late)}h'

    def _calculate_expedite_cost(self, shipment: Dict[str, Any], delay_hours: float) -> float:
        """Calculate cost of expediting shipment."""
        base_cost = 500
        value_factor = shipment['cargo_value'] / 10000
        return base_cost + (delay_hours * 50) + (value_factor * 100)

    def _calculate_reroute_cost(self, shipment: Dict[str, Any]) -> float:
        """Calculate cost of rerouting."""
        base_cost = 650
        mode_multipliers = {'road': 1.0, 'rail': 1.2, 'sea': 1.5, 'air': 2.0}
        multiplier = mode_multipliers.get(shipment['transport_mode'], 1.0)
        return base_cost * multiplier

    def _has_alternate_route(self, shipment: Dict[str, Any]) -> bool:
        """Check if alternate route is available."""
        # Simplified logic - in production, this would query routing database
        return shipment['transport_mode'] in ['road', 'rail', 'sea']

    def generate_reasoning(
        self,
        recommended_option: str,
        options: List[DecisionOption],
        shipment: Dict[str, Any],
        risk_level: str
    ) -> str:
        """
        Generate human-readable reasoning for the recommendation.

        Args:
            recommended_option: Recommended option ID
            options: All options
            shipment: Shipment data
            risk_level: Risk level

        Returns:
            Reasoning text
        """
        option = next((opt for opt in options if opt.option_id == recommended_option), None)
        if not option:
            return "Unable to generate reasoning"

        reasons = []

        # Cost reasoning
        if option.cost == 0:
            reasons.append("No additional cost")
        else:
            cost_ratio = (option.cost / shipment['cargo_value']) * 100
            reasons.append(f"Cost is {cost_ratio:.1f}% of cargo value")

        # SLA reasoning
        if 'breach' in option.sla_impact:
            reasons.append("Avoids or minimizes SLA breach")
        elif 'within' in option.sla_impact:
            reasons.append("Maintains SLA commitment")

        # Customer reasoning
        if shipment['customer_tier'] in ['high', 'VIP']:
            reasons.append(f"{shipment['customer_tier']} customer - relationship preservation matters")

        # Risk reasoning
        reasons.append(f"{risk_level.capitalize()} risk profile")

        return "; ".join(reasons) + "."


# Global instance
decision_engine = DecisionEngine()
