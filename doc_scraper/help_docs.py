"""Classes to implement a minimal documentation system.

Idea behind is to embed help in form of classes close to
the related implementation, e.g. in field metadata for
dataclasses.
"""

import dataclasses
from typing import (
    Sequence,
    Optional,
    Tuple,
    Union,
    Type,
    Any,
    List,
    cast,
)
import re

# Convenience type to allow adding samples via tuple.
ConfigFieldSampleType = Union[Tuple[str, Any], Any]


class RawSample():
    """Class to mark the content to be _literaly_ inserted.

    Otherwise suplied values are converted to string form.
    """

    def __init__(self, raw: Any) -> None:
        """Construct an instance.

        Args:
            raw: literal string to use in sample config.
        """
        self.raw = raw


class ClassBasedSample():
    """Class to mark help docs to be generated from a class."""

    def __init__(self, config_type: type[object]) -> None:
        """Construct an instance.

        Args:
            config_type: Type of the dataclass config class.
        """
        self.config_type = config_type


class TextConvertible():
    """Base class for all help data that converts to text."""

    def _prefix_text_lines(self, text: str, prefix: str = '    ') -> str:
        """Prefix each line of a string with a prefix.

        Used to indent text or turn it into a comment.
        """
        return '\n'.join((prefix + line for line in text.split('\n')))

    def as_yaml(self) -> str:
        """Convert the object into a Yaml config with comments."""
        raise NotImplementedError('Implement in subclasses.')

    def _is_single_line(self, value: Any):
        """Decide if the value should be presented on a single line."""
        if isinstance(value, str):
            return True
        if isinstance(value, (dict, list, set, ClassBasedSample)):
            return False
        return True

    def _dict_value_as_yaml(self, key: str, value: Any, text: str = '') -> str:
        """Render a dict key-value, considering single/multi line format."""
        value_str = self._values_as_yaml(value)
        if text:
            text = '  # ' + text
        if self._is_single_line(value):
            space_sep = ' ' if value_str else ''
            return f'{key}:{space_sep}{value_str}{text}'
        else:
            return f'{key}:{text}\n{value_str}'

    def _values_as_yaml(self, value: Any) -> str:
        """Convert a value into a YAML-format string.

        Inserts the raw content of RawSample instances.
        """
        if value is None:
            return ''
        if isinstance(value, str):
            if not value:
                return ''
            return f'"{value}"'
        if isinstance(value, dict):
            result = (self._dict_value_as_yaml(key, value2)
                      for key, value2 in cast(dict[str, Any], value.items()))
            result = (self._prefix_text_lines(value2) for value2 in result)
            return '\n'.join(result)
        if isinstance(value, list):
            result = (self._values_as_yaml(value2)
                      for value2 in cast(list[Any], value))
            result = (value2 if value2[0] == ' ' else '    ' + value2
                      for value2 in result)
            result = ('-' + value2[1:] for value2 in result)
            result_str = '\n'.join(result)
            return result_str
        if isinstance(value, re.Pattern):
            return cast(re.Pattern[str], value).pattern
        if isinstance(value, RawSample):
            return value.raw
        if isinstance(value, ClassBasedSample):
            docs = ConfigHelp.from_config_class(value.config_type).as_yaml()
            docs = self._prefix_text_lines(docs)
            return docs
        return str(value)


@dataclasses.dataclass
class ConfigFieldHelp(TextConvertible):
    """Documentation for a config field.

    Attributes:
        name: The name of the attribute.
        field_type: The Python type of the field.
        text: The actual help text.
        sample_values: A list of tuples containing
            help text and a sample value.
    """

    name: str
    field_type: type
    text: str
    sample_values: Sequence[Tuple[str, Any]]

    @classmethod
    def _gen_default_sample(cls,
                            field: dataclasses.Field[Any]) -> Tuple[str, Any]:
        """Generate the default sample based on default values in fields."""
        if not isinstance(field.default, type(dataclasses.MISSING)):
            value = field.default
        elif not isinstance(field.default_factory, type(dataclasses.MISSING)):
            value = cast(Any, field.default_factory)()
        else:
            return ('', RawSample('...'))
        if dataclasses.is_dataclass(value):
            value = ClassBasedSample(type(value))
        return ('Default', value)

    @classmethod
    def from_dataclasses_field(
            cls, field: dataclasses.Field[Any]) -> 'ConfigFieldHelp':
        """Create an instance from a dataclass.Field object.

        Relies on the field's `metadata` to extract 'help_text' and
        'help_samples'.
        """
        samples: List[Tuple[str, Any]] = []
        for sample in field.metadata.get('help_samples',
                                         [cls._gen_default_sample(field)]):
            if isinstance(sample, Tuple):
                samples.append(cast(Tuple[str, Any], sample))
            else:
                samples.append(('', sample))

        return ConfigFieldHelp(field.name, field.type,
                               field.metadata.get('help_text', ''), samples)

    def as_yaml(self) -> str:
        """Convert the instance to YAML."""
        comment_str: str = ''

        if self.text:
            comment_str = self._prefix_text_lines(self.text, '# ') + '\n'

        first_sample_str: str = ''
        if self.sample_values:
            first_text, first_value = self.sample_values[0]
            first_sample_str = self._dict_value_as_yaml(
                self.name, first_value, first_text)

        other_samples: List[str] = []

        for sample in self.sample_values[1:]:
            sample_str = self._dict_value_as_yaml(self.name, sample[1],
                                                  sample[0])
            sample_str = self._prefix_text_lines(sample_str, prefix='    # ')
            other_samples.append(sample_str)

        other_samples_str: str = ''
        if other_samples:
            other_samples_str = '\n' + '\n'.join(other_samples)
        return f'{comment_str}{first_sample_str}{other_samples_str}'


