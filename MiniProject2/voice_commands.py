"""Turn spoken library commands into REST calls, and API results into replies.

Everything here is a pure function: no Flask and no Azure, so it can be
tested on plain strings.

    parse_command(text)  -> {"intent", "method", "path", "body", "query", "item_id"}
    build_message(command, status, result, item=None) -> sentence for the librarian
"""

import re

# ---------- Numbers ----------

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    # Words the recognizer may hear instead of a number.
    "won": 1, "to": 2, "too": 2, "for": 4, "ate": 8,
}


def word_to_number(token):
    """Return the int for "7", "seven" or a homophone like "for", else None."""
    token = token.strip(" .,;:!?#").lower()
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


def to_int(value):
    """Turn a spoken amount ("250", "1,200", "twelve") into an int.

    If no number is found the text is returned unchanged so the API can
    reject it with its own 400 message.
    """
    match = re.search(r"\d[\d,]*", value)
    if match:
        return int(match.group().replace(",", ""))
    number = word_to_number(value)
    return number if number is not None else value


# ---------- Text clean-up ----------

# A single letter followed by a dot at the very end, e.g. "J.D." or "Plan B."
_INITIAL_AT_END = re.compile(r"(?:^|[\s.])[A-Za-z]\.$")


def strip_edges(text):
    """Trim spaces and separators; keep a final dot that belongs to an initial."""
    text = " ".join(text.split()).strip(" ,;:=-")
    while text and text[-1] in ".!?" and not _INITIAL_AT_END.search(text):
        text = text[:-1].rstrip(" ,;:=-")
    return text


_POLITE_PREFIX = re.compile(
    r"^(?:(?:please|hey|hi|hello|ok|okay|so|now|librarian|can you|could you|"
    r"would you|will you|i want to|i would like to|i'd like to|i need to|"
    r"let me|let's)\b[\s,]*)+",
    re.IGNORECASE)
_POLITE_SUFFIX = re.compile(r"[\s,]*\b(?:please|thanks|thank you)$", re.IGNORECASE)


def normalize(text):
    """Collapse spaces, drop polite words and trailing punctuation."""
    text = strip_edges(text or "")
    text = _POLITE_PREFIX.sub("", text)
    text = _POLITE_SUFFIX.sub("", text)
    return strip_edges(text)


# ---------- Item numbers ----------

_ITEM_NUMBER = re.compile(
    r"\bitem\b(?:\s+number\b|\s+no\.?|\s*#)?\s*#?\s*([A-Za-z0-9]+)", re.IGNORECASE)


def find_item_id(text):
    """Return (item_id, end_index) for "item 3" / "item number three", else (None, None)."""
    for match in _ITEM_NUMBER.finditer(text):
        number = word_to_number(match.group(1))
        if number is not None:
            return number, match.end()
    return None, None


# ---------- Item fields ----------

TYPE_WORDS = {
    "book": "book", "books": "book",
    "dvd": "dvd", "dvds": "dvd", "dvd's": "dvd",
    "movie": "dvd", "movies": "dvd", "film": "dvd", "films": "dvd",
}

# Spoken keyword -> API field name. Longer phrases are listed first.
FIELD_KEYWORDS = (
    ("type", r"type"),
    ("title", r"title|called|named"),
    ("author", r"directed by|written by|author|director|writer"),
    ("page_count", r"page count|number of pages|pages|page"),
    ("duration", r"running time|runtime|duration|minutes|mins"),
)
# "by" also means author, but only when no explicit author keyword is used,
# because "by" can appear inside titles ("Stand by Me").
BY_KEYWORD = ("author", r"by")

_NUMERIC_FIELDS = ("page_count", "duration")


def _keyword_pattern(alternatives):
    return re.compile(rf"(?<![\w.])(?:{alternatives})(?!\w)", re.IGNORECASE)


_FIELD_PATTERNS = [(field, _keyword_pattern(alts)) for field, alts in FIELD_KEYWORDS]
_BY_PATTERN = _keyword_pattern(BY_KEYWORD[1])


