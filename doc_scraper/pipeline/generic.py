"""Implementation of a generic builder base class for all builders."""

import inspect
import dataclasses
import builtins
from typing import (
    Callable,
    Any,
    Dict,
    Type,
    Optional,
    cast,
    TypeVar,
    Tuple,
    Generic,
    Union,
    Protocol,
    runtime_checkable,
    Sequence,
    Mapping,
    get_args,
    get_origin,
)

import dacite

from doc_scraper import help_docs
from doc_scraper import doc_struct
from doc_scraper.basic_transforms import tags_basic

HelpDocArg = Optional[Union[str, help_docs.BuilderKindHelp]]


@runtime_checkable
class CmdLineInjectable(Protocol):
    """Interface to pass command line details to an instance/config."""

    def set_commandline_args(self, *args: str, **kwargs: str) -> None:
        """Provide command line arguments to update the object."""


@dataclasses.dataclass(kw_only=True)
class BuilderConfig():
    """Generic config to create an instance from a builder."""

    # Identify the builder to be used.
    kind: str

    # Additional configuration to pass to the builder.
    config: Any = None


_T = TypeVar('_T')


class _BuilderData(Generic[_T]):
    """Generic implementation of the builder data, stored in builders.

    Is built around the builder function, adding metadata to handle
    the passed arguments and to support help_docs.
    """

    def get_arg_type(
        self,
        func: Callable[..., _T],
    ) -> Tuple[bool, Optional[Type[object]]]:
        """Discover if a callable has an argument and determine its type.

        Args:
            func: The callable to inspect.

        Returns:
            Tupple containing if a single parameter is required and
                if so, what type the parameter has. If the actual type
                of the argument cannot be determined, e.g. since a lambda
                expression was passed, (True,None) is returned.
        """
        signature = inspect.signature(func)
        if not signature.parameters:
            return (False, None)

        args = list(signature.parameters.items())
        if len(args) == 0:
            return (False, None)
        if len(args) != 1:
            raise ValueError(f'Expecting max one arg in hints: {signature}')
        arg_type = args[0][1].annotation
        if arg_type == inspect.Parameter.empty:
            arg_type = None
        return (True, arg_type)

    def __init__(self,
                 dacite_config: dacite.Config,
                 kind: str,
                 build_func: Callable[..., _T],
                 config_type: Optional[Type[object]] = None,
                 default_factory: Optional[Callable[[], Any]] = None,
                 help_doc: HelpDocArg = None) -> None:
        """Create an instance.

        Args:
            dacite_config: Used when an instance is created from a dict as
                argument, to configure Dacite, which is used to convert the
                arg into a dataclass object.
            kind: String to identify the the builder function.
            build_func: The actual build function used when registering the
                builder along with the kind.
            config_type: Optionaly allows to override the type of the first
                arg of build_function, when not available, e.g. in lambdas.
            default_factory: Optionaly add a factory function that creates
                a config object when one is expected but not passed when
                creating the instance.
            help_doc: Documentation details.
        """
        self._dacite_config = dacite_config
        self.kind = kind
        self.build_func = build_func
        self.default_factory = default_factory

        self.has_arg, target_config_type = self.get_arg_type(build_func)
        if config_type is not None:
            target_config_type = config_type
        self.config_type = target_config_type

        self._help_doc = help_doc

    def _get_arg_type(self) -> Optional[Type[object]]:
        """Get the arg type, considering optional types."""
        arg_type = self.config_type

        if get_origin(arg_type) is Union:
            # Take the first non-None arg
            union_args: Sequence[Type[object]] = get_args(arg_type)
            for union_arg in union_args:
                if union_arg is not type(None):  # noqa: E721
                    arg_type = union_arg
                    break
        return arg_type

    def __call__(self, arg: Any) -> _T:
        """Handle argument details then call the original build function."""
        if not self.has_arg:
            if arg is not None:
                raise TypeError(f'Does not accept args: {self.build_func}')
            return self.build_func()

        arg_type = self._get_arg_type()

        if arg_type is None:
            # No better information available, just call
            return self.build_func(arg)

        if isinstance(arg, dict):
            arg = dacite.from_dict(
                config=self._dacite_config,
                data=cast(Dict[str, Any], arg),
                data_class=arg_type,
            )

        if arg is None:
            if self.default_factory:
                arg = self.default_factory()

        if arg is not None and not isinstance(arg, arg_type):
            raise TypeError(f'Expected type {self.config_type} for' +
                            f' {self.build_func}. Got {arg}')

        return self.build_func(arg)

    @property
    def help_doc(self) -> help_docs.BuilderKindHelp:
        """Provide the help doc for the builder, including registrations."""
        if isinstance(self._help_doc, help_docs.BuilderKindHelp):
            return self._help_doc

        if self.has_arg:
            return help_docs.BuilderKindHelp.from_config_class(
                self.kind, self._help_doc or '', self.config_type)

        return help_docs.BuilderKindHelp(self.kind, self._help_doc or '')


