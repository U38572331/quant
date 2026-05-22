import sqlite3
import time

conn = sqlite3.connect("cftc_data.db")
c = conn.cursor()
# Delete Dow Jones data to force clean re-fetch
code = '124601'
c.execute("DELETE FROM cot_legacy WHERE cftc_contract_market_code=?", (code,))
conn.commit()
print(f"Deleted rows for {code}. Rows deleted: {c.rowcount}")
conn.close()