def _find_keywords(text):
    """Return non-overlapping (start, end, field) keyword matches in order."""
    found = [(m.start(), m.end(), field)
             for field, pattern in _FIELD_PATTERNS
             for m in pattern.finditer(text)]
    if not any(field == "author" for _, _, field in found):
        found += [(m.start(), m.end(), "author") for m in _BY_PATTERN.finditer(text)]
    # Earliest first; for the same start the longest phrase wins.
    found.sort(key=lambda hit: (hit[0], -(hit[1] - hit[0])))
    result, last_end = [], -1
    for start, end, field in found:
        if start >= last_end:
            result.append((start, end, field))
            last_end = end
    return result


def normalize_type(value):
    """Map "book" / "DVD" / "movie" to the API type; unknown words stay as said."""
    word = re.sub(r"^(?:a|an|the)\s+", "", value.strip(), flags=re.IGNORECASE)
    word = word.strip(" .,").lower()
    return TYPE_WORDS.get(word, word)


def extract_fields(text, lenient=False):
    """Read type/title/author/pages/duration values from a command.

    The value of a field is the text between its keyword and the next keyword.
    Titles and names keep their original spelling (e.g. "J.D. Salinger").

    Args:
        text: The part of the command that holds the fields.
        lenient: Also drop a leading "to"/"is"/"as" ("set title to Dune").

    Returns:
        (fields, head) where head is the text before the first keyword.
    """
    # "220 pages" -> "pages 220", "116 minutes" -> "duration 116"
    text = re.sub(r"\b(\d[\d,]*)\s*pages?\b", r"pages \1", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d[\d,]*)\s*(?:minutes?|mins?)\b", r"duration \1", text,
                  flags=re.IGNORECASE)

    keywords = _find_keywords(text)
    head = text[:keywords[0][0]] if keywords else text
    fields = {}
    for index, (_, end, field) in enumerate(keywords):
        stop = keywords[index + 1][0] if index + 1 < len(keywords) else len(text)
        value = strip_edges(text[end:stop])
        if field in _NUMERIC_FIELDS:
            value = re.sub(r"^(?:is|of|to|equals?)\s+", "", value, flags=re.IGNORECASE)
        elif lenient:
            value = re.sub(r"^(?:to|is|as)\s+", "", value, flags=re.IGNORECASE)
        value = strip_edges(re.sub(r"\s+(?:and|with)$", "", value, flags=re.IGNORECASE))
        if not value or field in fields:
            continue
        if field == "type":
            fields[field] = normalize_type(value)
        elif field in _NUMERIC_FIELDS:
            fields[field] = to_int(value)
        else:
            fields[field] = value
    return fields, head


# ---------- Intents ----------

_INTENT_PATTERNS = (
    ("help", r"(?:help|what can you do|what can i say)\b"),
    ("checkout", r"(?:check[\s-]?out|borrow|lend me)\b"),
    ("return", r"(?:return\b|(?:give|bring)\b.*\bback\b)"),
    ("delete", r"(?:delete|remove)\b"),
    ("replace", r"replace\b"),
    ("update", r"(?:update|change|edit|set|modify)\b"),
    ("create", r"(?:create|add|new)\b"),
    ("get", r"(?:tell me about|describe|get|show|display|find|look up|what is|what's)\b"),
    ("list", r"(?:list|show|display|find|get|what|which|give me)\b"),
)
_INTENT_REGEXES = [(name, re.compile(rx, re.IGNORECASE)) for name, rx in _INTENT_PATTERNS]

_CREATE_PREFIX = re.compile(
    r"^(?:create|add|new)\b\s*(?:(?:a|an|the|new|another)\s+)*"
    r"(?:(?P<type>books?|dvd'?s?|movies?|films?)\b)?\s*(?:items?\b)?",
    re.IGNORECASE)

_ITEM_ACTIONS = {
    # intent: (HTTP method, path suffix after /api/items/<id>)
    "get": ("GET", ""),
    "checkout": ("POST", "/checkout"),
    "return": ("POST", "/return"),
    "delete": ("DELETE", ""),
    "replace": ("PUT", ""),
    "update": ("PATCH", ""),
}

_LIST_UNAVAILABLE = re.compile(
    r"\b(?:checked[\s-]?out|borrowed|unavailable|not available|on loan)\b", re.IGNORECASE)
_LIST_AVAILABLE = re.compile(r"\b(?:available|in stock|on the shelf)\b", re.IGNORECASE)
_LIST_FILLER = {
    "me", "all", "the", "every", "of", "my", "your", "a", "an", "that", "are", "is",
    "there", "in", "library", "collection", "currently", "now", "you", "have", "do",
    "item", "items", "everything", "thing", "things", "any", "some", "which", "what",
    "for", "please",
}


