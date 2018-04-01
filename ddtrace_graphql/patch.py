"""
Tracing for the graphql-core library.

https://github.com/graphql-python/graphql-core
"""

# stdlib
import functools
import json
import logging
import os
import re

# 3p
import wrapt
import graphql
from graphql.language.ast import Document
from graphql.error import GraphQLError, format_error

# project
import ddtrace
from ddtrace.util import unwrap


logger = logging.getLogger(__name__)

_graphql = graphql.graphql

TYPE = 'graphql'
QUERY = 'query'
ERRORS = 'errors'
INVALID = 'invalid'
DATA_EMPTY = 'data_empty'
RES_NAME = 'graphql.graphql'
#
SERVICE_ENV_VAR = 'DDTRACE_GRAPHQL_SERVICE'
SERVICE = 'graphql'


class TracedGraphQLSchema(graphql.GraphQLSchema):
    def __init__(self, *args, **kwargs):
        if 'datadog_tracer' in kwargs:
            self.datadog_tracer = kwargs.pop('datadog_tracer')
            logger.debug(
                'For schema %s using own tracer %s',
                self, self.datadog_tracer)
        super(TracedGraphQLSchema, self).__init__(*args, **kwargs)


def patch(span_kwargs=None):
    """
    Monkeypatches graphql-core library to trace graphql calls execution.
    """
    logger.debug('Patching `graphql.graphql` function.')

    def wrapper(func, _, args, kwargs):
        return _traced_graphql(func, args, kwargs, span_kwargs=span_kwargs)

    wrapt.wrap_function_wrapper(graphql, 'graphql', wrapper)


def unpatch():
    logger.debug('Unpatching `graphql.graphql` function.')
    unwrap(graphql, 'graphql')


def _is_server_error(result):
    return bool(
        (
            result.errors
            and not result.invalid
        )
        or
        (
            result.errors
            and result.invalid
            and len(result.errors) == 1
            and not isinstance(result.errors[0], GraphQLError)
        )
    )


def _format_errors(errors):
    return json.dumps(
        [
            # fix for graphql-core==1.x
            format_error(err) if hasattr(err, 'message') else str(err)
            for err in errors
        ],
        indent=2,
    )


def _resolve_query_res(query):
    # split by '(' for queries with arguments
    # split by '{' for queries without arguments
    # rather full query than empty resource name
    return re.split('[({]', query, 1)[0].strip() or query


def _traced_graphql(func, args, kwargs, span_kwargs=None):
    """
    Wrapper for graphql.graphql function.
    """

    schema = args[0]

    # get the query as a string
    if len(args) > 1:
        request_string = args[1]
    else:
        request_string = kwargs.get('request_string')

    if isinstance(request_string, Document):
        query = request_string.loc.source.body
    else:
        query = request_string

    # allow schemas their own tracer with fall-back to the global
    tracer = getattr(schema, 'datadog_tracer', ddtrace.tracer)

    if not tracer.enabled:
        return func(*args, **kwargs)

    _span_kwargs = {
        'name': RES_NAME,
        'span_type': TYPE,
        'service': os.getenv(SERVICE_ENV_VAR, SERVICE),
        'resource': _resolve_query_res(query)
    }
    _span_kwargs.update(span_kwargs or {})

    with tracer.trace(**_span_kwargs) as span:
        span.set_tag(QUERY, query)
        result = None
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # `span.error` must be integer
            span.error = int(result is None)

            if result is not None:

                result.errors and span.set_tag(
                    ERRORS, _format_errors(result.errors))
                span.error = int(_is_server_error(result))

                span.set_metric(INVALID, int(result.invalid))
                span.set_metric(DATA_EMPTY, int(result.data is None))


def traced_graphql(*args, span_kwargs=None, **kwargs):
    return _traced_graphql(_graphql, args, kwargs, span_kwargs=span_kwargs)

