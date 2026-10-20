"""Demo that calls every LibraryCollection method once, including each error."""

from custom_classes import (
    DVD,
    Book,
    ItemNotFoundError,
    ItemStateError,
    LibraryCollection,
    MediaItem,
)


def show(title):
    """Print a section heading."""
    print(f"\n--- {title} ---")


library = LibraryCollection()

show("add_item: ids are given in order")
gatsby_id = library.add_item(Book("The Great Gatsby", "F. Scott Fitzgerald", 180))
inception_id = library.add_item(DVD("Inception", "Christopher Nolan", 148))
magazine_id = library.add_item(MediaItem("National Geographic", "Various Authors"))
print("New ids:", gatsby_id, inception_id, magazine_id)

show("create_item: build a Book from plain values")
orwell = library.create_item("book", title="1984", author="George Orwell",
                             page_count=328)
print(orwell.to_dict())

show("get_item and to_dict")
print(library.get_item(inception_id).to_dict())

show("checkout (Book and DVD)")
print(library.get_item(gatsby_id).checkout())
print(library.get_item(inception_id).checkout())

show("checkout an item that is already out -> ItemStateError")
try:
    library.get_item(gatsby_id).checkout()
except ItemStateError as error:
    print("ItemStateError:", error)

show("list_items with filters")
print("All:      ", [item.title for item in library.list_items()])
print("Available:", [item.title for item in library.list_items(available=True)])
print("DVDs:     ", [item.title for item in library.list_items(item_type="dvd")])
print("list_available():", library.list_available())

show("list_items with a bad filter -> ValueError")
try:
    library.list_items(item_type="vinyl")
except ValueError as error:
    print("ValueError:", error)

show("return_item")
print(library.get_item(gatsby_id).return_item())

show("return an item that is not checked out -> ItemStateError")
try:
    library.get_item(gatsby_id).return_item()
except ItemStateError as error:
    print("ItemStateError:", error)

show("update_item: change some editable fields")
print(library.update_item(orwell.id, title="Nineteen Eighty-Four").to_dict())

show("update_item on id, type or is_available -> ValueError")
try:
    library.update_item(orwell.id, is_available=False)
except ValueError as error:
    print("ValueError:", error)

show("replace_item: set all editable fields")
print(library.replace_item(orwell.id, title="1984", author="George Orwell",
                           page_count=352).to_dict())

show("remove a checked-out item -> ItemStateError")
try:
    library.remove_item(inception_id)
except ItemStateError as error:
    print("ItemStateError:", error)

show("remove_item")
library.remove_item(magazine_id)
print("Removed item", magazine_id)

show("get a removed item -> ItemNotFoundError")
try:
    library.get_item(magazine_id)
except ItemNotFoundError as error:
    print("ItemNotFoundError:", error)

show("ids are never reused after a delete")
new_id = library.add_item(DVD("Arrival", "Denis Villeneuve", 116))
print("New DVD id:", new_id)

show("final collection")
for item in library.list_items():
    print(item)
