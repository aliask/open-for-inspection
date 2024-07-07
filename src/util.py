import re
import unicodedata


def slugify(value: str) -> str:
    """
    Converts an unsafe input string into a hypenated slug
    
    Example: slugify("github.com/example/repo/") -> "github-com-example-repo"
    """
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return value.strip("-")