import subprocess
from pathlib import Path


def gitc(git_args: list[str], cwd: Path = None) -> str:
    """
    Call a git command in the terminal and return its output as a decoded string.

    Args:
        git_args: list of argument to pass to git.
        cwd: current working directory, usually root of the git repository.

    Returns:
        output of the git command
    """
    command = ["git"] + git_args
    commit = subprocess.check_output(command, cwd=cwd)
    # XXX: is the rstrip safe in all cases ?
    return commit.decode("utf-8").rstrip("\n")


def get_current_commit_hash(repository_path: Path = None) -> str:
    """
    Return the hash of the latest commit the repository is currently at.

    Args:
        repository_path:
            optional filesysten path to an existing directory,
            use current working directory (cwd) if not provided.
    """
    return gitc(["rev-parse", "HEAD"], cwd=repository_path)
