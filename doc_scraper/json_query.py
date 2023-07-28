"""Query support for JSON data (wrapper around jq)."""

from typing import Any, Optional, Mapping, Sequence, List
import re

import jq


class JsonException(Exception):
    """Exception to wrap around the jq generated ones."""

    def __init__(self, reason: str, prog: str, preamble: str = '') -> None:
        """Create an instance."""
        super().__init__(
            f'Exception in JSON query: {reason} Original string: ' +
            '{preamble!r} {prog!r}')
        self.prog = prog
        self.preamble = preamble


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

    # If matching, we need to add semicolon at end.
    PREAMBLE_NEED_SEMICOLON_RE = re.compile(r'[^;\s]\s*$', re.S)

    def __init__(self,
                 query: str,
                 preamble: str = '',
                 var_names: Optional[Sequence[str]] = None,
                 **kwargs: Any) -> None:
        """Create an instance.

        Args:
            query: The query, as jq program.
            preamble: Additional definitions that go before the query.
            var_names: List of variable names to set with set_vars().
            kwargs: Global variable definitions for the jq program.
        """
        self._query = query

        if self.PREAMBLE_NEED_SEMICOLON_RE.search(preamble):
            preamble = f'{preamble};'
        self._preamble = preamble
        self._var_names = var_names or []
        var_str = ''.join(f'${name}, ' for name in self._var_names)
        vars_unpack_prefix = f"""
            . as {{
                "_vars": [{var_str} $__null_dummy__],
                "_content": $__content__
            }} | $__content__
        """
        self._wrapped_query = f"""
            {self._preamble}
            {vars_unpack_prefix}
            |
            ({query})
        """

        try:
            self._compiled_query = _jq_compile(self._wrapped_query,
                                               args=kwargs)
        except Exception as exc:
            raise JsonException('Compiling', query, preamble) from exc

    def get_all(
        self,
        input_: Any,
        **kwargs: Any,
    ) -> Sequence[Any]:
        """Return all matching JSON items as sequence."""
        var_values = [kwargs.get(name) for name in self._var_names]
        remaining_keys = set(kwargs.keys()) - set(self._var_names)
        if remaining_keys:
            raise ValueError(f'Bad variable assignments: {remaining_keys!r}')

        try:
            wrapped_input = {
                '_vars': var_values,
                '_content': input_,
            }
            return self._compiled_query.input(value=wrapped_input).all()
        except Exception as exc:
            raise JsonException('Query', self._query) from exc

    def get_first(self, input_: Any, **kwargs: Any) -> Any | NoOutput:
        """Return the first matching JSON item.

        Returns:
            The JSON item or an instance of NoOutput if nothing was found.
        """
        var_values = [kwargs.get(name) for name in self._var_names]
        remaining_keys = set(kwargs.keys()) - set(self._var_names)
        if remaining_keys:
            raise ValueError(f'Bad variable assignments: {remaining_keys!r}')

        try:
            wrapped_input = {
                '_vars': var_values,
                '_content': input_,
            }
            return self._compiled_query.input(value=wrapped_input).first()
        except StopIteration:
            return NoOutput()
        except Exception as exc:
            raise JsonException('Query', self._query) from exc

    def __str__(self) -> str:
        """Convert to string."""
        return self._query

    def __repr__(self) -> str:
        """Convert to representation."""
        return (f'Query({self._query!r}, preamble={self._preamble!r}, ' +
                f'var_names={self._var_names!r})')

    def __eq__(self, other: object) -> bool:
        """Test if other object is equal."""
        if not isinstance(other, Query):
            return False
        return (self._query == other._query and
                self._var_names == other._var_names and
                self._preamble == other._preamble)


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
