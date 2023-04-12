class IdentityError(Exception):
    """
    Raised when there are issues with session / file identities. For example,
    when trying to set a file in a session that doesn't match the session
    identity.
    """
    ...


class MissingFilesError(Exception):
    """
    Raised when there are files missing that are expected to be there. Usually
    this means the file is missing from the subsection.
    """
    ...
