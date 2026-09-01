from pathlib import Path
import os


class PathSecurityError(Exception):
    """Raised when a path violates NEXUS security rules."""


def get_protected_paths() -> tuple[Path, ...]:
    paths = [
        Path(
            os.environ.get(
                "WINDIR",
                "C:/Windows",
            )
        ),
        Path(
            os.environ.get(
                "ProgramFiles",
                "C:/Program Files",
            )
        ),
        Path(
            os.environ.get(
                "ProgramFiles(x86)",
                "C:/Program Files (x86)",
            )
        ),
        Path(
            os.environ.get(
                "ProgramData",
                "C:/ProgramData",
            )
        ),
    ]

    return tuple(
        path.resolve()
        for path in paths
        if path.exists()
    )


class PathSecurityService:
    @staticmethod
    def normalize(
        raw_path: str,
    ) -> Path:
        path = Path(raw_path).expanduser()

        if not path.is_absolute():
            raise PathSecurityError(
                "The path must be absolute."
            )

        try:
            return path.resolve(strict=True)
        except FileNotFoundError as exc:
            raise PathSecurityError(
                "The specified path does not exist."
            ) from exc

    @staticmethod
    def is_protected(
        path: Path,
    ) -> bool:
        for protected in get_protected_paths():
            if path == protected:
                return True

            if protected in path.parents:
                return True

        return False

    def validate(
        self,
        raw_path: str,
    ) -> Path:
        path = Path(raw_path).expanduser()

        if not path.is_absolute():
            raise PathSecurityError(
                "The path must be absolute."
            )

        try:
            path = path.resolve(strict=True)
        except FileNotFoundError as exc:
            raise PathSecurityError(
                "The specified path does not exist."
            ) from exc

        if not path.is_dir():
            raise PathSecurityError(
                "The specified path is not a directory."
            )

        if self.is_protected(path):
            raise PathSecurityError(
                "The specified directory is protected."
            )

        return path

    @staticmethod
    def is_within(
        path: Path,
        root: Path,
    ) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    def validate_file(
        self,
        file_path: Path,
        workspace_root: Path,
    ) -> Path:
        resolved_file = file_path.resolve(
            strict=True,
        )

        if not self.is_within(
            resolved_file,
            workspace_root,
        ):
            raise PathSecurityError(
                "File is outside the workspace."
            )

        if not resolved_file.is_file():
            raise PathSecurityError(
                "The path is not a file."
            )

        return resolved_file
