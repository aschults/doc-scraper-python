"""Functionality to make some builtins configurable."""

from typing import Optional, Literal, IO, Sequence
import glob


class FileSystemAdapter():
    """Wrapper to make filesystem functions adaptable."""

    def open(
        self,
        file: int | str,
        mode: Literal['r', 'w', 'a'] = "r",
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
    ) -> IO[str]:
        """Open a file, like the builtins function."""
        return open(file,
                    mode,
                    encoding=encoding,
                    errors=errors,
                    newline=newline)

    def glob(self,
             pathname: str,
             *,
             root_dir: Optional[str] = None,
             recursive: bool = False) -> Sequence[str]:
        """Find matching files, like glob.glob."""
        return glob.glob(pathname, root_dir=root_dir, recursive=recursive)

    # Singleton for the filesystem adapter
    _fs_instance: 'Optional[FileSystemAdapter]' = None

    @classmethod
    def get_fs(cls,) -> 'FileSystemAdapter':
        """Get the current filesystem adaptter."""
        if not cls._fs_instance:
            cls._fs_instance = FileSystemAdapter()
        return cls._fs_instance

    @classmethod
    def set_fs(cls, fs: 'FileSystemAdapter'):
        """Set the current filesystem adapter."""
        cls._fs_instance = fs


def get_fs() -> FileSystemAdapter:
    """Get the current filesystem adaptter."""
    return FileSystemAdapter.get_fs()
