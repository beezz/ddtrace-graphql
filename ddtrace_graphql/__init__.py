"""
To trace all GraphQL requests, patch the library like so::

    from ddtrace_graphql import patch
    patch()

    from graphql import graphql
    result = graphql(schema, query)


If you do not want to monkeypatch ``graphql.graphql`` function or want to trace
only certain calls you can use the ``traced_graphql`` function::

    from ddtrace_graphql import traced_graphql
    traced_graphql(schema, query)
"""


from ddtrace.contrib import require_modules

required_modules = ['graphql']

with require_modules(required_modules) as missing_modules:
    if not missing_modules:
        from .base import (
            TracedGraphQLSchema, traced_graphql,
            TYPE, SERVICE, QUERY, ERRORS, INVALID, RES_NAME, DATA_EMPTY,
            CLIENT_ERROR
        )
        from .patch import patch, unpatch
        __all__ = [
            'TracedGraphQLSchema',
            'patch', 'unpatch', 'traced_graphql',
            'TYPE', 'SERVICE', 'QUERY', 'ERRORS', 'INVALID',
            'RES_NAME', 'DATA_EMPTY', 'CLIENT_ERROR',
        ]

