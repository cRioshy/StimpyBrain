import io
import unittest
from unittest.mock import patch

from stimpy.config import StimpyConfig
from stimpy.public_market_feed import CoinbasePublicTickerFeed
from stimpy.shitzo.models import SUPPORTED_SYMBOLS


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self,*_): self.close()


class ShitzoExtendedAssetTests(unittest.TestCase):
    def test_six_symbols_are_validated_and_default_for_future_runs(self):
        expected={"BTC-USD","ETH-USD","XRP-USD","SOL-USD","ADA-USD","DOGE-USD"}
        self.assertEqual(expected,set(SUPPORTED_SYMBOLS));self.assertEqual(expected,set(StimpyConfig.from_env().shitzo_symbols))

    def test_public_adapter_uses_get_only_product_endpoint_for_new_assets(self):
        requests=[]
        def open_fixture(request,timeout):
            requests.append((request.full_url,request.get_method(),timeout));return Response(b'{"price":"1.25","volume":"42"}')
        feed=CoinbasePublicTickerFeed(3)
        with patch("stimpy.public_market_feed.urllib.request.urlopen",open_fixture):
            ticks=[feed.read_latest(symbol) for symbol in ("SOL-USD","ADA-USD","DOGE-USD")]
        self.assertEqual(["SOL-USD","ADA-USD","DOGE-USD"],[tick.symbol for tick in ticks]);self.assertTrue(all(method=="GET" for _,method,_ in requests));self.assertEqual([f"https://api.exchange.coinbase.com/products/{symbol}/ticker" for symbol in ("SOL-USD","ADA-USD","DOGE-USD")],[url for url,_,_ in requests])


if __name__=="__main__":unittest.main()
