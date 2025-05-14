import sys
import json
import base64
import argparse


def decode_jwt(token):
    """
    Decode a JWT token without verification.

    Args:
        token: The JWT token to decode

    Returns:
        The decoded header and payload
    """
    # Split the token into parts
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format")

    # Decode the header and payload
    # Add padding if needed
    def decode_part(part):
        padding_needed = len(part) % 4
        if padding_needed:
            part += '=' * (4 - padding_needed)
        return base64.urlsafe_b64decode(part).decode('utf-8')

    header = json.loads(decode_part(parts[0]))
    payload = json.loads(decode_part(parts[1]))

    return header, payload


def main():
    parser = argparse.ArgumentParser(
        description='Decode JWT tokens from the web3 auth system')
    parser.add_argument('token', help='JWT token to decode')
    parser.add_argument('--raw', action='store_true',
                        help='Show raw decoded output')
    args = parser.parse_args()

    try:
        header, payload = decode_jwt(args.token)

        if args.raw:
            print("Header:", json.dumps(header, indent=2))
            print("Payload:", json.dumps(payload, indent=2))
        else:
            print(f"\n=== JWT Token Analysis ===")
            print(f"Algorithm: {header.get('alg')}")
            print(f"Token Type: {header.get('typ')}")

            print(f"\n=== Token Data ===")
            print(f"Subject: {payload.get('sub')}")
            print(f"Wallet Address: {payload.get('wallet_address')}")

            if 'exp' in payload:
                import datetime
                exp_time = datetime.datetime.fromtimestamp(payload['exp'])
                now = datetime.datetime.now()
                time_left = exp_time - now

                print(f"Expires: {exp_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Time remaining: {time_left}")
                print(
                    f"Token status: {'VALID' if time_left.total_seconds() > 0 else 'EXPIRED'}")

            # Check for additional claims
            other_claims = {k: v for k, v in payload.items() if k not in [
                'sub', 'wallet_address', 'exp']}
            if other_claims:
                print("\n=== Additional Claims ===")
                for key, value in other_claims.items():
                    print(f"{key}: {value}")

    except Exception as e:
        print(f"Error decoding token: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
