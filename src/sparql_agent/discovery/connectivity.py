"""
SPARQL Endpoint Connectivity and Health Check Module

This module provides comprehensive connectivity testing, health checks, and
connection management for SPARQL endpoints with both synchronous and asynchronous interfaces.
"""

import time
import asyncio
import ssl
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
from urllib.parse import urlparse
import logging

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EndpointStatus(Enum):
    """Status of SPARQL endpoint health check"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNREACHABLE = "unreachable"
    TIMEOUT = "timeout"
    SSL_ERROR = "ssl_error"
    AUTH_REQUIRED = "auth_required"
    AUTH_FAILED = "auth_failed"


@dataclass
class EndpointHealth:
    """Health check result for a SPARQL endpoint"""
    endpoint_url: str
    status: EndpointStatus
    response_time_ms: Optional[float] = None
    status_code: Optional[int] = None
    ssl_valid: bool = True
    ssl_expiry: Optional[datetime] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    server_info: Dict[str, str] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert health check result to dictionary"""
        return {
            'endpoint_url': self.endpoint_url,
            'status': self.status.value,
            'response_time_ms': self.response_time_ms,
            'status_code': self.status_code,
            'ssl_valid': self.ssl_valid,
            'ssl_expiry': self.ssl_expiry.isoformat() if self.ssl_expiry else None,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat(),
            'server_info': self.server_info,
            'capabilities': self.capabilities
        }


@dataclass
class ConnectionConfig:
    """Configuration for endpoint connections"""
    timeout: float = 10.0  # seconds
    verify_ssl: bool = True
    follow_redirects: bool = True
    max_redirects: int = 5
    user_agent: str = "SPARQL-Agent/1.0"
    auth: Optional[Tuple[str, str]] = None
    headers: Dict[str, str] = field(default_factory=dict)
    retry_attempts: int = 3
    retry_delay: float = 1.0  # seconds
    retry_backoff: float = 2.0  # exponential backoff multiplier


class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, rate: float, burst: int):
        """
        Initialize rate limiter

        Args:
            rate: Requests per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire token (async)"""
        async with self._lock:
            await self._wait_for_token()

    async def _wait_for_token(self) -> None:
        """Wait until a token is available"""
        while True:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                break

            # Wait for next token
            wait_time = (1 - self.tokens) / self.rate
            await asyncio.sleep(wait_time)

    def acquire_sync(self) -> None:
        """Acquire token (sync)"""
        while True:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                break

            # Wait for next token
            wait_time = (1 - self.tokens) / self.rate
            time.sleep(wait_time)


class ConnectionPool:
    """Connection pool manager for SPARQL endpoints"""

    def __init__(self, max_connections: int = 10, max_keepalive: int = 5):
        """
        Initialize connection pool

        Args:
            max_connections: Maximum number of concurrent connections
            max_keepalive: Maximum number of keepalive connections
        """
        self.max_connections = max_connections
        self.max_keepalive = max_keepalive
        self._async_client: Optional[Any] = None
        self._sync_session: Optional[Any] = None

    def get_async_client(self, config: ConnectionConfig) -> Any:
        """Get or create async HTTP client"""
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx is required for async operations. Install with: pip install httpx")

        if self._async_client is None:
            limits = httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive
            )
            self._async_client = httpx.AsyncClient(
                timeout=config.timeout,
                verify=config.verify_ssl,
                follow_redirects=config.follow_redirects,
                max_redirects=config.max_redirects,
                limits=limits
            )
        return self._async_client

    def get_sync_session(self, config: ConnectionConfig) -> Any:
        """Get or create sync HTTP session"""
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests is required for sync operations. Install with: pip install requests")

        if self._sync_session is None:
            self._sync_session = requests.Session()
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=self.max_connections,
                pool_maxsize=self.max_connections,
                max_retries=0  # We handle retries manually
            )
            self._sync_session.mount('http://', adapter)
            self._sync_session.mount('https://', adapter)
        return self._sync_session

    async def close_async(self) -> None:
        """Close async client"""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    def close_sync(self) -> None:
        """Close sync session"""
        if self._sync_session:
            self._sync_session.close()
            self._sync_session = None


