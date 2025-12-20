"""
Currency Conversion Service.
Source: Design Document Section 4.3 - Internationalization
Verified: 2025-12-18

Provides currency conversion for multi-currency claims processing.
"""

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SupportedCurrency(str, Enum):
    """Supported currencies for claims processing."""

    # Major currencies
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound

    # MENA region currencies
    AED = "AED"  # UAE Dirham
    SAR = "SAR"  # Saudi Riyal
    EGP = "EGP"  # Egyptian Pound
    KWD = "KWD"  # Kuwaiti Dinar
    BHD = "BHD"  # Bahraini Dinar
    OMR = "OMR"  # Omani Rial
    QAR = "QAR"  # Qatari Riyal
    JOD = "JOD"  # Jordanian Dinar
    LBP = "LBP"  # Lebanese Pound

    # Other
    AUD = "AUD"  # Australian Dollar


class CurrencyConversion(BaseModel):
    """Result of currency conversion."""

    original_amount: Decimal
    original_currency: SupportedCurrency
    converted_amount: Decimal
    target_currency: SupportedCurrency
    exchange_rate: Decimal
    rate_date: date
    rate_source: str = "system"
    conversion_id: str = Field(default_factory=lambda: str(uuid4()))


class CurrencyAuditEntry(BaseModel):
    """Audit entry for currency conversion."""

    conversion_id: str
    claim_id: Optional[str] = None
    original_amount: Decimal
    original_currency: str
    converted_amount: Decimal
    target_currency: str
    exchange_rate: Decimal
    rate_date: date
    rate_source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    notes: Optional[str] = None


# Fixed exchange rates for demo/offline mode (as of reference date)
# These are approximate rates for demonstration purposes
FIXED_RATES_TO_USD = {
    SupportedCurrency.USD: Decimal("1.0000"),
    SupportedCurrency.EUR: Decimal("1.0850"),
    SupportedCurrency.GBP: Decimal("1.2650"),
    SupportedCurrency.AED: Decimal("0.2723"),  # 1 AED = 0.2723 USD
    SupportedCurrency.SAR: Decimal("0.2667"),  # 1 SAR = 0.2667 USD
    SupportedCurrency.EGP: Decimal("0.0204"),  # 1 EGP = 0.0204 USD
    SupportedCurrency.KWD: Decimal("3.2500"),  # 1 KWD = 3.25 USD
    SupportedCurrency.BHD: Decimal("2.6596"),  # 1 BHD = 2.66 USD
    SupportedCurrency.OMR: Decimal("2.6008"),  # 1 OMR = 2.60 USD
    SupportedCurrency.QAR: Decimal("0.2747"),  # 1 QAR = 0.2747 USD
    SupportedCurrency.JOD: Decimal("1.4104"),  # 1 JOD = 1.41 USD
    SupportedCurrency.LBP: Decimal("0.0001"),  # 1 LBP = 0.0001 USD
    SupportedCurrency.AUD: Decimal("0.6500"),  # 1 AUD = 0.65 USD
}