class GenericBuilder(Generic[_T]):
    """Implementation of a builder for a generic type.

    Provides a registry of different builders, identified by string (`kind`).
    The instances then are created by a Callable that accepts an optional
    config and returns an instance of the type to be built.

    Attributes:
        dacite_config: The config used when creating instances with dict
            structures passed as argument. Mainly to configure the needed
            type conversions.
        modules: Additional module instances. Used during conversion of
            `type` instances in Dacite. The conversion is performed from
            strings, looking up the type to be returned from the modules
            listed in this attribute.
    """

    def __init__(self) -> None:
        """Create an instance."""
        self._registry: Dict[str, _BuilderData[_T]] = dict()

        self.dacite_config = dacite.Config(
            strict=True,
            strict_unions_match=True,
            type_hooks={
                tags_basic.StringMatcher:
                    tags_basic.StringMatcher,
                tags_basic.MappingMatcher:
                    lambda data: tags_basic.MappingMatcher(**data),
                tags_basic.TypeMatcher:
                    lambda data: tags_basic.TypeMatcher.from_strings(*data),
            })

        self.modules = [builtins, doc_struct]
        self._cmdline_args: Sequence[str] = []
        self._cmdline_kwargs: Mapping[str, str] = {}

    def set_commandline_args(self, *args: str, **kwargs: str) -> None:
        """Set the command line arguments to be used during instance creation.

        If the passed config or the created instance implements the protocol
        CmdLineInjectable, the passed command line details are injected into
        the config or new instance.
        """
        self._cmdline_args = args
        self._cmdline_kwargs = kwargs

    def register(self,
                 kind: str,
                 build_func: Callable[..., _T],
                 config_type: Optional[Type[object]] = None,
                 default_factory: Optional[Callable[[], Any]] = None,
                 help_doc: HelpDocArg = None) -> None:
        """Register a new kind of builder.

        Args:
            kind: string to build instances of this _kind_
            build_func: Callable that creates the instance, optionally
                accepting a parameter to configure the creation.
            config_type: Optional indication of the type the config parameter
                for build_func has.
            default_factory: Used to build config arguments when needed but
                not passed during create_instance.
            help_doc: Documentation for the kind of builder.
        """
        if kind in self._registry:
            raise ValueError(f'Kine {kind} already registerd.')

        self._registry[kind] = _BuilderData[_T](self.dacite_config, kind,
                                                build_func, config_type,
                                                default_factory, help_doc)

    def create_instance(self,
                        kind_or_config: Union[str, BuilderConfig],
                        config: Any = None) -> _T:
        """Create an instance.

        Injects command line args if to config or instance if they inherit
        from CmdLineInjectable.

        Args:
            kind: The kind of build function to use.
            config: Optional config instance. Can be a dict, in which case
                a dacite conversion to the registerd config_type is atempted.

        Returns:
            New instance.
        """
        if isinstance(kind_or_config, BuilderConfig):
            return self.create_instance(kind_or_config.kind,
                                        kind_or_config.config)
        kind: str = kind_or_config
        if kind not in self._registry:
            available_items = list(self._registry.keys())
            raise ValueError(f'Could not find kind {kind} in registry. ' +
                             f'Available: {available_items}')
        builder_func = self._registry[kind]

        if isinstance(config, CmdLineInjectable):
            config.set_commandline_args(*self._cmdline_args,
                                        **self._cmdline_kwargs)
        instance = builder_func(config)
        if isinstance(instance, CmdLineInjectable):
            instance.set_commandline_args(*self._cmdline_args,
                                          **self._cmdline_kwargs)

        return instance

    @property
    def help_doc(self) -> help_docs.BuilderHelp:
        """Provide help documentation."""
        return help_docs.BuilderHelp(
            sorted((data.help_doc for data in self._registry.values()),
                   key=lambda item: item.kind))
