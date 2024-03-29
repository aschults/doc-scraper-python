"""Classes and functions to provide basic document sources/loaders."""

import dataclasses
import itertools
import logging

from typing import (Iterable, Iterator, List, Optional, Sequence)

from doc_scraper import doc_struct
from doc_scraper import html_extractor
from doc_scraper import doc_loader
from doc_scraper import adaptors

from . import generic

# Representation of a document source.
SourceType = Iterable[doc_struct.Document]

# Class to configure SourceBuilder.create_instance().
SourceConfig = generic.BuilderConfig

SEARCH_LINK = 'https://developers.google.com/drive/api/guides/ref-search-terms'


@dataclasses.dataclass(kw_only=True)
class DocLoaderConfig():
    """Configuration of Google Docs to download."""

    doc_ids: Sequence[str] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text':
                'Document IDs (part of the URL) to download.',
            'help_samples': [[
                '1HZUlXXXXXX_SAMPLE1_XXXXXXIAQOa-xx9XxXx-xXxx',
                '1HZUlXXXXXX_SAMPLE2_XXXXXXIAQOa-xx9XxXx-xXxx',
            ]],
        })
    username: str = dataclasses.field(
        default='',
        metadata={
            'help_text':
                'Google account username (as email), incl. service accounts.',
            'help_samples': ['someone@gmail.com'],
        })

    queries: Sequence[str] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text':
                f'Drive query to search for docs \n({SEARCH_LINK}).',
            'help_samples': [[
                'name contains \'Report\'',
                'starred = true and \'someone@anywhere.com\' in owners',
            ]],
        })


class DocLoader(SourceType, generic.CmdLineInjectable):
    """Download docs from Google Drive/Docs."""

    def __init__(
        self,
        doc_ids: Optional[List[str]] = None,
        queries: Optional[Sequence[str]] = None,
        username: Optional[str] = None,
        downloader_or_creds_store: doc_loader.DocDownloader |
        doc_loader.CredentialsStore | None = None
    ) -> None:
        """Create an instance.

        Args:
            doc_ids: IDs of docs to fetch. Default: []. The list can be
                extended using set_commandline_args().
            queries: List of query strings for drive.files.list
            username: Username associated with the credentials to use.
                Use None(default) for default credentials.
            downloader_or_creds_store: Pass down DocDownloader itself, or
                credentials required to set up one.
        """
        self._doc_ids: List[str] = doc_ids or []
        if isinstance(downloader_or_creds_store, doc_loader.DocDownloader):
            self._doc_downloader = downloader_or_creds_store
        elif downloader_or_creds_store is not None:
            self._doc_downloader = doc_loader.DocDownloader(
                username=username, creds_store=downloader_or_creds_store)
        else:
            self._doc_downloader = doc_loader.DocDownloader(username=username)
        self._queries = queries

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
            new_attrs = dict(document.attrs)
            new_attrs.update(doc_id=doc_id)
            document = dataclasses.replace(document, attrs=new_attrs)
            yield document

        for query in self._queries or []:
            logging.debug('processing query %r', query)
            for entry in self._doc_downloader.list_files(query):
                document = self._doc_downloader.get_from_html(entry['id'])
                logging.debug('Fetched doc with id %s: %s', entry['id'],
                              str(document))
                new_attrs = dict(document.attrs)
                new_attrs.update(
                    doc_id=entry['id'],
                    doc_name=entry['name'],
                )
                document = dataclasses.replace(document, attrs=new_attrs)
                yield document

    @classmethod
    def from_config(
        cls,
        config: Optional[DocLoaderConfig],
        creds_store: doc_loader.CredentialsStore,
    ) -> 'DocLoader':
        """Build an instance from config.

        Args:
            config: Configuration containing document IDs to fetch as well as
                the user under which to access.
            creds_store:
                Credentials needed to access Google Docs.
        """
        if config is None:
            config = DocLoaderConfig()
        return DocLoader(doc_ids=list(config.doc_ids),
                         username=config.username,
                         downloader_or_creds_store=creds_store,
                         queries=config.queries)


@dataclasses.dataclass(kw_only=True)
class FileLoaderConfig():
    """Configuration to load from local files."""

    doc_filenames: Sequence[str] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text': 'Paths to local files.',
            'help_samples': [['/path/to/a', '/path/to/b']]
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
            with adaptors.get_fs().open(filename, "r",
                                        encoding='utf-8') as file:
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
        iterables = [
            self.create_instance(config) for config in list(config_data)
        ]
        return itertools.chain(*iterables)


def get_default_builder(
    credentials_store: Optional[doc_loader.CredentialsStore] = None
) -> SourceBuilder:
    """Create a source builder with pre-registered source types.

    Args:
        credentials_store: Storage for Google credentials, to access
            Google Docs.
    """
    if credentials_store is None:
        credentials_store = doc_loader.CredentialsStore()
        credentials_store.add_available_credentials()
    default_builder = SourceBuilder()
    default_builder.register(
        'google_doc_html',
        lambda config: DocLoader.from_config(config, credentials_store),
        DocLoaderConfig,
        help_doc='Load from Google Drive API as exported HTML.')
    default_builder.register('doc_files',
                             FileLoader.from_config,
                             config_type=FileLoaderConfig,
                             help_doc='Load from local files (as HTML).')

    return default_builder
