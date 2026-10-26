from custom_classes import Calculator

calc = Calculator()
print("Initial value:", calc._current_val)

total = calc.add(10, 5)
doubled = calc.multiply(total, 2)
result = calc.divide(doubled, 3)
print("10+5) * 2 / 3 =", result)

print("10-4=", calc.subtract(10, 4))
print("current value:", calc._current_val)

try:
    calc.divide(1, 0)
except ValueError as error:
    print("Error:", error)