def command(intent, method=None, path=None, body=None, query=None, item_id=None, **extra):
    """Build the dictionary that parse_command returns."""
    return {"intent": intent, "method": method, "path": path, "body": body,
            "query": query or {}, "item_id": item_id, **extra}


def _parse_list(rest):
    """Build GET /api/items with ?available= and ?type= from the spoken filters."""
    query = {}
    if _LIST_UNAVAILABLE.search(rest):
        query["available"] = "false"
        rest = _LIST_UNAVAILABLE.sub(" ", rest)
    elif _LIST_AVAILABLE.search(rest):
        query["available"] = "true"
        rest = _LIST_AVAILABLE.sub(" ", rest)

    words = [w for w in re.findall(r"[\w']+", rest.lower()) if w not in _LIST_FILLER]
    types = {TYPE_WORDS[w] for w in words if w in TYPE_WORDS}
    unknown = [w for w in words if w not in TYPE_WORDS]
    if len(types) == 1 and not unknown:
        query["type"] = types.pop()
    elif words:
        # An unknown kind ("magazines") is sent as said so the API answers 400.
        query["type"] = " ".join(words)
    return command("list", "GET", "/api/items", None, query)


def _parse_create(text):
    """Build POST /api/items from "create item, type book, title X, ..."."""
    prefix = _CREATE_PREFIX.match(text)
    spoken_type = normalize_type(prefix.group("type")) if prefix.group("type") else None
    fields, head = extract_fields(text[prefix.end():])

    # "add a book Dune by Frank Herbert" -> the text before the first keyword is the title.
    head = strip_edges(re.sub(r"^\s*(?:with|called|named)\b", "", head, flags=re.IGNORECASE))
    if "title" not in fields and head:
        fields["title"] = head

    item_type = fields.pop("type", None) or spoken_type
    if item_type is None:
        if "page_count" in fields:
            item_type = "book"
        elif "duration" in fields:
            item_type = "dvd"
    body = {"type": item_type} if item_type else {}
    for name in ("title", "author", "page_count", "duration"):
        if name in fields:
            body[name] = fields.pop(name)
    body.update(fields)
    return command("create", "POST", "/api/items", body)


def parse_command(text):
    """Turn a spoken sentence into the REST call it asks for.

    Returns:
        dict with intent, method, path, body, query and item_id. method is
        None for "help" and "unknown", which do not call the API.
    """
    text = normalize(text)
    if not text:
        return command("unknown")

    intent = next((name for name, rx in _INTENT_REGEXES if rx.match(text)), None)
    if intent is None:
        return command("unknown")
    if intent == "help":
        return command("help")
    if intent == "create":
        return _parse_create(text)

    item_id, id_end = find_item_id(text)
    if intent == "get" and item_id is None:
        intent = "list"
    if intent == "list":
        intents = dict(_INTENT_REGEXES)
        verb = intents["list"].match(text) or intents["get"].match(text)
        return _parse_list(text[verb.end():] if verb else text)

    if item_id is None:
        return command("unknown", reason="missing_item_id", requested=intent)

    method, suffix = _ITEM_ACTIONS[intent]
    path = f"/api/items/{item_id}{suffix}"
    body = None
    if intent in ("replace", "update"):
        body, _ = extract_fields(text[id_end:], lenient=(intent == "update"))
    return command(intent, method, path, body, item_id=item_id)


# ---------- Replies ----------

HELP_MESSAGE = (
    "You can say: list items, list available books, show DVDs, or list checked out items. "
    "Get item 3, check out item 3, return item 3, or delete item 3. "
    "Create item, type book, title, author, pages; or for a DVD, director and duration. "
    "Update item 3, pages 250. Or replace item 3, with title, author and pages.")

UNKNOWN_MESSAGE = "Sorry, I didn't understand that. Say 'help' to hear what I can do."

_FIELD_LABELS = {"title": "title", "page_count": "pages", "duration": "duration"}


def join_words(words):
    """Join a list as "A", "A and B" or "A, B, and C"."""
    words = list(words)
    if len(words) <= 2:
        return " and ".join(words)
    return ", ".join(words[:-1]) + f", and {words[-1]}"


