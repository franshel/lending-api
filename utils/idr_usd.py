# from fastapi import FastAPI, HTTPException
import asyncio
import httpx

# app = FastAPI()

EXCHANGE_API_URL = "https://open.er-api.com/v6/latest/USD"

# @app.get("/usd-to-idr")
async def get_usd_to_idr():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(EXCHANGE_API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            rate = data.get("rates", {}).get("IDR")
            if rate is None:
                raise Exception("IDR rate not found in response")
            # Convert IDR to USD (1/rate) and scale by 1e8 to avoid decimals
            idrtousd = int(1e8 * (1 / rate)) if rate else None
            
            return {"rate": idrtousd, "source": "open.er-api.com"}
        except httpx.RequestError:
            raise Exception("IDR rate not found in response")
        except Exception as e:
            raise Exception("IDR rate not found in response")

asyncio.run(get_usd_to_idr())