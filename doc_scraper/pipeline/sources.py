"""Classes and functions to provide basic document sources/loaders."""

import dataclasses
import itertools
import logging

from typing import (Iterable, Iterator, List, Optional, Sequence)

from doc_scraper import doc_struct
from doc_scraper import html_extractor
from doc_scraper.doc_loader import DocDownloader
from doc_scraper import help_docs

from . import generic

# Representation of a document source.
SourceType = Iterable[doc_struct.Document]

# Class to configure SourceBuilder.create_instance().
SourceConfig = generic.BuilderConfig


@dataclasses.dataclass(kw_only=True)
class DocLoaderConfig():
    """Configuration of Google Docs to download."""

    doc_ids: Sequence[str] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text':
                'Document IDs (part of the URL) to download.',
            'help_samples': [
                help_docs.RawSample(
                    '\n- "1HZUlXXXXXX_SAMPLE1_XXXXXXIAQOa-xx9XxXx-xXxx"\n' +
                    '- "1HZUlXXXXXX_SAMPLE2_XXXXXXIAQOa-xx9XxXx-xXxx"')
            ],
        })


class DocLoader(SourceType, generic.CmdLineInjectable):
    """Download docs from Google Drive/Docs."""

    def __init__(self,
                 doc_ids: Optional[List[str]] = None,
                 doc_downloader: Optional[DocDownloader] = None) -> None:
        """Create an instance.

        Args:
            doc_ids: IDs of docs to fetch. Default: []. The list can be
                extended using set_commandline_args().
            doc_downloader: Mainly for testing purpose to mock the download.
        """
        self._doc_ids: List[str] = doc_ids or []
        self._doc_downloader: DocDownloader = doc_downloader or DocDownloader()

    def set_commandline_args(self, *args: str, **kwargs: str) -> None:
        """Add doc ids specified on command-line.

        Args:
            args: Additional Google Doc IDs to read from
            kwargs: Currently ignored.
        """
        self._doc_ids.extend(args)

    def __iter__(self) -> Iterator[doc_struct.Document]:
        """Create an iterator that returns the indicated docs."""
        for index, doc_id in enumerate(self._doc_ids):
            document = self._doc_downloader.get_from_html(doc_id)
            logging.debug('Fetched doc %d, id %s: %s', index, doc_id,
                          str(document))
            yield document

    @classmethod
    def from_config(cls, config: Optional[DocLoaderConfig]) -> 'DocLoader':
        """Build an instance from config."""
        if config is None:
            config = DocLoaderConfig()
        return DocLoader(doc_ids=list(config.doc_ids))


@dataclasses.dataclass(kw_only=True)
class FileLoaderConfig():
    """Configuration to load from local files."""

    doc_filenames: Sequence[str] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text':
                'Paths to local files.',
            'help_samples': [
                help_docs.RawSample('\n- /path/to/a\n- /path/to/b')
            ]
        })


class FileLoader(SourceType, generic.CmdLineInjectable):
    """Load documents as HTML from files."""

    def __init__(self, doc_filenames: Optional[Sequence[str]] = None) -> None:
        """Create an instance.

        Args:
            doc_filenames: List of filenames to read from. Default: []
                the list can be extended using set_commandline_args().
        """
        self.doc_filenames: List[str] = list(doc_filenames or [])

    def set_commandline_args(self, *args: str, **kwargs: str) -> None:
        """Add filenames to process from command line.

        Args:
            args: Additional filenames to read from
            kwargs: Currently ignored.
        """
        self.doc_filenames.extend(args)

    def __iter__(self) -> Iterator[doc_struct.Document]:
        """Create an iterator returning the indicated documents."""
        for index, filename in enumerate(self.doc_filenames):
            parser = html_extractor.ToStructParser()
            with open(filename, "r", encoding='utf-8') as file:
                parser.feed(file.read())

            document = parser.as_struct()
            logging.debug('Reading doc %d, file %s: %s', index, filename,
                          str(document))
            yield document

    @classmethod
    def from_config(cls, config: Optional[FileLoaderConfig]) -> 'FileLoader':
        """Create an instance from config."""
        if config is None:
            config = FileLoaderConfig()
        return FileLoader(config.doc_filenames)


class SourceBuilder(generic.GenericBuilder[SourceType]):
    """Build a source by source name and config."""

    def create_chain(
            self, *config_data: SourceConfig) -> Iterator[doc_struct.Document]:
        """Create an iterator that goes through multiple sources."""
        iterables = [self.create_instance(config) for config in config_data]
        return itertools.chain(*iterables)


def get_default_builder() -> SourceBuilder:
    """Create a source builder with pre-registered source types."""
    default_builder = SourceBuilder()
    default_builder.register(
        'google_doc_html',
        DocLoader.from_config,
        help_doc='Load from Google Drive API as exported HTML.')
    default_builder.register('doc_files',
                             FileLoader.from_config,
                             help_doc='Load from local files (as HTML).')

    return default_builder
