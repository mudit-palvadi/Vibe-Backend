def parse_tags(tags: str) -> list[str]:
    """splits the comma separated tags into a clean list"""
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


def join_tags(tags: list[str]) -> str:
    """joins the tags back into the comma separated form the api uses"""
    return ",".join(tags)
