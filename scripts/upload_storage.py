"""Stage uploads completely, then publish without replacing existing files."""

import os
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def staging_path(directory: Path, suffix: str = ".tmp"):
    fd, name = tempfile.mkstemp(prefix=".upload-", suffix=suffix, dir=directory)
    os.close(fd)
    path = Path(name)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def publish_upload(staged: Path, preferred: Path) -> Path:
    """Atomically claim a filename; all candidates use exclusive publication."""
    candidate = preferred
    while True:
        try:
            if os.name == "nt":
                # Windows rename fails if the destination already exists.
                os.rename(staged, candidate)
            else:
                # POSIX rename would overwrite, so use an exclusive hard link.
                os.link(staged, candidate)
            return candidate
        except FileExistsError:
            candidate = preferred.with_name(
                f"{preferred.stem}_{uuid.uuid4().hex}{preferred.suffix}"
            )


async def store_upload(upload, preferred: Path) -> Path:
    with staging_path(preferred.parent) as staged:
        with staged.open("wb") as buffer:
            while chunk := await upload.read(1024 * 1024):
                buffer.write(chunk)
            buffer.flush()
            os.fsync(buffer.fileno())
        return publish_upload(staged, preferred)
