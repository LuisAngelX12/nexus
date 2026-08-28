from pathlib import Path


class PathOutsideWorkspaceError(Exception):
    pass


def validate_path_inside_workspace(
    workspace_root: Path,
    target: Path,
) -> Path:
    root = workspace_root.resolve()
    resolved_target = target.resolve()

    try:
        resolved_target.relative_to(root)
    except ValueError as exc:
        raise PathOutsideWorkspaceError(
            "The requested path is outside the workspace."
        ) from exc

    return resolved_target