"""Test the base classes for the pipeline."""

import dataclasses
import unittest
from typing import Type, List, Dict, Optional

import dacite

from doc_scraper.pipeline import generic


@dataclasses.dataclass(kw_only=True)
class SampleConfig():
    """Sample config to test the builder."""

    attr_a: int = 10
    attr_type: Type[object] = str


@dataclasses.dataclass(kw_only=True)
class SampleConfigWithCmdline(generic.CmdLineInjectable):
    """Sample config that supports passing cmdline params."""

    attr_a: str = ''
    attr_b: str = ''

    def set_commandline_args(self, *args: str, **kwargs: str) -> None:
        """Update attribs from command line."""
        self.attr_a = args[0]
        self.attr_b = kwargs.get('b', '')


class SimpleListResult(generic.CmdLineInjectable):
    """Type for a sink instance, supporting command line params."""

    def __init__(self, *args: str, **kwargs: str) -> None:
        """Create an instance."""
        self.args: List[str] = list(args)
        self.kwargs: Dict[str, str] = dict(kwargs)

    def set_commandline_args(self, *args: str, **kwargs: str) -> None:
        """Add command line params to the instance."""
        self.args.extend(args)
        self.kwargs.update(kwargs)


class TestGenericBuilder(unittest.TestCase):
    """Test the generic verion of the builder class."""

    def setUp(self) -> None:
        """Provide a default builder instance."""
        super().setUp()
        self.builder = generic.GenericBuilder[int]()

    def test_simple(self):
        """Test simple registration and instantiation."""
        self.builder.register('x', lambda n: int(n + 1))

        self.assertEqual(23, self.builder.create_instance('x', 22))

    def test_explicit_type(self):
        """Test registration with explicit type."""
        self.builder.register('x', lambda n: int(n[0] + 1), list)

        self.assertEqual(23, self.builder.create_instance('x', [22]))

    def test_with_hint(self):
        """Test registration from function type hints."""

        def builder_func(config_str: str) -> int:
            return int(config_str) + 1

        self.builder.register('x', builder_func)

        self.assertEqual(23, self.builder.create_instance('x', '22'))

    def test_no_arg(self):
        """Test the no arg version of the builder function."""

        def builder_func() -> int:
            return 111

        self.builder.register('x', builder_func)

        self.assertEqual(111, self.builder.create_instance('x'))

    def test_fail_bad_config_type(self):
        """Test that passing bad argument types causes an exception."""

        def builder_func(i: int) -> int:
            return i + 1

        self.builder.register('x', builder_func)

        self.assertRaisesRegex(
            TypeError, r'Expected.*\'int\'.*',
            lambda: self.builder.create_instance('x', 'should be int'))

    def test_fail_arg_on_no_arg(self):
        """Test that passing an arg to a no-arg builder fails."""

        def builder_func() -> int:
            return 111

        self.builder.register('x', builder_func)

        self.assertRaisesRegex(
            TypeError, r'Does not accept args.*',
            lambda: self.builder.create_instance('x', 'should be no arg'))

    def test_fail_bad_kind(self):
        """Test that bad builder kinds cause an exception."""
        self.builder.register('x', lambda n: int(n + 1))

        self.assertRaisesRegex(
            ValueError, r'Could not find.*another_key.*',
            lambda: self.builder.create_instance('another_key'))

    def test_convert_dict(self):
        """Test construction of the config from dict."""

        def builder_func(config: SampleConfig) -> int:
            return config.attr_a + 1

        self.builder.register('x', builder_func)

        self.assertEqual(23, self.builder.create_instance('x', {'attr_a': 22}))

    def test_convert_dict_optional(self):
        """Test construction of the config from dict."""

        def builder_func(config: Optional[SampleConfig]) -> int:
            if config is None:
                return 9999
            return config.attr_a + 1

        self.builder.register('x', builder_func)

        self.assertEqual(23, self.builder.create_instance('x', {'attr_a': 22}))

    def test_convert_dict_optional_none(self):
        """Test construction of the config from dict."""

        def builder_func(config: Optional[SampleConfig]) -> int:
            if config is None:
                return 9999
            return config.attr_a + 1

        self.builder.register('x', builder_func)

        self.assertEqual(9999, self.builder.create_instance('x', None))

    def test_convert_dict_optional_none_with_default(self):
        """Test construction of the config from dict."""

        def builder_func(config: Optional[SampleConfig]) -> int:
            if config is None:
                return 9999
            return config.attr_a + 1

        self.builder.register('x',
                              builder_func,
                              default_factory=lambda: SampleConfig(attr_a=100))

        self.assertEqual(101, self.builder.create_instance('x', None))

    def test_convert_dict_optional_bad_type(self):
        """Test construction of the config from dict."""

        def builder_func(config: Optional[SampleConfig]) -> int:
            if config is None:
                return 9999
            return config.attr_a + 1

        self.builder.register('x', builder_func)

        self.assertRaisesRegex(
            dacite.WrongTypeError, '.*',
            lambda: self.builder.create_instance('x', {'attr_a': 'str'}))

    def test_type_from_str(self):
        """Test that dacite is able to assign type fields from strings."""

        def builder_func(config: SampleConfig) -> int:
            return 11 if config.attr_type == float else 33

        self.builder.register('x', builder_func)

        self.assertEqual(
            11, self.builder.create_instance('x', {'attr_type': 'float'}))

    def test_type_from_str_not_found(self):
        """Test that unknown type strings cause an exception."""

        def builder_func(config: SampleConfig) -> int:
            return 11 if config.attr_type == float else 33

        self.builder.register('x', builder_func)

        self.assertRaisesRegex(
            TypeError, r'Could not find type for whatever', lambda: self.
            builder.create_instance('x', {'attr_type': 'whatever'}))

    def test_cmdline_args_instance(self):
        """Test if command line args are passed to the new instance."""
        simple_builder = generic.GenericBuilder[SimpleListResult]()
        simple_builder.register('x', lambda s: SimpleListResult(s, k0=s, k1=s))
        simple_builder.set_commandline_args('arg1', 'arg2', k1='a1', k2='a2')

        result = simple_builder.create_instance('x', 'inst0')

        self.assertEqual(['inst0', 'arg1', 'arg2'], result.args)
        self.assertEqual({
            'k0': 'inst0',
            'k1': 'a1',
            'k2': 'a2'
        }, result.kwargs)

    def test_cmdline_args_config(self):
        """Test that the command line args are passd to the config."""
        simple_builder = generic.GenericBuilder[str]()

        def _build_instance(config: SampleConfigWithCmdline) -> str:
            return f'{config.attr_a},{config.attr_b}'

        simple_builder.register('x', _build_instance)
        simple_builder.set_commandline_args('arg0', b='a0')

        result = simple_builder.create_instance('x', SampleConfigWithCmdline())

        self.assertEqual('arg0,a0', result)
