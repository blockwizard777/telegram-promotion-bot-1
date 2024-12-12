def classify_token_input(input_string):
    # Known valid URL patterns and their expected structures
    valid_url_patterns = {
        "movepump.com/token/": "move.pump",
        "app.turbos.finance/fun/#/fun/": "turbos.fun",
        "hop.ag/fun/": "hop.fun",
    }

    # Check if the input is a valid coinType (must have "::" exactly twice)
    if "::" in input_string and input_string.count("::") == 2 and input_string.startswith("0x"):
        return "coinType", {'coinType':input_string}  # Return the classification and the coinType itself
    
    # Check if the input is a valid launchURL
    for url_fragment, launchpad_name in valid_url_patterns.items():
        if url_fragment in input_string:
            # Validate the URL format by checking if it contains a valid coinType after the URL
            coin_type_part = input_string.split(url_fragment)[-1]
            if "::" in coin_type_part and coin_type_part.count("::") == 2 and coin_type_part.startswith("0x"):
                # Extract name and symbol from coinType part
                try:
                    _, name, symbol = coin_type_part.split("::")
                except ValueError:
                    return "invalid", f"Unable to parse name and symbol from: {coin_type_part}"
                
                return "launchURL", {
                    "launchPad": launchpad_name,
                    "launchURL": input_string,
                    "coinType": coin_type_part,
                    "name": name,
                    "symbol": symbol
                }
            else:
                return "invalid", f"Invalid launchURL format: {input_string}"
    
    # If it doesn't match any valid patterns
    return "invalid", f"Invalid input: {input_string}"


def generate_launchpad_url(launchpad, coin_type):
    if launchpad == 'move.pump':
        return f"https://movepump.com/token/{coin_type}"
    elif launchpad == 'turbos.fun':
        return f"https://app.turbos.finance/fun/#/fun/{coin_type}"
    elif launchpad == 'hop.fun':
        return f"https://hop.ag/fun/{coin_type}"
    else:
        return f"https://movepump.com/token/{coin_type}"

def parse_launchpad_url(launchpad_url):
    if "movepump.com/token/" in launchpad_url:
        launchpad = "move.pump"
        coin_type = launchpad_url.split("movepump.com/token/")[-1]
    elif "app.turbos.finance/fun/#/fun/" in launchpad_url:
        launchpad = "turbos.fun"
        coin_type = launchpad_url.split("app.turbos.finance/fun/#/fun/")[-1]
    elif "hop.ag/fun/" in launchpad_url:
        launchpad = "hop.fun"
        coin_type = launchpad_url.split("hop.ag/fun/")[-1]
    else:
        raise ValueError(f"Unrecognized launchpad URL: {launchpad_url}")

    return launchpad, coin_type


""" def check_url(launchpad_url):
        try:
            # Attempt to parse the URL
            launchpad, coin_type = parse_launchpad_url(launchpad_url)
            print(f"Launchpad: {launchpad}, Coin Type: {coin_type}")
        except ValueError as e:
            # If a ValueError is raised, print the error message
            print(f"Error detected: {e}")

# Test with a valid URL
check_url("https://movepump.com/token/0x9b90ec30683ec6573729c5b68290d0417beff525e12dfb0973509381848c222e::bapbul::BAPBUL")
# Expected Output: Launchpad: move.pump, Coin Type: 0x9b90ec30683ec6573729c5b68290d0417beff525e12dfb0973509381848c222e::bapbul::BAPBUL

# Test with an invalid (wrong) URL
check_url("https://unknownsite.com/token/0x123abc456def")
# Expected Output: Error detected: Unrecognized launchpad URL: https://unknownsite.com/token/0x123abc456def """