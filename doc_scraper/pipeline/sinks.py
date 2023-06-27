"""Implementation of basic sink(output) functions and their builder."""

import dataclasses
import json
import sys
import logging

from typing import (
    Iterable,
    Callable,
    TextIO,
    Union,
    Type,
    Optional,
    Any,
    Dict,
    Sequence,
    Mapping,
)

from doc_scraper import doc_struct
from doc_scraper import help_docs

from . import generic

OutputConfig = generic.BuilderConfig

# The types of arguments that can be sent to a sink.
SinkItemType = Union[doc_struct.Element, Sequence[Any], Mapping[str, Any]]

# Function type representing the output of a single document.
# SinkBuilder registers this type to internally process individual docs.
OutputFunction = Callable[[SinkItemType], None]

# Function type representing a sink, i.e. a function that can store an
# iterable of items.
SinkFunction = Callable[[Iterable[SinkItemType]], None]


def _convert_to_string(document: SinkItemType) -> str:
    """Convert a doc struct to JSON, then to string."""
    if isinstance(document, doc_struct.Element):
        document = doc_struct.as_dict(document)
    return json.dumps(document, indent=4)


class FileOutputBase():
    """Base class for file based output.

    Includes the necessary conversion to string.
    Actual output is done in a subclass.
    """

    def __init__(self) -> None:
        """Create an instance."""
        self.output_index: int = 0

    def _perform_output(self,
                        as_string: str,
                        context: Optional[Dict[str, Any]] = None) -> None:
        """Perform the output operation, once converted to string.

        e.g. writing to file,...

        In addition to the context parameter, the class keeps track of the
        document number in `self.output_index`, which is increased each time
        __call__() is executed.

        Args:
            as_string: The document, already serialized to string.
            context: Provides the doc structure `attrs` dict for context.

        Raises:
            NotImplementedError: Needs to be overwritten in subclass.
        """
        raise NotImplementedError('Implemented in subclasses')

    def __call__(self, item: Any) -> Any:
        """Process the passed item for output."""
        context: Dict[str, Any] = {}
        if isinstance(item, doc_struct.Element):
            context.update(item.attrs)
        as_string = _convert_to_string(item)
        logging.debug('Writing document %d: %s', self.output_index,
                      repr(as_string))
        self._perform_output(as_string, context)
        self.output_index += 1


@dataclasses.dataclass(kw_only=True)
class SingleFileConfig():
    """Configuration to write to a single file, concatenated."""

    output_file: Optional[str] = dataclasses.field(
        default='-',
        metadata={
            'help_text': 'Provide a filename to write to. Default: stdout',
            'help_samples': ['/tmp/file.json'],  # nosec
        })


class SingleFileOutput(FileOutputBase):
    """Output to a single file/filehandle."""

    def __init__(self,
                 output_file: Optional[Union[str, TextIO]] = None,
                 separator: Optional[str] = None) -> None:
        r"""Create an instance.

        Args;
            output_file: file(TextIO) instance to use for output.
                Default: stdout.
            separator: Separator string to add between each output file.
                Default: "\n---\n'
        """
        super().__init__()
        if separator is None:
            separator = '\n---\n'
        if output_file is None:
            output_file = sys.stdout
        self.separator = separator
        self.output_file = output_file

    def _perform_output(self,
                        as_string: str,
                        context: Optional[Dict[str, Any]] = None) -> None:
        """Append the converted doc to the filehandle."""
        logging.debug('Writing to file %s', str(self.output_file))
        if isinstance(self.output_file, str):
            with open(self.output_file,
                      'w' if self.output_index == 0 else 'a',
                      encoding='utf-8') as output_file:
                if self.output_index > 0:
                    output_file.write(self.separator)
                output_file.write(as_string)
        else:
            if self.output_index > 0:
                self.output_file.write(self.separator)
            self.output_file.write(as_string)
            self.output_file.flush()

    @classmethod
    def from_config(
            cls,
            config: Optional[SingleFileConfig] = None) -> 'SingleFileOutput':
        """Create an instance from a config object."""
        if config is None:
            config = SingleFileConfig()

        if config.output_file is None or config.output_file == '-':
            output_file = sys.stdout
        else:
            output_file = open(config.output_file, 'w', encoding='utf-8')
        return SingleFileOutput(output_file)


@dataclasses.dataclass(kw_only=True)
class TemplatedPathConfig():
    """Configuration for temlate-based file outpout."""

    output_path_template: str = dataclasses.field(
        metadata={
            'help_text':
                'Template for the filename. Text in braces ' +
                '({var}) is expanded.\n\n' +
                'All attributes in Document.attrs are supported,\n' +
                'and "i" (as file counter)',
            'help_samples': [('Suffix every file with a number',
                              'file{i}.json'),
                             (
                                 'Use attribute "blah" from attrs.',
                                 'filename_{blah}.json',
                             )],
        })


