"""Classes and functions to build pipelines.

General concepts:

*   _Pipeline_: A sequence of document transformations, fed from one
    or more sources, output into one or more sink.
*   _Source_: Iterable[Document], i.e. any class that allows iterating
    through documents.
*   _Transformation_: Callable[[Document], Document], i.e. A function that
    consumes a document and yields one.
*   _Sink_: Callable[[Iterable[Document]],None], i.e. a function that
    takes iterables, runs through them, storing the documents.
*   _Output_: Callable[[Document], None], i.e. function that processes
    one document.
*   _Builder_: Class that, based on supplying a `kind` (as string), produces
    an element of the pipeline (e.g. TransformationBuilder).
*   _Builder functions_: Builders allow to register additional kinds by
    supplying a builder function (i.e.  Callable[...,TransformationFunction]).
*   _Config classes_: Dataclass that contains details to be passed as arg
    to builder functions. The argument type is stored inside the builder,
    and if a dict is passed, a conversion from dict to the config class
    is performed (using https://github.com/konradhalas/dacite).
*   `get_default_*()`: Creates a Builder with basic kinds pre-registered,
    ready to use. Additional kinds can be registerd after retreiving the
    default builder.
"""
