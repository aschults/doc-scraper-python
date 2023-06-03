"""Fetcha a Google Doc and extract data as JSON.

The script is built on a pipeline system of:
*   sources (to obtain a doc)
*   transformations (to change the content and structure)
*   sinks (to store the doc in JSOn format)

The pipeline is configured through a YAML file (see --config).
A fully documented sample config can be obtained (use --config_sample).

"""
from typing import Sequence
import logging

from absl import app  # type: ignore
from absl import flags  # type: ignore

from doc_scraper.pipeline import pipeline

CONFIG_FILE_FLAG: flags.FlagHolder[str] = flags.DEFINE_string(  # type:ignore
    'config', None, 'Config YAML file')

DUMP_SAMPLE_FLAG: flags.FlagHolder[bool] = flags.DEFINE_bool(  # type:ignore
    'config_sample', False, 'Dump sample config')

CONFIG_MISSING_ERROR = 'Need to provide config file (--config)'


def main(argv: Sequence[str]):
    """Fetch a Google Document and convert to JSON."""
    logging.basicConfig(level=logging.INFO)

    builder = pipeline.PipelineBuilder()

    if DUMP_SAMPLE_FLAG.value:
        print(builder.help_doc.as_yaml())
        return

    if not CONFIG_FILE_FLAG.value:
        app.usage(detailed_error=CONFIG_MISSING_ERROR)  # type:ignore
    builder.set_commandline_args(*argv[1:])
    pipeline_instance = builder.from_file(CONFIG_FILE_FLAG.value)

    pipeline_instance()


def app_main():
    """Run extract_doc."""
    app.run(main)  # type: ignore


if __name__ == '__main__':
    app.run(main)  # type: ignore

# TODO: Add example execution (doc Screenshot) -- Resultin JSON
# TODO: JSON... Order of keys... _ first?
# TODO: Permissions on creds files.
