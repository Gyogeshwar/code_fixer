def check_even_or_odd(number):
    # Check if the number is even or odd
    if number % 2 == 0:
        return f"{number} is an even number."
    else:
        return f"{number} is an odd number."

# Example usage
user_input = int(input("Enter a number: "))
result = check_even_or_odd(user_input)
print(result)
