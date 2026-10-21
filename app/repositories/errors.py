class RepositoryError(Exception):
    """base error for the repository layer"""


class UserNotFoundError(RepositoryError):
    """the user does not exist"""


class SongNotFoundError(RepositoryError):
    """the song does not exist"""


class PlaylistNotFoundError(RepositoryError):
    """the playlist does not exist"""


class DuplicateSongError(RepositoryError):
    """the song is already in the playlist"""
