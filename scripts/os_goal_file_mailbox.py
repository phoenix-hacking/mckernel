"""Read immutable GitHub instructions and publish a separate UTF-8 reply file.

The caller owns polling, receipts, and the existing instruction queue. This
module uses fixed-repository API endpoints and never follows download URLs.
GitHub's storage/API limits apply; no application payload quota is added.
"""
import base64
import binascii
import hashlib
import re
from urllib.parse import quote, urlencode


# GitHub's web editor committer: https://github.com/web-flow . Its profile's
# avatar URL is https://avatars.githubusercontent.com/u/19864447 . GitHub signs
# web commits: https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification
WEB_FLOW_ID = 19864447
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_UNSET = object()


class ReplyWriteError(RuntimeError):
    """A reply PUT has an uncertain outcome; the next call must GET first."""
    uncertain = True


def _valid_path(path):
    return (isinstance(path, str) and bool(path) and not path.startswith("/") and "\\" not in path
            and all(part not in {"", ".", ".."} for part in path.split("/"))
            and all(ord(c) >= 32 and ord(c) != 127 for c in path))


def _configuration(config):
    if not isinstance(config, dict):
        raise ValueError("File mailbox configuration must contain an object")
    remote = config.get("repo")
    user_id = config.get("authorized_user_id")
    login = config.get("authorized_user_login") or config.get("authorized_login")
    branch, path = config.get("file_inbox_branch"), config.get("file_inbox_path")
    if (not isinstance(remote, str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", remote)
            or any(part in {".", ".."} for part in remote.split("/"))
            or type(user_id) is not int or user_id <= 0
            or not isinstance(login, str) or not re.fullmatch(r"[A-Za-z0-9-]+", login)):
        raise ValueError("File mailbox requires one repository and numeric owner identity")
    if (not isinstance(branch, str) or not branch or any(ord(c) < 32 or ord(c) == 127 for c in branch)
            or not _valid_path(path)):
        raise ValueError("File mailbox requires an explicit branch and repository-relative file path")
    return remote, user_id, login, branch, path


def _identity(user, user_id, login):
    return (isinstance(user, dict) and type(user.get("id")) is int and user["id"] == user_id
            and user.get("type") == "User" and isinstance(user.get("login"), str)
            and user["login"].casefold() == login.casefold())


def _blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _file_metadata(metadata, path):
    if (not isinstance(metadata, dict) or metadata.get("type") != "file" or metadata.get("path") != path
            or "target" in metadata or metadata.get("submodule_git_url") is not None
            or not isinstance(metadata.get("sha"), str) or not _SHA.fullmatch(metadata["sha"])
            or type(metadata.get("size")) is not int or metadata["size"] < 0):
        raise ValueError("File mailbox source is not the configured regular Git file")


def _decode(data, blob_sha, size):
    if (not isinstance(data, dict) or data.get("sha") != blob_sha
            or type(data.get("size")) is not int or data["size"] != size
            or data.get("encoding") != "base64" or not isinstance(data.get("content"), str)):
        raise ValueError("File mailbox blob metadata does not match its immutable source")
    try:
        encoded = re.sub(rb"[\r\n\t ]", b"", data["content"].encode("ascii"))
        raw = base64.b64decode(encoded, validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError):
        raise ValueError("File mailbox blob has invalid base64 content") from None
    if len(raw) != size:
        raise ValueError("File mailbox blob is truncated or its byte size does not match")
    if _blob_sha(raw) != blob_sha:
        raise ValueError("File mailbox blob hash does not match its immutable source")
    return raw


def read_revision(config, *, api):
    """Return READY/EMPTY revision metadata; reject invalid or untrusted content.

    Only the newest commit changing the configured path is observed. Every
    subsequent read is bound to its immutable SHA, so branch movement cannot
    substitute another instruction. A blank file is inactive and needs no
    author trust; nonblank text requires a verified owner-authored commit.
    """
    remote, user_id, login, branch, path = _configuration(config)
    endpoint = f"repos/{remote}"
    query = urlencode({"sha": branch, "path": path, "per_page": 1}, quote_via=quote, safe="")
    commits = api(endpoint + "/commits?" + query, timeout=10)
    if not isinstance(commits, list) or len(commits) > 1:
        raise ValueError("GitHub returned malformed file mailbox commit history")
    result = {"status": "EMPTY", "commit_sha": None, "blob_sha": None, "text": "",
              "source_url": None, "branch": branch, "path": path, "byte_size": 0,
              "author_login": None, "author_id": None, "committer_login": None, "committer_id": None}
    if not commits:
        return result
    revision = commits[0]
    if not isinstance(revision, dict) or not isinstance(revision.get("sha"), str) or not _SHA.fullmatch(revision["sha"]):
        raise ValueError("GitHub returned an invalid file mailbox commit SHA")
    commit_sha = revision["sha"]
    encoded_path = quote(path, safe="/")
    metadata = api(f"{endpoint}/contents/{encoded_path}?ref={commit_sha}", timeout=10,
                   accept="application/vnd.github.object+json")
    _file_metadata(metadata, path)
    blob_sha, size = metadata["sha"], metadata["size"]
    data = metadata
    if metadata.get("encoding") == "none":
        if metadata.get("content") is not None and metadata.get("content") != "":
            raise ValueError("File mailbox contents response has an invalid omitted-body encoding")
        data = api(f"{endpoint}/git/blobs/{blob_sha}", timeout=10)
    raw = _decode(data, blob_sha, size)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("File mailbox must contain UTF-8 text, not binary data") from None
    if _CONTROL.search(text):
        raise ValueError("File mailbox contains binary/control characters")
    if text.startswith("version https://git-lfs.github.com/spec/v1\n") or text.startswith("version https://git-lfs.github.com/spec/v1\r\n"):
        raise ValueError("File mailbox cannot be a Git LFS pointer")
    author = revision.get("author") if isinstance(revision.get("author"), dict) else {}
    committer = revision.get("committer") if isinstance(revision.get("committer"), dict) else {}
    result.update(commit_sha=commit_sha, blob_sha=blob_sha, text=text, byte_size=size,
                  source_url=f"https://github.com/{remote}/blob/{commit_sha}/{encoded_path}",
                  author_login=author.get("login"), author_id=author.get("id"),
                  committer_login=committer.get("login"), committer_id=committer.get("id"))
    if not text.strip():
        return result
    commit = revision.get("commit")
    verification = commit.get("verification") if isinstance(commit, dict) else None
    web_committer = (committer.get("login") == "web-flow" and type(committer.get("id")) is int
                     and committer["id"] == WEB_FLOW_ID and committer.get("type") == "User")
    if (not _identity(author, user_id, login)
            or not (_identity(committer, user_id, login) or web_committer)
            or not isinstance(verification, dict) or verification.get("verified") is not True
            or verification.get("reason") != "valid"):
        raise ValueError("File mailbox instruction requires a verified owner-authored commit and trusted committer")
    result["status"] = "READY"
    return result


def write_reply(config, text, *, api, expected_blob_sha=_UNSET):
    """Observe or CAS-update the separate reply file with one PUT at most.

    An uncertain write is never retried here. On the next poll, the initial GET
    can prove whether the previous PUT already published the desired blob.
    Supplying an expected blob preserves a different result written since that
    observation. Explicit None conservatively expects no prior file; omitting
    the argument keeps the ordinary latest-notice replacement behavior.
    """
    remote, _, _, branch, inbox_path = _configuration(config)
    path = config.get("file_reply_path")
    if not _valid_path(path) or path == inbox_path:
        raise ValueError("File mailbox reply requires a separate repository-relative file path")
    if not isinstance(text, str) or _CONTROL.search(text):
        raise ValueError("File mailbox reply must be UTF-8 text without binary/control characters")
    if (expected_blob_sha is not _UNSET and expected_blob_sha is not None
            and (not isinstance(expected_blob_sha, str) or not _SHA.fullmatch(expected_blob_sha))):
        raise ValueError("Expected reply blob must be an immutable Git SHA or explicit None")
    try:
        raw = text.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("File mailbox reply must be valid UTF-8 text") from None
    desired = _blob_sha(raw)
    encoded_path = quote(path, safe="/")
    endpoint = f"repos/{remote}/contents/{encoded_path}"
    metadata = api(endpoint + "?" + urlencode({"ref": branch}, quote_via=quote, safe=""), timeout=10,
                   accept="application/vnd.github.object+json")
    _file_metadata(metadata, path)
    result = {"status": "OBSERVED", "blob_sha": desired, "commit_sha": None,
              "branch": branch, "path": path, "byte_size": len(raw)}
    if metadata["sha"] == desired:
        if metadata["size"] != len(raw):
            raise ValueError("File mailbox reply observed hash and size disagree")
        return result
    if expected_blob_sha is not _UNSET and metadata["sha"] != expected_blob_sha:
        result.update(status="PRESERVED", blob_sha=metadata["sha"], byte_size=metadata["size"])
        return result
    payload = {"branch": branch, "sha": metadata["sha"],
               "content": base64.b64encode(raw).decode("ascii"), "message": "Update McKernel mailbox reply [skip ci]"}
    try:
        response = api(endpoint, method="PUT", payload=payload, timeout=10)
        if not isinstance(response, dict):
            raise ValueError("Missing reply receipt")
        content, commit = response.get("content"), response.get("commit")
        _file_metadata(content, path)
        if (content["sha"] != desired or content["size"] != len(raw)
                or not isinstance(commit, dict) or not isinstance(commit.get("sha"), str)
                or not _SHA.fullmatch(commit["sha"])):
            raise ValueError("Mismatched reply receipt")
    except Exception:
        raise ReplyWriteError("File mailbox reply PUT outcome is unconfirmed; re-read before retrying") from None
    result.update(status="POSTED", commit_sha=commit["sha"])
    return result
