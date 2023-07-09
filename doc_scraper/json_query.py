"""Query support for JSON data (wrapper around jq)."""

from typing import Any, Optional, Mapping, Sequence, List
import jq


class JsonException(Exception):
    """Exception to wrap around the jq generated ones."""

    def __init__(self, reason: str, prog: str) -> None:
        """Create an instance."""
        super().__init__(
            f'Exception in JSON query: {reason} Original string: {prog!r}')
        self.prog = prog


class _JqProgramWithInput():
    """Wrapper class to simplify jq binding."""

    def __init__(self, prog: Any) -> None:
        self._prog = prog

    def all(self) -> Sequence[Any]:
        """Get all results."""
        return self._prog.all()

    def first(self) -> Any:
        """Get first result."""
        return self._prog.first()


class _JqProgram():
    """Wrapper class to simplify jq binding."""

    def __init__(self, prog: Any) -> None:
        self._prog = prog

    @property
    def program_string(self) -> str:
        """Get the original program string."""
        return self._prog.program_string

    def input(self,
              value: Optional[Any] = None,
              text: Optional[str] = None) -> _JqProgramWithInput:
        """Feed data."""
        if value is not None:
            return _JqProgramWithInput(self._prog.input(value=value))
        elif text is not None:
            return _JqProgramWithInput(self._prog.input(text=text))
        else:
            raise ValueError('either set value or text, not none or both')


def _jq_compile(prog: str,
                args: Optional[Mapping[str, str]] = None) -> _JqProgram:
    """Wrap the jq.compile function to add typing."""
    if not args:
        return jq.compile(prog)  # type:ignore
    else:
        return jq.compile(prog, args=args)  # type:ignore


class NoOutput():
    """Returned when Query.get_first returns no output, not even None."""


class Query():
    """Execute a query in a JSON object and return results."""

    def __init__(self, query: str, **kwargs: Any) -> None:
        """Create an instance.

        Args:
            query: The query, as jq program.
            kwargs: Variable definitions for the jq program.
        """
        self._query = query
        self._vars = kwargs
        try:
            self._compiled_query = _jq_compile(query, args=self._vars)
        except Exception as exc:
            raise JsonException('Compiling', query) from exc

    def set_vars(self, **kwargs: Any):
        """Update the variables of the query."""
        self._vars = kwargs
        try:
            self._compiled_query = _jq_compile(self._query, args=self._vars)
        except Exception as exc:
            raise JsonException('Compiling', self._query) from exc

    def get_all(self, input_: Any) -> Sequence[Any]:
        """Return all matching JSON items as sequence."""
        try:
            return self._compiled_query.input(value=input_).all()
        except Exception as exc:
            raise JsonException('Query', self._query) from exc

    def get_first(self, input_: Any) -> Any | NoOutput:
        """Return the first matching JSON item.

        Returns:
            The JSON item or an instance of NoOutput if nothing was found.
        """
        try:
            return self._compiled_query.input(value=input_).first()
        except StopIteration:
            return NoOutput()
        except Exception as exc:
            raise JsonException('Query', self._query) from exc

    def __str__(self) -> str:
        """Convert to string."""
        return self._query

    def __repr__(self) -> str:
        """Convert to representation."""
        return f'Query({self._query!r}, vars={self._vars!r})'

    def __eq__(self, other: object) -> bool:
        """Test if other object is equal."""
        if not isinstance(other, Query):
            return False
        return self._query == other._query and self._vars == other._vars


def is_output(data: Any | NoOutput) -> bool:
    """Determine if the result of a get_first() contains output."""
    return not isinstance(data, NoOutput)


class Filter():
    """Filter a sequence of inputs by a list of expressions."""

    def __init__(self, *args: str | Query) -> None:
        """Create an instance."""
        self._queries = [
            arg if isinstance(arg, Query) else Query(arg) for arg in args
        ]

    def get_unmatched(self, data: Any) -> Sequence[Query]:
        """Return the query string of all queries returning falsy."""
        unmatched: List[Query] = []
        for query in self._queries:
            result = query.get_first(data)
            if not (is_output(result) and result):
                unmatched.append(query)
        return unmatched

    def matches_all(self, data: Any) -> bool:
        """Check if all queries return truthy."""
        for query in self._queries:
            result = query.get_first(data)
            if not is_output(result):
                return False
            if not result:
                return False
        return True

    def filter(self, data: Sequence[Any]) -> Sequence[Any]:
        """Filter a sequence of data, returning only matching."""
        return [item for item in data if self.matches_all(item)]
