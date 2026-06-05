import re
import unicodedata


def normalize_search_text(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def search_matches(value, search):
    haystack = normalize_search_text(value)
    terms = normalize_search_text(search).split()
    return all(term in haystack for term in terms)