@dataclasses.dataclass
class ConfigHelp(TextConvertible):
    """Documentation for a config field.

    Attributes:
        name: The name of the config class.
        text: The actual help text.
        field_doc: A list of field help instances.
    """

    name: str
    text: str
    fields_doc: Sequence[ConfigFieldHelp] = dataclasses.field(
        default_factory=list)

    @classmethod
    def from_config_class(cls, config_class: Type[object]) -> 'ConfigHelp':
        """Create an instance from a config class.

        Iterates through all dataclass fields and extracts field help docs.
        """
        field_data: List[ConfigFieldHelp] = []
        if dataclasses.is_dataclass(config_class):
            field_data = [
                ConfigFieldHelp.from_dataclasses_field(field)
                for field in dataclasses.fields(config_class)
            ]

        return ConfigHelp(config_class.__name__, config_class.__doc__ or '',
                          field_data)

    def as_yaml(self) -> str:
        """Convert the instance into YAML."""
        return '\n'.join((item.as_yaml() for item in self.fields_doc))


@dataclasses.dataclass()
class BuilderKindHelp(TextConvertible):
    """Documentation for a specific kind of builder function.

    Attributes:
        kind: The `kind` identifier used with the builder.
        text: The actual help text.
        doc_config: Documentation for the config class used
            passed when creating an instance.
    """

    kind: str
    text: str
    config_doc: Optional[ConfigHelp] = None

    @classmethod
    def from_config_class(
            cls,
            kind: str,
            text: str,
            config_class: Optional[Type[object]] = None) -> 'BuilderKindHelp':
        """Create an instance from the needed builder details."""
        if config_class is None:
            return BuilderKindHelp(kind, text)

        return BuilderKindHelp(kind, text,
                               ConfigHelp.from_config_class(config_class))

    def as_yaml(self) -> str:
        """Convert to YAML."""
        config_doc_str: str = ''
        config_comment_str: str = ''
        config_key_str: str = ''
        if self.config_doc is not None:
            config_doc_str = self.config_doc.as_yaml()
            config_comment_str = self.config_doc.text
            config_key_str = 'config:\n'

        if config_doc_str:
            config_doc_str = self._prefix_text_lines(config_doc_str,
                                                     '  ') + '\n'
            config_comment_str = self._prefix_text_lines(
                config_comment_str, '# ') + '\n'

        content = "".join([config_comment_str, config_key_str, config_doc_str])
        return f'kind: {self.kind}\n{content}'


@dataclasses.dataclass()
class BuilderHelp(TextConvertible):
    """Documentation for a builder.

    Attributes:
        kinds: List of al kind that are registered.
    """

    kinds: Sequence[BuilderKindHelp]

    def as_yaml(self) -> str:
        """Convert to YAML."""
        result = ''

        for kind in self.kinds:
            comment = ''
            if kind.text:
                comment = self._prefix_text_lines(kind.text, '# ') + '\n'

            inner_config = self._prefix_text_lines(kind.as_yaml(), "  ")
            inner_config = '-' + inner_config[1:]
            result += f'{comment}{inner_config}\n'

        return result


@dataclasses.dataclass()
class PipelineHelp(TextConvertible):
    """Documentation for the entire pipeline.

    Attributes:
        text: The actual help text.
        sources:
        transformations:
        sinks: Help for each builder type.
    """

    text: str
    sources: BuilderHelp
    transformations: BuilderHelp
    sinks: BuilderHelp

    def as_yaml(self) -> str:
        """Convert to YAML."""
        sections = ('sources', 'transformations', 'sinks')
        section_comments = (
            'Load from various sources (some are aware of command line arg)',
            'Steps executed in order to modify the documents',
            'Places to write down the result',
        )

        section_comments_prefixed = [
            self._prefix_text_lines(comment, '# ')
            for comment in section_comments
        ]

        doc_list = [
            self._prefix_text_lines(item.as_yaml())
            for item in (self.sources, self.transformations, self.sinks)
        ]

        field_docs = "\n\n".join(
            (f'{comment}\n{section}:\n{doc}' for section, comment, doc in zip(
                sections, section_comments_prefixed, doc_list)))

        text_prefixed = self._prefix_text_lines(self.text, '# ')
        return f'#\n{text_prefixed}\n#\n{field_docs}'