class EndpointPinger:
    """
    SPARQL endpoint health checker and connectivity tester

    Provides comprehensive health checks including:
    - HTTP/HTTPS connectivity
    - SSL/TLS validation
    - Response time measurement
    - Authentication support
    - Rate limiting
    - Connection pooling
    - Retry logic with exponential backoff
    """

    # Simple ASK query for health checks
    HEALTH_CHECK_QUERY = "ASK { ?s ?p ?o }"

    def __init__(
        self,
        config: Optional[ConnectionConfig] = None,
        rate_limit: Optional[Tuple[float, int]] = None,
        pool_size: int = 10
    ):
        """
        Initialize endpoint pinger

        Args:
            config: Connection configuration
            rate_limit: Optional (rate, burst) for rate limiting
            pool_size: Connection pool size
        """
        self.config = config or ConnectionConfig()
        self.rate_limiter = RateLimiter(*rate_limit) if rate_limit else None
        self.pool = ConnectionPool(max_connections=pool_size)
        self._health_history: Dict[str, deque] = {}

    async def ping_async(
        self,
        endpoint_url: str,
        check_query: bool = True,
        config: Optional[ConnectionConfig] = None
    ) -> EndpointHealth:
        """
        Ping SPARQL endpoint asynchronously

        Args:
            endpoint_url: SPARQL endpoint URL
            check_query: Whether to execute a test query
            config: Optional connection config (overrides default)

        Returns:
            EndpointHealth result
        """
        config = config or self.config

        # Apply rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(config.retry_attempts):
            try:
                if attempt > 0:
                    delay = config.retry_delay * (config.retry_backoff ** (attempt - 1))
                    await asyncio.sleep(delay)

                return await self._execute_ping_async(endpoint_url, check_query, config)

            except Exception as e:
                last_error = e
                logger.warning(f"Ping attempt {attempt + 1} failed for {endpoint_url}: {e}")

        # All retries failed
        return EndpointHealth(
            endpoint_url=endpoint_url,
            status=EndpointStatus.UNREACHABLE,
            error_message=f"All {config.retry_attempts} attempts failed: {last_error}"
        )

    async def _execute_ping_async(
        self,
        endpoint_url: str,
        check_query: bool,
        config: ConnectionConfig
    ) -> EndpointHealth:
        """Execute a single ping attempt (async)"""
        client = self.pool.get_async_client(config)

        # Prepare headers
        headers = {
            'User-Agent': config.user_agent,
            'Accept': 'application/sparql-results+json,application/json',
            **config.headers
        }

        start_time = time.monotonic()

        try:
            # Prepare auth
            auth = None
            if config.auth:
                auth = httpx.BasicAuth(config.auth[0], config.auth[1])

            if check_query:
                # Execute test query
                params = {'query': self.HEALTH_CHECK_QUERY}
                response = await client.get(
                    endpoint_url,
                    params=params,
                    headers=headers,
                    auth=auth
                )
            else:
                # Simple HEAD request
                response = await client.head(
                    endpoint_url,
                    headers=headers,
                    auth=auth
                )

            response_time = (time.monotonic() - start_time) * 1000  # ms

            # Check SSL certificate
            ssl_valid = True
            ssl_expiry = None
            if endpoint_url.startswith('https://'):
                ssl_valid, ssl_expiry = await self._check_ssl_async(endpoint_url, config)

            # Determine status
            status = self._determine_status(response.status_code, response_time)

            # Extract server info
            server_info = self._extract_server_info(response.headers)

            # Check for capabilities
            capabilities = self._detect_capabilities(response.headers)

            return EndpointHealth(
                endpoint_url=endpoint_url,
                status=status,
                response_time_ms=response_time,
                status_code=response.status_code,
                ssl_valid=ssl_valid,
                ssl_expiry=ssl_expiry,
                server_info=server_info,
                capabilities=capabilities
            )

        except httpx.TimeoutException as e:
            response_time = (time.monotonic() - start_time) * 1000
            return EndpointHealth(
                endpoint_url=endpoint_url,
                status=EndpointStatus.TIMEOUT,
                response_time_ms=response_time,
                error_message=f"Request timeout after {config.timeout}s"
            )

        except httpx.HTTPStatusError as e:
            response_time = (time.monotonic() - start_time) * 1000
            if e.response.status_code == 401:
                return EndpointHealth(
                    endpoint_url=endpoint_url,
                    status=EndpointStatus.AUTH_REQUIRED,
                    response_time_ms=response_time,
                    status_code=e.response.status_code,
                    error_message="Authentication required"
                )
            elif e.response.status_code == 403:
                return EndpointHealth(
                    endpoint_url=endpoint_url,
                    status=EndpointStatus.AUTH_FAILED,
                    response_time_ms=response_time,
                    status_code=e.response.status_code,
                    error_message="Authentication failed"
                )
            else:
                return EndpointHealth(
                    endpoint_url=endpoint_url,
                    status=EndpointStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    status_code=e.response.status_code,
                    error_message=f"HTTP error: {e.response.status_code}"
                )

        except ssl.SSLError as e:
            return EndpointHealth(
                endpoint_url=endpoint_url,
                status=EndpointStatus.SSL_ERROR,
                ssl_valid=False,
                error_message=f"SSL error: {str(e)}"
            )

        except Exception as e:
            return EndpointHealth(
                endpoint_url=endpoint_url,
                status=EndpointStatus.UNREACHABLE,
                error_message=f"Connection error: {str(e)}"
            )

    def ping_sync(
        self,
        endpoint_url: str,
        check_query: bool = True,
        config: Optional[ConnectionConfig] = None
    ) -> EndpointHealth:
        """
        Ping SPARQL endpoint synchronously

        Args:
            endpoint_url: SPARQL endpoint URL
            check_query: Whether to execute a test query
            config: Optional connection config (overrides default)

        Returns:
            EndpointHealth result
        """
        config = config or self.config

        # Apply rate limiting
        if self.rate_limiter:
            self.rate_limiter.acquire_sync()

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(config.retry_attempts):
            try:
                if attempt > 0:
                    delay = config.retry_delay * (config.retry_backoff ** (attempt - 1))
                    time.sleep(delay)

                return self._execute_ping_sync(endpoint_url, check_query, config)

            except Exception as e:
                last_error = e
                logger.warning(f"Ping attempt {attempt + 1} failed for {endpoint_url}: {e}")

        # All retries failed
        return EndpointHealth(
            endpoint_url=endpoint_url,
            status=EndpointStatus.UNREACHABLE,
            error_message=f"All {config.retry_attempts} attempts failed: {last_error}"
        )

    def _execute_ping_sync(
        self,
        endpoint_url: str,
        check_query: bool,
        config: ConnectionConfig
    ) -> EndpointHealth:
        """Execute a single ping attempt (sync)"""
        session = self.pool.get_sync_session(config)

        # Prepare headers
        headers = {
            'User-Agent': config.user_agent,
            'Accept': 'application/sparql-results+json,application/json',
            **config.headers
        }

        start_time = time.monotonic()

        try:
            # Prepare auth
            auth = config.auth if config.auth else None

            if check_query:
                # Execute test query
                params = {'query': self.HEALTH_CHECK_QUERY}
                response = session.get(
                    endpoint_url,
                    params=params,
                    headers=headers,
                    auth=auth,
                    timeout=config.timeout,
                    verify=config.verify_ssl,
                    allow_redirects=config.follow_redirects
                )
            else:
                # Simple HEAD request
                response = session.head(
                    endpoint_url,
                    headers=headers,
                    auth=auth,
                    timeout=config.timeout,
                    verify=config.verify_ssl,
                    allow_redirects=config.follow_redirects
                )

            response_time = (time.monotonic() - start_time) * 1000  # ms

            # Check SSL certificate
            ssl_valid = True
            ssl_expiry = None
            if endpoint_url.startswith('https://'):
                ssl_valid, ssl_expiry = self._check_ssl_sync(endpoint_url, config)

            # Determine status
            status = self._determine_status(response.status_code, response_time)

            # Extract server info
            server_info = self._extract_server_info(dict(response.headers))

            # Check for capabilities
            capabilities = self._detect_capabilities(dict(response.headers))

            return EndpointHealth(
                endpoint_url=endpoint_url,
                status=status,
                response_time_ms=response_time,
                status_code=response.status_code,
                ssl_valid=ssl_valid,
                ssl_expiry=ssl_expiry,
                server_info=server_info,
                capabilities=capabilities
            )

        except requests.exceptions.Timeout:
            response_time = (time.monotonic() - start_time) * 1000
            return EndpointHealth(
                endpoint_url=endpoint_url,
                status=EndpointStatus.TIMEOUT,
                response_time_ms=response_time,
                error_message=f"Request timeout after {config.timeout}s"
            )

        except requests.exceptions.HTTPError as e:
            response_time = (time.monotonic() - start_time) * 1000
            if e.response.status_code == 401:
                return EndpointHealth(
                    endpoint_url=endpoint_url,
                    status=EndpointStatus.AUTH_REQUIRED,
                    response_time_ms=response_time,
                    status_code=e.response.status_code,
                    error_message="Authentication required"
                )
            elif e.response.status_code == 403:
                return EndpointHealth(
                    endpoint_url=endpoint_url,
                    status=EndpointStatus.AUTH_FAILED,
                    response_time_ms=response_time,
                    status_code=e.response.status_code,
                    error_message="Authentication failed"
                )
            else:
                return EndpointHealth(
                    endpoint_url=endpoint_url,
                    status=EndpointStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    status_code=e.response.status_code,
                    error_message=f"HTTP error: {e.response.status_code}"
                )

        except requests.exceptions.SSLError as e:
            return EndpointHealth(
                endpoint_url=endpoint_url,
                status=EndpointStatus.SSL_ERROR,
                ssl_valid=False,
                error_message=f"SSL error: {str(e)}"
            )

        except Exception as e:
            return EndpointHealth(
                endpoint_url=endpoint_url,
                status=EndpointStatus.UNREACHABLE,
                error_message=f"Connection error: {str(e)}"
            )

    async def ping_multiple_async(
        self,
        endpoint_urls: List[str],
        check_query: bool = True,
        config: Optional[ConnectionConfig] = None
    ) -> List[EndpointHealth]:
        """
        Ping multiple endpoints concurrently

        Args:
            endpoint_urls: List of SPARQL endpoint URLs
            check_query: Whether to execute test queries
            config: Optional connection config

        Returns:
            List of EndpointHealth results
        """
        tasks = [
            self.ping_async(url, check_query, config)
            for url in endpoint_urls
        ]
        return await asyncio.gather(*tasks)

    def ping_multiple_sync(
        self,
        endpoint_urls: List[str],
        check_query: bool = True,
        config: Optional[ConnectionConfig] = None
    ) -> List[EndpointHealth]:
        """
        Ping multiple endpoints sequentially

        Args:
            endpoint_urls: List of SPARQL endpoint URLs
            check_query: Whether to execute test queries
            config: Optional connection config

        Returns:
            List of EndpointHealth results
        """
        return [
            self.ping_sync(url, check_query, config)
            for url in endpoint_urls
        ]

    def _determine_status(self, status_code: int, response_time_ms: float) -> EndpointStatus:
        """Determine endpoint health status"""
        if status_code == 200:
            if response_time_ms < 1000:
                return EndpointStatus.HEALTHY
            elif response_time_ms < 5000:
                return EndpointStatus.DEGRADED
            else:
                return EndpointStatus.UNHEALTHY
        elif 200 <= status_code < 300:
            return EndpointStatus.HEALTHY
        elif status_code == 401:
            return EndpointStatus.AUTH_REQUIRED
        elif status_code == 403:
            return EndpointStatus.AUTH_FAILED
        else:
            return EndpointStatus.UNHEALTHY

    def _extract_server_info(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Extract server information from headers"""
        info = {}

        # Common server headers
        server_headers = ['Server', 'X-Powered-By', 'X-SPARQL-Server']
        for header in server_headers:
            if header.lower() in [h.lower() for h in headers.keys()]:
                actual_key = [h for h in headers.keys() if h.lower() == header.lower()][0]
                info[header] = headers[actual_key]

        return info

    def _detect_capabilities(self, headers: Dict[str, str]) -> List[str]:
        """Detect endpoint capabilities from headers"""
        capabilities = []

        # Check for CORS support
        if any(h.lower().startswith('access-control-') for h in headers.keys()):
            capabilities.append('CORS')

        # Check for specific SPARQL features
        if 'X-SPARQL-Update' in headers or 'x-sparql-update' in [h.lower() for h in headers.keys()]:
            capabilities.append('UPDATE')

        return capabilities

    async def _check_ssl_async(
        self,
        endpoint_url: str,
        config: ConnectionConfig
    ) -> Tuple[bool, Optional[datetime]]:
        """Check SSL certificate validity (async)"""
        try:
            parsed = urlparse(endpoint_url)
            hostname = parsed.hostname
            port = parsed.port or 443

            # Create SSL context
            context = ssl.create_default_context()
            if not config.verify_ssl:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

            # Connect and get certificate
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(hostname, port, ssl=context),
                timeout=config.timeout
            )

            # Get certificate info
            ssl_object = writer.get_extra_info('ssl_object')
            cert = ssl_object.getpeercert()
            writer.close()
            await writer.wait_closed()

            if cert:
                # Parse expiry date
                expiry_str = cert.get('notAfter')
                if expiry_str:
                    expiry = datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y %Z')
                    return True, expiry

            return True, None

        except Exception as e:
            logger.debug(f"SSL check failed for {endpoint_url}: {e}")
            return False, None

    def _check_ssl_sync(
        self,
        endpoint_url: str,
        config: ConnectionConfig
    ) -> Tuple[bool, Optional[datetime]]:
        """Check SSL certificate validity (sync)"""
        try:
            parsed = urlparse(endpoint_url)
            hostname = parsed.hostname
            port = parsed.port or 443

            # Create SSL context
            context = ssl.create_default_context()
            if not config.verify_ssl:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

            # Connect and get certificate
            with ssl.create_connection((hostname, port), timeout=config.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()

            if cert:
                # Parse expiry date
                expiry_str = cert.get('notAfter')
                if expiry_str:
                    expiry = datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y %Z')
                    return True, expiry

            return True, None

        except Exception as e:
            logger.debug(f"SSL check failed for {endpoint_url}: {e}")
            return False, None

    def record_health(self, health: EndpointHealth, max_history: int = 100) -> None:
        """
        Record health check result in history

        Args:
            health: EndpointHealth result
            max_history: Maximum history entries to keep per endpoint
        """
        if health.endpoint_url not in self._health_history:
            self._health_history[health.endpoint_url] = deque(maxlen=max_history)

        self._health_history[health.endpoint_url].append(health)

    def get_health_history(self, endpoint_url: str) -> List[EndpointHealth]:
        """Get health check history for an endpoint"""
        return list(self._health_history.get(endpoint_url, []))

    def get_uptime_percentage(
        self,
        endpoint_url: str,
        time_window: Optional[timedelta] = None
    ) -> Optional[float]:
        """
        Calculate uptime percentage for an endpoint

        Args:
            endpoint_url: SPARQL endpoint URL
            time_window: Optional time window (default: all history)

        Returns:
            Uptime percentage (0-100) or None if no history
        """
        history = self.get_health_history(endpoint_url)
        if not history:
            return None

        # Filter by time window
        if time_window:
            cutoff = datetime.utcnow() - time_window
            history = [h for h in history if h.timestamp >= cutoff]

        if not history:
            return None

        # Calculate uptime
        healthy_count = sum(
            1 for h in history
            if h.status in [EndpointStatus.HEALTHY, EndpointStatus.DEGRADED]
        )

        return (healthy_count / len(history)) * 100

    def get_average_response_time(
        self,
        endpoint_url: str,
        time_window: Optional[timedelta] = None
    ) -> Optional[float]:
        """
        Calculate average response time for an endpoint

        Args:
            endpoint_url: SPARQL endpoint URL
            time_window: Optional time window (default: all history)

        Returns:
            Average response time in milliseconds or None
        """
        history = self.get_health_history(endpoint_url)
        if not history:
            return None

        # Filter by time window
        if time_window:
            cutoff = datetime.utcnow() - time_window
            history = [h for h in history if h.timestamp >= cutoff]

        if not history:
            return None

        # Calculate average (only for successful checks)
        response_times = [
            h.response_time_ms for h in history
            if h.response_time_ms is not None
        ]

        if not response_times:
            return None

        return sum(response_times) / len(response_times)

    async def close_async(self) -> None:
        """Close async resources"""
        await self.pool.close_async()

    def close_sync(self) -> None:
        """Close sync resources"""
        self.pool.close_sync()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close_sync()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_async()
