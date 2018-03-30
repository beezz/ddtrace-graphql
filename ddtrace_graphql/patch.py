"""
Tracing for the graphql-core library.

https://github.com/graphql-python/graphql-core
"""

# stdlib
import logging
import re

# 3p
import wrapt
import graphql
from graphql.language.ast import Document
from graphql.error import GraphQLError

# project
import ddtrace
from ddtrace.util import unwrap


logger = logging.getLogger(__name__)

_graphql = graphql.graphql

TYPE = 'graphql'
SERVICE = 'graphql'
QUERY = 'graphql.query'
ERRORS = 'graphql.errors'
INVALID = 'graphql.invalid'
DATA_EMPTY = 'graphql.data_empty'
RES = 'graphql.graphql'


class TracedGraphQLSchema(graphql.GraphQLSchema):
    def __init__(self, *args, **kwargs):
        if 'datadog_tracer' in kwargs:
            self.datadog_tracer = kwargs.pop('datadog_tracer')
            logger.debug(
                'For schema %s using own tracer %s',
                self, self.datadog_tracer)
        super(TracedGraphQLSchema, self).__init__(*args, **kwargs)


def patch():
    """
    Monkeypatches graphql-core library to trace graphql calls execution.
    """
    logger.debug('Patching `graphql.graphql` function.')
    wrapt.wrap_function_wrapper(graphql, 'graphql', _traced_graphql)


def unpatch():
    logger.debug('Unpatching `graphql.graphql` function.')
    unwrap(graphql, 'graphql')


def _resolve_query_res(query):
    # split by '(' for queries with arguments
    # split by '{' for queries without arguments
    # rather full query than empty resource name
    return re.split('[({]', query, 1)[0].strip() or query


def _traced_graphql(func, args, kwargs):
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

    with tracer.trace(
        RES,
        span_type=TYPE,
        service=SERVICE,
        resource=_resolve_query_res(query)
    ) as span:
        span.set_tag(QUERY, query)
        result = None
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # `span.error` must be integer
            span.error = int(result is None)
            if result is not None:
                span.set_tag(ERRORS, result.errors)
                span.set_metric(INVALID, int(result.invalid))
                span.set_metric(DATA_EMPTY, int(result.data is None))
                if result.errors and not result.invalid:
                    span.error = 1
                elif (
                    result.errors
                    and result.invalid
                    and len(result.errors) == 1
                    and not isinstance(result.errors[0], GraphQLError)
                ):
                    # based on execute_graphql implementation
                    # graphql/graphql.py#L41
                    span.error = 1


def traced_graphql(*args, **kwargs):
    return _traced_graphql(_graphql, args, kwargs)