class TemplatedPathOutput(FileOutputBase):
    """Write the documents to files using templated filename."""

    def __init__(self, path_template: str) -> None:
        """Create an instance.

        Args:
            path_template: `str.format()` template string. All entries of the
                original's document's `attrs` field are available, plus the
                number of the current file (starting with 0) as variable `i`.
        """
        super().__init__()
        self.path_template = path_template

    def _perform_output(self,
                        as_string: str,
                        context: Optional[Dict[str, str]] = None) -> None:
        """Write to individual files, filenames generated trhough template."""
        template_vars = dict(context or {}, i=self.output_index)
        filename = self.path_template.format(**template_vars)

        logging.debug('writing to file %s', filename)
        with open(filename, 'w', encoding='utf-8') as output_file:
            output_file.write(as_string)

    @classmethod
    def from_config(cls, config: TemplatedPathConfig) -> 'TemplatedPathOutput':
        """Create an instance from a config object."""
        return TemplatedPathOutput(config.output_path_template)


class SinkBuilder(generic.CmdLineInjectable):
    """Container for all sink types."""

    def __init__(self,) -> None:
        """Create an instance."""
        self.output_builder = generic.GenericBuilder[OutputFunction]()

    def register(
        self,
        kind: str,
        build_func: Callable[..., OutputFunction],
        config_type: Optional[Type[object]] = None,
        default_factory: Optional[Callable[[], Any]] = None,
        help_doc: generic.HelpDocArg = None,
    ) -> None:
        """Register a builder function.

        Note: SinkBuilder registers functions that build *output* functions,
            but itself returns *sink* functions (output mapped to iterable).

        Args:
            kind: string tag to identify the builder.
            build_func: A function that builds the desired output function.
            config_type: Type of the optional configuration passed to the
                build function.
            default_factory: Provide a config onbject when not available.
            help_doc: Add help documentation.
        """
        self.output_builder.register(kind, build_func, config_type,
                                     default_factory, help_doc)

    def set_commandline_args(self, *args: str, **kwargs: str) -> None:
        """Store command line args to inject during instance creation.

        Passes the arguments down to the output_builder functions.
        """
        self.output_builder.set_commandline_args(*args, **kwargs)

    def create_instance(
        self,
        kind_or_config: Union[str, generic.BuilderConfig],
        config: Any = None,
    ) -> SinkFunction:
        """Create a function acting as sink for documents.

        Args:
            kind_or_config: Either accepts a string identifying the
                desired build function, or a BuilderConfig instance,
                which contains kind and config in term.

            config: Optional config, passed to hte OutputFunction, if a string
                has been passed in the previous argument.

        Return:
            Function that is passed an iterable of documents.
            The returned function then consumes all items in the
            iterable, calling the corresponding registered
            OutputFunction for each item.
        """
        if isinstance(kind_or_config, generic.BuilderConfig):
            return self.create_instance(kind_or_config.kind,
                                        kind_or_config.config)

        output_func = self.output_builder.create_instance(
            kind_or_config, config)

        def _sink_func(source: Iterable[SinkItemType]) -> None:
            for doc in source:
                output_func(doc)

        return _sink_func

    def create_multiplexed(
            self, *config_data: generic.BuilderConfig) -> SinkFunction:
        """Create a sink function that outputs to multiple OutputFunctions."""
        output_funcs = [
            self.output_builder.create_instance(config)
            for config in config_data
        ]

        def _sink_func(source: Iterable[SinkItemType]) -> None:
            for document in source:
                for func in output_funcs:
                    func(document)

        return _sink_func

    @property
    def help_doc(self) -> help_docs.BuilderHelp:
        """Provide help documentation."""
        return self.output_builder.help_doc


def get_default_bulider() -> SinkBuilder:
    # pylint: disable=unnecessary-lambda
    """Create a sink builder, with basic sink pre-registered."""
    builder = SinkBuilder()

    builder.register('stdout',
                     lambda: SingleFileOutput.from_config(),
                     help_doc='Write to stdout, with separators between.')
    builder.register(
        'single_file',
        SingleFileOutput.from_config,
        default_factory=SingleFileConfig,
        config_type=SingleFileConfig,
        help_doc='Write to a single file, with separators between.')
    builder.register(
        'template_path',
        TemplatedPathOutput.from_config,
        help_doc='Write to individual files, with templated filenames')

    return builder