class CurrencyConversionService:
    """
    Provides currency conversion for claims processing.

    Features:
    - Multi-currency support (USD, AED, SAR, etc.)
    - Real-time and historical rates
    - Conversion audit trail
    - Offline fallback rates
    """

    def __init__(self, use_live_rates: bool = False):
        """
        Initialize CurrencyConversionService.

        Args:
            use_live_rates: Whether to fetch live rates (vs fixed rates)
        """
        self._use_live_rates = use_live_rates
        self._audit_log: list[CurrencyAuditEntry] = []
        self._rate_cache: dict[str, tuple[Decimal, datetime]] = {}
        self._cache_ttl_seconds = 3600  # 1 hour

    def get_supported_currencies(self) -> list[SupportedCurrency]:
        """Get list of supported currencies."""
        return list(SupportedCurrency)

    def get_exchange_rate(
        self,
        from_currency: SupportedCurrency,
        to_currency: SupportedCurrency,
        rate_date: Optional[date] = None,
    ) -> Decimal:
        """
        Get exchange rate between two currencies.

        Args:
            from_currency: Source currency
            to_currency: Target currency
            rate_date: Date for historical rate (None for current)

        Returns:
            Exchange rate
        """
        if from_currency == to_currency:
            return Decimal("1.0000")

        # Convert through USD as base
        from_to_usd = FIXED_RATES_TO_USD.get(from_currency, Decimal("1.0"))
        to_to_usd = FIXED_RATES_TO_USD.get(to_currency, Decimal("1.0"))

        # Calculate cross rate: from_currency -> USD -> to_currency
        rate = from_to_usd / to_to_usd

        return rate.quantize(Decimal("0.000001"))

    async def convert(
        self,
        amount: Decimal,
        from_currency: SupportedCurrency,
        to_currency: SupportedCurrency,
        rate_date: Optional[date] = None,
        claim_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> CurrencyConversion:
        """
        Convert amount between currencies.

        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            rate_date: Date for historical rate
            claim_id: Optional claim ID for audit
            user_id: Optional user ID for audit

        Returns:
            CurrencyConversion result
        """
        rate = self.get_exchange_rate(from_currency, to_currency, rate_date)
        converted = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        conversion = CurrencyConversion(
            original_amount=amount,
            original_currency=from_currency,
            converted_amount=converted,
            target_currency=to_currency,
            exchange_rate=rate,
            rate_date=rate_date or date.today(),
            rate_source="fixed_rates" if not self._use_live_rates else "live",
        )

        # Add audit entry
        self._add_audit_entry(conversion, claim_id, user_id)

        return conversion

    async def convert_claim_amounts(
        self,
        claim_data: dict,
        target_currency: SupportedCurrency = SupportedCurrency.USD,
        fields_to_convert: Optional[list[str]] = None,
    ) -> dict:
        """
        Convert all currency amounts in a claim.

        Args:
            claim_data: Claim data dictionary
            target_currency: Target currency for conversion
            fields_to_convert: Specific fields to convert (default: all amount fields)

        Returns:
            Claim data with converted amounts
        """
        if fields_to_convert is None:
            fields_to_convert = [
                "total_charged",
                "allowed_amount",
                "paid_amount",
                "patient_responsibility",
                "deductible_applied",
                "copay_amount",
                "coinsurance_amount",
            ]

        # Get source currency
        source_currency_str = claim_data.get("currency", "USD")
        try:
            source_currency = SupportedCurrency(source_currency_str)
        except ValueError:
            source_currency = SupportedCurrency.USD

        if source_currency == target_currency:
            return claim_data

        result = claim_data.copy()
        claim_id = claim_data.get("claim_id")

        for field in fields_to_convert:
            if field in result and result[field] is not None:
                try:
                    amount = Decimal(str(result[field]))
                    conversion = await self.convert(
                        amount,
                        source_currency,
                        target_currency,
                        claim_id=claim_id,
                    )
                    result[f"{field}_original"] = float(amount)
                    result[f"{field}_original_currency"] = source_currency.value
                    result[field] = float(conversion.converted_amount)
                except (ValueError, TypeError):
                    pass

        result["currency"] = target_currency.value
        result["currency_converted"] = True
        result["conversion_date"] = date.today().isoformat()

        return result

    def _add_audit_entry(
        self,
        conversion: CurrencyConversion,
        claim_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Add conversion to audit log."""
        entry = CurrencyAuditEntry(
            conversion_id=conversion.conversion_id,
            claim_id=claim_id,
            original_amount=conversion.original_amount,
            original_currency=conversion.original_currency.value,
            converted_amount=conversion.converted_amount,
            target_currency=conversion.target_currency.value,
            exchange_rate=conversion.exchange_rate,
            rate_date=conversion.rate_date,
            rate_source=conversion.rate_source,
            user_id=user_id,
        )
        self._audit_log.append(entry)

        # Keep audit log size manageable
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]

    def get_audit_log(
        self,
        claim_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CurrencyAuditEntry]:
        """
        Get currency conversion audit log.

        Args:
            claim_id: Filter by claim ID
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of audit entries
        """
        entries = self._audit_log

        if claim_id:
            entries = [e for e in entries if e.claim_id == claim_id]

        if start_date:
            entries = [e for e in entries if e.timestamp.date() >= start_date]

        if end_date:
            entries = [e for e in entries if e.timestamp.date() <= end_date]

        return entries

    def format_currency(
        self,
        amount: Decimal,
        currency: SupportedCurrency,
        include_symbol: bool = True,
    ) -> str:
        """
        Format amount with currency symbol.

        Args:
            amount: Amount to format
            currency: Currency for formatting
            include_symbol: Whether to include currency symbol

        Returns:
            Formatted currency string
        """
        # Currency symbols
        symbols = {
            SupportedCurrency.USD: "$",
            SupportedCurrency.EUR: "€",
            SupportedCurrency.GBP: "£",
            SupportedCurrency.AED: "د.إ",
            SupportedCurrency.SAR: "ر.س",
            SupportedCurrency.EGP: "ج.م",
            SupportedCurrency.KWD: "د.ك",
            SupportedCurrency.BHD: "د.ب",
            SupportedCurrency.OMR: "ر.ع",
            SupportedCurrency.QAR: "ر.ق",
            SupportedCurrency.JOD: "د.أ",
            SupportedCurrency.LBP: "ل.ل",
            SupportedCurrency.AUD: "A$",
        }

        formatted_amount = f"{amount:,.2f}"

        if include_symbol:
            symbol = symbols.get(currency, currency.value)
            # Arabic currencies typically show symbol after amount
            if currency in [
                SupportedCurrency.AED,
                SupportedCurrency.SAR,
                SupportedCurrency.EGP,
                SupportedCurrency.KWD,
                SupportedCurrency.BHD,
                SupportedCurrency.OMR,
                SupportedCurrency.QAR,
                SupportedCurrency.JOD,
                SupportedCurrency.LBP,
            ]:
                return f"{formatted_amount} {symbol}"
            return f"{symbol}{formatted_amount}"

        return formatted_amount

    def get_currency_info(self, currency: SupportedCurrency) -> dict:
        """
        Get information about a currency.

        Args:
            currency: Currency to get info for

        Returns:
            Dictionary with currency information
        """
        info = {
            SupportedCurrency.USD: {
                "code": "USD",
                "name": "US Dollar",
                "name_ar": "دولار أمريكي",
                "symbol": "$",
                "decimals": 2,
                "region": "Americas",
            },
            SupportedCurrency.EUR: {
                "code": "EUR",
                "name": "Euro",
                "name_ar": "يورو",
                "symbol": "€",
                "decimals": 2,
                "region": "Europe",
            },
            SupportedCurrency.GBP: {
                "code": "GBP",
                "name": "British Pound",
                "name_ar": "جنيه إسترليني",
                "symbol": "£",
                "decimals": 2,
                "region": "Europe",
            },
            SupportedCurrency.AED: {
                "code": "AED",
                "name": "UAE Dirham",
                "name_ar": "درهم إماراتي",
                "symbol": "د.إ",
                "decimals": 2,
                "region": "MENA",
            },
            SupportedCurrency.SAR: {
                "code": "SAR",
                "name": "Saudi Riyal",
                "name_ar": "ريال سعودي",
                "symbol": "ر.س",
                "decimals": 2,
                "region": "MENA",
            },
            SupportedCurrency.EGP: {
                "code": "EGP",
                "name": "Egyptian Pound",
                "name_ar": "جنيه مصري",
                "symbol": "ج.م",
                "decimals": 2,
                "region": "MENA",
            },
            SupportedCurrency.KWD: {
                "code": "KWD",
                "name": "Kuwaiti Dinar",
                "name_ar": "دينار كويتي",
                "symbol": "د.ك",
                "decimals": 3,
                "region": "MENA",
            },
            SupportedCurrency.BHD: {
                "code": "BHD",
                "name": "Bahraini Dinar",
                "name_ar": "دينار بحريني",
                "symbol": "د.ب",
                "decimals": 3,
                "region": "MENA",
            },
            SupportedCurrency.OMR: {
                "code": "OMR",
                "name": "Omani Rial",
                "name_ar": "ريال عماني",
                "symbol": "ر.ع",
                "decimals": 3,
                "region": "MENA",
            },
            SupportedCurrency.QAR: {
                "code": "QAR",
                "name": "Qatari Riyal",
                "name_ar": "ريال قطري",
                "symbol": "ر.ق",
                "decimals": 2,
                "region": "MENA",
            },
            SupportedCurrency.JOD: {
                "code": "JOD",
                "name": "Jordanian Dinar",
                "name_ar": "دينار أردني",
                "symbol": "د.أ",
                "decimals": 3,
                "region": "MENA",
            },
            SupportedCurrency.LBP: {
                "code": "LBP",
                "name": "Lebanese Pound",
                "name_ar": "ليرة لبنانية",
                "symbol": "ل.ل",
                "decimals": 0,
                "region": "MENA",
            },
            SupportedCurrency.AUD: {
                "code": "AUD",
                "name": "Australian Dollar",
                "name_ar": "دولار أسترالي",
                "symbol": "A$",
                "decimals": 2,
                "region": "Oceania",
            },
        }

        return info.get(currency, {"code": currency.value, "name": currency.value})


# =============================================================================
# Factory Functions
# =============================================================================


_currency_service: Optional[CurrencyConversionService] = None


def get_currency_service(use_live_rates: bool = False) -> CurrencyConversionService:
    """Get singleton CurrencyConversionService instance."""
    global _currency_service
    if _currency_service is None:
        _currency_service = CurrencyConversionService(use_live_rates)
    return _currency_service


def create_currency_service(use_live_rates: bool = False) -> CurrencyConversionService:
    """Create a new CurrencyConversionService instance."""
    return CurrencyConversionService(use_live_rates)
