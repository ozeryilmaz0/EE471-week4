"""Demo script that simulates checkouts in the library system."""
from custom_classes import MediaItem, Book, DVD, LibraryCollection

book = MediaItem("Clean Code", "Robert C. Martin")
movie = MediaItem("Inception", "Christopher Nolan")

print("--- Library items ---")
print(book)
print(movie)

print("\n--- Checking out the book ---")
print(book.checkout())
print(book)

print("\n--- Trying to check out the same book again ---")
print(book.checkout())

print("\n--- Final status ---")
print(book)
print(movie)

print("\n=== Part 3: Inheritance ===")

novel = Book("Dune", "Frank Herbert", 412)
print(novel)

dvd = DVD("Interstellar", "Christopher Nolan", 169)
print(dvd)

print("\n--- Checking out the DVD ---")
print(dvd.checkout())
print(dvd)

print("\n--- Trying to check out the same DVD again ---")
print(dvd.checkout())

print("\n=== Part 4: Library collection ===")

# Use new objects so the checkouts above do not affect this listing.
library = LibraryCollection()

pragmatic = Book("The Pragmatic Programmer", "Andrew Hunt", 352)
matrix = DVD("The Matrix", "The Wachowskis", 136)
magazine = MediaItem("National Geographic", "Various Authors")
orwell = Book("1984", "George Orwell", 328)

library.add_item(pragmatic)
library.add_item(matrix)
library.add_item(magazine)
library.add_item(orwell)

print("Available before checkout:", library.list_available())

print("\n--- Checking out 2 items ---")
print(pragmatic.checkout())
print(matrix.checkout())

print("\nAvailable after checkout:", library.list_available())