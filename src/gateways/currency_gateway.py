"""
Currency Exchange Gateway with fawazahmed0 and Exchange Rates API.

Provides currency conversion capabilities for multi-currency claims:
- Primary: fawazahmed0/exchange-api (free, open data)
- Fallback: exchangeratesapi.io (commercial)

Features:
- Real-time exchange rates
- Historical rate lookup
- Rate caching for performance
- Multi-currency support (USD, AED, SAR, EGP, etc.)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

import httpx

from src.core.config import get_claims_settings
from src.core.enums import CurrencyProvider
from src.gateways.base import (
    BaseGateway,
    GatewayConfig,
    GatewayError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


# Common currencies for healthcare claims
SUPPORTED_CURRENCIES = [
    "USD",  # US Dollar
    "AED",  # UAE Dirham
    "SAR",  # Saudi Riyal
    "EGP",  # Egyptian Pound
    "KWD",  # Kuwaiti Dinar
    "BHD",  # Bahraini Dinar
    "OMR",  # Omani Rial
    "QAR",  # Qatari Riyal
    "EUR",  # Euro
    "GBP",  # British Pound
    "AUD",  # Australian Dollar
]


@dataclass
class ExchangeRate:
    """Exchange rate between two currencies."""

    from_currency: str
    to_currency: str
    rate: Decimal
    timestamp: datetime
    source: str
    inverse_rate: Optional[Decimal] = None

    def convert(self, amount: Decimal) -> Decimal:
        """Convert an amount using this rate."""
        return amount * self.rate

    def convert_inverse(self, amount: Decimal) -> Decimal:
        """Convert in reverse direction."""
        if self.inverse_rate:
            return amount * self.inverse_rate
        return amount / self.rate


@dataclass
class CurrencyRequest:
    """Request for currency conversion."""

    amount: Decimal
    from_currency: str
    to_currency: str
    rate_date: Optional[date] = None  # None for current rate
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CurrencyResponse:
    """Response from currency conversion."""

    original_amount: Decimal
    converted_amount: Decimal
    from_currency: str
    to_currency: str
    exchange_rate: Decimal
    rate_date: date
    provider: str = ""
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class RateCache:
    """Simple in-memory cache for exchange rates."""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: dict[str, tuple[ExchangeRate, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> Optional[ExchangeRate]:
        """Get rate from cache if not expired."""
        if key in self._cache:
            rate, cached_at = self._cache[key]
            if datetime.now(timezone.utc) - cached_at < self._ttl:
                return rate
            else:
                del self._cache[key]
        return None

    def set(self, key: str, rate: ExchangeRate) -> None:
        """Store rate in cache."""
        self._cache[key] = (rate, datetime.now(timezone.utc))

    def clear(self) -> None:
        """Clear all cached rates."""
        self._cache.clear()


class CurrencyGateway(BaseGateway[CurrencyRequest, CurrencyResponse, CurrencyProvider]):
    """
    Currency Exchange Gateway for multi-currency claims.

    Supports:
    - fawazahmed0/exchange-api (primary, free)
    - exchangeratesapi.io (fallback, commercial)
    """

    # API endpoints
    FAWAZAHMED_BASE = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1"
    EXCHANGERATES_BASE = "https://api.exchangeratesapi.io/v1"

    def __init__(self, config: Optional[GatewayConfig] = None):
        settings = get_claims_settings()

        if config is None:
            config = GatewayConfig(
                primary_provider=settings.CURRENCY_PRIMARY_PROVIDER.value,
                fallback_provider=(
                    settings.CURRENCY_FALLBACK_PROVIDER.value
                    if settings.CURRENCY_FALLBACK_ON_ERROR
                    else None
                ),
                fallback_on_error=settings.CURRENCY_FALLBACK_ON_ERROR,
                timeout_seconds=10.0,
            )

        super().__init__(config)
        self._settings = settings
        self._http_client: Optional[httpx.AsyncClient] = None
        self._cache = RateCache(ttl_seconds=settings.CURRENCY_CACHE_TTL_SECONDS)

    @property
    def gateway_name(self) -> str:
        return "Currency"

    async def _initialize_provider(self, provider: CurrencyProvider) -> None:
        """Initialize currency provider."""
        self._http_client = httpx.AsyncClient(timeout=self.config.timeout_seconds)

        if provider == CurrencyProvider.FAWAZAHMED:
            # Test connection to fawazahmed0 API
            try:
                response = await self._http_client.get(
                    f"{self.FAWAZAHMED_BASE}/currencies.json"
                )
                if response.status_code != 200:
                    raise ProviderUnavailableError(
                        f"fawazahmed0 API returned {response.status_code}",
                        provider=provider.value,
                    )
            except httpx.ConnectError as e:
                raise ProviderUnavailableError(
                    f"Could not connect to fawazahmed0 API: {e}",
                    provider=provider.value,
                )
            logger.info("fawazahmed0 currency API initialized")

        elif provider == CurrencyProvider.EXCHANGERATES_API:
            if not self._settings.EXCHANGERATES_API_KEY:
                raise ProviderUnavailableError(
                    "ExchangeRates API key not configured",
                    provider=provider.value,
                )
            logger.info("ExchangeRates API initialized")

    async def _execute_request(
        self, request: CurrencyRequest, provider: CurrencyProvider
    ) -> CurrencyResponse:
        """Execute currency conversion request."""
        if provider == CurrencyProvider.FAWAZAHMED:
            return await self._convert_fawazahmed(request)
        elif provider == CurrencyProvider.EXCHANGERATES_API:
            return await self._convert_exchangerates(request)
        else:
            raise GatewayError(f"Unsupported currency provider: {provider}")

    async def _convert_fawazahmed(self, request: CurrencyRequest) -> CurrencyResponse:
        """Convert using fawazahmed0 API."""
        if not self._http_client:
            raise ProviderUnavailableError(
                "HTTP client not initialized", provider="fawazahmed"
            )

        from_curr = request.from_currency.lower()
        to_curr = request.to_currency.lower()

        # Check cache first
        cache_key = f"{from_curr}_{to_curr}"
        cached_rate = self._cache.get(cache_key)

        if cached_rate:
            converted = cached_rate.convert(request.amount)
            return CurrencyResponse(
                original_amount=request.amount,
                converted_amount=converted,
                from_currency=request.from_currency,
                to_currency=request.to_currency,
                exchange_rate=cached_rate.rate,
                rate_date=cached_rate.timestamp.date(),
                provider="fawazahmed",
                metadata={"cached": True},
            )

        # Fetch rate from API
        if request.rate_date:
            date_str = request.rate_date.strftime("%Y-%m-%d")
            url = f"{self.FAWAZAHMED_BASE}/currencies/{from_curr}.json"
        else:
            url = f"{self.FAWAZAHMED_BASE}/currencies/{from_curr}.json"

        try:
            response = await self._http_client.get(url)

            if response.status_code != 200:
                raise GatewayError(
                    f"fawazahmed0 API error: {response.status_code}",
                    provider="fawazahmed",
                )

            data = response.json()
            rates = data.get(from_curr, {})

            if to_curr not in rates:
                raise GatewayError(
                    f"Currency pair {from_curr}/{to_curr} not available",
                    provider="fawazahmed",
                )

            rate = Decimal(str(rates[to_curr]))
            converted = request.amount * rate

            # Cache the rate
            exchange_rate = ExchangeRate(
                from_currency=request.from_currency,
                to_currency=request.to_currency,
                rate=rate,
                timestamp=datetime.now(timezone.utc),
                source="fawazahmed",
            )
            self._cache.set(cache_key, exchange_rate)

            return CurrencyResponse(
                original_amount=request.amount,
                converted_amount=converted.quantize(Decimal("0.01")),
                from_currency=request.from_currency,
                to_currency=request.to_currency,
                exchange_rate=rate,
                rate_date=date.today(),
                provider="fawazahmed",
            )

        except httpx.TimeoutException:
            raise GatewayError(
                "fawazahmed0 API request timed out", provider="fawazahmed"
            )

    async def _convert_exchangerates(
        self, request: CurrencyRequest
    ) -> CurrencyResponse:
        """Convert using ExchangeRates API."""
        if not self._http_client:
            raise ProviderUnavailableError(
                "HTTP client not initialized", provider="exchangerates_api"
            )

        api_key = self._settings.EXCHANGERATES_API_KEY
        from_curr = request.from_currency.upper()
        to_curr = request.to_currency.upper()

        # Build URL
        if request.rate_date:
            date_str = request.rate_date.strftime("%Y-%m-%d")
            url = f"{self.EXCHANGERATES_BASE}/{date_str}"
        else:
            url = f"{self.EXCHANGERATES_BASE}/latest"

        params = {
            "access_key": api_key,
            "base": from_curr,
            "symbols": to_curr,
        }

        try:
            response = await self._http_client.get(url, params=params)

            if response.status_code != 200:
                raise GatewayError(
                    f"ExchangeRates API error: {response.status_code}",
                    provider="exchangerates_api",
                )

            data = response.json()

            if not data.get("success", True):
                error = data.get("error", {}).get("type", "Unknown error")
                raise GatewayError(
                    f"ExchangeRates API error: {error}",
                    provider="exchangerates_api",
                )

            rates = data.get("rates", {})
            if to_curr not in rates:
                raise GatewayError(
                    f"Currency {to_curr} not available",
                    provider="exchangerates_api",
                )

            rate = Decimal(str(rates[to_curr]))
            converted = request.amount * rate

            return CurrencyResponse(
                original_amount=request.amount,
                converted_amount=converted.quantize(Decimal("0.01")),
                from_currency=request.from_currency,
                to_currency=request.to_currency,
                exchange_rate=rate,
                rate_date=request.rate_date or date.today(),
                provider="exchangerates_api",
            )

        except httpx.TimeoutException:
            raise GatewayError(
                "ExchangeRates API request timed out", provider="exchangerates_api"
            )

    async def _health_check(self, provider: CurrencyProvider) -> bool:
        """Check if currency provider is healthy."""
        try:
            test_request = CurrencyRequest(
                amount=Decimal("100"),
                from_currency="USD",
                to_currency="EUR",
            )
            await self._execute_request(test_request, provider)
            return True
        except Exception as e:
            logger.warning(f"Currency health check failed for {provider.value}: {e}")
            return False

    def _parse_provider(self, provider_str: str) -> CurrencyProvider:
        """Parse provider string to CurrencyProvider enum."""
        return CurrencyProvider(provider_str)

    # Convenience methods for claims processing

    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        rate_date: Optional[date] = None,
    ) -> CurrencyResponse:
        """Simple currency conversion."""
        request = CurrencyRequest(
            amount=amount,
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            rate_date=rate_date,
        )
        result = await self.execute(request)

        if not result.success or not result.data:
            raise GatewayError(f"Currency conversion failed: {result.error}")

        return result.data

    async def get_rate(
        self, from_currency: str, to_currency: str, rate_date: Optional[date] = None
    ) -> ExchangeRate:
        """Get exchange rate between two currencies."""
        response = await self.convert(
            Decimal("1"),
            from_currency,
            to_currency,
            rate_date,
        )

        return ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=response.exchange_rate,
            timestamp=datetime.combine(response.rate_date, datetime.min.time()),
            source=response.provider,
        )

    async def convert_claim_amount(
        self,
        claim_amount: Decimal,
        claim_currency: str,
        target_currency: str,
        service_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Convert claim amount to target currency.

        Returns dict with original and converted amounts plus rate info.
        """
        response = await self.convert(
            claim_amount, claim_currency, target_currency, service_date
        )

        return {
            "original_amount": float(response.original_amount),
            "original_currency": response.from_currency,
            "converted_amount": float(response.converted_amount),
            "target_currency": response.to_currency,
            "exchange_rate": float(response.exchange_rate),
            "rate_date": response.rate_date.isoformat(),
            "rate_source": response.provider,
        }

    def clear_cache(self) -> None:
        """Clear the rate cache."""
        self._cache.clear()

    async def close(self) -> None:
        """Clean up currency gateway resources."""
        if self._http_client:
            await self._http_client.aclose()
        self._cache.clear()
        await super().close()


# Singleton instance
_currency_gateway: Optional[CurrencyGateway] = None


def get_currency_gateway() -> CurrencyGateway:
    """Get or create the singleton Currency gateway instance."""
    global _currency_gateway
    if _currency_gateway is None:
        _currency_gateway = CurrencyGateway()
    return _currency_gateway


async def reset_currency_gateway() -> None:
    """Reset the Currency gateway (for testing)."""
    global _currency_gateway
    if _currency_gateway:
        await _currency_gateway.close()
    _currency_gateway = None
