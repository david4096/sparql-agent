"""
Model Context Protocol (MCP) integration module.

This module provides MCP server implementation for AI agent workflows.

The MCP server exposes SPARQL operations, endpoint discovery, query generation,
validation, and ontology lookup capabilities to AI agents and other MCP clients.

Example:
    Run the MCP server:
    >>> from sparql_agent.mcp import MCPServer, MCPServerConfig
    >>> config = MCPServerConfig(name="my-sparql-server")
    >>> server = MCPServer(config=config)
    >>> await server.run()
"""

try:
    from .server import (
        MCPServer,
        MCPServerConfig,
        MCPServerCapability,
        main,
    )
    from .handlers import (
        RequestRouter,
        RequestType,
        ResponseStatus,
        MCPRequest,
        MCPResponse,
        ProgressUpdate,
        RateLimitConfig,
        RateLimiter,
        BaseHandler,
        QueryHandler,
        DiscoveryHandler,
        GenerationHandler,
        ValidationHandler,
        FormattingHandler,
        OntologyHandler,
        create_router,
        handle_request,
    )
    from .middleware import (
        ErrorMiddleware,
        ErrorMiddlewareConfig,
        LoggingMiddleware,
        LoggingMiddlewareConfig,
        ValidationMiddleware,
        ValidationMiddlewareConfig,
        MiddlewareChain,
        LogLevel,
    )
    __all__ = [
        # Server
        "MCPServer",
        "MCPServerConfig",
        "MCPServerCapability",
        "main",
        # Handlers
        "RequestRouter",
        "RequestType",
        "ResponseStatus",
        "MCPRequest",
        "MCPResponse",
        "ProgressUpdate",
        "RateLimitConfig",
        "RateLimiter",
        "BaseHandler",
        "QueryHandler",
        "DiscoveryHandler",
        "GenerationHandler",
        "ValidationHandler",
        "FormattingHandler",
        "OntologyHandler",
        "create_router",
        "handle_request",
        # Middleware
        "ErrorMiddleware",
        "ErrorMiddlewareConfig",
        "LoggingMiddleware",
        "LoggingMiddlewareConfig",
        "ValidationMiddleware",
        "ValidationMiddlewareConfig",
        "MiddlewareChain",
        "LogLevel",
    ]
except ImportError:
    # MCP SDK not available, try to import handlers and middleware only
    try:
        from .handlers import (
            RequestRouter,
            RequestType,
            ResponseStatus,
            MCPRequest,
            MCPResponse,
            ProgressUpdate,
            RateLimitConfig,
            RateLimiter,
            BaseHandler,
            QueryHandler,
            DiscoveryHandler,
            GenerationHandler,
            ValidationHandler,
            FormattingHandler,
            OntologyHandler,
            create_router,
            handle_request,
        )
        from .middleware import (
            ErrorMiddleware,
            ErrorMiddlewareConfig,
            LoggingMiddleware,
            LoggingMiddlewareConfig,
            ValidationMiddleware,
            ValidationMiddlewareConfig,
            MiddlewareChain,
            LogLevel,
        )
        __all__ = [
            "RequestRouter",
            "RequestType",
            "ResponseStatus",
            "MCPRequest",
            "MCPResponse",
            "ProgressUpdate",
            "RateLimitConfig",
            "RateLimiter",
            "BaseHandler",
            "QueryHandler",
            "DiscoveryHandler",
            "GenerationHandler",
            "ValidationHandler",
            "FormattingHandler",
            "OntologyHandler",
            "create_router",
            "handle_request",
            "ErrorMiddleware",
            "ErrorMiddlewareConfig",
            "LoggingMiddleware",
            "LoggingMiddlewareConfig",
            "ValidationMiddleware",
            "ValidationMiddlewareConfig",
            "MiddlewareChain",
            "LogLevel",
        ]
    except ImportError:
        # Neither available
        __all__ = []
