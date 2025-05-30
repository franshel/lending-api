
import requests
import json


def format_token_holding(token_data):
    """Format token holding data into a friendly, easy-to-analyze string."""
    # token_data = json.loads(token_data)

    print('TD', token_data)

    token_info = token_data.get('token', {})
    token_instance = token_data.get('token_instance', {})

    # Extract the most important details
    token_name = token_info.get('name', 'Unknown Token')
    token_symbol = token_info.get('symbol', 'N/A')
    token_type = token_info.get('type', 'Unknown Type')
    token_value = token_data.get('value', 'N/A')
    token_decimals = token_info.get('decimals', '0')

    token_circulating_market_cap = token_info.get(
        'circulating_market_cap', 'N/A')
    token_total_supply = token_info.get('total_supply', 'N/A')
    # Format value based on decimals if available
    try:
        decimal_value = float(token_value) / (10 ** int(token_decimals))
        formatted_value = f"{decimal_value:.4f}"
    except (ValueError, TypeError):
        formatted_value = token_value

    # Create readable summary
    summary = (
        f"Token: {token_name} ({token_symbol})\n"
        f"Type: {token_type}\n"
        f"Amount: {formatted_value} {token_symbol}\n"
        f"Circulating Market Cap: ${token_circulating_market_cap}\n"
        f"Total Supply: {token_total_supply} {token_symbol}\n"
    )

    # Add additional meaningful information if available
    if 'exchange_rate' in token_info:
        summary += f"Exchange Rate: ${token_info['exchange_rate']}\n"

    # Include metadata summary if this is an NFT
    if token_instance and token_instance.get('is_unique'):
        metadata = token_instance.get('metadata', {})
        if metadata:
            summary += f"NFT ID: {token_instance.get('id', 'N/A')}\n"
            summary += f"Name: {metadata.get('name', 'Unnamed NFT')}\n"
            summary += f"Description: {metadata.get('description', 'No description')[:100]}...\n"

    return summary

# Example usage with the provided JSON data


def get_token_holdings_data(wallet_address):

    try:
        response = requests.get(
            f"https://sepolia-blockscout.lisk.com/api/v2/addresses/{wallet_address}/token-balances",
            timeout=15)

        if response.status_code != 200:
            print(f"Failed to fetch token holdings: {response.status_code}")
            return []

        holdings_data = response.json()
        if not holdings_data:
            print(
                f"No token holdings found for wallet address: {wallet_address}")
            return []

        print(
            f"Retrieved {len(holdings_data)} token holdings for {wallet_address}")
        return holdings_data

    except Exception as e:
        print(
            f"Error retrieving token holdings for {wallet_address}: {str(e)}")
        return []


def get_token_holdings_summary(wallet_address):
    """
    Get token holdings for a wallet address.
    Returns an empty list if no holdings found.
    """
    results = []

    try:
        response = requests.get(
            f"https://sepolia-blockscout.lisk.com/api/v2/addresses/{wallet_address}/token-balances",
            timeout=15)

        if response.status_code != 200:
            print(f"Failed to fetch token holdings: {response.status_code}")
            return []

        holdings_data = response.json()
        print(holdings_data)
        if not holdings_data:
            print(
                f"No token holdings found for wallet address: {wallet_address}")
            return []

        results = [format_token_holding(holding) for holding in holdings_data]
        print(f"Processed {len(results)} token holdings for {wallet_address}")
        return results

    except Exception as e:
        print(
            f"Error processing token holdings for {wallet_address}: {str(e)}")
        return []
