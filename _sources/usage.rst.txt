Usage
=====

Basic example
-------------

The main entry point of the library is the :class:`timescale_access.client.TimescaleAccess`
class. It wraps common operations against a TimescaleDB/PostgreSQL instance.

.. code-block:: python

   from timescale_access.client import TimescaleAccess

   db_url = "postgresql://user:password@localhost:5432/postgres"

   db = TimescaleAccess(db_url)

   # Check connection
   if not db.check_connection():
       raise RuntimeError("Could not connect to database")

   # Ensure schema exists
   db.ensure_schema_exists("raw_data")

   # Insert a DataFrame
   import pandas as pd
   from datetime import datetime

   df = pd.DataFrame(
       [
           {
               "instrument_name": "BTC-PERPETUAL",
               "trade_seq": 123456,
               "timestamp": datetime.utcnow(),
               "value": 42.0,
           }
       ]
   )

   db.insert_hypertable("raw_data", "btc_perp_trades", df)

   # Read back data
   result = db.get_table("raw_data", "btc_perp_trades")
   print(result.head())
