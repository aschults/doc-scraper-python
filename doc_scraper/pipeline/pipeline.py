"""Functionality to assemble whole pipelines."""

from typing import Any, Dict, Sequence, Optional, Union, TextIO
import dataclasses
import logging

import dacite
import yaml

from doc_scraper import help_docs

from . import transforms
from . import sources
from . import sinks
from . import generic


@dataclasses.dataclass(kw_only=True, frozen=True)
class PipelineConfig():
    """Configuration for a whole pipeline."""

    sources: Sequence[sources.SourceConfig]
    transformations: Sequence[transforms.TransformConfig]
    outputs: Sequence[sinks.OutputConfig]


class Pipeline():
    """Complete pipeline, ready to execute."""

    def __init__(self, source: sources.SourceType,
                 transform: transforms.TransformationFunction,
                 sink: sinks.SinkFunction) -> None:
        """Create an instance from key parts."""
        self.source = source
        self.transform = transform
        self.sink = sink

    def __call__(self) -> None:
        """Run the entire pipeline."""
        self.sink(map(self.transform, self.source))


class PipelineBuilder(generic.CmdLineInjectable):
    """Build a pipeline from builders of their parts."""

    def __init__(self,
                 source_builder: Optional[sources.SourceBuilder] = None,
                 transform_builder: Optional[
                     transforms.TransformBuilder] = None,
                 sink_builder: Optional[sinks.SinkBuilder] = None) -> None:
        """Construct an instance.

        If *_builder arguments are not passed, use the get_default_builder
        function in the corresponding modules.
        """
        if source_builder is None:
            source_builder = sources.get_default_builder()
        if transform_builder is None:
            transform_builder = transforms.get_default_builder()
        if sink_builder is None:
            sink_builder = sinks.get_default_bulider()
        self.source_builder: sources.SourceBuilder = source_builder
        self.transform_builder: transforms.TransformBuilder = transform_builder
        self.sink_builder: sinks.SinkBuilder = sink_builder

    def set_commandline_args(self, *args: str, **kwargs: str) -> None:
        """Pass command line args down to the individual builders."""
        self.source_builder.set_commandline_args(*args, **kwargs)
        self.transform_builder.set_commandline_args(*args, **kwargs)
        self.sink_builder.set_commandline_args(*args, **kwargs)

    def from_config(self, config: PipelineConfig) -> Pipeline:
        """Build a pipeline from PipelineConfig."""
        source = self.source_builder.create_chain(*config.sources)
        transform = self.transform_builder.create_chain(
            *config.transformations)
        sink = self.sink_builder.create_multiplexed(*config.outputs)
        return Pipeline(source, transform, sink)

    def from_dict(self, data: Dict[str, Any]) -> Pipeline:
        """Convert a dict-list structure to Pipeline."""
        try:
            pipeline_config = dacite.from_dict(data_class=PipelineConfig,
                                               data=data)
            return self.from_config(pipeline_config)
        except Exception:
            logging.info('Reading pipeline from data structure: %s', str(data))
            raise

    def from_file(self, config_file: Union[str, TextIO]) -> Pipeline:
        """Create a pipeline from a YAML config file."""
        if isinstance(config_file, str):
            config_file = open(config_file, 'r', encoding='utf-8')
        data: Dict[str, Any] = yaml.safe_load(config_file)  # type: ignore
        return self.from_dict(data)

    @property
    def help_doc(self) -> help_docs.PipelineHelp:
        """Provide help documentation."""
        return help_docs.PipelineHelp('Configure a pipeline',
                                      self.source_builder.help_doc,
                                      self.transform_builder.help_doc,
                                      self.sink_builder.help_doc)
