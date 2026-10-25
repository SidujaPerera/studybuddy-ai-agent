# Python Loops

*Sample demonstration note for Study Buddy (fictional, not a real student's notes).*

## for loops
A `for` loop repeats code once for each item in a sequence.

```python
for number in range(3):
    print(number)   # prints 0, 1, 2
```

- `range(3)` gives 0, 1 and 2 (it stops before 3).
- Use a `for` loop when you know how many times to repeat.

## while loops
A `while` loop repeats code as long as a condition is true.

```python
count = 0
while count < 3:
    print(count)
    count += 1      # without this line the loop never ends
```

## break and continue
- `break` stops the loop immediately.
- `continue` skips to the next repetition.

## Common mistakes
- Forgetting to change the variable in a `while` loop (infinite loop).
- Off-by-one errors: `range(1, 5)` gives 1, 2, 3, 4 - not 5.