def type_name(item_type):
    """Return the spoken name of an item type."""
    return "DVD" if item_type == "dvd" else (item_type or "item")


def describe_item(item):
    """Return "the book 'X' by Y, 220 pages" style text for an item dict."""
    title, author = item.get("title"), item.get("author")
    if item.get("type") == "book":
        return f"the book '{title}' by {author}, {item.get('page_count')} pages"
    if item.get("type") == "dvd":
        return f"the DVD '{title}' directed by {author}, {item.get('duration')} minutes"
    return f"the item '{title}' by {author}"


def _title_part(item_id, item):
    """Return "Item 4, 'X'," or "Item 4" when the title is not known."""
    if item and item.get("title"):
        return f"Item {item_id}, '{item['title']}',"
    return f"Item {item_id}"


def _change_text(field, item):
    """Return "pages is now 250" for one changed field."""
    value = item.get(field)
    if field == "author":
        return f"{'director' if item.get('type') == 'dvd' else 'author'} is now {value}"
    if field == "title":
        return f"title is now '{value}'"
    if field == "duration":
        return f"duration is now {value} minutes"
    return f"{_FIELD_LABELS.get(field, field)} is now {value}"


def _error_text(result):
    """Return the API error message without a final dot."""
    if isinstance(result, dict) and result.get("error"):
        return str(result["error"]).rstrip(". ")
    return "the request was not valid"


def build_message(cmd, status, result, item=None):
    """Return what the librarian says about the result of a command.

    Args:
        cmd: The dict returned by parse_command.
        status: HTTP status code of the API call (None if no call was made).
        result: JSON body of the API response (None for 204).
        item: The item as it was before the call (from a GET), used for titles.
    """
    intent = cmd.get("intent")
    item_id = cmd.get("item_id")

    if intent == "help":
        return HELP_MESSAGE
    if intent == "unknown":
        if cmd.get("reason") == "missing_item_id":
            return ("Sorry, which item? Please say the item number, "
                    f"for example '{cmd.get('requested', 'get')} item 3'.")
        return UNKNOWN_MESSAGE

    if status == 404:
        return f"Sorry, item {item_id} was not found." if item_id else "Sorry, that was not found."
    if status == 409:
        if intent == "checkout":
            return f"Sorry, item {item_id} is already checked out."
        if intent == "return":
            return f"Sorry, item {item_id} is not checked out."
        if intent == "delete":
            return f"Sorry, item {item_id} is checked out and cannot be deleted."
        return f"Sorry, I couldn't do that: {_error_text(result)}."
    if status == 400:
        return f"Sorry, I couldn't do that: {_error_text(result)}."

    if intent == "create" and status == 201:
        return (f"Successfully created {type_name(result.get('type'))} "
                f"'{result.get('title')}' with ID {result.get('id')}.")
    if intent == "list" and status == 200:
        if not result:
            return "There are no matching items."
        titles = [f"'{entry.get('title')}'" for entry in result]
        count = len(titles)
        if count > 5:
            return f"I found {count} items. The first 5 are: {join_words(titles[:5])}."
        noun = "item" if count == 1 else "items"
        return f"I found {count} {noun}: {join_words(titles)}."
    if intent == "get" and status == 200:
        state = "available" if result.get("is_available") else "checked out"
        return f"Item {result.get('id')} is {describe_item(result)}, and it is {state}."
    if intent == "replace" and status == 200:
        return f"Item {result.get('id')} has been replaced: it is now {describe_item(result)}."
    if intent == "update" and status == 200:
        changes = [_change_text(field, result) for field in (cmd.get("body") or {})]
        return f"Item {result.get('id')} has been updated: {join_words(changes)}."
    if intent == "delete" and status == 204:
        return f"{_title_part(item_id, item)} has been deleted."
    if intent == "checkout" and status == 200:
        current = (result or {}).get("item") or item
        message = f"{_title_part(item_id, current)} has been checked out."
        api_message = (result or {}).get("message", "")
        if "Handle with care" in api_message:
            reminder = api_message[api_message.index("Handle with care"):].rstrip(".")
            message += f" {reminder}."
        return message
    if intent == "return" and status == 200:
        current = (result or {}).get("item") or item
        return f"{_title_part(item_id, current)} has been returned. Thank you!"

    return f"Sorry, something went wrong (status {status})."
