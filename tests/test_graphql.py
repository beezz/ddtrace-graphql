from graphql import (
    GraphQLObjectType,
    GraphQLField,
    GraphQLString
)
import graphql
from graphql.execution import ExecutionResult
from graphql.language.source import Source as GraphQLSource
from graphql.language.parser import parse as graphql_parse
from wrapt import FunctionWrapper
from ddtrace.encoding import JSONEncoder, MsgpackEncoder
from ddtrace.tracer import Tracer
from ddtrace.writer import AgentWriter


from ddtrace_graphql import (
    TracedGraphQLSchema,
    patch, unpatch, traced_graphql,
    QUERY, ERRORS, INVALID, DATA_EMPTY
)
from ddtrace_graphql.patch import _traced_graphql


class DummyWriter(AgentWriter):
    """
    # NB: This is coy fo DummyWriter class from ddtraces tests suite

    DummyWriter is a small fake writer used for tests. not thread-safe.
    """

    def __init__(self):
        # original call
        super(DummyWriter, self).__init__()
        # dummy components
        self.spans = []
        self.traces = []
        self.services = {}
        self.json_encoder = JSONEncoder()
        self.msgpack_encoder = MsgpackEncoder()

    def write(self, spans=None, services=None):
        if spans:
            # the traces encoding expect a list of traces so we
            # put spans in a list like we do in the real execution path
            # with both encoders
            trace = [spans]
            self.json_encoder.encode_traces(trace)
            self.msgpack_encoder.encode_traces(trace)
            self.spans += spans
            self.traces += trace

        if services:
            self.json_encoder.encode_services(services)
            self.msgpack_encoder.encode_services(services)
            self.services.update(services)

    def pop(self):
        # dummy method
        s = self.spans
        self.spans = []
        return s

    def pop_traces(self):
        # dummy method
        traces = self.traces
        self.traces = []
        return traces

    def pop_services(self):
        # dummy method
        s = self.services
        self.services = {}
        return s


def get_dummy_tracer():
    tracer = Tracer()
    tracer.writer = DummyWriter()
    return tracer


def get_traced_schema(tracer=None, query=None, resolver=None):
    resolver = resolver or (lambda *_: 'world')
    tracer = tracer or get_dummy_tracer()
    query = query or GraphQLObjectType(
        name='RootQueryType',
        fields={
            'hello': GraphQLField(
                type=GraphQLString,
                resolver=resolver,
            )
        }
    )
    return tracer, TracedGraphQLSchema(query=query, datadog_tracer=tracer)


class TestGraphQL:

    def test_unpatch(self):
        gql = graphql.graphql
        unpatch()
        assert gql == graphql.graphql
        assert not isinstance(graphql.graphql, FunctionWrapper)
        patch()
        assert isinstance(graphql.graphql, FunctionWrapper)
        unpatch()
        assert gql == graphql.graphql

    def test_invalid(self):
        tracer, schema = get_traced_schema()
        result = traced_graphql(schema, '{ hello world }')
        span = tracer.writer.pop()[0]
        assert span.get_metric(INVALID) == int(result.invalid)
        assert span.get_metric(DATA_EMPTY) == 1
        assert span.error == 0

        result = traced_graphql(schema, '{ hello }')
        span = tracer.writer.pop()[0]
        assert span.get_metric(INVALID) == int(result.invalid)
        assert span.error == 0

    def test_unhandled_exception(self, monkeypatch):

        def exc_resolver(*args):
            raise Exception('Testing stuff')

        tracer, schema = get_traced_schema(resolver=exc_resolver)
        result = traced_graphql(schema, '{ hello }')
        span = tracer.writer.pop()[0]
        assert span.get_metric(INVALID) == 0
        assert span.error == 1
        assert span.get_metric(DATA_EMPTY) == 0

        def _tg(*args, **kwargs):
            def func(*args, **kwargs):
                return ExecutionResult(
                    errors=[Exception()],
                    invalid=True,
                )
            return _traced_graphql(func, args, kwargs)

        tracer, schema = get_traced_schema(resolver=exc_resolver)
        result = _tg(schema, '{ hello }')

        span = tracer.writer.pop()[0]
        assert span.get_metric(INVALID) == 1
        assert span.error == 1
        assert span.get_metric(DATA_EMPTY) == 1


    def test_request_string_resolve(self):
        query = '{ hello }'

        # string as args[1]
        tracer, schema = get_traced_schema()
        traced_graphql(schema, query)
        span = tracer.writer.pop()[0]
        assert span.get_tag(QUERY) == query

        # string as kwargs.get('request_string')
        tracer, schema = get_traced_schema()
        traced_graphql(schema, request_string=query)
        span = tracer.writer.pop()[0]
        assert span.get_tag(QUERY) == query

        # ast as args[1]
        tracer, schema = get_traced_schema()
        ast_query = graphql_parse(GraphQLSource(query, 'Test Request'))
        traced_graphql(schema, ast_query)
        span = tracer.writer.pop()[0]
        assert span.get_tag(QUERY) == query

        # ast as kwargs.get('request_string')
        tracer, schema = get_traced_schema()
        ast_query = graphql_parse(GraphQLSource(query, 'Test Request'))
        traced_graphql(schema, request_string=ast_query)
        span = tracer.writer.pop()[0]
        assert span.get_tag(QUERY) == query

    @staticmethod
    def test_query_tag():
        query = '{ hello }'
        tracer, schema = get_traced_schema()
        traced_graphql(schema, query)
        span = tracer.writer.pop()[0]
        assert span.get_tag(QUERY) == query

        # test query also for error span, just in case
        query = '{ hello world }'
        tracer, schema = get_traced_schema()
        traced_graphql(schema, query)
        span = tracer.writer.pop()[0]
        assert span.get_tag(QUERY) == query

    @staticmethod
    def test_errors_tag():
        query = '{ hello world }'
        tracer, schema = get_traced_schema()
        result = traced_graphql(schema, query)
        span = tracer.writer.pop()[0]
        assert span.get_tag(ERRORS)
        assert str(result.errors) == span.get_tag(ERRORS)

    @staticmethod
    def test_resource():
        query = '{ hello world }'
        tracer, schema = get_traced_schema()
        traced_graphql(schema, query)
        span = tracer.writer.pop()[0]
        assert span.resource == query

        query = 'mutation fnCall(args: Args) { }'
        traced_graphql(schema, query)
        span = tracer.writer.pop()[0]
        assert span.resource == 'mutation fnCall'

        query = 'mutation fnCall { }'
        traced_graphql(schema, query)
        span = tracer.writer.pop()[0]
        assert span.resource == 'mutation fnCall'

    @staticmethod
    def test_tracer_disabled():
        query = '{ hello world }'
        tracer, schema = get_traced_schema()
        tracer.enabled = False
        traced_graphql(schema, query)
        assert not tracer.writer.pop()
