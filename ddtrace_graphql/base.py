import logging
import os

import ddtrace
import graphql
from ddtrace.constants import ERROR_MSG, ERROR_STACK, ERROR_TYPE

from ddtrace_graphql import utils

logger = logging.getLogger(__name__)
_graphql = graphql.graphql


TYPE = 'graphql'
QUERY = 'query'
ERRORS = 'errors'
INVALID = 'invalid'
CLIENT_ERROR = 'client_error'
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


def traced_graphql_wrapped(
    func,
    args,
    kwargs,
    span_kwargs=None,
    span_callback=None,
    ignore_exceptions=(),
):
    """
    Wrapper for graphql.graphql function.
    """
    # allow schemas their own tracer with fall-back to the global
    schema = args[0]
    tracer = getattr(schema, 'datadog_tracer', ddtrace.tracer)

    if not tracer.enabled:
        return func(*args, **kwargs)

    query = utils.get_query_string(args, kwargs)

    _span_kwargs = {
        'name': RES_NAME,
        'span_type': TYPE,
        'service': os.getenv(SERVICE_ENV_VAR, SERVICE),
        'resource': utils.resolve_query_res(query)
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

                span.error = 0
                if result.errors:
                    span.set_tag(
                        ERRORS,
                        utils.format_errors(result.errors))
                    span.set_tag(
                        ERROR_STACK,
                        utils.format_errors_traceback(result.errors))
                    span.set_tag(
                        ERROR_MSG,
                        utils.format_errors_msg(result.errors))
                    span.set_tag(
                        ERROR_TYPE,
                        utils.format_errors_type(result.errors))

                    span.error = int(utils.is_server_error(
                        result,
                        ignore_exceptions,
                    ))

                span.set_metric(
                    CLIENT_ERROR,
                    int(bool(not span.error and result.errors))
                )
                span.set_metric(INVALID, int(result.invalid))
                span.set_metric(DATA_EMPTY, int(result.data is None))

            if span_callback is not None:
                span_callback(result=result, span=span)


def traced_graphql(
    *args,
    span_kwargs=None,
    span_callback=None,
    ignore_exceptions=(),
    **kwargs
):
    return traced_graphql_wrapped(
        _graphql, args, kwargs,
        span_kwargs=span_kwargs,
        span_callback=span_callback,
        ignore_exceptions=ignore_exceptions
    )
