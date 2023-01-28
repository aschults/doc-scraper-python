# Doc Scraper

Python modules and script supporting the extraction of semi-structured data from
Google Docs to make it available in structured or tabular form.

It starts from the experience that information is more easily managed in a document
vs. a sheet or table, particularly if some base structure or template is provided
when filling in the details. Unfortunately, extraction of the information often needs
to be done manually as the original structure of a (Google) Doc is not trivial to navigate
and find information. Doc scraper aims to close this gap by providing tools to simplify
a the structure of documents and making them easy to filter and extract the needed information.
Here some [use cases](docs/use_cases.md) to make the goal more tangible.

## Usage

Doc scraper can be used as library (check module `doc_scraper.pipeline`) and as script
(`doc_extract.py`). The script basically configures a pipeline using a YAML config and
then executes the pipeline. Here an example [config](docs/sample_config.yaml).

The script then is started as `extract_docs.py --config=docs/sample_config.yaml`.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

## License

Apache 2.0; see [`LICENSE`](LICENSE) for details.

## Disclaimer

This project is not an official Google project. It is not supported by
Google and Google specifically disclaims all warranties as to its quality,
merchantability, or fitness for a particular purpose.
