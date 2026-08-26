\# Pluang — Zapi reference

\> Data pasar Pluang lintas aset: order book, running trade, tradebook dan ringkasan broker per saham IDX, plus saham Amerika, emas, kripto, sinyal analis dan berita.

\*\*Base URL:\*\* \`https://api.zpi.web.id\`  
\*\*Auth:\*\* Send \`x-api-key: YOUR\_KEY\` header on every request. Get a free key at https://zpi.web.id/dashboard/keys.  
\*\*Response envelope:\*\* \`{ content, message, errors }\`  
\*\*Rate limit:\*\* 60 req/min on free tier.

\*\*Related:\*\*  
\- Detail page: https://zpi.web.id/api/finance/pluang  
\- Endpoint catalog: https://zpi.web.id/category/finance  
\- Concise index: https://zpi.web.id/llms.txt  
\- Full reference: https://zpi.web.id/llms-full.txt

\---

\#\# Pluang

\*\*Category:\*\* finance · \*\*Slug:\*\* \`pluang\`  
\*\*Detail page:\*\* https://zpi.web.id/api/finance/pluang

Data pasar Pluang lintas aset: order book, running trade, tradebook dan ringkasan broker per saham IDX, plus saham Amerika, emas, kripto, sinyal analis dan berita.

\*\*Tags:\*\* pluang, saham, idx, order-book, broker-summary, crypto, gold, finance

\#\#\# Resolve Stock Code

Tukar kode saham IDX jadi id numerik Pluang. Endpoint IDX lain berkunci pada id ini.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/resolve\`  
\- \*\*Cache TTL:\*\* 86400s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | yes | Stock code. Required. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/resolve?code=BBCA" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/resolve?code=BBCA", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/resolve?code=BBCA",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "code": "BBCA",  
  "source": "pluang",  
  "stockId": 10020  
}  
\`\`\`

\---

\#\#\# Quote

Kutipan satu saham IDX berikut key stats yang Pluang tampilkan: kapitalisasi pasar, volume, lot, turnover, harga rata-rata, IEP/IEV. Terima \`code\` atau \`stockId\`.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/quote\`  
\- \*\*Cache TTL:\*\* 30s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/quote?code=BBCA\&stockId=10020" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/quote?code=BBCA\&stockId=10020", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/quote?code=BBCA\&stockId=10020",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "code": "BBCA",  
  "source": "pluang",  
  "stockId": 10020,  
  "keyStats": {  
    "avg": "6,328.83",  
    "iep": "6,350",  
    "iev": "158.78K",  
    "lot": "569.54K",  
    "val": "360.45B",  
    "vol": "56.95M",  
    "turnover": "360.45B",  
    "market\_cap": "778.02T"  
  },  
  "highestIndicativePrice": 6350  
}  
\`\`\`

\---

\#\#\# Multi Quote

Snapshot bid/ask/OHLC beberapa saham sekaligus, maksimal 20 instrumen per panggilan.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/summary\`  
\- \*\*Cache TTL:\*\* 30s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`codes\` | string | query | no | Comma-separated stock codes, max 20\. |  
| \`stockIds\` | string | query | no | Comma-separated numeric ids, max 20\. Alternative to \`codes\`. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/summary?codes=BBCA%2CTLKM\&stockIds=10020%2C10048" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/summary?codes=BBCA%2CTLKM\&stockIds=10020%2C10048", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/summary?codes=BBCA%2CTLKM\&stockIds=10020%2C10048",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "count": 2,  
  "items": \[  
    {  
      "ask": 6350,  
      "bid": 6325,  
      "low": 6275,  
      "code": "BBCA",  
      "high": 6350,  
      "open": 6300,  
      "volume": 56953500,  
      "stockId": 10020,  
      "lastPrice": 6350,  
      "previousClose": 6375  
    },  
    {  
      "ask": 2620,  
      "bid": 2610,  
      "low": 2590,  
      "code": "TLKM",  
      "high": 2630,  
      "open": 2600,  
      "volume": 80799200,  
      "stockId": 10175,  
      "lastPrice": 2620,  
      "previousClose": 2590  
    }  
  \],  
  "source": "pluang"  
}  
\`\`\`

\---

\#\#\# Reference Prices

Harga acuan di tiap horizon — 1 hari, 1 minggu, 1 bulan, 3 bulan, YTD, 1 tahun, 5 tahun. Yang dikirim harga, bukan persentase.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/price-change\`  
\- \*\*Cache TTL:\*\* 300s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/price-change?code=BBCA\&stockId=10020" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/price-change?code=BBCA\&stockId=10020", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/price-change?code=BBCA\&stockId=10020",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "ytd": 8075,  
  "code": "BBCA",  
  "basis": "reference price at each horizon",  
  "oneDay": 6375,  
  "source": "pluang",  
  "oneWeek": 6375,  
  "oneYear": 8775,  
  "stockId": 10020,  
  "fiveYear": 6410,  
  "oneMonth": 6125,  
  "threeMonth": 6100  
}  
\`\`\`

\---

\#\#\# Intraday Chart

Candle intraday satu sesi, berjarak 5 menit. Upstream hanya melayani satu timeframe; riwayat panjang ada di \`finance:idx/stock-history\`.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/chart\`  
\- \*\*Cache TTL:\*\* 60s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/chart?code=BBCA\&stockId=10020" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/chart?code=BBCA\&stockId=10020", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/chart?code=BBCA\&stockId=10020",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "code": "BBCA",  
  "count": 85,  
  "items": \[  
    {  
      "low": 6300,  
      "high": 6300,  
      "open": 6300,  
      "close": 6300,  
      "volume": 1428700,  
      "endTime": "2026-08-14T02:00:00Z",  
      "startTime": "2026-08-14T01:55:00Z"  
    },  
    {  
      "low": 6300,  
      "high": 6350,  
      "open": 6300,  
      "close": 6325,  
      "volume": 1049800,  
      "endTime": "2026-08-14T02:05:00Z",  
      "startTime": "2026-08-14T02:00:00Z"  
    },  
    {  
      "low": 6325,  
      "high": 6350,  
      "open": 6325,  
      "close": 6350,  
      "volume": 106600,  
      "endTime": "2026-08-14T02:10:00Z",  
      "startTime": "2026-08-14T02:05:00Z"  
    },  
    {  
      "low": 6325,  
      "high": 6350,  
      "open": 6350,  
      "close": 6325,  
      "volume": 1256000,  
      "endTime": "2026-08-14T02:15:00Z",  
      "startTime": "2026-08-14T02:10:00Z"  
    },  
    {  
      "low": 6325,  
      "high": 6350,  
      "open": 6325,  
      "close": 6325,  
      "volume": 287800,  
      "endTime": "2026-08-14T02:20:00Z",  
      "startTime": "2026-08-14T02:15:00Z"  
    },  
    {  
      "low": 6325,  
      "high": 6350,  
      "open": 6325,  
      "close": 6325,  
      "volume": 532800,  
      "endTime": "2026-08-14T02:25:00Z",  
      "startTime": "2026-08-14T02:20:00Z"  
    }  
  \],  
  "source": "pluang",  
  "stockId": 10020,  
  "timeFrame": "1d",  
  "intervalSeconds": 300  
}  
\`\`\`

\---

\#\#\# Order Book

Antrean bid dan ask satu saham IDX beserta lot-nya, plus porsi bid/ask.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/orderbook\`  
\- \*\*Cache TTL:\*\* 15s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/orderbook?code=BBCA\&stockId=10020" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/orderbook?code=BBCA\&stockId=10020", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/orderbook?code=BBCA\&stockId=10020",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "asks": \[  
    {  
      "lots": 14620,  
      "price": 6350  
    }  
  \],  
  "bids": \[  
    {  
      "lots": 17597,  
      "price": 6325  
    }  
  \],  
  "code": "BBCA",  
  "source": "pluang",  
  "bestAsk": 6350,  
  "bestBid": 6325,  
  "stockId": 10020,  
  "askCount": 1,  
  "bidCount": 1,  
  "askPercent": 45,  
  "bidPercent": 55  
}  
\`\`\`

\---

\#\#\# Running Trade

Tiap cetakan transaksi satu saham, terbaru dulu, dengan kursor untuk menarik lebih dalam. Bisa disaring per sisi agresor dan ambang lot. Tidak ada kode broker per cetakan.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/running-trades\`  
\- \*\*Cache TTL:\*\* 15s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |  
| \`action\` | enum(BUY|SELL) | query | no | Keep one aggressor side. Filtered here — the upstream ignores its own tab parameter. |  
| \`minLot\` | number | query | no | Keep prints of at least this many lots (big-print filter). |  
| \`cursor\` | string | query | no | Continue from a previous response's \`nextCursor\`. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/running-trades?code=BBCA\&stockId=10020\&action=BUY\&minLot=500\&cursor=MTA3MTY%3D" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/running-trades?code=BBCA\&stockId=10020\&action=BUY\&minLot=500\&cursor=MTA3MTY%3D", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/running-trades?code=BBCA\&stockId=10020\&action=BUY\&minLot=500\&cursor=MTA3MTY%3D",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "code": "BBCA",  
  "count": 19,  
  "items": \[  
    {  
      "lots": 200,  
      "time": "15:49:51",  
      "price": 6350,  
      "action": "BUY",  
      "sequence": 10989  
    },  
    {  
      "lots": 155,  
      "time": "15:49:51",  
      "price": 6350,  
      "action": "BUY",  
      "sequence": 10977  
    },  
    {  
      "lots": 104,  
      "time": "15:49:51",  
      "price": 6350,  
      "action": "BUY",  
      "sequence": 10958  
    },  
    {  
      "lots": 1355,  
      "time": "15:49:51",  
      "price": 6350,  
      "action": "BUY",  
      "sequence": 10955  
    },  
    {  
      "lots": 137,  
      "time": "15:49:48",  
      "price": 6325,  
      "action": "SELL",  
      "sequence": 10942  
    },  
    {  
      "lots": 130,  
      "time": "15:49:45",  
      "price": 6350,  
      "action": "BUY",  
      "sequence": 10927  
    }  
  \],  
  "minLot": 100,  
  "source": "pluang",  
  "fetched": 332,  
  "stockId": 10020,  
  "nextCursor": "MTA3MTY="  
}  
\`\`\`

\---

\#\#\# Tradebook

Rekap transaksi per harga, per waktu, dan per volume — ketiganya dikirim sekaligus, lengkap dengan sesi pra dan pasca.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/tradebook\`  
\- \*\*Cache TTL:\*\* 30s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |  
| \`tab\` | enum(ALL|PRICE|TIME|VOLUME) | query | no | Which block fills \`items\`: PRICE (default), TIME or VOLUME. ALL returns the price block. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/tradebook?code=BBCA\&stockId=10020\&tab=PRICE" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/tradebook?code=BBCA\&stockId=10020\&tab=PRICE", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/tradebook?code=BBCA\&stockId=10020\&tab=PRICE",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "tab": "PRICE",  
  "code": "BBCA",  
  "count": 4,  
  "items": \[  
    {  
      "price": 6350,  
      "buyFreq": 2489,  
      "buyLots": 53734,  
      "preFreq": 0,  
      "preLots": 0,  
      "postFreq": 140,  
      "postLots": 8465,  
      "sellFreq": 0,  
      "sellLots": 0,  
      "totalFreq": 3105,  
      "totalLots": 220983  
    },  
    {  
      "price": 6325,  
      "buyFreq": 1975,  
      "buyLots": 90923,  
      "preFreq": 0,  
      "preLots": 0,  
      "postFreq": 0,  
      "postLots": 0,  
      "sellFreq": 3125,  
      "sellLots": 125284,  
      "totalFreq": 5100,  
      "totalLots": 216207  
    },  
    {  
      "price": 6300,  
      "buyFreq": 230,  
      "buyLots": 31328,  
      "preFreq": 365,  
      "preLots": 14287,  
      "postFreq": 0,  
      "postLots": 0,  
      "sellFreq": 2789,  
      "sellLots": 85247,  
      "totalFreq": 3384,  
      "totalLots": 130862  
    },  
    {  
      "price": 6275,  
      "buyFreq": 0,  
      "buyLots": 0,  
      "preFreq": 0,  
      "preLots": 0,  
      "postFreq": 0,  
      "postLots": 0,  
      "sellFreq": 74,  
      "sellLots": 1483,  
      "totalFreq": 74,  
      "totalLots": 1483  
    }  
  \],  
  "byTime": \[\],  
  "source": "pluang",  
  "byPrice": \[  
    {  
      "price": 6350,  
      "buyFreq": 2489,  
      "buyLots": 53734,  
      "preFreq": 0,  
      "preLots": 0,  
      "postFreq": 140,  
      "postLots": 8465,  
      "sellFreq": 0,  
      "sellLots": 0,  
      "totalFreq": 3105,  
      "totalLots": 220983  
    },  
    {  
      "price": 6325,  
      "buyFreq": 1975,  
      "buyLots": 90923,  
      "preFreq": 0,  
      "preLots": 0,  
      "postFreq": 0,  
      "postLots": 0,  
      "sellFreq": 3125,  
      "sellLots": 125284,  
      "totalFreq": 5100,  
      "totalLots": 216207  
    },  
    {  
      "price": 6300,  
      "buyFreq": 230,  
      "buyLots": 31328,  
      "preFreq": 365,  
      "preLots": 14287,  
      "postFreq": 0,  
      "postLots": 0,  
      "sellFreq": 2789,  
      "sellLots": 85247,  
      "totalFreq": 3384,  
      "totalLots": 130862  
    },  
    {  
      "price": 6275,  
      "buyFreq": 0,  
      "buyLots": 0,  
      "preFreq": 0,  
      "preLots": 0,  
      "postFreq": 0,  
      "postLots": 0,  
      "sellFreq": 74,  
      "sellLots": 1483,  
      "totalFreq": 74,  
      "totalLots": 1483  
    }  
  \],  
  "stockId": 10020,  
  "byVolume": \[\]  
}  
\`\`\`

\---

\#\#\# Broker Summary

Ringkasan broker per saham atas rentang tanggal: lot, nilai, dan harga rata-rata tiap sisi. Upstream memberi sepuluh broker teratas, bukan tabel penuh.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/broker-summary\`  
\- \*\*Cache TTL:\*\* 300s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |  
| \`startDate\` | string | query | no | Range start (YYYY-MM-DD). Defaults to \`endDate\`. |  
| \`endDate\` | string | query | no | Range end (YYYY-MM-DD). Defaults to today. |  
| \`net\` | enum(true|false) | query | no | \`true\` (default) nets buy against sell per broker; \`false\` returns gross. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/broker-summary?code=BBCA\&stockId=10020\&startDate=2026-08-01\&endDate=2026-08-14\&net=true" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/broker-summary?code=BBCA\&stockId=10020\&startDate=2026-08-01\&endDate=2026-08-14\&net=true", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/broker-summary?code=BBCA\&stockId=10020\&startDate=2026-08-01\&endDate=2026-08-14\&net=true",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "net": true,  
  "code": "BBCA",  
  "count": 10,  
  "buyers": \[  
    {  
      "lots": 1310018,  
      "value": 832292697500,  
      "broker": "ZP",  
      "averagePrice": 6353  
    },  
    {  
      "lots": 307857,  
      "value": 196743635000,  
      "broker": "RX",  
      "averagePrice": 6390  
    },  
    {  
      "lots": 191390,  
      "value": 122735672500,  
      "broker": "AZ",  
      "averagePrice": 6412  
    },  
    {  
      "lots": 98308,  
      "value": 66368732500,  
      "broker": "BK",  
      "averagePrice": 6751  
    },  
    {  
      "lots": 70975,  
      "value": 44601875000,  
      "broker": "KZ",  
      "averagePrice": 6284  
    },  
    {  
      "lots": 54720,  
      "value": 35565697500,  
      "broker": "IF",  
      "averagePrice": 6499  
    }  
  \],  
  "capped": true,  
  "source": "pluang",  
  "endDate": "2026-08-14",  
  "sellers": \[  
    {  
      "lots": 441220,  
      "value": 280909935000,  
      "broker": "AK",  
      "averagePrice": 6366  
    },  
    {  
      "lots": 300363,  
      "value": 189810415000,  
      "broker": "CC",  
      "averagePrice": 6319  
    },  
    {  
      "lots": 240852,  
      "value": 153742430000,  
      "broker": "NI",  
      "averagePrice": 6383  
    },  
    {  
      "lots": 140832,  
      "value": 89638357500,  
      "broker": "LG",  
      "averagePrice": 6364  
    },  
    {  
      "lots": 137094,  
      "value": 87217600000,  
      "broker": "PD",  
      "averagePrice": 6361  
    },  
    {  
      "lots": 129971,  
      "value": 83048745000,  
      "broker": "BB",  
      "averagePrice": 6389  
    }  
  \],  
  "stockId": 10020,  
  "startDate": "2026-08-01"  
}  
\`\`\`

\---

\#\#\# Broker List

Daftar induk broker IDX menurut Pluang, dengan klasifikasi lokal/asing versi mereka.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/brokers\`  
\- \*\*Cache TTL:\*\* 86400s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`type\` | enum(LOCAL|FOREIGN) | query | no | Keep one broker type, as Pluang classifies it. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/brokers?type=FOREIGN" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/brokers?type=FOREIGN", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/brokers?type=FOREIGN",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "type": "FOREIGN",  
  "count": 23,  
  "items": \[  
    {  
      "code": "AG",  
      "name": "Kiwoom Sekuritas Indonesia",  
      "type": "FOREIGN"  
    },  
    {  
      "code": "AH",  
      "name": "Shinhan Sekuritas Indonesia",  
      "type": "FOREIGN"  
    },  
    {  
      "code": "AI",  
      "name": "UOB Kay Hian Sekuritas",  
      "type": "FOREIGN"  
    },  
    {  
      "code": "AK",  
      "name": "UBS Sekuritas Indonesia",  
      "type": "FOREIGN"  
    },  
    {  
      "code": "BK",  
      "name": "J.P. Morgan Sekuritas Indonesia",  
      "type": "FOREIGN"  
    },  
    {  
      "code": "BQ",  
      "name": "Korea Investment and Sekuritas Indonesia",  
      "type": "FOREIGN"  
    }  
  \],  
  "source": "pluang"  
}  
\`\`\`

\---

\#\#\# Fundamentals

EPS aktual per kuartal, ikhtisar, dan rasio valuasi/profitabilitas satu emiten.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/fundamentals\`  
\- \*\*Cache TTL:\*\* 21600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/fundamentals?code=BBCA\&stockId=10020" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/fundamentals?code=BBCA\&stockId=10020", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/fundamentals?code=BBCA\&stockId=10020",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "code": "BBCA",  
  "ratios": {  
    "dividend": {  
      "ttm": "5.61%",  
      "payoutRatio": "0.12%",  
      "dividendPerShare": "55"  
    },  
    "solvency": {  
      "cr": "-",  
      "de": "4.6%"  
    },  
    "valuation": {  
      "pb": "2.78x",  
      "pe": "13.61x",  
      "ps": "6.09x",  
      "cps": "Rp207.35",  
      "rps": "Rp1,042.5",  
      "cfps": "-"  
    },  
    "profitability": {  
      "gpm": "56.01%",  
      "npm": "45.22%",  
      "opm": "56.01%",  
      "roa": "3.63%",  
      "roe": "20.44%"  
    }  
  },  
  "source": "pluang",  
  "stockId": 10020,  
  "earnings": \[  
    {  
      "quarter": "Q2 '25",  
      "actualEps": 475.51  
    },  
    {  
      "quarter": "Q3 '25",  
      "actualEps": 474.12  
    },  
    {  
      "quarter": "Q4 '25",  
      "actualEps": 466.74  
    },  
    {  
      "quarter": "Q1 '26",  
      "actualEps": 481.28  
    },  
    {  
      "quarter": "Q2 '26",  
      "actualEps": 484  
    }  
  \],  
  "overview": {  
    "eps": "Rp466.74",  
    "bvps": "Rp2,283.24",  
    "revenue": "Rp127.23T",  
    "net\_income": "Rp57.54T",  
    "gross\_profit": "Rp71.26T"  
  },  
  "lastUpdated": "Last updated on 29 Jul 2026"  
}  
\`\`\`

\---

\#\#\# Financial Statements

Neraca, arus kas, dan laba rugi satu emiten, kuartalan maupun tahunan.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/financials\`  
\- \*\*Cache TTL:\*\* 21600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |  
| \`period\` | enum(quarterly|annually|both) | query | no | Which period block to return. Default both. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/financials?code=BBCA\&stockId=10020\&period=quarterly" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/financials?code=BBCA\&stockId=10020\&period=quarterly", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/financials?code=BBCA\&stockId=10020\&period=quarterly",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "code": "BBCA",  
  "period": "quarterly",  
  "source": "pluang",  
  "stockId": 10020,  
  "quarterly": {  
    "cashFlow": {  
      "chart": \[  
        {  
          "netCF": 0,  
          "finance": \-33082545000000,  
          "investing": 13076544000000,  
          "operating": 40923218000000,  
          "timeframe": "Q2\\n’25"  
        },  
        {  
          "netCF": 0,  
          "finance": \-32695944000000,  
          "investing": \-18460091000000,  
          "operating": 65931980000000,  
          "timeframe": "Q3\\n’25"  
        },  
        {  
          "netCF": 0,  
          "finance": \-41708637000000,  
          "investing": \-33690926000000,  
          "operating": 77508785000000,  
          "timeframe": "Q4\\n’25"  
        },  
        {  
          "netCF": 0,  
          "finance": \-1072636000000,  
          "investing": \-16987375000000,  
          "operating": 47920728000000,  
          "timeframe": "Q1\\n’26"  
        },  
        {  
          "netCF": 0,  
          "finance": 10516285000000,  
          "investing": \-34324511000000,  
          "operating": 32261974000000,  
          "timeframe": "Q2\\n’26"  
        }  
      \],  
      "table": \[  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q2 2025"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "CF from Operations"  
              },  
              "column2": {  
                "value": "Rp40.92T"  
              },  
              "column3": {  
                "color": "\#FF7570",  
                "value": "-12.63%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "CF from Investment"  
              },  
              "column2": {  
                "value": "Rp13.08T"  
              },  
              "column3": {  
                "color": "\#FF7570",  
                "value": "-144.07%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "CF from Financing"  
              },  
              "column2": {  
                "value": "Rp33.08T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+15.78%"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#6B7072"  
            }  
          \],  
          "title": "Q2\\n’25",  
          "isSelected": false  
        },  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q3 2025"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "CF from Operations"  
              },  
              "column2": {  
                "value": "Rp65.93T"  
              },  
              "column3": {  
                "color": "\#FF7570",  
                "value": "-11.12%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "CF from Investment"  
              },  
              "column2": {  
                "value": "Rp18.46T"  
              },  
              "column3": {  
                "color": "\#FF7570",  
                "value": "-72.89%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "CF from Financing"  
              },  
              "column2": {  
                "value": "Rp32.7T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+14.42%"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#6B7072"  
            }  
          \],  
          "title": "Q3\\n’25",  
          "isSelected": false  
        },  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q4 2025"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "CF from Operations"  
              },  
              "column2": {  
                "value": "Rp77.51T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+44.01%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "CF from Investment"  
              },  
              "column2": {  
                "value": "Rp33.69T"  
              },  
              "column3": {  
                "color": "\#FF7570",  
                "value": "-42.85%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "CF from Financing"  
              },  
              "column2": {  
                "value": "Rp41.71T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+25.14%"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#6B7072"  
            }  
          \],  
          "title": "Q4\\n’25",  
          "isSelected": false  
        },  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q1 2026"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "CF from Operations"  
              },  
              "column2": {  
                "value": "Rp47.92T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+36.2%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "CF from Investment"  
              },  
              "column2": {  
                "value": "Rp16.99T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+294.98%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "CF from Financing"  
              },  
              "column2": {  
                "value": "Rp1.07T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+49103.49%"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#6B7072"  
            }  
          \],  
          "title": "Q1\\n’26",  
          "isSelected": false  
        },  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q2 2026"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "CF from Operations"  
              },  
              "column2": {  
                "value": "Rp32.26T"  
              },  
              "column3": {  
                "color": "\#FF7570",  
                "value": "-21.16%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "CF from Investment"  
              },  
              "column2": {  
                "value": "Rp34.32T"  
              },  
              "column3": {  
                "color": "\#FF7570",  
                "value": "-362.49%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "CF from Financing"  
              },  
              "column2": {  
                "value": "Rp10.52T"  
              },  
              "column3": {  
                "color": "\#FF7570",  
                "value": "-131.79%"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#6B7072"  
            }  
          \],  
          "title": "Q2\\n’26",  
          "isSelected": true  
        }  
      \],  
      "title": "Cash Flow"  
    },  
    "balanceSheet": {  
      "chart": \[  
        {  
          "assets": 1504118975000000,  
          "timeframe": "Q2\\n’25",  
          "debtToAsset": 0.82,  
          "liabilities": 1233079977000000  
        },  
        {  
          "assets": 1538501812000000,  
          "timeframe": "Q3\\n’25",  
          "debtToAsset": 0.81,  
          "liabilities": 1251857118000000  
        },  
        {  
          "assets": 1586828536000000,  
          "timeframe": "Q4\\n’25",  
          "debtToAsset": 0.82,  
          "liabilities": 1294508286000000  
        },  
        {  
          "assets": 1640830566000000,  
          "timeframe": "Q1\\n’26",  
          "debtToAsset": 0.84,  
          "liabilities": 1370360247000000  
        },  
        {  
          "assets": 1660579336000000,  
          "timeframe": "Q2\\n’26",  
          "debtToAsset": 0.83,  
          "liabilities": 1379511881000000  
        }  
      \],  
      "table": \[  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q2 2025"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Total Assets"  
              },  
              "column2": {  
                "value": "Rp1504.12T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+5.52%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Liabilities"  
              },  
              "column2": {  
                "value": "Rp1233.08T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+4.83%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Equity"  
              },  
              "column2": {  
                "value": "Rp261.6T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+8.69%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Liabilities & Total Equity"  
              },  
              "column2": {  
                "value": "Rp1494.68T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+5.48%"  
              },  
              "viewType": "subheader"  
            }  
          \],  
          "title": "Q2\\n’25",  
          "isSelected": false  
        },  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q3 2025"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Total Assets"  
              },  
              "column2": {  
                "value": "Rp1538.5T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+7.31%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Liabilities"  
              },  
              "column2": {  
                "value": "Rp1251.86T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+7.04%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Equity"  
              },  
              "column2": {  
                "value": "Rp276.42T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+8.07%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Liabilities & Total Equity"  
              },  
              "column2": {  
                "value": "Rp1528.27T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+7.22%"  
              },  
              "viewType": "subheader"  
            }  
          \],  
          "title": "Q3\\n’25",  
          "isSelected": false  
        },  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q4 2025"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Total Assets"  
              },  
              "column2": {  
                "value": "Rp1586.83T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+9.49%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Liabilities"  
              },  
              "column2": {  
                "value": "Rp1294.51T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+9.95%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Equity"  
              },  
              "column2": {  
                "value": "Rp281.47T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+7.17%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Liabilities & Total Equity"  
              },  
              "column2": {  
                "value": "Rp1575.97T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+9.44%"  
              },  
              "viewType": "subheader"  
            }  
          \],  
          "title": "Q4\\n’25",  
          "isSelected": false  
        },  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q1 2026"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Total Assets"  
              },  
              "column2": {  
                "value": "Rp1640.83T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+6.98%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Liabilities"  
              },  
              "column2": {  
                "value": "Rp1370.36T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+7.22%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Equity"  
              },  
              "column2": {  
                "value": "Rp259.13T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+5.2%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Liabilities & Total Equity"  
              },  
              "column2": {  
                "value": "Rp1629.49T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+6.9%"  
              },  
              "viewType": "subheader"  
            }  
          \],  
          "title": "Q1\\n’26",  
          "isSelected": false  
        },  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q2 2026"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Total Assets"  
              },  
              "column2": {  
                "value": "Rp1660.58T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+10.4%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Liabilities"  
              },  
              "column2": {  
                "value": "Rp1379.51T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+11.88%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Equity"  
              },  
              "column2": {  
                "value": "Rp270.44T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+3.38%"  
              },  
              "viewType": "subheader"  
            },  
            {  
              "column1": {  
                "value": "Total Liabilities & Total Equity"  
              },  
              "column2": {  
                "value": "Rp1649.95T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+10.39%"  
              },  
              "viewType": "subheader"  
            }  
          \],  
          "title": "Q2\\n’26",  
          "isSelected": true  
        }  
      \],  
      "title": "Balance Sheet"  
    },  
    "incomeStatement": {  
      "chart": \[  
        {  
          "revenue": 75713936000000,  
          "timeframe": "Q2\\n’25",  
          "profitMargin": 0.38,  
          "netProfitLoss": 29016414000000  
        },  
        {  
          "revenue": 114691174000000,  
          "timeframe": "Q3\\n’25",  
          "profitMargin": 0.38,  
          "netProfitLoss": 43397415000000  
        },  
        {  
          "revenue": 127229123000000,  
          "timeframe": "Q4\\n’25",  
          "profitMargin": 0.45,  
          "netProfitLoss": 57537287000000  
        },  
        {  
          "revenue": 37661317000000,  
          "timeframe": "Q1\\n’26",  
          "profitMargin": 0.39,  
          "netProfitLoss": 14684123000000  
        },  
        {  
          "revenue": 75842128000000,  
          "timeframe": "Q2\\n’26",  
          "profitMargin": 0.39,  
          "netProfitLoss": 29534446000000  
        }  
      \],  
      "table": \[  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q2 2025"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Revenue"  
              },  
              "column2": {  
                "value": "Rp75.71T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+28.64%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "Cost of Revenue"  
              },  
              "column2": {  
                "value": "Rp38.78T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+51.27%"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Gross Profit"  
              },  
              "column2": {  
                "value": "Rp35.79T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+7.74%"  
              },  
              "viewType": "subheader"  
            }  
          \],  
          "title": "Q2\\n’25",  
          "isSelected": false  
        },  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q3 2025"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Revenue"  
              },  
              "column2": {  
                "value": "Rp114.69T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+7.27%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "Cost of Revenue"  
              },  
              "column2": {  
                "value": "Rp58.86T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+6.9%"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Gross Profit"  
              },  
              "column2": {  
                "value": "Rp53.77T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+5.74%"  
              },  
              "viewType": "subheader"  
            }  
          \],  
          "title": "Q3\\n’25",  
          "isSelected": false  
        },  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q4 2025"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Revenue"  
              },  
              "column2": {  
                "value": "Rp127.23T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+5.29%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "Cost of Revenue"  
              },  
              "column2": {  
                "value": "Rp55.97T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+6.36%"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Gross Profit"  
              },  
              "column2": {  
                "value": "Rp71.26T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+4.46%"  
              },  
              "viewType": "subheader"  
            }  
          \],  
          "title": "Q4\\n’25",  
          "isSelected": false  
        },  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q1 2026"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Revenue"  
              },  
              "column2": {  
                "value": "Rp37.66T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+20.05%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "Cost of Revenue"  
              },  
              "column2": {  
                "value": "Rp19.08T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+37.1%"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Gross Profit"  
              },  
              "column2": {  
                "value": "Rp18.08T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+3.56%"  
              },  
              "viewType": "subheader"  
            }  
          \],  
          "title": "Q1\\n’26",  
          "isSelected": false  
        },  
        {  
          "items": \[  
            {  
              "column1": {  
                "value": "Item"  
              },  
              "column2": {  
                "value": "Q2 2026"  
              },  
              "column3": {  
                "value": "Y/Y Change"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Revenue"  
              },  
              "column2": {  
                "value": "Rp75.84T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+0.17%"  
              },  
              "viewType": "row"  
            },  
            {  
              "column1": {  
                "value": "Cost of Revenue"  
              },  
              "column2": {  
                "value": "Rp38.01T"  
              },  
              "column3": {  
                "color": "\#FF7570",  
                "value": "-1.97%"  
              },  
              "viewType": "row"  
            },  
            {  
              "dividerColor": "\#202224"  
            },  
            {  
              "column1": {  
                "value": "Gross Profit"  
              },  
              "column2": {  
                "value": "Rp36.45T"  
              },  
              "column3": {  
                "color": "\#08F691",  
                "value": "+1.84%"  
              },  
              "viewType": "subheader"  
            }  
          \],  
          "title": "Q2\\n’26",  
          "isSelected": true  
        }  
      \],  
      "title": "Income Statement"  
    }  
  }  
}  
\`\`\`

\---

\#\#\# Corporate Actions

Aksi korporasi yang lalu dan yang akan datang — dividen, split, RUPS — beserta tanggal cum, ex, dan pembayarannya.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/corporate-action\`  
\- \*\*Cache TTL:\*\* 21600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |  
| \`when\` | enum(past|upcoming|both) | query | no | Which set to return. Default both. |  
| \`type\` | string | query | no | Keep one action type, e.g. DIVIDEND. |  
| \`length\` | number | query | no | Rows per set (default 50, max 200\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/corporate-action?code=BBCA\&stockId=10020\&when=upcoming\&type=DIVIDEND\&length=20" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/corporate-action?code=BBCA\&stockId=10020\&when=upcoming\&type=DIVIDEND\&length=20", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/corporate-action?code=BBCA\&stockId=10020\&when=upcoming\&type=DIVIDEND\&length=20",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "code": "BBCA",  
  "past": \[  
    {  
      "id": "6a26c4508a75a80d34feef70",  
      "type": "DIVIDEND",  
      "title": "Dividend",  
      "value": "Rp20",  
      "fields": {  
        "Ex Date": "17 Jun '26",  
        "Cum Date": "15 Jun '26",  
        "Pay Date": "26 Jun '26",  
        "Rec Date": "18 Jun '26"  
      }  
    },  
    {  
      "id": "69b806348cf6342e72f91bc8",  
      "type": "DIVIDEND",  
      "title": "Dividend",  
      "value": "Rp281",  
      "fields": {  
        "Ex Date": "30 Mar '26",  
        "Cum Date": "27 Mar '26",  
        "Pay Date": "08 Apr '26",  
        "Rec Date": "31 Mar '26"  
      }  
    },  
    {  
      "id": "6925af95dcb9d0863b0f1890",  
      "type": "DIVIDEND",  
      "title": "Dividend",  
      "value": "Rp55",  
      "fields": {  
        "Ex Date": "03 Dec '25",  
        "Cum Date": "02 Dec '25",  
        "Pay Date": "22 Dec '25",  
        "Rec Date": "04 Dec '25"  
      }  
    },  
    {  
      "id": "68beb46f3040ab65c8e21d21",  
      "type": "DIVIDEND",  
      "title": "Dividend",  
      "value": "Rp250",  
      "fields": {  
        "Ex Date": "21 Mar '25",  
        "Cum Date": "20 Mar '25",  
        "Pay Date": "11 Apr '25",  
        "Rec Date": "24 Mar '25"  
      }  
    },  
    {  
      "id": "68beb46f3040ab65c8e21d18",  
      "type": "DIVIDEND",  
      "title": "Dividend",  
      "value": "Rp50",  
      "fields": {  
        "Ex Date": "21 Nov '24",  
        "Cum Date": "20 Nov '24",  
        "Pay Date": "11 Dec '24",  
        "Rec Date": "22 Nov '24"  
      }  
    },  
    {  
      "id": "68beb46c4c4e4258101b1d10",  
      "type": "DIVIDEND",  
      "title": "Dividend",  
      "value": "Rp228",  
      "fields": {  
        "Ex Date": "25 Mar '24",  
        "Cum Date": "22 Mar '24",  
        "Pay Date": "04 Apr '24",  
        "Rec Date": "26 Mar '24"  
      }  
    }  
  \],  
  "type": "DIVIDEND",  
  "when": "both",  
  "count": 10,  
  "source": "pluang",  
  "stockId": 10020,  
  "upcoming": \[\]  
}  
\`\`\`

\---

\#\#\# Company Profile

Profil emiten menurut Pluang: sektor, sejarah, alamat, direksi, komisaris, pemegang saham, dan FAQ.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/company-profile\`  
\- \*\*Cache TTL:\*\* 86400s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/company-profile?code=BBCA\&stockId=10020" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/company-profile?code=BBCA\&stockId=10020", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/company-profile?code=BBCA\&stockId=10020",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "code": "BBCA",  
  "faqs": \[\],  
  "name": "PT. Bank Central Asia Tbk",  
  "about": "PT. Bank Central Asia, Tbk (the Company) was established under the name of N.V. Perseroan Dagang Dan Industrie Semarang Knitting Factory based on notarial deed No. 38 of Raden Mas  Soeprapto dated 10 August 1955, which was then changed to PT Bank Central Asia based on notarial deed No. 144 of Ridwan Suselo dated 21 May 1974.",  
  "sector": "Banks",  
  "source": "pluang",  
  "address": "Address: Menara BCA, Grand Indonesia\\nJl. MH Thamrin No. 1 \- Jakarta Pusat 10310\\nPhone: (021) 2358 8000\\nFax: (021) 2358 8300\\nEmail: investor\_relations@bca.co.id\\nWebsite: www.bca.co.id",  
  "stockId": 10020,  
  "directors": \[\],  
  "shareholders": \[  
    {  
      "name": "PT Dwimuria Investama (C)",  
      "share": 54.942  
    },  
    {  
      "name": "Share Ownership of \<5 \- Scripless",  
      "share": 42.134  
    },  
    {  
      "name": "Share Ownership of \<5 \- Scrip",  
      "share": 2.508  
    },  
    {  
      "name": "Treasury Stock",  
      "share": 0.351  
    },  
    {  
      "name": "Jahja Setiaatmadja (Komisaris)",  
      "share": 0.03  
    },  
    {  
      "name": "Tan Ho Hien/Subur (Direksi)",  
      "share": 0.01  
    }  
  \],  
  "commissioners": \[\]  
}  
\`\`\`

\---

\#\#\# Similar Stocks

Saham sejenis menurut Pluang, dengan perubahan harganya.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/similar-stocks\`  
\- \*\*Cache TTL:\*\* 21600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/similar-stocks?code=BBCA\&stockId=10020" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/similar-stocks?code=BBCA\&stockId=10020", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/similar-stocks?code=BBCA\&stockId=10020",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "code": "BBCA",  
  "count": 20,  
  "items": \[  
    {  
      "code": "BYAN",  
      "name": "Bayan Resources Tbk.",  
      "stockId": 10048,  
      "category": "INDO\_STOCK",  
      "priceChangePercent": "+20%"  
    },  
    {  
      "code": "MPRO",  
      "name": "Maha Properti Indonesia Tbk.",  
      "stockId": 10407,  
      "category": "INDO\_STOCK",  
      "priceChangePercent": "+17.92%"  
    },  
    {  
      "code": "SRAJ",  
      "name": "Sejahteraraya Anugrahjaya Tbk.",  
      "stockId": 10090,  
      "category": "INDO\_STOCK",  
      "priceChangePercent": "+15.38%"  
    },  
    {  
      "code": "ITMG",  
      "name": "Indo Tambangraya Megah Tbk",  
      "stockId": 10069,  
      "category": "INDO\_STOCK",  
      "priceChangePercent": "+2.35%"  
    },  
    {  
      "code": "AADI",  
      "name": "Adaro Andalan Indonesia Tbk.",  
      "stockId": 10520,  
      "category": "INDO\_STOCK",  
      "priceChangePercent": "+4.14%"  
    },  
    {  
      "code": "MGLV",  
      "name": "Panca Anugrah Wisesa Tbk.",  
      "stockId": 10928,  
      "category": "INDO\_STOCK",  
      "priceChangePercent": "+2.31%"  
    }  
  \],  
  "source": "pluang",  
  "stockId": 10020  
}  
\`\`\`

\---

\#\#\# Stock News

Berita per emiten IDX. Upstream membatasi 20 item per halaman, jadi jalannya paging.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/news\`  
\- \*\*Cache TTL:\*\* 900s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Stock code. Either this or \`stockId\` is required. |  
| \`stockId\` | number | query | no | Numeric Pluang asset id, 10000 or greater. Alternative to \`code\`. |  
| \`page\` | number | query | no | Page number, 1-based. Default 1\. |  
| \`size\` | number | query | no | Items per page, max 20 (upstream cap). Default 20\. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/news?code=BBCA\&stockId=10020\&page=1\&size=20" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/news?code=BBCA\&stockId=10020\&page=1\&size=20", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/news?code=BBCA\&stockId=10020\&page=1\&size=20",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "code": "BBCA",  
  "page": 1,  
  "size": 20,  
  "count": 20,  
  "items": \[  
    {  
      "title": "BCA DORONG PERTUMBUHAN UMKM MELALUI KREDIT RINGAN DAN EKOSISTEM BISNIS TERINTEGRASI",  
      "description": "PT Bank Central Asia Tbk (BCA) kembali mengukuhkan komitmennya dalam memperkuat ekosistem Usaha Mikro, Kecil, dan Menengah (UMKM) dengan menghadirkan BCA UMKM Fest 2026\. Menjelang perhelatan tahunan tersebut, BCA turut menghadirkan suku bunga kredit khusus bagi pelaku UMKM yang berlaku mulai 1 Juli 2026 hingga Januari 2027.\\n\\nPembiayaan khusus ini bertajuk Kredit Multiguna Usaha (KMU) Hari UMKM 2026\. Program ini menawarkan suku bunga mulai dari 5,81% eff p.a. serta jangka waktu kredit lebih panjang bagi UMKM, sehingga memberikan angsuran yang lebih ringan untuk pelaku usaha.\\n\\nWakil Presiden Direktur BCA John Kosasih menyampaikan, \\"Program pembiayaan ini diharapkan dapat membantu pelaku UMKM memperoleh akses modal lebih terjangkau sehingga mampu meningkatkan kapasitas produksi, memperluas jaringan usaha, melakukan investasi, hingga menciptakan lapangan kerja baru. Dukungan pembiayaan berkelanjutan juga menjadi bagian komitmen BCA mendorong pertumbuhan ekonomi nasional melalui penguatan sektor UMKM\\".\\n\\nSelain melalui KMU Hari UMKM 2026, BCA juga memiliki Kredit Multiguna Usaha MerDeKa (Material, Developer, dan Kontraktor) yang ditujukan bagi calon debitur di sektor properti, konstruksi, serta bahan bangunan. Produk ini diharapkan mampu menciptakan efek berganda terhadap penyerapan tenaga kerja lokal dan percepatan pertumbuhan ekonomi di sektor riil dan perumahan.\\n\\nLangkah ini melengkapi berbagai solusi pembiayaan inklusif BCA, termasuk transaksi dan pengembangan bisnis pelaku UMKM. Secara khusus, BCA turut mendorong pengembangan bisnis UMKM salah satunya melalui perhelatan BCA UMKM Fest 2026, yang akan digelar secara hybrid mulai 1 Agustus-20 September 2026 (online) dan pada 20-23 Agustus 2026 (offline) di Indonesia Arena, Senayan, Jakarta. Ajang ini diharapkan bisa menjadi wadah bagi pelaku usaha untuk memperluas akses pasar, mendapatkan edukasi, hingga akses pembiayaan.\\n\\n\\"BCA berharap kehadiran berbagai solusi pembiayaan ini dapat menjawab kebutuhan pelaku usaha di berbagai sektor. Kami percaya, dukungan optimal bagi pelaku UMKM dapat berkontribusi dalam skala lebih besar bagi ekonomi nasional hingga menciptakan lapangan kerja baru demi mendorong pertumbuhan ekonomi yang inklusif,\\" kata John Kosasih.\\n\\nPenyaluran kredit BCA ke sektor UKM menyentuh Rp134,6 triliun atau tumbuh 6% YoY per semester I 2026\. Dukungan BCA terhadap UMKM diwujudkan melalui pendekatan menyeluruh berbasis tiga pilar yaitu penguatan pembiayaan, pembinaan, dan transaksi.\\n\\nBCA tidak hanya membuka akses permodalan terjangkau, tetapi juga memberikan edukasi bisnis serta perluasan pasar lewat inisiatif BCA Bangga Lokal, BCA UMKM Fest, Sertifikasi Halal UMKM, dan UMKM Go Export. Kemudahan ini semakin lengkap dengan efisiensi pembayaran digital berbasis QRIS BCA, aplikasi Merchant BCA, hingga layanan myBCA. Integrasi seluruh ekosistem ini dihadirkan agar UMKM Indonesia dapat bertransformasi, naik kelas, serta memperkuat daya saing secara berkelanjutan di pasar domestik maupun global. (end)",  
      "publishedAt": "2026-08-04T09:30:24Z"  
    },  
    {  
      "title": "BCA TAWARKAN SUKU BUNGA KREDIT KHUSUS BAGI UMKM HINGGA JANUARI 2027",  
      "description": "PT Bank Central Asia Tbk (BBCA) atau BCA menawarkan suku bunga kredit khusus bagi usaha mikro, kecil, dan menengah (UMKM) yang berlaku mulai 1 Juni 2026 hingga Januari 2027.\\n\\nProgram itu dijalankan melalui pembiayaan bertajuk Kredit Multiguna Usaha (KMU) Hari UMKM 2026, dengan penawaran suku bunga mulai dari 5,81 persen efektif per tahun. Jangka waktu kredit juga diberikan lebih panjang bagi UMKM agar nilai angsuran lebih ringan.\\n\\n\\"Program pembiayaan ini diharapkan dapat membantu pelaku UMKM memperoleh akses modal lebih terjangkau, sehingga mampu meningkatkan kapasitas produksi, memperluas jaringan usaha, melakukan investasi, hingga menciptakan lapangan kerja baru,\\" kata Wakil Presiden Direktur BCA John Kosasih dalam keterangan tertulis di Jakarta, Kamis.\\n\\nSelain KMU Hari UMKM 2026, BCA juga memiliki program Kredit Multiguna Usaha MerDeKa (Material, Developer, dan Kontraktor) yang ditujukan bagi calon debitur di sektor properti, konstruksi, serta bahan bangunan.\\n\\nProduk tersebut diharapkan mampu menciptakan efek berganda terhadap penyerapan tenaga kerja lokal dan percepatan pertumbuhan ekonomi di sektor riil dan perumahan.\\n\\nUntuk mendukung UMKM, BCA akan mengadakan UMKM Fest 2026 yang digelar secara hibrida, dengan rincian perhelatan daring sepanjang 1 Agustus hingga 20 September 2026 dan perhelatan luring pada 20-23 Agustus 2026 di Indonesia Arena, Senayan, Jakarta.\\n\\nKegiatan itu bertujuan untuk menjadi wadah bagi pelaku usaha memperluas akses pasar, mendapatkan edukasi, hingga akses pembiayaan.\\n\\nJohn mengatakan berbagai dukungan itu diharapkan dapat menjawab kebutuhan pelaku usaha di berbagai sektor.\\n\\n\\"Kami percaya, dukungan optimal bagi pelaku UMKM dapat berkontribusi dalam skala lebih besar bagi ekonomi nasional hingga menciptakan lapangan kerja baru demi mendorong pertumbuhan ekonomi yang inklusif,\\" katanya lagi.\\n\\nPenyaluran kredit BCA ke sektor UKM menyentuh Rp134,6 triliun atau tumbuh 6 persen (year-on-year/yoy) per semester I-2026. Dukungan terhadap UMKM disalurkan melalui pendekatan berbasis tiga pilar, yaitu penguatan pembiayaan, pembinaan, dan transaksi. (end)",  
      "publishedAt": "2026-07-31T00:20:07Z"  
    },  
    {  
      "title": "BCA BERHARAP PIMPINAN BARU BI TERUS DORONG EKONOMI NASIONAL",  
      "description": "Presiden Direktur PT Bank Central Asia Tbk (BBCA) atau BCA, Hendra Lembong berharap pimpinan terbaru Bank Indonesia (BI) dapat terus membantu pertumbuhan ekonomi Indonesia semakin lebih baik ke depan.\\n\\n\\"Mengenai pertanyaan Gubernur BI, ya kita tunggu kabar berikutnya. Pesan untuk calon-calonnya, ya tentu selalu semangat untuk membantu pertumbuhan ekonomi Indonesia supaya lebih baik lagi,\\" ujar Hendra dalam Konferensi Pers Paparan Kinerja Semester I-2026 BCA di Jakarta, Selasa.\\n\\nTerkait estafet kepemimpinan pada bank sentral tersebut, Hendra menyatakan bahwa pihaknya masih terus mencermati dinamika dan perkembangan yang ada saat ini.\\n\\nSeiring dengan itu, EVP Corporate Communication & Social Responsibility BCA, Hera F. Haryn menyatakan harapannya untuk pimpinan baru BI dapat bersama-sama mendorong pertumbuhan ekonomi nasional.\\n\\n\\"Untuk terkait dengan Gubernur Bank Indonesia yang baru, kami berharap tetap memberikan semangat beliau untuk terus bersama-sama menumbuhkan perekonomian nasional, jadi bersama-sama,\\" ujar Hera.\\n\\nPada prinsipnya, BCA mendukung upaya pemerintah dan regulator memperkuat industri jasa keuangan, serta berkomitmen menjalankan bisnis dengan menjunjung tinggi prinsip kehati-hatian dan menerapkan manajemen risiko disiplin.\\n\\nSebagaimana diketahui, Menteri Sekretaris Negara (Mensesneg) Prasetyo Hadi menyatakan Presiden Prabowo Subianto telah menerima pengunduran diri Gubernur BI Perry Warjiyo dan akan menindaklanjutinya sesuai mekanisme yang diatur dalam Undang-Undang (UU) BI.\\n\\nPrasetyo menambahkan, sesuai ketentuan dalam Undang-Undang Bank Indonesia, jabatan Gubernur BI untuk sementara akan dijalankan oleh Deputi Gubernur Senior Destry Damayanti hingga gubernur definitif ditetapkan.\\n\\n\\"Untuk selanjutnya sesuai dengan Undang-Undang Bank Indonesia, jabatan Gubernur Bank Indonesia akan secara otomatis dijabat oleh Deputi Gubernur Senior yang selanjutnya akan menjalankan seluruh tugas sebagai Pejabat Gubernur Sementara. Di dalam catatan yang dimaksud dengan Deputi Gubernur Senior adalah ibu Destry Damayanti,\\" kata Prasetyo. (end)",  
      "publishedAt": "2026-07-29T00:24:39Z"  
    },  
    {  
      "title": "BCA CATAT LABA KONSOLIDASI Rp29,5 TRILIUN DI SEMESTER I-2026",  
      "description": "PT Bank Central Asia Tbk (BBCA) dan entitas anak, membukukan laba bersih sebesar Rp29,5 triliun pada semester I 2026, atau tumbuh tipis dibandingkan Rp28,5 triliun pada periode sama tahun sebelumnya.\\n\\nLaba perseroan ditopang oleh penyaluran kredit yang tumbuh 8 persen (yoy) mencapai Rp1.036 triliun pada semester I-2026, atau untuk pertama kalinya menembus level Rp1.000 triliun.\\n\\n\\"Kinerja pada paruh pertama 2026 ditopang berbagai hal, seperti BCA Expoversary 2026 dan penyaluran kredit produktif ke berbagai sektor. Kami memastikan penyaluran kredit perseroan dilakukan dengan selalu mempertimbangkan prinsip kehati-hatian dan kondisi likuiditas perusahaan,\\" ujar Presiden Direktur BCA Hendra Lembong dalam Paparan Publik di Jakarta, Selasa.\\n\\nCapaian kinerja perseroan ditopang oleh pendanaan yang solid, dengan pertumbuhan giro dan tabungan (CASA) sebesar 10,2 persen (yoy) mencapai Rp1.082 triliun pada semester I 2026.\\n\\nKemudian, total Dana Pihak Ketiga (DPK) perseroan tumbuh 7,9 persen (yoy) mencapai Rp1.284 triliun pada semester I 2026, dengan porsi CASA perseroan mencapai sekitar 84,3 persen dari total DPK, dan Cost of Fund (CoF) konsisten terjaga.\\n\\n\\"BCA berterima kasih atas seluruh kepercayaan nasabah setia selama ini, sehingga kami dapat terus tumbuh dan memberikan pelayanan terbaik,\\" ujar Hendra,.\\n\\nPenyaluran kredit perseroan ditopang oleh segmen pembiayaan produktif yang mencapai Rp802 triliun pada semester I 2026, atau tumbuh 11 persen (yoy).\\n\\nAdapun, penyaluran kredit produktif mencakup pembiayaan korporasi yang tumbuh 13,6 persen (yoy) menjadi Rp513,4 triliun, serta kredit komersial dan UKM dengan pertumbuhan 6,6 persen (yoy) menjadi Rp288,5 triliun pada semester I 2026.\\n\\nKemudian, kredit hijau (green financing) perseroan tumbuh 19 persen (yoy) mencapai Rp123 triliun pada semester I 2026, salah satunya ditopang pembiayaan berkelanjutan ke sektor Energi Baru Terbarukan (EBT) yang tumbuh hingga 82 persen (yoy) menjadi Rp7,7 triliun.\\n\\nSelain itu, kredit kendaraan bermotor listrik tumbuh 25 persen (yoy) mencapai Rp4 triliun pada semester I 2026.\\n\\nSementara itu, rasio loan at risk (LAR) dan non performing loan (NPL) terjaga masing-masing 4,9 persen dan 1,9 persen. Per Juni 2026, pendapatan non bunga perseroan tercatat senilai Rp13,2 triliun atau tumbuh 11 persen (yoy). (end)",  
      "publishedAt": "2026-07-29T00:15:19Z"  
    },  
    {  
      "title": "BCA BORONG 6 PENGHARGAAN BERGENGSI DI DIGITAL CX AWARDS 2026",  
      "description": "PT Bank Central Asia Tbk (BCA) meraih sejumlah penghargaan pada ajang Digital CX Awards 2026 yang digelar oleh lembaga publikasi independen The Digital Banker. Penghargaan tersebut diberikan atas berbagai inovasi digital BCA melalui platform myBCA, myBCA Bisnis, dan Ocean by BCA, yang terus dikembangkan untuk menghadirkan layanan perbankan yang relevan, mudah diakses, dan berorientasi pada kebutuhan nasabah.\\n\\nDigital CX Awards merupakan ajang penghargaan global yang mengevaluasi dan mengapresiasi institusi keuangan dengan inovasi pengalaman nasabah digital (Digital Customer Experience) yang paling menonjol, konsisten, dan berdampak masif.\\n\\nPresiden Direktur BCA, Hendra Lembong, menyatakan bahwa penghargaan ini jadi motivasi bagi BCA untuk terus menghadirkan inovasi yang relevan dan berdampak positif bagi seluruh nasabah.\\n\\n\\"Kami percaya bahwa transformasi digital harus selalu berpusat pada kebutuhan nasabah. Oleh karena itu, BCA terus mengembangkan berbagai platform dan layanan digital yang aman, mudah digunakan, dan mampu memberikan nilai tambah bagi nasabah individu maupun bisnis,\\" ujar Hendra.\\n\\nPada ajang tersebut, di tingkat nasional, myBCA meraih penghargaan sebagai Best Retail Bank for Digital CX \- Indonesia dan Ocean by BCA memperoleh predikat Highly Acclaimed untuk kategori Best Wholesale/Transaction Bank for Digital CX \- Indonesia.\\n\\nPada kategori Customer Journey/Strategy, Ocean by BCA mencatatkan pencapaian yang membanggakan dengan meraih penghargaan Outstanding Use of Digital Channels for Improved CX \- Wholesale Banking. Penghargaan ini menjadi pengakuan atas upaya BCA dalam mengoptimalkan kanal digital guna meningkatkan pengalaman dan kenyamanan nasabah korporasi dalam mengakses layanan perbankan.\\n\\nBCA juga meraih penghargaan Excellence in Consistent Multi-Language CX pada kategori Omni Channel, yang mencerminkan komitmen perseroan dalam menghadirkan pengalaman layanan yang konsisten dan inklusif bagi nasabah dari berbagai latar belakang melalui berbagai kanal interaksi.\\n\\nTidak hanya di tingkat nasional, Ocean by BCA dengan layanan myBCA Bisnis juga berhasil meraih penghargaan regional sebagai Best Wholesale/Transaction Bank for Digital CX \-  Southeast Asia dan penghargaan Outstanding Digital CX Cash Management Platform \- Southeast Asia pada kategori Wholesale/Transaction Banking.\\n\\nPada kuartal I 2026, sebanyak 99,8% transaksi yang diproses BCA merupakan transaksi digital. Secara keseluruhan, total frekuensi transaksi BCA tumbuh 61% dalam 3 tahun terakhir. Selaras dengan hal tersebut, jumlah nasabah BCA mencapai 34,5 juta, atau tumbuh 18% dalam 3 tahun terakhir.\\n\\n\\"Pertumbuhan ini tentunya turut didukung oleh lini perbankan transaksi korporasi dan komersial yang stabil melalui berbagai aplikasi dan platform kami, sekaligus memperkuat posisi BCA sebagai pilar utama dalam ekosistem digital banking dan cash management nasional,\\"tambah Hendra. (end)",  
      "publishedAt": "2026-07-15T04:14:56Z"  
    },  
    {  
      "title": "BAKTI BCA GELAR WORKSHOP GASTRONOMI UNTUK PENGELOLA DESA WISATA DI LABUAN BAJO",  
      "description": "PT Bank Central Asia Tbk (BCA) melalui program corporate shared value (CSV) Bakti BCA menggelar workshop peningkatan keterampilan gastronomi bagi para pengelola desa binaan di Labuan Bajo, Nusa Tenggara Timur. Langkah strategis yang diikuti oleh sembilan pengelola desa Bakti BCA ini diambil sebagai bentuk komitmen nyata perusahaan dalam memperkuat pemberdayaan masyarakat dan memaksimalkan potensi lokal di wilayah Indonesia Timur.\\n\\nMelalui lokakarya ini, desa wisata binaan diharapkan mampu menggali kaitan kuliner lokal dengan sejarah, seni, dan budaya setempat untuk menumbuhkan inspirasi penyajian di masing-masing desa. EVP Corporate Communication & Social Responsibility BCA, Hera F. Haryn, menjelaskan bahwa kuliner lokal merupakan salah satu potensi terdekat dengan keseharian masyarakat yang dapat menjadi penggerak ekonomi berkelanjutan jika disajikan dengan standar yang lebih baik.\\n\\nWorkshop ini mengusung pendekatan penyajian gastronomi end-to-end, mulai dari pemilihan dan pengolahan bahan baku lokal, teknik memasak, hingga tata cara menata hidangan agar menarik di mata wisatawan. Selama pelatihan, para peserta diajak mempraktikkan langsung setiap tahapan penyajian dengan didampingi langsung oleh Dapur Tara, pelaku usaha kuliner berbasis budaya Flores di Labuan Bajo yang bertindak sebagai fasilitator.\\n\\nSelain di Labuan Bajo, Bakti BCA secara rutin mendampingi desa wisata binaan di berbagai wilayah Indonesia melalui pembinaan holistik untuk meningkatkan kualitas sumber daya manusia (SDM) desa. Program pengembangan tersebut mencakup pengelolaan keuangan, rumah pangan hidup (RPH), revitalisasi kebun kopi, hingga dukungan sertifikasi demi mengoptimalkan potensi ekonomi lokal di bidang kuliner, kerajinan, dan pariwisata.\\n\\nSeluruh kontribusi nyata tersebut dijalankan secara terstruktur melalui tiga pilar utama inisiatif Desa Bakti BCA. Ketiga pilar tersebut meliputi Usaha Berbasis Kemasyarakatan untuk memastikan kepemilikan lokal, Peningkatan Kapasitas melalui pelatihan berkala untuk penguatan SDM dan tata kelola, serta Akses Pasar untuk memberikan dukungan promosi serta perluasan pasar melalui ekosistem BCA.\\n\\nHera menambahkan bahwa penguatan kapasitas masyarakat desa harus dilakukan secara konsisten dan berkesinambungan agar dampaknya benar-benar terasa dalam jangka panjang. Inisiatif ini menjadi bagian dari upaya berkelanjutan Bakti BCA dalam membangun ekosistem desa yang mandiri dan berdaya saing, sekaligus memastikan setiap program memberikan dampak nyata yang dapat tumbuh berkelanjutan. (end)",  
      "publishedAt": "2026-07-13T06:53:36Z"  
    }  
  \],  
  "total": 212,  
  "source": "pluang",  
  "hasMore": true,  
  "stockId": 10020  
}  
\`\`\`

\---

\#\#\# US Stock Quote

Kutipan saham atau indeks Amerika di Pluang, termasuk sesi extended-hours. Membawa penanda \`delayed\` karena Pluang sendiri menyatakan harganya tertunda.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/us-stock-quote\`  
\- \*\*Cache TTL:\*\* 60s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`stockId\` | number | query | yes | Numeric Pluang global-stock id. Upstream accepts 10000-20000. Required. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/us-stock-quote?stockId=10751" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/us-stock-quote?stockId=10751", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/us-stock-quote?stockId=10751",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "change": \-1.4800000000000182,  
  "source": "pluang",  
  "spread": 0,  
  "delayed": true,  
  "stockId": 10751,  
  "midPrice": 776.34,  
  "sellPrice": 776.34,  
  "buyBackPrice": 776.34,  
  "changePercent": \-0.19027538505052816,  
  "previousClose": 777.82,  
  "pricePrecision": 2,  
  "extendedHoursMidPrice": 776.34,  
  "extendedHoursSellPrice": 776.34,  
  "extendedHoursBuyBackPrice": 776.34  
}  
\`\`\`

\---

\#\#\# US Stock Closes

Harga penutupan tiap horizon untuk saham atau indeks Amerika.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/us-stock-closes\`  
\- \*\*Cache TTL:\*\* 3600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`stockId\` | number | query | yes | Numeric Pluang global-stock id. Upstream accepts 10000-20000. Required. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/us-stock-closes?stockId=10751" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/us-stock-closes?stockId=10751", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/us-stock-closes?stockId=10751",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "ytd": 683.21,  
  "basis": "closing price at each horizon",  
  "source": "pluang",  
  "oneWeek": 768.6,  
  "oneYear": 644.87,  
  "stockId": 10751,  
  "fiveYear": 445.92,  
  "oneMonth": 749.08,  
  "threeMonth": 742.37  
}  
\`\`\`

\---

\#\#\# US Stock Financials

Laporan keuangan saham Amerika, kuartalan dan tahunan.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/us-stock-financials\`  
\- \*\*Cache TTL:\*\* 21600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`stockId\` | number | query | yes | Numeric Pluang global-stock id. Upstream accepts 10000-20000. Required. |  
| \`period\` | enum(quarterly|annually|both) | query | no | Which period block to return. Default both. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/us-stock-financials?stockId=10738\&period=quarterly" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/us-stock-financials?stockId=10738\&period=quarterly", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/us-stock-financials?stockId=10738\&period=quarterly",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "period": "both",  
  "source": "pluang",  
  "stockId": 10738,  
  "annually": {  
    "cashFlow": {  
      "chart": \[\],  
      "table": \[\],  
      "title": "Cash Flow"  
    },  
    "balanceSheet": {  
      "chart": \[\],  
      "table": \[\],  
      "title": "Balance Sheet"  
    },  
    "incomeStatement": {  
      "chart": \[\],  
      "table": \[\],  
      "title": "Income Statement"  
    }  
  },  
  "quarterly": {  
    "cashFlow": {  
      "chart": \[\],  
      "table": \[\],  
      "title": "Cash Flow"  
    },  
    "balanceSheet": {  
      "chart": \[\],  
      "table": \[\],  
      "title": "Balance Sheet"  
    },  
    "incomeStatement": {  
      "chart": \[\],  
      "table": \[\],  
      "title": "Income Statement"  
    }  
  }  
}  
\`\`\`

\---

\#\#\# US Stock Technicals

Indikator teknikal saham atau indeks Amerika di enam timeframe, dari 5 menit sampai bulanan.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/us-stock-technicals\`  
\- \*\*Cache TTL:\*\* 300s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`stockId\` | number | query | yes | Numeric Pluang global-stock id. Upstream accepts 10000-20000. Required. |  
| \`timeFrame\` | enum(FIVE\_MINUTES|FIFTEEN\_MINUTES|HOURLY|DAILY|WEEKLY|MONTHLY) | query | no | Indicator timeframe — the upstream's full accepted set. Default DAILY. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/us-stock-technicals?stockId=10751\&timeFrame=DAILY" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/us-stock-technicals?stockId=10751\&timeFrame=DAILY", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/us-stock-technicals?stockId=10751\&timeFrame=DAILY",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "source": "pluang",  
  "stockId": 10751,  
  "timeFrame": "DAILY",  
  "technicals": {  
    "oscillators": {  
      "indicators": \[  
        {  
          "key": "RSI\_6",  
          "value": 70.68034557235413,  
          "signal": "SELL"  
        },  
        {  
          "key": "RSI\_12",  
          "value": 76.83947373336737,  
          "signal": "SELL"  
        },  
        {  
          "key": "ADX\_6",  
          "value": 78.29064295022499,  
          "signal": "BUY"  
        },  
        {  
          "key": "ADX\_12",  
          "value": 32.8219929610966,  
          "signal": "BUY"  
        },  
        {  
          "key": "CCI\_5",  
          "value": 166.6666666666712,  
          "signal": "BUY"  
        },  
        {  
          "key": "CCI\_10",  
          "value": 92.81409104522271,  
          "signal": "NEUTRAL"  
        }  
      \],  
      "oscillatorsSummary": {  
        "icon": "https://image-cdn.pluang.com/icons/light/technical-indicators/bar-neutral.svg",  
        "signal": "NEUTRAL",  
        "buyCount": 5,  
        "sellCount": 5,  
        "neutralCount": 4,  
        "indicatorBars": \[  
          {  
            "color": "\#FF504B",  
            "isActive": false  
          },  
          {  
            "color": "\#FFA7A5",  
            "isActive": false  
          },  
          {  
            "color": "\#D5D7DC",  
            "isActive": true  
          },  
          {  
            "color": "\#8FE295",  
            "isActive": false  
          },  
          {  
            "color": "\#1FC62A",  
            "isActive": false  
          }  
        \]  
      }  
    },  
    "movingAverages": {  
      "simpleIndicators": \[  
        {  
          "key": "SMA\_5",  
          "value": 773.3980000000001,  
          "signal": "BUY"  
        },  
        {  
          "key": "SMA\_10",  
          "value": 768.112,  
          "signal": "BUY"  
        },  
        {  
          "key": "SMA\_20",  
          "value": 754.5276249999998,  
          "signal": "BUY"  
        },  
        {  
          "key": "SMA\_50",  
          "value": 748.4596499999998,  
          "signal": "BUY"  
        },  
        {  
          "key": "SMA\_100",  
          "value": 728.1498750000003,  
          "signal": "BUY"  
        },  
        {  
          "key": "SMA\_200",  
          "value": 704.984728,  
          "signal": "BUY"  
        }  
      \],  
      "exponentialIndicators": \[  
        {  
          "key": "EMA\_5",  
          "value": 773.6426666666667,  
          "signal": "BUY"  
        },  
        {  
          "key": "EMA\_10",  
          "value": 766.925090909091,  
          "signal": "BUY"  
        },  
        {  
          "key": "EMA\_20",  
          "value": 755.5222559523809,  
          "signal": "BUY"  
        },  
        {  
          "key": "EMA\_50",  
          "value": 749.2599656862744,  
          "signal": "BUY"  
        },  
        {  
          "key": "EMA\_100",  
          "value": 727.8662418316834,  
          "signal": "BUY"  
        },  
        {  
          "key": "EMA\_200",  
          "value": 705.2115610547263,  
          "signal": "BUY"  
        }  
      \],  
      "movingAveragesSummary": {  
        "icon": "https://image-cdn.pluang.com/icons/light/technical-indicators/bar-bullish.svg",  
        "signal": "BULLISH",  
        "buyCount": 13,  
        "sellCount": 0,  
        "neutralCount": 0,  
        "indicatorBars": \[  
          {  
            "color": "\#FF504B",  
            "isActive": false  
          },  
          {  
            "color": "\#FFA7A5",  
            "isActive": false  
          },  
          {  
            "color": "\#D5D7DC",  
            "isActive": false  
          },  
          {  
            "color": "\#8FE295",  
            "isActive": false  
          },  
          {  
            "color": "\#1FC62A",  
            "isActive": true  
          }  
        \]  
      }  
    },  
    "overallSummary": {  
      "icon": "https://image-cdn.pluang.com/icons/light/technical-indicators/overall-bullish.svg",  
      "signal": "BULLISH",  
      "buyCount": 18,  
      "sellCount": 5,  
      "neutralCount": 4,  
      "indicatorBars": \[  
        {  
          "color": "\#FF504B",  
          "isActive": false  
        },  
        {  
          "color": "\#FFA7A5",  
          "isActive": false  
        },  
        {  
          "color": "\#D5D7DC",  
          "isActive": false  
        },  
        {  
          "color": "\#8FE295",  
          "isActive": false  
        },  
        {  
          "color": "\#1FC62A",  
          "isActive": true  
        }  
      \]  
    },  
    "supportAndResistance": {  
      "indicators": \[  
        {  
          "key": "R3",  
          "color": "\#1FC62A",  
          "value": 783.6433333333333  
        },  
        {  
          "key": "R2",  
          "color": "\#1FC62A",  
          "value": 781.5066666666667  
        },  
        {  
          "key": "R1",  
          "color": "\#1FC62A",  
          "value": 779.6633333333333  
        },  
        {  
          "key": "PP",  
          "color": "\#000000",  
          "value": 777.5266666666666  
        },  
        {  
          "key": "S1",  
          "color": "\#FF504B",  
          "value": 775.6833333333333  
        },  
        {  
          "key": "S2",  
          "color": "\#FF504B",  
          "value": 773.5466666666666  
        }  
      \]  
    }  
  }  
}  
\`\`\`

\---

\#\#\# US Stock Profile

Profil dan status perdagangan saham atau indeks Amerika di Pluang.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/us-stock-description\`  
\- \*\*Cache TTL:\*\* 86400s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`stockId\` | number | query | yes | Numeric Pluang global-stock id. Upstream accepts 10000-20000. Required. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/us-stock-description?stockId=10738" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/us-stock-description?stockId=10738", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/us-stock-description?stockId=10738",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "source": "pluang",  
  "stockId": 10738,  
  "description": {  
    "icon": "https://image-cdn.pluang.com/icons/light/global-stocks/qqq.svg",  
    "paln": {  
      "stockId": 10738,  
      "enableBuy": false,  
      "enableSell": false,  
      "optionsInfo": {  
        "educationUrl": "https://pluang.com/pwa/education-option",  
        "onboardingUrl": "https://pluang.com/en/pwa/option-onboarding",  
        "isOptionsAllowed": false  
      },  
      "disabledPopup": {  
        "title": "Trading Dihentikan",  
        "description": "Trading saham tanpa leverage dihentikan untuk sementara. Kamu bisa coba lagi nanti atau gunakan saham dengan leverage sebagai gantinya. Harap diingat bahwa semakin tinggi leverage yang digunakan, semakin tinggi risikonya."  
      },  
      "socketChannels": {  
        "descriptionScreen": "us\_stock:trade\_price:10738",  
        "marketStatsScreen": "us\_stock:trade:10738",  
        "transactionScreen": "us\_stock:trade\_price:10738"  
      },  
      "isPreMarketOpen": false,  
      "isPostMarketOpen": false,  
      "recurringEnabled": true,  
      "recurringOrderId": null,  
      "hasRecurringOrder": false,  
      "palnTncPopupDetails": {  
        "text": "Konten ini merupakan informasi yang bersifat umum, dan tidak boleh dianggap sebagai segala bentuk ajakan, rekomendasi, atau saran apa pun. Pluang Saham AS dikelola resikonya oleh PT. PG Berjangka yang memiliki izin Penyaluran Amanat Nasabah ke bursa Luar Negeri (PALN) oleh BAPPEBTI. Transaksi-mu tercatat di Kliring Berjangka Indonesia (KBI). Baca \<span style=\\"color:\#463CFF;\\"\>Syarat dan Ketentuan\</span\> produk kami.",  
        "title": "Disclaimer",  
        "tncUrl": "https://pluang.com/tnc/us-stock-paln-terms"  
      },  
      "bufferBalancePercent": 5,  
      "isOvernightMarketOpen": false,  
      "recurringOrderDetails": null,  
      "transactionFeeDistribution": {  
        "promo": 0,  
        "exchangeFee": 0,  
        "ppnPercentage": 0,  
        "regFeeMultiplier": 0,  
        "tafFeeMultiplier": 0,  
        "commissionPercentage": 0.3  
      },  
      "extendedHoursTradingOnboarding": {  
        "icon": "https://mobile-app-production.s3.ap-southeast-1.amazonaws.com/icons/global-stocks/onboarding/24-5-onboarding.svg",  
        "title": "Trading kapan pun dengan 24-Hour Market",  
        "description": "Jangan lewatkan kesempatan trading dengan trading 24 jam. Antisipasi perilisan laporan keuangan perusahaan atau berita penting lainnya dengan trading \<b\>mulai Senin pukul 07:00 WIB hingga Sabtu pukul 07:00 WIB.\</b\>",  
        "learnMoreUrl": "https://faq.pluang.com/s/article/Pertanyaan-Umum-Seputar-24-Hour-Market",  
        "learnMoreText": "Untuk informasi lebih lanjut, baca \<font color=\#463CFF\>di sini\</font\>.",  
        "tradingHoursData": {  
          "preMarketText": "Pre-Market",  
          "marketOpenTime": "20:30",  
          "postmarketText": "After-Hours",  
          "marketCloseTime": "03:00",  
          "regularHoursText": "Jam Reguler",  
          "preMarketOpenTime": "15:00",  
          "overnightMarketText": "Overnight",  
          "postMarketCloseTime": "07:00",  
          "overnightMarketOpenTime": "07:00"  
        },  
        "timezoneDescription": "Zona waktu yang ditampilkan adalah UTC+7 (WIB)"  
      },  
      "dummyTransactionFeeDistribution": null,  
      "bufferBalancePercentForStopBuyPALN": {  
        "stopPriceThreshold": 50,  
        "bufferPercentAboveThreshold": 2.5,  
        "bufferPercentBelowThreshold": 4  
      }  
    },  
    "enableBuy": false,  
    "stockType": "PALN",  
    "topLabels": \[  
      {  
        "url": "https://faq.pluang.com/s/article/Pertanyaan-Umum-Seputar-24-Hour-Market",  
        "icon": "https://mobile-app-production.s3.ap-southeast-1.amazonaws.com/icons/global-stocks/onboarding/24-5.svg",  
        "text": "",  
        "type": "24\_hour\_market",  
        "textColor": "",  
        "borderColor": "",  
        "description": "Kamu bisa trading aset ini 24 jam dalam sehari, mulai dari Senin pukul 07:00 WIB hingga Sabtu pukul 07:00 WIB. \<span style=\\"color:\#463CFF;\\"\>Pelajari lebih lanjut\</span\>",  
        "backgroundColor": ""  
      },  
      {  
        "url": "",  
        "icon": "",  
        "text": "Hingga 4x",  
        "type": "intraday\_leverage",  
        "textColor": "\#463CFF",  
        "borderColor": "\#BCBCFF",  
        "description": "Leverage hingga 4x tersedia untuk aset ini.",  
        "backgroundColor": "\#EEF2FF"  
      },  
      {  
        "url": "",  
        "icon": "https://mobile-app-production.s3.ap-southeast-1.amazonaws.com/icons/global-stocks/top-labels/market-holiday.svg",  
        "text": "",  
        "type": "market\_holiday",  
        "textColor": "",  
        "borderColor": "",  
        "description": "Pasar modal sedang ditutup karena hari libur dan akan kembali dibuka pada 17 Aug 2026, 07:00 WIB.",  
        "backgroundColor": ""  
      }  
    \],  
    "enableSell": false,  
    "cfdLeverage": {  
      "stockId": 10861,  
      "enableBuy": false,  
      "enableSell": false,  
      "intradayInfo": {  
        "tag": "4x (Day Trade)",  
        "image": "https://image-cdn.pluang.com/icons/common/global-stocks/leverage/leverage-4x.svg",  
        "title": "Day trade dengan leverage 4x",  
        "description": "Trading dengan 4x daya beli. Kamu harus menjual semua posisi day trade pada hari trading yang sama."  
      },  
      "isMarginCall": false,  
      "disabledPopup": {  
        "title": "Trading Dihentikan",  
        "description": "Trading saham dengan leverage dihentikan untuk sementara. Silakan coba lagi nanti."  
      },  
      "socketChannels": {  
        "descriptionScreen": "us\_stock:trade\_price:10861",  
        "marketStatsScreen": "us\_stock:trade:10861",  
        "transactionScreen": "us\_stock:trade\_price:10861"  
      },  
      "leverageFeeInfo": {  
        "title": "Leverage Daily Fee",  
        "description": "Biaya overnight 7,5% per tahun (0,021% per hari) akan dikenakan secara harian pada pukul 13:00 WIB apabila kamu tidak menjual sahammu hingga bursa tutup.Biaya ini akan dihitung dari nilai eksposur, dan nominal biaya harian akan bervariasi sesuai dengan harga terakhir pada saat bursa tutup."  
      },  
      "leverageOptions": \[  
        {  
          "key": "2x",  
          "leverage": 2,  
          "isDefault": false,  
          "isIntraday": false,  
          "description": "Gandakan daya belimu. Posisi dikenakan biaya harian hingga ditutup."  
        },  
        {  
          "key": "4x (Day Trade)",  
          "leverage": 4,  
          "isDefault": true,  
          "isIntraday": true,  
          "description": "Trading dengan 4x daya beli. Posisi harus ditutup sebelum pasar modal tutup."  
        }  
      \],  
      "marginCallPopup": {  
        "title": "Kamu Menerima Margin Call",  
        "description": "Margin level kamu telah turun di bawah 70,00%. Untuk keluar dari margin call dan menghindari likuidasi, kamu harus mengembalikan margin level ke 100,00%. Tambahkan saldo USD Margin atau jual sebagian dari posisi kamu."  
      },  
      "enableIntradayBuy": false,  
      "enableIntradaySell": false,  
      "isCfdLeverageEligible": false,  
      "transactionFeeDistribution": {  
        "promo": 0,  
        "exchangeFee": 0,  
        "ppnPercentage": 0,  
        "regFeeMultiplier": 0,  
        "tafFeeMultiplier": 0,  
        "commissionPercentage": 0.3  
      },  
      "dummyTransactionFeeDistribution": null,  
      "bufferBalancePercentForStopBuyCFD": 5  
    },  
    "displayName": "Nasdaq100 ETF",  
    "miniBanners": \[\],  
    "contractCode": "QQQ",  
    "securityType": "ETF",  
    "isPluangPlusUser": false,  
    "marketClosedIcon": "https://mobile-app-production.s3.ap-southeast-1.amazonaws.com/icons/global-stocks/market-closed.svg",  
    "tradingHaltActive": false,  
    "assetBannerMessage": {  
      "url": "",  
      "message": "",  
      "clickAction": "",  
      "messageType": "Alert",  
      "showMessage": false,  
      "showArrowButton": false  
    },  
    "topLabelsShowCount": 3,  
    "watchlistAssetCode": "USSTOCK:10738",  
    "bottomBannerMessage": {  
      "title": "",  
      "message": "",  
      "clickAction": "",  
      "description": "",  
      "messageType": "Alert",  
      "showMessage": false,  
      "showArrowButton": false  
    },  
    "waivedOffFeePercent": 0,  
    "advancedChartDetails": {  
      "advancedChartUrl": "https://trade.pluang.com/pwa/advance-charts?ticker=QQQ\&theme=light",  
      "enableTradingView": true,  
      "advancedChartTicker": "QQQ",  
      "showTradingViewBetaLabel": true  
    },  
    "minimumBuyAmountPaln": 0.98,  
    "minimumSellAmountPaln": 0.3,  
    "maxWaivedOffFeeAllowed": 0,  
    "fillByAmountFeeBufferMultiplier": 1,  
    "isLeverageEligibleForInstantMarginConversion": false  
  }  
}  
\`\`\`

\---

\#\#\# Gold Price

Harga emas Pluang per gram — beli, jual, cicilan — plus perubahan tiap horizon.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/gold-price\`  
\- \*\*Cache TTL:\*\* 60s

\*\*Parameters:\*\*

\_No parameters.\_

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/gold-price" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/gold-price", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/gold-price",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "asOf": "2026-08-15T16:06:46.760+00:00",  
  "unit": "gram",  
  "source": "pluang",  
  "buyPrice": 2445939,  
  "currency": "IDR",  
  "midPrice": 2498406,  
  "sellPrice": 2550873,  
  "changePercent": {  
    "ONE\_DAY": 0.3,  
    "ONE\_WEEK": 0.48,  
    "ONE\_YEAR": 32.57,  
    "FIVE\_YEAR": 199.62,  
    "ONE\_MONTH": 6.42,  
    "SIX\_MONTH": \-12.61,  
    "THREE\_YEAR": 153.21  
  },  
  "installmentPrice": 2550873  
}  
\`\`\`

\---

\#\#\# Gold Key Stats

Ukuran risiko emas yang Pluang tampilkan, seperti drawdown tiga bulan.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/gold-stats\`  
\- \*\*Cache TTL:\*\* 3600s

\*\*Parameters:\*\*

\_No parameters.\_

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/gold-stats" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/gold-stats", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/gold-stats",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "count": 3,  
  "items": \[  
    {  
      "key": "3M Drawdown",  
      "value": "11,41%",  
      "description": "Tingkat penurunan harga emas dari titik puncaknya ke titik terendah. Penurunan ini dipengaruhi time frame."  
    },  
    {  
      "key": "Trading Activity",  
      "value": "41% Beli | 59% Jual",  
      "description": "Persentase pengguna Pluang yang meningkatkan atau mengurangi posisi investasi dalam aset bersangkutan melalui perdagangan selama 24 jam terakhir. Meningkatnya aktivitas pembelian menandakan aset ini sedang diminati."  
    },  
    {  
      "key": "Typical Hold Time",  
      "value": "215 hari",  
      "description": "Waktu median yang menunjukkan lamanya pengguna Pluang hold aset ini sebelum menjualnya. Waktu hold yang panjang menunjukkan sebuah tren akumulasi. Pendeknya waktu hold mengindikasikan meningkatnya pergerakan ke aset lain."  
    }  
  \],  
  "title": "Key Stats",  
  "source": "pluang"  
}  
\`\`\`

\---

\#\#\# Gold Performance

Titik tertinggi dan terendah emas dalam 52 minggu dan 5 tahun, beserta tanggalnya.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/gold-performance\`  
\- \*\*Cache TTL:\*\* 3600s

\*\*Parameters:\*\*

\_No parameters.\_

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/gold-performance" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/gold-performance", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/gold-performance",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "source": "pluang",  
  "oneYear": {  
    "low": "52W Low: Rp485.000",  
    "high": "52W High: Rp3.227.664",  
    "lowDate": "27 March 2026",  
    "highDate": "17 October 2025",  
    "timeframe": "1Y",  
    "sliderPosition": 73.41,  
    "percentFromHigh": "-22,59%"  
  },  
  "fiveYear": {  
    "low": "5Y Low: Rp485.000",  
    "high": "5Y High: Rp3.227.664",  
    "lowDate": "27 March 2026",  
    "highDate": "17 October 2025",  
    "timeframe": "5Y",  
    "sliderPosition": 73.41,  
    "percentFromHigh": "-22,59%"  
  },  
  "currentMidPrice": "Rp2.498.406"  
}  
\`\`\`

\---

\#\#\# Market Overview

Ikhtisar lintas aset dalam satu panggilan: kripto, saham AS, saham Indonesia, komoditas, indeks global, mata uang, dan obligasi.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/market-overview\`  
\- \*\*Cache TTL:\*\* 60s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`category\` | string | query | no | Keep one category — cryptocurrency, global\_equity, indonesia\_stocks, commodities, global\_market, currencies, bonds. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/market-overview?category=commodities" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/market-overview?category=commodities", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/market-overview?category=commodities",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "count": 1,  
  "items": \[  
    {  
      "title": "Komoditi",  
      "assets": \[  
        {  
          "name": "Gold\*"  
        },  
        {  
          "name": "Silver\*"  
        },  
        {  
          "name": "Copper"  
        },  
        {  
          "name": "Crude Oil"  
        }  
      \],  
      "category": "commodities"  
    }  
  \],  
  "source": "pluang",  
  "category": "commodities"  
}  
\`\`\`

\---

\#\#\# Top Movers

Penggerak terbesar lintas kelas aset, naik maupun turun.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/top-movers\`  
\- \*\*Cache TTL:\*\* 300s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`direction\` | enum(gainers|losers|both) | query | no | Which side to return. Default both. |  
| \`length\` | number | query | no | Rows per side (default 20, max 100\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/top-movers?direction=gainers\&length=10" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/top-movers?direction=gainers\&length=10", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/top-movers?direction=gainers\&length=10",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "count": 5,  
  "losers": \[\],  
  "source": "pluang",  
  "gainers": \[  
    {  
      "id": "cryptocurrency-10349",  
      "name": "CoW Protocol",  
      "symbol": "COW",  
      "assetId": 10349,  
      "category": "cryptocurrency",  
      "tradable": true,  
      "changePercent": 54.01  
    },  
    {  
      "id": "cryptocurrency-10748",  
      "name": "Hemi",  
      "symbol": "HEMI",  
      "assetId": 10748,  
      "category": "cryptocurrency",  
      "tradable": true,  
      "changePercent": 29.74  
    },  
    {  
      "id": "cryptocurrency-10562",  
      "name": "Walrus",  
      "symbol": "WAL",  
      "assetId": 10562,  
      "category": "cryptocurrency",  
      "tradable": true,  
      "changePercent": 26.25  
    },  
    {  
      "id": "cryptocurrency-10802",  
      "name": "OLAXBT",  
      "symbol": "AIO",  
      "assetId": 10802,  
      "category": "cryptocurrency",  
      "tradable": true,  
      "changePercent": 26.14  
    },  
    {  
      "id": "cryptocurrency-10259",  
      "name": "Moonriver",  
      "symbol": "MOVR",  
      "assetId": 10259,  
      "category": "cryptocurrency",  
      "tradable": true,  
      "changePercent": 23.69  
    }  
  \],  
  "direction": "gainers"  
}  
\`\`\`

\---

\#\#\# Asset Search

Cari aset lintas kelas di Pluang — saham IDX, saham AS, kripto.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/search\`  
\- \*\*Cache TTL:\*\* 3600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`query\` | string | query | yes | Text to search. Required. |  
| \`length\` | number | query | no | Rows to return (default 20, max 100\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/search?query=bbca\&length=20" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/search?query=bbca\&length=20", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/search?query=bbca\&length=20",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "count": 1,  
  "items": \[  
    {  
      "id": "globalStock-10343",  
      "name": "Banco Bilbao Vizcaya Argentaria SA",  
      "symbol": "BBVA",  
      "assetId": 10343,  
      "category": "PALN",  
      "tradable": true  
    }  
  \],  
  "query": "bbca",  
  "total": 1,  
  "source": "pluang"  
}  
\`\`\`

\---

\#\#\# Analyst Top Picks

Pilihan teratas analis yang Pluang tampilkan, lengkap dengan target harga. Ini sinyal pihak ketiga, bukan data bursa.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/signals\`  
\- \*\*Cache TTL:\*\* 3600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`category\` | string | query | no | Keep one asset category as Pluang labels it. |  
| \`length\` | number | query | no | Rows to return (default 20, max 100\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/signals?category=globalStock\&length=20" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/signals?category=globalStock\&length=20", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/signals?category=globalStock\&length=20",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "count": 10,  
  "items": \[  
    {  
      "name": "Braze Inc",  
      "symbol": "BRZE",  
      "assetId": 10610,  
      "category": "globalStock",  
      "signalId": "6a7f8223d62561e621dfca81"  
    },  
    {  
      "name": "Global E Online Ltd",  
      "symbol": "GLBE",  
      "assetId": 11073,  
      "category": "globalStock",  
      "signalId": "6a7f82245ff50983642363d4"  
    },  
    {  
      "name": "Neurocrine Biosciences Inc",  
      "symbol": "NBIX",  
      "assetId": 11080,  
      "category": "globalStock",  
      "signalId": "6a7f82245ff50983642363d6"  
    },  
    {  
      "name": "Cytokinetics Inc",  
      "symbol": "CYTK",  
      "assetId": 10969,  
      "category": "globalStock",  
      "signalId": "6a7f8224e7dd77bef74695c0"  
    },  
    {  
      "name": "Bitdeer Technologies Group",  
      "symbol": "BTDR",  
      "assetId": 10961,  
      "category": "globalStock",  
      "signalId": "6a7f8224e7dd77bef74695ba"  
    },  
    {  
      "name": "Vertiv Holdings Co",  
      "symbol": "VRT",  
      "assetId": 10945,  
      "category": "globalStock",  
      "signalId": "6a7f8224e7dd77bef74695b0"  
    }  
  \],  
  "total": 10,  
  "source": "pluang"  
}  
\`\`\`

\---

\#\#\# Market News

Feed berita pasar Pluang, lintas aset.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/news-feed\`  
\- \*\*Cache TTL:\*\* 900s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`length\` | number | query | no | Rows to return (default 25, max 200\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/news-feed?length=25" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/news-feed?length=25", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/news-feed?length=25",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "count": 10,  
  "items": \[  
    {  
      "id": "d841d016c885c2f7a05c85e06e688e867a70cdeef65fa4d654ee887d11abb0f0",  
      "link": "https://www.antaranews.com/berita/5696176/rapbn-2027-jaga-ketahanan-pangan-nyalakan-kemandirian-energi",  
      "title": "RAPBN 2027:  Jaga ketahanan pangan, nyalakan kemandirian energi",  
      "source": "antara",  
      "publishedAt": "2026-08-15T10:06:53.336Z"  
    },  
    {  
      "id": "e89de2e08f1c56da7ebe4398a9c2297324c7b04d2f297cad91498f0f3328185e",  
      "link": "https://www.antaranews.com/berita/5695935/djp-bali-membarui-data-pajak-bersama-pemda-dongkrak-penerimaan",  
      "title": "DJP Bali membarui data pajak bersama pemda dongkrak penerimaan",  
      "source": "antara",  
      "publishedAt": "2026-08-15T07:06:52.821Z"  
    },  
    {  
      "id": "f4c661a0a9663bf87e9e83b7ceebc872a048f0f25aa959aa655c119a07c8508d",  
      "link": "https://www.antaranews.com/berita/5695931/pakar-unej-harapkan-rapbn-2027-membawa-ekonomi-ri-naik-kelas",  
      "title": "Pakar Unej harapkan RAPBN 2027 membawa ekonomi RI naik kelas",  
      "source": "antara",  
      "publishedAt": "2026-08-15T07:06:55.918Z"  
    },  
    {  
      "id": "313a91d294eecb4c7224e8d399b86931a1d3a135665fb30e6744d94835642f19",  
      "link": "https://www.antaranews.com/berita/5695905/rapbn-2027-navigasi-pertumbuhan-disiplin-fiskal-dan-kesejahteraan",  
      "title": "RAPBN 2027: Navigasi pertumbuhan, disiplin fiskal, dan kesejahteraan",  
      "source": "antara",  
      "publishedAt": "2026-08-15T06:07:03.976Z"  
    },  
    {  
      "id": "5dd7eb600d4e1af3149645878e08546e2cc22f29cf3dbcbde9068b4b96e5ed70",  
      "link": "https://www.antaranews.com/berita/5695792/emas-vs-tabungan-bank-mana-yang-lebih-menguntungkan-ini-faktanya",  
      "title": "Emas vs tabungan bank: Mana yang lebih menguntungkan? Ini faktanya",  
      "source": "antara",  
      "publishedAt": "2026-08-15T05:06:52.723Z"  
    },  
    {  
      "id": "d5ce70ef5f72b9770e2a9162ef8691dcc47364acbefefb3ab09c92da914a78a7",  
      "link": "https://www.antaranews.com/berita/5695728/lps-ingatkan-nasabah-perhatikan-tingkat-bunga-sebelum-menabung-di-bank",  
      "title": "LPS ingatkan nasabah perhatikan tingkat bunga sebelum menabung di bank",  
      "source": "antara",  
      "publishedAt": "2026-08-15T04:06:51.054Z"  
    }  
  \],  
  "total": 10,  
  "source": "pluang"  
}  
\`\`\`

\---

\#\#\# Staking Rates

Imbal staking kripto di Pluang, tarif normal dan Pluang+.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/staking-rates\`  
\- \*\*Cache TTL:\*\* 3600s

\*\*Parameters:\*\*

\_No parameters.\_

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/staking-rates" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/staking-rates", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/staking-rates",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "count": 3,  
  "items": \[  
    {  
      "name": "Ethereum",  
      "symbol": "ETH",  
      "assetId": 10001,  
      "ratePercent": 1.19,  
      "plusRatePercent": 2  
    },  
    {  
      "name": "Solana",  
      "symbol": "SOL",  
      "assetId": 10032,  
      "ratePercent": 2.22,  
      "plusRatePercent": 4.5  
    },  
    {  
      "name": "Cosmos",  
      "symbol": "ATOM",  
      "assetId": 10028,  
      "ratePercent": 6.98,  
      "plusRatePercent": 11.34  
    }  
  \],  
  "source": "pluang"  
}  
\`\`\`

\---

\#\#\# Crypto Futures

Instrumen kripto berjangka yang Pluang tawarkan.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:pluang/crypto-futures\`  
\- \*\*Cache TTL:\*\* 21600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`length\` | number | query | no | Rows to return (default 100, max 500\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:pluang/crypto-futures?length=50" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:pluang/crypto-futures?length=50", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:pluang/crypto-futures?length=50",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "count": 49,  
  "items": \[  
    {  
      "createdAt": "2025-03-27T03:11:09.829+00:00",  
      "updatedAt": "2025-04-09T11:33:06.099+00:00",  
      "instrumentId": 10024  
    },  
    {  
      "createdAt": "2025-02-24T03:11:24.788+00:00",  
      "updatedAt": "2025-02-27T12:05:47.509+00:00",  
      "instrumentId": 10014  
    },  
    {  
      "createdAt": "2025-04-30T02:45:52.542+00:00",  
      "updatedAt": "2025-04-30T06:56:30.419+00:00",  
      "instrumentId": 10059  
    },  
    {  
      "createdAt": "2025-02-12T01:02:57.705+00:00",  
      "updatedAt": "2025-02-27T10:21:12.000+00:00",  
      "instrumentId": 10004  
    },  
    {  
      "createdAt": "2026-06-19T03:04:01.358+00:00",  
      "updatedAt": "2026-06-19T08:06:35.434+00:00",  
      "instrumentId": 10197  
    },  
    {  
      "createdAt": "2025-03-27T03:11:09.837+00:00",  
      "updatedAt": "2025-04-09T11:33:03.570+00:00",  
      "instrumentId": 10028  
    }  
  \],  
  "total": 49,  
  "source": "pluang"  
}  
\`\`\`

\---

\_Generated: 2026-08-26T13:38:52.095Z\_  
