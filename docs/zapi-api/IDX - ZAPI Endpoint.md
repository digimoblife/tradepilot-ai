\# IDX (Bursa Efek Indonesia) — Zapi reference

\> Data Bursa Efek Indonesia: ringkasan saham & indeks, top movers, broker, emiten, laporan keuangan, berita, dan passthrough ke ratusan endpoint /primary/.

\*\*Base URL:\*\* \`https://api.zpi.web.id\`  
\*\*Auth:\*\* Send \`x-api-key: YOUR\_KEY\` header on every request. Get a free key at https://zpi.web.id/dashboard/keys.  
\*\*Response envelope:\*\* \`{ status, message, content }\`  
\*\*Rate limit:\*\* 60 req/min on free tier.

\*\*Related:\*\*  
\- Detail page: https://zpi.web.id/api/finance/idx  
\- Endpoint catalog: https://zpi.web.id/category/finance  
\- Concise index: https://zpi.web.id/llms.txt  
\- Full reference: https://zpi.web.id/llms-full.txt

\---

\#\# IDX (Bursa Efek Indonesia)

\*\*Category:\*\* finance · \*\*Slug:\*\* \`idx\`  
\*\*Detail page:\*\* https://zpi.web.id/api/finance/idx

Data Bursa Efek Indonesia: ringkasan saham & indeks, top movers, broker, emiten, laporan keuangan, berita, dan passthrough ke ratusan endpoint /primary/.

\*\*Tags:\*\* idx, saham, stock, bursa, indonesia, finance

\#\#\# Ringkasan Saham

Ringkasan perdagangan semua saham (harga, volume, value, frekuensi).

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/stock-summary\`  
\- \*\*Cache TTL:\*\* 1800s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`length\` | number | query | no | Jumlah baris per halaman (default 20, max 1000\) |  
| \`start\` | number | query | no | Offset awal (default 0\) |  
| \`date\` | string | query | no | Tanggal data (YYYYMMDD atau YYYY-MM-DD). Default hari bursa terakhir. Bisa ambil data historis. |  
| \`code\` | string | query | no | Filter kode saham tertentu (opsional) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/stock-summary?length=20\&start=0\&date=20260612\&code=BBCA" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/stock-summary?length=20\&start=0\&date=20260612\&code=BBCA", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/stock-summary?length=20\&start=0\&date=20260612\&code=BBCA",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "No": 1,  
      "Bid": 8625,  
      "Low": 8050,  
      "Date": "2026-06-12T00:00:00",  
      "High": 8850,  
      "Close": 8650,  
      "Offer": 8650,  
      "Value": 182271837500,  
      "Change": 600,  
      "Volume": 21262200,  
      "persen": null,  
      "Remarks": "XDMO1SD0F10000A121------------",  
      "Previous": 8050,  
      "BidVolume": 29200,  
      "Frequency": 9962,  
      "OpenPrice": 8100,  
      "StockCode": "AADI",  
      "StockName": "Adaro Andalan Indonesia Tbk.",  
      "FirstTrade": 8075,  
      "ForeignBuy": 5896500,  
      "percentage": null,  
      "ForeignSell": 9874800,  
      "OfferVolume": 67500,  
      "ListedShares": 7786891760,  
      "DelistingDate": "",  
      "IDStockSummary": 4031673,  
      "TradebleShares": 7786891760,  
      "WeightForIndex": 1486517637,  
      "IndexIndividual": 155.9,  
      "NonRegularValue": 5466551,  
      "NonRegularVolume": 659,  
      "NonRegularFrequency": 16  
    },  
    {  
      "No": 2,  
      "Bid": 6175,  
      "Low": 6025,  
      "Date": "2026-06-12T00:00:00",  
      "High": 6325,  
      "Close": 6175,  
      "Offer": 6225,  
      "Value": 18983070000,  
      "Change": 125,  
      "Volume": 3068700,  
      "persen": null,  
      "Remarks": "--MO113E100000D232------------",  
      "Previous": 6050,  
      "BidVolume": 51900,  
      "Frequency": 3424,  
      "OpenPrice": 6075,  
      "StockCode": "AALI",  
      "StockName": "Astra Agro Lestari Tbk.",  
      "FirstTrade": 6050,  
      "ForeignBuy": 1104500,  
      "percentage": null,  
      "ForeignSell": 1285200,  
      "OfferVolume": 3000,  
      "ListedShares": 1924688333,  
      "DelistingDate": "",  
      "IDStockSummary": 4031674,  
      "TradebleShares": 1924688333,  
      "WeightForIndex": 390711732,  
      "IndexIndividual": 501.6,  
      "NonRegularValue": 0,  
      "NonRegularVolume": 0,  
      "NonRegularFrequency": 0  
    },  
    {  
      "No": 3,  
      "Bid": 35,  
      "Low": 35,  
      "Date": "2026-06-12T00:00:00",  
      "High": 35,  
      "Close": 35,  
      "Offer": 36,  
      "Value": 10220000,  
      "Change": 0,  
      "Volume": 292000,  
      "persen": null,  
      "Remarks": "--U-4100000000E614-E---------X",  
      "Previous": 35,  
      "BidVolume": 8000,  
      "Frequency": 59,  
      "OpenPrice": 0,  
      "StockCode": "ABBA",  
      "StockName": "Mahaka Media Tbk.",  
      "FirstTrade": 0,  
      "ForeignBuy": 0,  
      "percentage": null,  
      "ForeignSell": 0,  
      "OfferVolume": 1020800,  
      "ListedShares": 3935892857,  
      "DelistingDate": "",  
      "IDStockSummary": 4031675,  
      "TradebleShares": 3935892857,  
      "WeightForIndex": 1298844643,  
      "IndexIndividual": 77.3,  
      "NonRegularValue": 0,  
      "NonRegularVolume": 0,  
      "NonRegularFrequency": 0  
    }  
  \],  
  "start": 0,  
  "length": 3,  
  "dataset": "stock-summary",  
  "provider": "idx",  
  "recordsTotal": 959,  
  "recordsFiltered": 959  
}  
\`\`\`

\---

\#\#\# Ringkasan Indeks

Ringkasan semua indeks IDX (IHSG/COMPOSITE, LQ45, IDX30, dll).

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/index-summary\`  
\- \*\*Cache TTL:\*\* 1800s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`length\` | number | query | no | Jumlah indeks (default 50\) |  
| \`start\` | number | query | no | Offset (default 0\) |  
| \`date\` | string | query | no | Tanggal data (YYYYMMDD atau YYYY-MM-DD). Default hari bursa terakhir. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/index-summary?length=50\&start=0\&date=20260612" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/index-summary?length=50\&start=0\&date=20260612", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/index-summary?length=50\&start=0\&date=20260612",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "No": 1,  
      "Date": "2026-06-12T00:00:00",  
      "Close": 6007.656,  
      "Value": 21654846683780,  
      "Change": 121.624,  
      "Lowest": 5952.852,  
      "Volume": 34775696450,  
      "Highest": 6074.072,  
      "Previous": 5886.032,  
      "Frequency": 2346364,  
      "IndexCode": "COMPOSITE",  
      "MarketCapital": 10524297346477400,  
      "NumberOfStock": 913,  
      "IndexSummaryID": 193005  
    },  
    {  
      "No": 2,  
      "Date": "2026-06-12T00:00:00",  
      "Close": 597.448,  
      "Value": 12206901755616,  
      "Change": 10.606,  
      "Lowest": 594.635,  
      "Volume": 12651287578,  
      "Highest": 607.958,  
      "Previous": 586.842,  
      "Frequency": 819004,  
      "IndexCode": "LQ45",  
      "MarketCapital": 4125839000206770,  
      "NumberOfStock": 45,  
      "IndexSummaryID": 193006  
    },  
    {  
      "No": 3,  
      "Date": "2026-06-12T00:00:00",  
      "Close": 87.187,  
      "Value": 9911848320501,  
      "Change": 1.362,  
      "Lowest": 86.992,  
      "Volume": 3945789568,  
      "Highest": 88.837,  
      "Previous": 85.825,  
      "Frequency": 586876,  
      "IndexCode": "IDXLQ45LCL",  
      "MarketCapital": 4303050354047150,  
      "NumberOfStock": 37,  
      "IndexSummaryID": 193045  
    },  
    {  
      "No": 4,  
      "Date": "2026-06-12T00:00:00",  
      "Close": 338.988,  
      "Value": 10146806912295,  
      "Change": 4.6,  
      "Lowest": 338.707,  
      "Volume": 10087520928,  
      "Highest": 345.174,  
      "Previous": 334.388,  
      "Frequency": 623335,  
      "IndexCode": "IDX30",  
      "MarketCapital": 3507589087883250,  
      "NumberOfStock": 30,  
      "IndexSummaryID": 193014  
    },  
    {  
      "No": 5,  
      "Date": "2026-06-12T00:00:00",  
      "Close": 89.678,  
      "Value": 16205619462397,  
      "Change": 1.963,  
      "Lowest": 88.938,  
      "Volume": 16349915979,  
      "Highest": 91.217,  
      "Previous": 87.715,  
      "Frequency": 1172821,  
      "IndexCode": "IDX80",  
      "MarketCapital": 4994502370344020,  
      "NumberOfStock": 80,  
      "IndexSummaryID": 193025  
    }  
  \],  
  "dataset": "index-summary",  
  "provider": "idx",  
  "recordsTotal": 45  
}  
\`\`\`

\---

\#\#\# Top Movers

Saham paling aktif: top gainer, loser, volume, value, frequent.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/top-movers\`  
\- \*\*Cache TTL:\*\* 900s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`type\` | enum(gainer|loser|volume|value|frequent) | query | yes | Jenis: gainer (naik), loser (turun), volume, value, frequent (paling sering) |  
| \`resultCount\` | number | query | no | Jumlah saham teratas yang dikembalikan (default 10\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/top-movers?type=gainer\&resultCount=10" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/top-movers?type=gainer\&resultCount=10", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/top-movers?type=gainer\&resultCount=10",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "Code": "KIOS",  
      "Price": 91,  
      "Value": 4186683900,  
      "Change": 23,  
      "Volume": 49168300,  
      "Percent": 33.82,  
      "Frequency": 2892  
    },  
    {  
      "Code": "ASPR",  
      "Price": 216,  
      "Value": 140679325600,  
      "Change": 51,  
      "Volume": 705910000,  
      "Percent": 30.91,  
      "Frequency": 38164  
    },  
    {  
      "Code": "PART",  
      "Price": 100,  
      "Value": 2590827500,  
      "Change": 20,  
      "Volume": 27542300,  
      "Percent": 25,  
      "Frequency": 2324  
    },  
    {  
      "Code": "BUKK",  
      "Price": 1005,  
      "Value": 280842500,  
      "Change": 200,  
      "Volume": 289400,  
      "Percent": 24.84,  
      "Frequency": 212  
    },  
    {  
      "Code": "RLCO",  
      "Price": 3020,  
      "Value": 11771918000,  
      "Change": 600,  
      "Volume": 4123100,  
      "Percent": 24.79,  
      "Frequency": 4944  
    }  
  \],  
  "type": "gainer",  
  "dataset": "top-movers",  
  "provider": "idx",  
  "resultCount": 5  
}  
\`\`\`

\---

\#\#\# Ringkasan Broker

Ringkasan perdagangan per broker/anggota bursa.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/broker-summary\`  
\- \*\*Cache TTL:\*\* 1800s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`length\` | number | query | no | Jumlah broker (default 50\) |  
| \`start\` | number | query | no | Offset (default 0\) |  
| \`date\` | string | query | no | Tanggal data (YYYYMMDD atau YYYY-MM-DD). Default hari bursa terakhir. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/broker-summary?length=50\&start=0\&date=20260612" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/broker-summary?length=50\&start=0\&date=20260612", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/broker-summary?length=50\&start=0\&date=20260612",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "No": 1,  
      "Date": "2026-06-12T00:00:00",  
      "Value": 1187317700,  
      "IDFirm": "AD",  
      "Volume": 5131200,  
      "FirmName": "Sukadana Prima Sekuritas",  
      "Frequency": 204,  
      "IDBrokerSummary": 957287  
    },  
    {  
      "No": 2,  
      "Date": "2026-06-12T00:00:00",  
      "Value": 3582812000,  
      "IDFirm": "AF",  
      "Volume": 5211500,  
      "FirmName": "Harita Kencana Sekuritas",  
      "Frequency": 145,  
      "IDBrokerSummary": 957288  
    },  
    {  
      "No": 3,  
      "Date": "2026-06-12T00:00:00",  
      "Value": 198130186500,  
      "IDFirm": "AG",  
      "Volume": 296854100,  
      "FirmName": "Kiwoom Sekuritas Indonesia",  
      "Frequency": 22106,  
      "IDBrokerSummary": 957289  
    }  
  \],  
  "start": 0,  
  "length": 3,  
  "dataset": "broker-summary",  
  "provider": "idx",  
  "recordsTotal": 88  
}  
\`\`\`

\---

\#\#\# Emiten Tercatat

Profil perusahaan/emiten tercatat di BEI.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/companies\`  
\- \*\*Cache TTL:\*\* 21600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`length\` | number | query | no | Jumlah emiten per halaman (default 20, max 1000\) |  
| \`start\` | number | query | no | Offset (default 0\) |  
| \`code\` | string | query | no | Filter kode emiten tertentu (opsional) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/companies?length=20\&start=0\&code=BBCA" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/companies?length=20\&start=0\&code=BBCA", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/companies?length=20\&start=0\&code=BBCA",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "id": 0,  
      "BAE": "PT. Datindo Entrycom",  
      "Fax": "(021) 2553 3066",  
      "Logo": "/Portals/0/StaticData/ListedCompanies/LogoEmiten/AADI.jpg",  
      "NPKP": "",  
      "NPWP": "02.433.115.9-091.000",  
      "Email": "corsec@adaroindonesia.com",  
      "Alamat": "Cyber 2 Tower Lantai 26\\nJl. H.R. Rasuna Said Blok X-5, No.13\\nJakarta 12950 \- Indonesia",  
      "DataID": 0,  
      "Divisi": null,  
      "Sektor": "Energi",  
      "Status": 0,  
      "Telepon": "(021) 2553 3065",  
      "Website": "www.adaroindonesia.com",  
      "Industri": "Batu Bara",  
      "SubSektor": "Minyak, Gas \&amp; Batu Bara",  
      "KodeDivisi": null,  
      "KodeEmiten": "AADI",  
      "NamaEmiten": "PT Adaro Andalan Indonesia Tbk",  
      "JenisEmiten": null,  
      "SubIndustri": "Produksi Batu Bara",  
      "EfekEmiten\_EBA": false,  
      "EfekEmiten\_ETF": false,  
      "EfekEmiten\_SPEI": false,  
      "PapanPencatatan": "Utama",  
      "EfekEmiten\_Saham": true,  
      "TanggalPencatatan": "2024-12-05T00:00:00",  
      "KegiatanUsahaUtama": "Perkebunan kelapa sawit, karet dan tanaman penghasil getah lain, perusahaan holding, dan konsultasi manajemen lainnya",  
      "EfekEmiten\_Obligasi": false  
    },  
    {  
      "id": 0,  
      "BAE": "PT. Raya Saham Registra",  
      "Fax": "461-6655, 461-6677, 461-6688",  
      "Logo": "/Portals/0/StaticData/ListedCompanies/LogoEmiten/AALI.jpg",  
      "NPKP": "",  
      "NPWP": "001.334.427.0-054.000",  
      "Email": "Investor@astra-agro.co.id",  
      "Alamat": "Jl. Puloayang Raya Kawasan Industri Pulo Gadung, OR, 1, Jatinegara, Cakung, Kota ADM, Jakarta Timur, DKI Jakarta, 13930",  
      "DataID": 0,  
      "Divisi": null,  
      "Sektor": "Barang Konsumen Primer",  
      "Status": 0,  
      "Telepon": "461-65-55",  
      "Website": "http://www.astra-agro.co.id",  
      "Industri": "Produk Makanan Pertanian",  
      "SubSektor": "Makanan \&amp; Minuman",  
      "KodeDivisi": null,  
      "KodeEmiten": "AALI",  
      "NamaEmiten": "Astra Agro Lestari Tbk",  
      "JenisEmiten": null,  
      "SubIndustri": "Perkebunan \&amp; Tanaman Pangan",  
      "EfekEmiten\_EBA": false,  
      "EfekEmiten\_ETF": false,  
      "EfekEmiten\_SPEI": false,  
      "PapanPencatatan": "Utama",  
      "EfekEmiten\_Saham": true,  
      "TanggalPencatatan": "1997-12-09T00:00:00",  
      "KegiatanUsahaUtama": "Agriculture Plantation",  
      "EfekEmiten\_Obligasi": false  
    }  
  \],  
  "start": 0,  
  "length": 2,  
  "dataset": "listed-companies",  
  "provider": "idx",  
  "recordsTotal": 958,  
  "recordsFiltered": 958  
}  
\`\`\`

\---

\#\#\# Daftar Securities

Daftar saham tercatat: kode, nama, listing date, jumlah saham, papan.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/securities\`  
\- \*\*Cache TTL:\*\* 21600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`length\` | number | query | no | Jumlah per halaman (default 20, max 1000\) |  
| \`start\` | number | query | no | Offset (default 0\) |  
| \`code\` | string | query | no | Filter kode saham (opsional) |  
| \`sector\` | string | query | no | Filter sektor (opsional) |  
| \`board\` | string | query | no | Filter papan pencatatan: Utama/Pengembangan/Akselerasi/Ekonomi-Baru (opsional) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/securities?length=20\&start=0\&code=BBCA\&sector=Financials\&board=Utama" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/securities?length=20\&start=0\&code=BBCA\&sector=Financials\&board=Utama", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/securities?length=20\&start=0\&code=BBCA\&sector=Financials\&board=Utama",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "Code": "AALI",  
      "Name": "Astra Agro Lestari Tbk.",  
      "Shares": 1924688333,  
      "ListingDate": "1997-12-09T00:00:00",  
      "ListingBoard": "Utama"  
    },  
    {  
      "Code": "ABBA",  
      "Name": "Mahaka Media Tbk.",  
      "Shares": 3935892857,  
      "ListingDate": "2002-04-03T00:00:00",  
      "ListingBoard": "Pemantauan Khusus"  
    },  
    {  
      "Code": "ABDA",  
      "Name": "Asuransi Bina Dana Arta Tbk.",  
      "Shares": 620806680,  
      "ListingDate": "1989-07-06T00:00:00",  
      "ListingBoard": "Pengembangan"  
    }  
  \],  
  "start": 0,  
  "length": 3,  
  "dataset": "securities",  
  "provider": "idx",  
  "recordsTotal": 957,  
  "recordsFiltered": 957  
}  
\`\`\`

\---

\#\#\# Laporan Keuangan

Laporan keuangan emiten per tahun/periode (link file).

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/financial-report\`  
\- \*\*Cache TTL:\*\* 21600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`year\` | number | query | yes | Tahun laporan |  
| \`period\` | enum(tw1|tw2|tw3|audit) | query | no | Periode: tw1/tw2/tw3 (triwulan) atau audit (tahunan). Default audit |  
| \`code\` | string | query | no | Filter kode emiten (opsional) |  
| \`length\` | number | query | no | Jumlah baris (default 20\) |  
| \`start\` | number | query | no | Offset (default 0\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/financial-report?year=2024\&period=audit\&code=BBCA\&length=20\&start=0" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/financial-report?year=2024\&period=audit\&code=BBCA\&length=20\&start=0", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/financial-report?year=2024\&period=audit\&code=BBCA\&length=20\&start=0",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "KodeEmiten": "AADI",  
      "NamaEmiten": "PT Adaro Andalan Indonesia Tbk",  
      "Attachments": \[  
        {  
          "File\_ID": "edca4d28-7ff8-4c32-b18e-14141cb0dd59",  
          "File\_Name": "AnnualReport2024-AADI.pdf",  
          "File\_Path": "/Portals/0/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202504/52ff57ad3c\_f6912de316.pdf",  
          "File\_Size": 0,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "PT Adaro Andalan Indonesia Tbk",  
          "Emiten\_Code": "AADI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-04T18:44:28.883",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "96655ee5-3cb9-4c0e-95d9-16db102cc978",  
          "File\_Name": "FinancialStatement-2024-Tahunan-AADI.xlsx",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/AADI/FinancialStatement-2024-Tahunan-AADI.xlsx",  
          "File\_Size": 367860,  
          "File\_Type": ".xlsx",  
          "NamaEmiten": "PT Adaro Andalan Indonesia Tbk",  
          "Emiten\_Code": "AADI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-04T18:44:28.883",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "0949d36e-9a7a-4add-8b07-2e2399aeac61",  
          "File\_Name": "Checklist Pengungkapan LK 31 Desember 2024 AADI.pdf",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/AADI/Checklist Pengungkapan LK 31 Desember 2024 AADI.pdf",  
          "File\_Size": 704955,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "PT Adaro Andalan Indonesia Tbk",  
          "Emiten\_Code": "AADI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-04T18:44:28.883",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "bd296b95-7ee6-4846-b2c9-59a2ada5e06d",  
          "File\_Name": "FS 31 December 2024 AADI.pdf",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/AADI/FS 31 December 2024 AADI.pdf",  
          "File\_Size": 5432342,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "PT Adaro Andalan Indonesia Tbk",  
          "Emiten\_Code": "AADI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-04T18:44:28.883",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "a97b2840-c80c-402b-99ee-6660a9922549",  
          "File\_Name": "FinancialStatement-2024-Tahunan-AADI.pdf",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/AADI/FinancialStatement-2024-Tahunan-AADI.pdf",  
          "File\_Size": 891780,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "PT Adaro Andalan Indonesia Tbk",  
          "Emiten\_Code": "AADI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-04T18:44:28.883",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "2ac61344-c584-4dff-a805-a6fb291dc445",  
          "File\_Name": "inlineXBRL.zip",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/AADI/inlineXBRL.zip",  
          "File\_Size": 273599,  
          "File\_Type": ".zip",  
          "NamaEmiten": "PT Adaro Andalan Indonesia Tbk",  
          "Emiten\_Code": "AADI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-04T18:44:28.883",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "48834fc8-0ac3-4fda-933b-da8fa22f0a3e",  
          "File\_Name": "AnnualReport2024-AADI-att1.pdf",  
          "File\_Path": "/Portals/0/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202504/dd68aa1634\_ccc31cec64.pdf",  
          "File\_Size": 0,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "PT Adaro Andalan Indonesia Tbk",  
          "Emiten\_Code": "AADI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-04T18:44:28.883",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "109b23cc-ef8c-438e-ad40-e4cd8aa8fdd9",  
          "File\_Name": "instance.zip",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/AADI/instance.zip",  
          "File\_Size": 143996,  
          "File\_Type": ".zip",  
          "NamaEmiten": "PT Adaro Andalan Indonesia Tbk",  
          "Emiten\_Code": "AADI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-04T18:44:28.883",  
          "Report\_Period": "Audit"  
        }  
      \],  
      "Report\_Year": "2024",  
      "File\_Modified": "2025-03-04T18:44:28.883",  
      "Report\_Period": "Audit"  
    },  
    {  
      "KodeEmiten": "AALI",  
      "NamaEmiten": "Astra Agro Lestari Tbk",  
      "Attachments": \[  
        {  
          "File\_ID": "9d040440-11e2-44e2-a4b3-0afffce8a8b8",  
          "File\_Name": "instance.zip",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/AALI/instance.zip",  
          "File\_Size": 124227,  
          "File\_Type": ".zip",  
          "NamaEmiten": "Astra Agro Lestari Tbk",  
          "Emiten\_Code": "AALI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-02-20T18:52:30.817",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "babe240e-7b3a-48e2-a0ca-32f53516bc2e",  
          "File\_Name": "AnnualReport2024-AALI-att1.pdf",  
          "File\_Path": "/Portals/0/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202503/dcb2b35d05\_b2fb6becaa.pdf",  
          "File\_Size": 0,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "Astra Agro Lestari Tbk",  
          "Emiten\_Code": "AALI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-02-20T18:52:30.817",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "c5873da8-a4f2-42b7-b065-5c013847bc9f",  
          "File\_Name": "AALI Surat Pernyataan Direksi LK Tahunan 2024.pdf",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/AALI/AALI Surat Pernyataan Direksi LK Tahunan 2024.pdf",  
          "File\_Size": 387898,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "Astra Agro Lestari Tbk",  
          "Emiten\_Code": "AALI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-02-20T18:52:30.817",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "1c5cd578-a398-4d0c-85a1-7b6ca4987f8a",  
          "File\_Name": "AALI LK Tahunan 2024.pdf",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/AALI/AALI LK Tahunan 2024.pdf",  
          "File\_Size": 3197496,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "Astra Agro Lestari Tbk",  
          "Emiten\_Code": "AALI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-02-20T18:52:30.817",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "c181691a-f95d-4433-91d5-84a3084be6e9",  
          "File\_Name": "FinancialStatement-2024-Tahunan-AALI.pdf",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/AALI/FinancialStatement-2024-Tahunan-AALI.pdf",  
          "File\_Size": 800894,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "Astra Agro Lestari Tbk",  
          "Emiten\_Code": "AALI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-02-20T18:52:30.817",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "7892d4ec-62dc-45fc-8ba9-a76d117dfbaa",  
          "File\_Name": "FinancialStatement-2024-Tahunan-AALI.xlsx",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/AALI/FinancialStatement-2024-Tahunan-AALI.xlsx",  
          "File\_Size": 317450,  
          "File\_Type": ".xlsx",  
          "NamaEmiten": "Astra Agro Lestari Tbk",  
          "Emiten\_Code": "AALI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-02-20T18:52:30.817",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "9bcea6a0-5e5a-4147-abc2-acddc0b32df4",  
          "File\_Name": "AALI Checklist Pengungkapan LK AALI 2024.pdf",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/AALI/AALI Checklist Pengungkapan LK AALI 2024.pdf",  
          "File\_Size": 969992,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "Astra Agro Lestari Tbk",  
          "Emiten\_Code": "AALI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-02-20T18:52:30.817",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "149f5493-e3d6-4fa5-9246-c3a20f005695",  
          "File\_Name": "AnnualReport2024-AALI.pdf",  
          "File\_Path": "/Portals/0/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202503/7bf46a818f\_3ba87d6580.pdf",  
          "File\_Size": 0,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "Astra Agro Lestari Tbk",  
          "Emiten\_Code": "AALI",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-02-20T18:52:30.817",  
          "Report\_Period": "Audit"  
        }  
      \],  
      "Report\_Year": "2024",  
      "File\_Modified": "2025-02-20T18:52:30.817",  
      "Report\_Period": "Audit"  
    },  
    {  
      "KodeEmiten": "ABBA",  
      "NamaEmiten": "Mahaka Media Tbk",  
      "Attachments": \[  
        {  
          "File\_ID": "8283aeb0-8e02-4b1b-91b7-02257c5532bd",  
          "File\_Name": "AnnualReport2024-ABBA.pdf",  
          "File\_Path": "/Portals/0/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202505/57d67f88ce\_bf92dc00a5.pdf",  
          "File\_Size": 0,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "Mahaka Media Tbk",  
          "Emiten\_Code": "ABBA",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-27T00:15:30.017",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "fe5a1e16-22d1-4fe5-9176-1690139036e1",  
          "File\_Name": "inlineXBRL.zip",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/ABBA/inlineXBRL.zip",  
          "File\_Size": 221844,  
          "File\_Type": ".zip",  
          "NamaEmiten": "Mahaka Media Tbk",  
          "Emiten\_Code": "ABBA",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-27T00:15:30.017",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "92511c9f-5772-4454-ac1e-19666e315b18",  
          "File\_Name": "AnnualReport2024-ABBA-att1.pdf",  
          "File\_Path": "/Portals/0/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202505/8d0ec2f5d0\_7ad9ace030.pdf",  
          "File\_Size": 0,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "Mahaka Media Tbk",  
          "Emiten\_Code": "ABBA",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-27T00:15:30.017",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "17f0c06e-5acc-4461-9cf5-22bbdb2433a9",  
          "File\_Name": "instance.zip",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/ABBA/instance.zip",  
          "File\_Size": 111972,  
          "File\_Type": ".zip",  
          "NamaEmiten": "Mahaka Media Tbk",  
          "Emiten\_Code": "ABBA",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-27T00:15:30.017",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "0175e873-dc52-4d3b-9ed2-2cd12aef8044",  
          "File\_Name": "FinancialStatement-2024-Tahunan-ABBA.xlsx",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/ABBA/FinancialStatement-2024-Tahunan-ABBA.xlsx",  
          "File\_Size": 307403,  
          "File\_Type": ".xlsx",  
          "NamaEmiten": "Mahaka Media Tbk",  
          "Emiten\_Code": "ABBA",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-27T00:15:30.017",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "154f052f-044c-45a7-ba1a-3a78baaf1e05",  
          "File\_Name": "Surat\_Pengantar LK ABBA.pdf",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/ABBA/Surat\_Pengantar LK ABBA.pdf",  
          "File\_Size": 286181,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "Mahaka Media Tbk",  
          "Emiten\_Code": "ABBA",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-27T00:15:30.017",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "51e228be-e2bd-41fb-baa4-a06fbb4d4738",  
          "File\_Name": "Lapkeu ABBA 31 Des 24\_IDX.pdf",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/ABBA/Lapkeu ABBA 31 Des 24\_IDX.pdf",  
          "File\_Size": 8920519,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "Mahaka Media Tbk",  
          "Emiten\_Code": "ABBA",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-27T00:15:30.017",  
          "Report\_Period": "Audit"  
        },  
        {  
          "File\_ID": "22609fcf-2156-4996-ac00-ae881f0ac1a1",  
          "File\_Name": "Surat Pernyataan Direksi PT ABBA.pdf",  
          "File\_Path": "/Portals/0/StaticData/ListedCompanies/Corporate\_Actions/New\_Info\_JSX/Jenis\_Informasi/01\_Laporan\_Keuangan/02\_Soft\_Copy\_Laporan\_Keuangan//Laporan Keuangan Tahun 2024/Audit/ABBA/Surat Pernyataan Direksi PT ABBA.pdf",  
          "File\_Size": 444924,  
          "File\_Type": ".pdf",  
          "NamaEmiten": "Mahaka Media Tbk",  
          "Emiten\_Code": "ABBA",  
          "Report\_Type": "rdf",  
          "Report\_Year": "2024",  
          "File\_Modified": "2025-03-27T00:15:30.017",  
          "Report\_Period": "Audit"  
        }  
      \],  
      "Report\_Year": "2024",  
      "File\_Modified": "2025-03-27T00:15:30.017",  
      "Report\_Period": "Audit"  
    }  
  \],  
  "year": 2024,  
  "period": "audit",  
  "dataset": "financial-report",  
  "provider": "idx",  
  "recordsTotal": 936  
}  
\`\`\`

\---

\#\#\# Aktivitas Pasar

Saham suspend, relisting, dan UMA (Unusual Market Activity).

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/market-activity\`  
\- \*\*Cache TTL:\*\* 1800s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`type\` | enum(suspend|relisting|uma) | query | yes | Jenis: suspend (saham disuspend), relisting, uma (Unusual Market Activity) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/market-activity?type=suspend" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/market-activity?type=suspend", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/market-activity?type=suspend",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": {  
    "Results": \[  
      {  
        "Judul": "UMA atas Saham PT Solusi Environment Asia Tbk. (SOFA)",  
        "UMAID": null,  
        "Status": null,  
        "UMADate": "2026-06-11T00:00:00",  
        "CompanyID": "SOFA",  
        "Attachment": "/Portals/0/StaticData/NewsAndAnnouncement/UMA/2026/JUN/20260611-WAS\_UMA\_SOFA.pdf",  
        "CompanyName": null,  
        "AnnouncementNo": null  
      },  
      {  
        "Judul": "UMA atas Saham PT Sinarmas Multiartha Tbk. (SMMA)",  
        "UMAID": null,  
        "Status": null,  
        "UMADate": "2026-06-09T00:00:00",  
        "CompanyID": "SMMA",  
        "Attachment": "/Portals/0/StaticData/NewsAndAnnouncement/UMA/2026/JUN/20260609-WAS\_UMA\_SMMA.pdf",  
        "CompanyName": null,  
        "AnnouncementNo": null  
      },  
      {  
        "Judul": "UMA atas Saham PT Sentul City Tbk. (BKSL)",  
        "UMAID": null,  
        "Status": null,  
        "UMADate": "2026-06-08T00:00:00",  
        "CompanyID": "BKSL",  
        "Attachment": "/Portals/0/StaticData/NewsAndAnnouncement/UMA/2026/JUN/20260608-WAS\_UMA\_BKSL.pdf",  
        "CompanyName": null,  
        "AnnouncementNo": null  
      },  
      {  
        "Judul": "UMA atas Saham PT Techno9 Indonesia Tbk. (NINE)",  
        "UMAID": null,  
        "Status": null,  
        "UMADate": "2026-06-08T00:00:00",  
        "CompanyID": "NINE",  
        "Attachment": "/Portals/0/StaticData/NewsAndAnnouncement/UMA/2026/JUN/20260608-WAS\_UMA\_NINE.pdf",  
        "CompanyName": null,  
        "AnnouncementNo": null  
      },  
      {  
        "Judul": "UMA atas Saham PT Kedoya Adyaraya Tbk. (RSGK)",  
        "UMAID": null,  
        "Status": null,  
        "UMADate": "2026-06-08T00:00:00",  
        "CompanyID": "RSGK",  
        "Attachment": "/Portals/0/StaticData/NewsAndAnnouncement/UMA/2026/JUN/20260608-WAS\_UMA\_RSGK.pdf",  
        "CompanyName": null,  
        "AnnouncementNo": null  
      },  
      {  
        "Judul": "UMA atas Saham PT First Media Tbk. (KBLV)",  
        "UMAID": null,  
        "Status": null,  
        "UMADate": "2026-06-08T00:00:00",  
        "CompanyID": "KBLV",  
        "Attachment": "/Portals/0/StaticData/NewsAndAnnouncement/UMA/2026/JUN/20260608-WAS\_UMA\_KBLV.pdf",  
        "CompanyName": null,  
        "AnnouncementNo": null  
      },  
      {  
        "Judul": "UMA atas Saham PT RMK Energy Tbk. (RMKE)",  
        "UMAID": null,  
        "Status": null,  
        "UMADate": "2026-06-08T00:00:00",  
        "CompanyID": "RMKE",  
        "Attachment": "/Portals/0/StaticData/NewsAndAnnouncement/UMA/2026/JUN/20260608-WAS\_UMA\_RMKE.pdf",  
        "CompanyName": null,  
        "AnnouncementNo": null  
      }  
    \],  
    "ResultCount": 0,  
    "SearchCriteria": {  
      "DateTo": null,  
      "Keyword": "not used",  
      "DateFrom": null,  
      "pagesize": 10,  
      "indexfrom": 0  
    }  
  },  
  "type": "uma",  
  "dataset": "market-activity",  
  "provider": "idx"  
}  
\`\`\`

\---

\#\#\# Berita & Pengumuman

Berita dan pengumuman bursa, bisa dicari per kata kunci.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/news\`  
\- \*\*Cache TTL:\*\* 1800s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`keyword\` | string | query | no | Kata kunci pencarian (opsional) |  
| \`length\` | number | query | no | Jumlah berita (default 10\) |  
| \`start\` | number | query | no | Offset (default 0\) |  
| \`dateFrom\` | string | query | no | Tanggal mulai filter (YYYYMMDD atau YYYY-MM-DD, opsional) |  
| \`dateTo\` | string | query | no | Tanggal akhir filter (YYYYMMDD atau YYYY-MM-DD, opsional) |  
| \`locale\` | enum(id|en) | query | no | Bahasa (id/en, default id) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/news?keyword=dividen\&length=10\&start=0\&dateFrom=20260101\&dateTo=20260613\&locale=id" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/news?keyword=dividen\&length=10\&start=0\&dateFrom=20260101\&dateTo=20260613\&locale=id", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/news?keyword=dividen\&length=10\&start=0\&dateFrom=20260101\&dateTo=20260613\&locale=id",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "Id": 11692,  
      "Tags": "RUPST",  
      "Links": \[  
        {  
          "Rel": "self",  
          "Href": "/api/api/publication/news/11692",  
          "Method": "GET"  
        }  
      \],  
      "Title": "Panggilan Rapat Umum Pemegang Saham Tahunan PT Bursa Efek Indonesia Tahun 2026",  
      "ItemId": "2fb61ad4-2b66-f111-b149-dacbee12ffcb",  
      "Locale": "id-id",  
      "Summary": "Panggilan Rapat Umum Pemegang Saham Tahunan PT Bursa Efek Indonesia Tahun 2026",  
      "ImageUrl": "/media/1557/logo-bursa-efek-indonesia-final.jpg",  
      "PathBase": null,  
      "PathFile": null,  
      "IsHeadline": true,  
      "PublishedDate": "2026-06-12T08:00:00"  
    },  
    {  
      "Id": 11694,  
      "Tags": "Go Public,Workshop",  
      "Links": \[  
        {  
          "Rel": "self",  
          "Href": "/api/api/publication/news/11694",  
          "Method": "GET"  
        }  
      \],  
      "Title": "Go Public Workshop  “Go Public Sebagai Solusi Pendanaan di Tengah Tantangan Ekonomi Daerah” Kota Jayapura",  
      "ItemId": "b1c02193-3766-f111-b149-dacbee12ffcb",  
      "Locale": "id-id",  
      "Summary": "Go Public Workshop  “Go Public Sebagai Solusi Pendanaan di Tengah Tantangan Ekonomi Daerah” Kota Jayapura",  
      "ImageUrl": "/media/bmwgnbax/gpw-jayapura.jpg",  
      "PathBase": null,  
      "PathFile": null,  
      "IsHeadline": true,  
      "PublishedDate": "2026-06-02T12:00:00"  
    },  
    {  
      "Id": 11695,  
      "Tags": "Go Public,Workshop",  
      "Links": \[  
        {  
          "Rel": "self",  
          "Href": "/api/api/publication/news/11695",  
          "Method": "GET"  
        }  
      \],  
      "Title": "Go Public Workshop  “Go Public Sebagai Solusi Pendanaan di Tengah Tantangan Ekonomi Daerah” Kota Jayapura",  
      "ItemId": "b1c02193-3766-f111-b149-dacbee12ffcb",  
      "Locale": "en-us",  
      "Summary": "Go Public Workshop  “Go Public Sebagai Solusi Pendanaan di Tengah Tantangan Ekonomi Daerah” Kota Jayapura",  
      "ImageUrl": "/media/bmwgnbax/gpw-jayapura.jpg",  
      "PathBase": null,  
      "PathFile": null,  
      "IsHeadline": true,  
      "PublishedDate": "2026-06-02T12:00:00"  
    }  
  \],  
  "dataset": "news",  
  "keyword": "saham",  
  "provider": "idx"  
}  
\`\`\`

\---

\#\#\# Index Halaman

Index semua halaman publik idx.co.id (464 URL), terkategorikan per section.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/sitemap\`  
\- \*\*Cache TTL:\*\* 86400s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`locale\` | enum(id|en|all) | query | no | Filter bahasa URL: id, en, atau all (default id) |  
| \`section\` | string | query | no | Filter section tertentu (mis. data-pasar, perusahaan-tercatat, berita) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/sitemap?locale=id\&section=data-pasar" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/sitemap?locale=id\&section=data-pasar", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/sitemap?locale=id\&section=data-pasar",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "note": "Menampilkan 7 URL di section \\"idx-syariah\\".",  
  "urls": \[  
    "https://www.idx.co.id/id/idx-syariah/edukasi-pasar-modal-syariah",  
    "https://www.idx.co.id/id/idx-syariah/fatwa-regulasi",  
    "https://www.idx.co.id/id/idx-syariah/hubungi-kami",  
    "https://www.idx.co.id/id/idx-syariah/indeks-saham-syariah",  
    "https://www.idx.co.id/id/idx-syariah/pertanyaan-dan-jawaban",  
    "https://www.idx.co.id/id/idx-syariah/produk-syariah",  
    "https://www.idx.co.id/id/idx-syariah/transaksi-sesuai-syariah"  
  \],  
  "locale": "id",  
  "dataset": "sitemap",  
  "provider": "idx",  
  "totalUrls": 232,  
  "sectionCounts": {  
    "faq": 1,  
    "akun": 5,  
    "masuk": 2,  
    "berita": 11,  
    "daftar": 1,  
    "https:": 1,  
    "produk": 13,  
    "sitemap": 1,  
    "sign-out": 1,  
    "investhub": 13,  
    "peraturan": 7,  
    "data-pasar": 113,  
    "notifikasi": 1,  
    "idx-syariah": 7,  
    "market-data": 17,  
    "tentang-bei": 14,  
    "lupa-password": 1,  
    "daftar-istilah": 1,  
    "hasil-pencarian": 1,  
    "verifikasi-email": 1,  
    "form-atur-password": 1,  
    "perusahaan-tercatat": 13,  
    "verifikasi-email-sukses": 1,  
    "anggota-bursa-dan-partisipan": 5  
  }  
}  
\`\`\`

\---

\#\#\# Raw Passthrough

Akses endpoint data IDX /primary/... apa pun sebagai JSON (fleksibel, ratusan endpoint).

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/raw\`  
\- \*\*Cache TTL:\*\* 1800s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`path\` | string | query | yes | Path endpoint IDX setelah /primary/ (format Modul/GetXxx). Modul valid: TradingSummary, ListedCompany, StockData, Home, NewsAnnouncement, ExchangeMember, ListingActivity, BondSukuk, Slb, DerivativesData, StructuredWarrant, Regulation, dll. |  
| \`query\` | string | query | no | Query string mentah yang ditempel ke endpoint (opsional). Contoh: length=20\&start=0\&kodeEmiten=BBCA |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/raw?path=TradingSummary%2FGetStockSummary\&query=length%3D10%26start%3D0" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/raw?path=TradingSummary%2FGetStockSummary\&query=length%3D10%26start%3D0", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/raw?path=TradingSummary%2FGetStockSummary\&query=length%3D10%26start%3D0",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "No": 1,  
      "Bid": 8625,  
      "Low": 8050,  
      "Date": "2026-06-12T00:00:00",  
      "High": 8850,  
      "Close": 8650,  
      "Offer": 8650,  
      "Value": 182271837500,  
      "Change": 600,  
      "Volume": 21262200,  
      "persen": null,  
      "Remarks": "XDMO1SD0F10000A121------------",  
      "Previous": 8050,  
      "BidVolume": 29200,  
      "Frequency": 9962,  
      "OpenPrice": 8100,  
      "StockCode": "AADI",  
      "StockName": "Adaro Andalan Indonesia Tbk.",  
      "FirstTrade": 8075,  
      "ForeignBuy": 5896500,  
      "percentage": null,  
      "ForeignSell": 9874800,  
      "OfferVolume": 67500,  
      "ListedShares": 7786891760,  
      "DelistingDate": "",  
      "IDStockSummary": 4031673,  
      "TradebleShares": 7786891760,  
      "WeightForIndex": 1486517637,  
      "IndexIndividual": 155.9,  
      "NonRegularValue": 5466551,  
      "NonRegularVolume": 659,  
      "NonRegularFrequency": 16  
    },  
    {  
      "No": 2,  
      "Bid": 6175,  
      "Low": 6025,  
      "Date": "2026-06-12T00:00:00",  
      "High": 6325,  
      "Close": 6175,  
      "Offer": 6225,  
      "Value": 18983070000,  
      "Change": 125,  
      "Volume": 3068700,  
      "persen": null,  
      "Remarks": "--MO113E100000D232------------",  
      "Previous": 6050,  
      "BidVolume": 51900,  
      "Frequency": 3424,  
      "OpenPrice": 6075,  
      "StockCode": "AALI",  
      "StockName": "Astra Agro Lestari Tbk.",  
      "FirstTrade": 6050,  
      "ForeignBuy": 1104500,  
      "percentage": null,  
      "ForeignSell": 1285200,  
      "OfferVolume": 3000,  
      "ListedShares": 1924688333,  
      "DelistingDate": "",  
      "IDStockSummary": 4031674,  
      "TradebleShares": 1924688333,  
      "WeightForIndex": 390711732,  
      "IndexIndividual": 501.6,  
      "NonRegularValue": 0,  
      "NonRegularVolume": 0,  
      "NonRegularFrequency": 0  
    },  
    {  
      "No": 3,  
      "Bid": 35,  
      "Low": 35,  
      "Date": "2026-06-12T00:00:00",  
      "High": 35,  
      "Close": 35,  
      "Offer": 36,  
      "Value": 10220000,  
      "Change": 0,  
      "Volume": 292000,  
      "persen": null,  
      "Remarks": "--U-4100000000E614-E---------X",  
      "Previous": 35,  
      "BidVolume": 8000,  
      "Frequency": 59,  
      "OpenPrice": 0,  
      "StockCode": "ABBA",  
      "StockName": "Mahaka Media Tbk.",  
      "FirstTrade": 0,  
      "ForeignBuy": 0,  
      "percentage": null,  
      "ForeignSell": 0,  
      "OfferVolume": 1020800,  
      "ListedShares": 3935892857,  
      "DelistingDate": "",  
      "IDStockSummary": 4031675,  
      "TradebleShares": 3935892857,  
      "WeightForIndex": 1298844643,  
      "IndexIndividual": 77.3,  
      "NonRegularValue": 0,  
      "NonRegularVolume": 0,  
      "NonRegularFrequency": 0  
    },  
    {  
      "No": 4,  
      "Bid": 3220,  
      "Low": 3100,  
      "Date": "2026-06-12T00:00:00",  
      "High": 3430,  
      "Close": 3390,  
      "Offer": 3390,  
      "Value": 33689000,  
      "Change": 60,  
      "Volume": 10200,  
      "persen": null,  
      "Remarks": "--UO2105000000G412------------",  
      "Previous": 3330,  
      "BidVolume": 100,  
      "Frequency": 35,  
      "OpenPrice": 3430,  
      "StockCode": "ABDA",  
      "StockName": "Asuransi Bina Dana Arta Tbk.",  
      "FirstTrade": 3340,  
      "ForeignBuy": 0,  
      "percentage": null,  
      "ForeignSell": 0,  
      "OfferVolume": 8600,  
      "ListedShares": 620806680,  
      "DelistingDate": "",  
      "IDStockSummary": 4031676,  
      "TradebleShares": 620806680,  
      "WeightForIndex": 81325675,  
      "IndexIndividual": 773.9,  
      "NonRegularValue": 0,  
      "NonRegularVolume": 0,  
      "NonRegularFrequency": 0  
    },  
    {  
      "No": 5,  
      "Bid": 2400,  
      "Low": 2300,  
      "Date": "2026-06-12T00:00:00",  
      "High": 2440,  
      "Close": 2420,  
      "Offer": 2420,  
      "Value": 1755194000,  
      "Change": 120,  
      "Volume": 739300,  
      "persen": null,  
      "Remarks": "--MO1135000000A121------------",  
      "Previous": 2300,  
      "BidVolume": 33500,  
      "Frequency": 486,  
      "OpenPrice": 2300,  
      "StockCode": "ABMM",  
      "StockName": "ABM Investama Tbk.",  
      "FirstTrade": 2350,  
      "ForeignBuy": 135000,  
      "percentage": null,  
      "ForeignSell": 89800,  
      "OfferVolume": 20700,  
      "ListedShares": 2753165000,  
      "DelistingDate": "",  
      "IDStockSummary": 4031677,  
      "TradebleShares": 2753165000,  
      "WeightForIndex": 413800700,  
      "IndexIndividual": 64.5,  
      "NonRegularValue": 0,  
      "NonRegularVolume": 0,  
      "NonRegularFrequency": 0  
    },  
    {  
      "No": 6,  
      "Bid": 356,  
      "Low": 352,  
      "Date": "2026-06-12T00:00:00",  
      "High": 360,  
      "Close": 356,  
      "Offer": 358,  
      "Value": 11953271200,  
      "Change": 4,  
      "Volume": 33615200,  
      "persen": null,  
      "Remarks": "CDMO1835UK6000E743------------",  
      "Previous": 352,  
      "BidVolume": 1716000,  
      "Frequency": 3109,  
      "OpenPrice": 356,  
      "StockCode": "ACES",  
      "StockName": "Aspirasi Hidup Indonesia Tbk.",  
      "FirstTrade": 356,  
      "ForeignBuy": 3864700,  
      "percentage": null,  
      "ForeignSell": 7173800,  
      "OfferVolume": 446300,  
      "ListedShares": 17120389700,  
      "DelistingDate": "",  
      "IDStockSummary": 4031678,  
      "TradebleShares": 17120389700,  
      "WeightForIndex": 6846443841,  
      "IndexIndividual": 434.1,  
      "NonRegularValue": 0,  
      "NonRegularVolume": 0,  
      "NonRegularFrequency": 0  
    },  
    {  
      "No": 7,  
      "Bid": 61,  
      "Low": 60,  
      "Date": "2026-06-12T00:00:00",  
      "High": 65,  
      "Close": 61,  
      "Offer": 62,  
      "Value": 245539000,  
      "Change": 1,  
      "Volume": 3937300,  
      "persen": null,  
      "Remarks": "--UO2100000000E413------------",  
      "Previous": 60,  
      "BidVolume": 574400,  
      "Frequency": 489,  
      "OpenPrice": 60,  
      "StockCode": "ACRO",  
      "StockName": "Samcro Hyosung Adilestari Tbk.",  
      "FirstTrade": 60,  
      "ForeignBuy": 144900,  
      "percentage": null,  
      "ForeignSell": 84100,  
      "OfferVolume": 500,  
      "ListedShares": 3469345537,  
      "DelistingDate": "",  
      "IDStockSummary": 4031679,  
      "TradebleShares": 749273042,  
      "WeightForIndex": 729950301,  
      "IndexIndividual": 56.5,  
      "NonRegularValue": 0,  
      "NonRegularVolume": 0,  
      "NonRegularFrequency": 0  
    },  
    {  
      "No": 8,  
      "Bid": 71,  
      "Low": 70,  
      "Date": "2026-06-12T00:00:00",  
      "High": 71,  
      "Close": 71,  
      "Offer": 72,  
      "Value": 12333000,  
      "Change": 1,  
      "Volume": 173800,  
      "persen": null,  
      "Remarks": "--U-4105000000J211-E---------X",  
      "Previous": 70,  
      "BidVolume": 178500,  
      "Frequency": 56,  
      "OpenPrice": 0,  
      "StockCode": "ACST",  
      "StockName": "Acset Indonusa Tbk.",  
      "FirstTrade": 0,  
      "ForeignBuy": 0,  
      "percentage": null,  
      "ForeignSell": 0,  
      "OfferVolume": 20600,  
      "ListedShares": 17675160000,  
      "DelistingDate": "",  
      "IDStockSummary": 4031680,  
      "TradebleShares": 17675160000,  
      "WeightForIndex": 1560716628,  
      "IndexIndividual": 5.2,  
      "NonRegularValue": 0,  
      "NonRegularVolume": 0,  
      "NonRegularFrequency": 0  
    }  
  \],  
  "path": "TradingSummary/GetStockSummary",  
  "provider": "idx",  
  "recordsTotal": 959,  
  "recordsFiltered": 959  
}  
\`\`\`

\---

\#\#\# Announcements

Keterbukaan informasi seluruh emiten, terbaru dulu. Berbasis halaman: pakai \`page\`, bukan offset.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/announcements\`  
\- \*\*Cache TTL:\*\* 300s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`page\` | number | query | no | Halaman ke berapa (default 1). Upstream berbasis halaman, bukan offset |  
| \`length\` | number | query | no | Jumlah pengumuman per halaman (default 20, maks 100\) |  
| \`locale\` | enum(id|en) | query | no | Bahasa pengumuman (default id) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/announcements?page=1\&length=20\&locale=id" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/announcements?page=1\&length=20\&locale=id", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/announcements?page=1\&length=20\&locale=id",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "id": "20260802163712-045a/DIR/SP-MGU/VII/2026\_id-id",  
      "code": "FOLK",  
      "type": "STOCK",  
      "title": "Penyampaian Bukti Iklan Informasi Laporan Keuangan Interim",  
      "attachments": \[  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/f0a450fdce\_6f5321d463.pdf",  
          "fileName": "f0a450fdce\_6f5321d463.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/2e469f5e3d\_cd42b96455.pdf",  
          "fileName": "2e469f5e3d\_cd42b96455.pdf"  
        }  
      \],  
      "publishedAt": "2026-08-02T16:37:12",  
      "announcementNo": "045a/DIR/SP-MGU/VII/2026"  
    },  
    {  
      "id": "20260802072958-053/SLIS/VIII/2026\_id-id",  
      "code": "SLIS",  
      "type": "STOCK",  
      "title": "Penyampaian Bukti Iklan Informasi Laporan Keuangan Interim",  
      "attachments": \[  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/977e0ae856\_8adcd7e223.pdf",  
          "fileName": "977e0ae856\_8adcd7e223.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/eac4821036\_79437e2dc4.pdf",  
          "fileName": "eac4821036\_79437e2dc4.pdf"  
        }  
      \],  
      "publishedAt": "2026-08-02T07:29:58",  
      "announcementNo": "053/SLIS/VIII/2026"  
    },  
    {  
      "id": "20260802025556-18/SAVITRA/VII/2026\_id-id",  
      "code": "VISI",  
      "type": "STOCK",  
      "title": "Penyampaian Laporan Keuangan Interim Yang Tidak Diaudit",  
      "attachments": \[  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/20260802030815-64113-0/FinancialStatement-2026-II-VISI.pdf",  
          "fileName": "FinancialStatement-2026-II-VISI.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/20260802030815-64113-0/2026TW2 VISI Laporan Keuangan.pdf",  
          "fileName": "2026TW2 VISI Laporan Keuangan.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/20260802030815-64113-0/FinancialStatement-2026-II-VISI.xlsx",  
          "fileName": "FinancialStatement-2026-II-VISI.xlsx"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/20260802030815-64113-0/I 1 Laporan Penilaian atas Properti VISI.pdf",  
          "fileName": "I 1 Laporan Penilaian atas Properti VISI.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/20260802030815-64113-0/I.2. Laporan Pendapat Kewajaran Short Form\_FO VISI.pdf",  
          "fileName": "I.2. Laporan Pendapat Kewajaran Short Form\_FO VISI.pdf"  
        }  
      \],  
      "publishedAt": "2026-08-02T02:55:56",  
      "announcementNo": "18/SAVITRA/VII/2026"  
    },  
    {  
      "id": "20260802015716-JGI-\_id-id",  
      "code": "KAQI",  
      "type": "STOCK",  
      "title": "Penyampaian Laporan Keuangan Interim Yang Tidak Diaudit",  
      "attachments": \[  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/20260802021030-63811-0/FinancialStatement-2026-II-KAQI.pdf",  
          "fileName": "FinancialStatement-2026-II-KAQI.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/20260802021030-63811-0/FinancialStatement-2026-II-KAQI.xlsx",  
          "fileName": "FinancialStatement-2026-II-KAQI.xlsx"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/20260802021030-63811-0/inlineXBRL.zip",  
          "fileName": "inlineXBRL.zip"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/20260802021030-63811-0/instance.zip",  
          "fileName": "instance.zip"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/20260802021030-63811-0/LK Triwulan 2 2026 \- KAQI.pdf",  
          "fileName": "LK Triwulan 2 2026 \- KAQI.pdf"  
        }  
      \],  
      "publishedAt": "2026-08-02T01:57:16",  
      "announcementNo": "JGI-"  
    },  
    {  
      "id": "20260801160933-296/CORSEC-MPR/VIII/2026\_id-id",  
      "code": "MANG",  
      "type": "STOCK",  
      "title": "Penyampaian Bukti Iklan Informasi Laporan Keuangan Interim",  
      "attachments": \[  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/0791062731\_4460c064b2.pdf",  
          "fileName": "0791062731\_4460c064b2.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202608/31cce1a139\_9bfa0daec2.pdf",  
          "fileName": "31cce1a139\_9bfa0daec2.pdf"  
        }  
      \],  
      "publishedAt": "2026-08-01T16:09:33",  
      "announcementNo": "296/CORSEC-MPR/VIII/2026"  
    }  
  \],  
  "page": 1,  
  "total": 249151,  
  "length": 5,  
  "locale": "id",  
  "dataset": "announcements",  
  "provider": "idx"  
}  
\`\`\`

\---

\#\#\# Company Announcements

Keterbukaan informasi satu emiten — riwayat aksi korporasi per kode saham, lengkap dengan lampiran PDF.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/company-announcements\`  
\- \*\*Cache TTL:\*\* 600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | yes | Kode emiten, 4 huruf |  
| \`length\` | number | query | no | Jumlah pengumuman (default 20, maks 100\) |  
| \`start\` | number | query | no | Offset baris (default 0\) |  
| \`locale\` | enum(id|en) | query | no | Bahasa pengumuman (default id) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/company-announcements?code=BBCA\&length=20\&start=0\&locale=id" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/company-announcements?code=BBCA\&length=20\&start=0\&locale=id", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/company-announcements?code=BBCA\&length=20\&start=0\&locale=id",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "code": "BBCA",  
  "data": \[  
    {  
      "id": "20260731175614-0069/CVG/2026\_id-id",  
      "code": "BBCA",  
      "type": "STOCK",  
      "title": "Perubahan dalam pengendalian baik langsung maupun tidak langsung terhadap Emiten atau Perusahaan Publik",  
      "formId": "11000",  
      "subject": "Perubahan dalam pengendalian b",  
      "createdAt": "2026-07-31T18:30:02",  
      "attachments": \[  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/59c9d62180\_96a02df66f.pdf",  
          "fileName": "59c9d62180\_96a02df66f.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/0b9ec31383\_5b374efdf5.pdf",  
          "fileName": "0b9ec31383\_5b374efdf5.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/db24579a40\_b573109a83.pdf",  
          "fileName": "db24579a40\_b573109a83.pdf"  
        }  
      \],  
      "publishedAt": "2026-07-31T17:56:14",  
      "announcementNo": "0069/CVG/2026"  
    },  
    {  
      "id": "20260728181934-0064/ESG/2026\_id-id",  
      "code": "BBCA",  
      "type": "STOCK",  
      "title": "Penyampaian Press Release terkait Informasi Ringkasan Kinerja Keuangan Kuartal II Tahun 2026 (unaudited) PT Bank Central Asia Tbk (\\"Perseroan\\")",  
      "formId": "11000",  
      "subject": "Penyampaian Press Release terk",  
      "createdAt": "2026-07-28T18:30:02",  
      "attachments": \[  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/9956e3a8ee\_1a56c5de11.pdf",  
          "fileName": "9956e3a8ee\_1a56c5de11.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/7ce136cfc4\_ec3dd6d7b3.pdf",  
          "fileName": "7ce136cfc4\_ec3dd6d7b3.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/baeecd07ff\_9a67b3ef57.pdf",  
          "fileName": "baeecd07ff\_9a67b3ef57.pdf"  
        }  
      \],  
      "publishedAt": "2026-07-28T18:19:34",  
      "announcementNo": "0064/ESG/2026"  
    },  
    {  
      "id": "20260728162427-018/ATX/2026\_id-id",  
      "code": "BBCA",  
      "type": "STOCK",  
      "title": "Penyampaian Laporan Keuangan Interim Yang Tidak Diaudit",  
      "formId": "11000",  
      "createdAt": "2026-07-30T13:00:08",  
      "attachments": \[  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/20260728163316-62836-0/FinancialStatement-2026-II-BBCA.pdf",  
          "fileName": "FinancialStatement-2026-II-BBCA.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/20260728163316-62836-0/FinancialStatement-2026-II-BBCA.xlsx",  
          "fileName": "FinancialStatement-2026-II-BBCA.xlsx"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/20260728163316-62836-0/inlineXBRL.zip",  
          "fileName": "inlineXBRL.zip"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/20260728163316-62836-0/instance.zip",  
          "fileName": "instance.zip"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/20260728163316-62836-0/Lapkeu BCA Jun26.pdf",  
          "fileName": "Lapkeu BCA Jun26.pdf"  
        }  
      \],  
      "publishedAt": "2026-07-28T16:24:27",  
      "announcementNo": "018/ATX/2026"  
    },  
    {  
      "id": "20260710105147-00981/DIR/2026\_id-id",  
      "code": "BBCA",  
      "type": "STOCK",  
      "title": "Laporan Pengalihan Kembali Saham Hasil Buy Back",  
      "formId": "11000",  
      "subject": "Laporan Pengalihan Kembali Sah",  
      "createdAt": "2026-07-10T11:00:02",  
      "attachments": \[  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/cd76c6d811\_d338ec9267.pdf",  
          "fileName": "cd76c6d811\_d338ec9267.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/7bb835fe3d\_b356f2dad6.pdf",  
          "fileName": "7bb835fe3d\_b356f2dad6.pdf"  
        }  
      \],  
      "publishedAt": "2026-07-10T10:51:47",  
      "announcementNo": "00981/DIR/2026"  
    },  
    {  
      "id": "20260710105119-0981/DIR/2026\_id-id",  
      "code": "BBCA",  
      "type": "STOCK",  
      "title": "Laporan Pengalihan Kembali Saham Hasil Buy Back",  
      "formId": "11000",  
      "subject": "Laporan Pengalihan Kembali Sah",  
      "createdAt": "2026-07-10T11:00:02",  
      "attachments": \[  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/0cb6f181fc\_a9f10cbeaf.pdf",  
          "fileName": "0cb6f181fc\_a9f10cbeaf.pdf"  
        },  
        {  
          "url": "https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From\_EREP/202607/55a68a68f2\_56424250f3.pdf",  
          "fileName": "55a68a68f2\_56424250f3.pdf"  
        }  
      \],  
      "publishedAt": "2026-07-10T10:51:19",  
      "announcementNo": "0981/DIR/2026"  
    }  
  \],  
  "start": 0,  
  "total": 213,  
  "length": 5,  
  "locale": "id",  
  "dataset": "company-announcements",  
  "provider": "idx"  
}  
\`\`\`

\---

\#\#\# Foreign Flow

Beli/jual investor asing per saham per hari bursa. Satuannya LEMBAR SAHAM, bukan rupiah. Bisa diurutkan berdasar net, buy, sell, atau kode.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/foreign-flow\`  
\- \*\*Cache TTL:\*\* 300s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`date\` | string | query | no | Tanggal bursa (YYYYMMDD atau YYYY-MM-DD). Default: hari bursa terakhir |  
| \`code\` | string | query | no | Saring satu kode emiten saja (opsional) |  
| \`sort\` | enum(net|buy|sell|code) | query | no | Urutan: net (asing beli bersih terbesar), buy, sell, atau code. Default net |  
| \`length\` | number | query | no | Jumlah baris (default 50, maks 200\) |  
| \`start\` | number | query | no | Offset baris (default 0\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/foreign-flow?date=2026-07-31\&code=BBCA\&sort=net\&length=20\&start=0" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/foreign-flow?date=2026-07-31\&code=BBCA\&sort=net\&length=20\&start=0", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/foreign-flow?date=2026-07-31\&code=BBCA\&sort=net\&length=20\&start=0",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "code": "IATA",  
      "name": "Karya Pacific Energy Tbk.",  
      "close": 76,  
      "value": 116766853900,  
      "volume": 1640828700,  
      "foreignBuyShares": 243242400,  
      "netForeignShares": 88222700,  
      "foreignSellShares": 155019700  
    },  
    {  
      "code": "MDIA",  
      "name": "Intermedia Capital Tbk.",  
      "close": 191,  
      "value": 203053711800,  
      "volume": 1136885000,  
      "foreignBuyShares": 205545700,  
      "netForeignShares": 81968300,  
      "foreignSellShares": 123577400  
    },  
    {  
      "code": "BBRI",  
      "name": "Bank Rakyat Indonesia (Persero) Tbk.",  
      "close": 3040,  
      "value": 684938094000,  
      "volume": 226634400,  
      "foreignBuyShares": 153647100,  
      "netForeignShares": 76995400,  
      "foreignSellShares": 76651700  
    },  
    {  
      "code": "DMAS",  
      "name": "Puradelta Lestari Tbk.",  
      "close": 148,  
      "value": 23774851200,  
      "volume": 161620100,  
      "foreignBuyShares": 80222700,  
      "netForeignShares": 72178500,  
      "foreignSellShares": 8044200  
    },  
    {  
      "code": "PACK",  
      "name": "Abadi Nusantara Hijau Investama Tbk.",  
      "close": 248,  
      "value": 66056582800,  
      "volume": 275994200,  
      "foreignBuyShares": 83806000,  
      "netForeignShares": 51360600,  
      "foreignSellShares": 32445400  
    }  
  \],  
  "date": "2026-07-31T00:00:00",  
  "sort": "net",  
  "unit": "shares",  
  "start": 0,  
  "total": 963,  
  "length": 5,  
  "dataset": "foreign-flow",  
  "provider": "idx"  
}  
\`\`\`

\---

\#\#\# Margin Summary

Ringkasan perdagangan efek margin. Terbit per periode margin, bukan harian — perhatikan tanggal pada respons.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/margin-summary\`  
\- \*\*Cache TTL:\*\* 3600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`date\` | string | query | no | Tanggal periode (YYYYMMDD atau YYYY-MM-DD). Default: periode terakhir |  
| \`length\` | number | query | no | Jumlah baris (default 50, maks 300\) |  
| \`start\` | number | query | no | Offset baris (default 0\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/margin-summary?date=2026-07-14\&length=50\&start=0" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/margin-summary?date=2026-07-14\&length=50\&start=0", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/margin-summary?date=2026-07-14\&length=50\&start=0",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "low": 8350,  
      "code": "AADI",  
      "high": 8500,  
      "close": 8400,  
      "value": 4010085000,  
      "change": 25,  
      "volume": 474200,  
      "frequency": 178  
    },  
    {  
      "low": 6300,  
      "code": "AALI",  
      "high": 6375,  
      "close": 6300,  
      "value": 247640000,  
      "change": 0,  
      "volume": 39000,  
      "frequency": 62  
    },  
    {  
      "low": 2350,  
      "code": "ABMM",  
      "high": 2420,  
      "close": 2370,  
      "value": 17927000,  
      "change": 60,  
      "volume": 7600,  
      "frequency": 12  
    },  
    {  
      "low": 344,  
      "code": "ACES",  
      "high": 350,  
      "close": 346,  
      "value": 402922600,  
      "change": \-4,  
      "volume": 1165000,  
      "frequency": 101  
    },  
    {  
      "low": 158,  
      "code": "ADHI",  
      "high": 163,  
      "close": 161,  
      "value": 30115900,  
      "change": 3,  
      "volume": 187300,  
      "frequency": 37  
    }  
  \],  
  "date": "2026-07-14T00:00:00",  
  "start": 0,  
  "total": 220,  
  "length": 5,  
  "dataset": "margin-summary",  
  "provider": "idx"  
}  
\`\`\`

\---

\#\#\# Ownership Files

Indeks publikasi Data Kepemilikan Saham dari KSEI: tanggal, kategori, dan tautan berkas. Berisi tautan, bukan isi berkasnya.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/ownership-files\`  
\- \*\*Cache TTL:\*\* 3600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`category\` | enum(lima-persen|satu-persen|klasifikasi|tipe) | query | no | Saring satu kategori. Default: semua kategori |  
| \`length\` | number | query | no | Jumlah berkas (default 50, maks 200\) |  
| \`start\` | number | query | no | Offset baris (default 0\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/ownership-files?category=lima-persen\&length=30\&start=0" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/ownership-files?category=lima-persen\&length=30\&start=0", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/ownership-files?category=lima-persen\&length=30\&start=0",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "data": \[  
    {  
      "url": "https://www.idx.co.id/Media/cqiex5iv/peng-2026-07-30-00043-lima-persen.xlsx",  
      "category": "lima-persen",  
      "fileName": "peng-2026-07-30-00043-lima-persen.xlsx",  
      "publishedAt": "2026-07-30",  
      "categoryLabel": "Pemegang saham di atas 5%"  
    },  
    {  
      "url": "https://www.idx.co.id/Media/uznhesu0/peng-2026-07-29-00042-lima-persen.xlsx",  
      "category": "lima-persen",  
      "fileName": "peng-2026-07-29-00042-lima-persen.xlsx",  
      "publishedAt": "2026-07-29",  
      "categoryLabel": "Pemegang saham di atas 5%"  
    },  
    {  
      "url": "https://www.idx.co.id/Media/z1ymz1fw/peng-2026-07-28-00041-lima-persen.xlsx",  
      "category": "lima-persen",  
      "fileName": "peng-2026-07-28-00041-lima-persen.xlsx",  
      "publishedAt": "2026-07-28",  
      "categoryLabel": "Pemegang saham di atas 5%"  
    },  
    {  
      "url": "https://www.idx.co.id/Media/myaod41g/peng-2026-07-27-00040-lima-persen.xlsx",  
      "category": "lima-persen",  
      "fileName": "peng-2026-07-27-00040-lima-persen.xlsx",  
      "publishedAt": "2026-07-27",  
      "categoryLabel": "Pemegang saham di atas 5%"  
    },  
    {  
      "url": "https://www.idx.co.id/Media/oiyfshho/peng-2026-07-24-00039-lima-persen.xlsx",  
      "category": "lima-persen",  
      "fileName": "peng-2026-07-24-00039-lima-persen.xlsx",  
      "publishedAt": "2026-07-24",  
      "categoryLabel": "Pemegang saham di atas 5%"  
    }  
  \],  
  "start": 0,  
  "total": 61,  
  "length": 5,  
  "source": "KSEI",  
  "dataset": "ownership-files",  
  "provider": "idx"  
}  
\`\`\`

\---

\#\#\# Exchange Members

Daftar induk 90 Anggota Bursa. Isi \`code\` untuk profil lengkap satu broker: lisensi, status keanggotaan, pemegang saham beserta status kepemilikan asing/lokal, modal disetor, MKBD, dan jumlah kantor cabang. \`view=full\` menambahkan kategori dan persentase kepemilikan asing untuk seluruh 90 anggota sekaligus.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/brokers\`  
\- \*\*Cache TTL:\*\* 21600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | no | Two-letter exchange member code. Returns one broker's full profile. |  
| \`view\` | enum(list|full) | query | no | \`list\` (default) returns all 90 members in one upstream call. \`full\` adds ownership category and foreign ownership per member — one upstream call each, \~38s, cached. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/brokers?code=YU\&view=list" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/brokers?code=YU\&view=list", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/brokers?code=YU\&view=list",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "city": "Jakarta Selatan",  
  "code": "YU",  
  "logo": "https://www.idx.co.id/StaticData/Brokers/Logo/YU.jpg",  
  "mkbd": 944675696954.63,  
  "name": "CGS INTERNATIONAL SEKURITAS INDONESIA",  
  "email": "jk.compliance@cgsi.com",  
  "phone": "5151330",  
  "address": "Gedung Bursa Efek Indonesia Tower 2,   20,   Jl. Jend. Sudirman Kav. 52-53 ,   Kav 52-53",  
  "dataset": "brokers",  
  "license": "APERD, DMA, DMA AO, LP SW, Margin, Online, Online AO, Penjamin Emisi Efek, Perantara Pedagang Efek, RT AO, SOTS",  
  "website": "www.cgsi.co.id",  
  "category": "patungan",  
  "provider": "idx",  
  "branchCount": 27,  
  "memberStatus": "Aktif",  
  "shareholders": \[  
    {  
      "name": "CGS INTERNATIONAL SECURITIES PTE. LTD.",  
      "type": "Badan Hukum",  
      "country": "Singapura",  
      "sharePct": 85,  
      "ownership": "asing"  
    },  
    {  
      "name": "CGS International Konsultan Manajemen Indonesia, PT",  
      "type": "Badan Hukum",  
      "country": "Indonesia",  
      "sharePct": 9.96,  
      "ownership": "lokal"  
    },  
    {  
      "name": "CGS INTERNATIONAL SECURITIES SINGAPORE PTE. LTD.",  
      "type": "Badan Hukum",  
      "country": "Singapura",  
      "sharePct": 5.04,  
      "ownership": "asing"  
    }  
  \],  
  "paidUpCapital": 356000000000,  
  "foreignOwnershipPct": 90.04  
}  
\`\`\`

\---

\#\#\# Stock History

Riwayat harian satu saham dalam satu panggilan, sampai 2020: OHLC, volume, nilai, frekuensi, bid/offer, saham tercatat, plus arus beli/jual investor asing dalam lembar dan nilai rupiah turunannya. Terima rentang \`from\`/\`to\` atau \`length\` hari bursa.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/stock-history\`  
\- \*\*Cache TTL:\*\* 300s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | yes | Stock code. Required. |  
| \`from\` | string | query | no | Start date (YYYY-MM-DD or YYYYMMDD). When set, \`length\` is derived from the range. |  
| \`to\` | string | query | no | End date (YYYY-MM-DD or YYYYMMDD). Defaults to the latest trading day. |  
| \`length\` | number | query | no | Number of trading days when \`from\` is not set (default 30, max 2000\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/stock-history?code=BBCA\&from=2026-07-01\&to=2026-08-08\&length=30" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/stock-history?code=BBCA\&from=2026-07-01\&to=2026-08-08\&length=30", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/stock-history?code=BBCA\&from=2026-07-01\&to=2026-08-08\&length=30",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "to": "2026-08-07",  
  "code": "SSIA",  
  "from": "2026-07-01",  
  "name": "Surya Semesta Internusa Tbk.",  
  "unit": "shares",  
  "count": 28,  
  "items": \[  
    {  
      "bid": 1670,  
      "low": 1655,  
      "date": "2026-08-07",  
      "high": 1690,  
      "open": 1655,  
      "close": 1670,  
      "offer": 1675,  
      "value": 14356282500,  
      "change": 15,  
      "volume": 8596500,  
      "previous": 1655,  
      "frequency": 2165,  
      "listedShares": 4705249440,  
      "foreignBuyValue": 1265192000,  
      "netForeignValue": 781560000,  
      "foreignBuyShares": 757600,  
      "foreignSellValue": 483632000,  
      "netForeignShares": 468000,  
      "foreignSellShares": 289600  
    },  
    {  
      "bid": 1655,  
      "low": 1655,  
      "date": "2026-08-06",  
      "high": 1710,  
      "open": 1685,  
      "close": 1655,  
      "offer": 1660,  
      "value": 19197284000,  
      "change": \-15,  
      "volume": 11447000,  
      "previous": 1670,  
      "frequency": 3305,  
      "listedShares": 4705249440,  
      "foreignBuyValue": 1200702500,  
      "netForeignValue": \-3797066500,  
      "foreignBuyShares": 725500,  
      "foreignSellValue": 4997769000,  
      "netForeignShares": \-2294300,  
      "foreignSellShares": 3019800  
    },  
    {  
      "bid": 1670,  
      "low": 1660,  
      "date": "2026-08-05",  
      "high": 1685,  
      "open": 1675,  
      "close": 1670,  
      "offer": 1675,  
      "value": 21255486500,  
      "change": 15,  
      "volume": 12726200,  
      "previous": 1655,  
      "frequency": 3174,  
      "listedShares": 4705249440,  
      "foreignBuyValue": 2823469000,  
      "netForeignValue": 947057000,  
      "foreignBuyShares": 1690700,  
      "foreignSellValue": 1876412000,  
      "netForeignShares": 567100,  
      "foreignSellShares": 1123600  
    },  
    {  
      "bid": 1655,  
      "low": 1635,  
      "date": "2026-08-04",  
      "high": 1690,  
      "open": 1650,  
      "close": 1655,  
      "offer": 1660,  
      "value": 24366083500,  
      "change": 5,  
      "volume": 14631400,  
      "previous": 1650,  
      "frequency": 3001,  
      "listedShares": 4705249440,  
      "foreignBuyValue": 3981102500,  
      "netForeignValue": 2325606000,  
      "foreignBuyShares": 2405500,  
      "foreignSellValue": 1655496500,  
      "netForeignShares": 1405200,  
      "foreignSellShares": 1000300  
    },  
    {  
      "bid": 1650,  
      "low": 1650,  
      "date": "2026-08-03",  
      "high": 1695,  
      "open": 1665,  
      "close": 1650,  
      "offer": 1655,  
      "value": 21072123500,  
      "change": 0,  
      "volume": 12636800,  
      "previous": 1650,  
      "frequency": 3471,  
      "listedShares": 4705249440,  
      "foreignBuyValue": 995940000,  
      "netForeignValue": \-4350555000,  
      "foreignBuyShares": 603600,  
      "foreignSellValue": 5346495000,  
      "netForeignShares": \-2636700,  
      "foreignSellShares": 3240300  
    },  
    {  
      "bid": 1650,  
      "low": 1615,  
      "date": "2026-07-31",  
      "high": 1690,  
      "open": 1630,  
      "close": 1650,  
      "offer": 1655,  
      "value": 29946218500,  
      "change": 40,  
      "volume": 18079300,  
      "previous": 1610,  
      "frequency": 3994,  
      "listedShares": 4705249440,  
      "foreignBuyValue": 2134605000,  
      "netForeignValue": 637560000,  
      "foreignBuyShares": 1293700,  
      "foreignSellValue": 1497045000,  
      "netForeignShares": 386400,  
      "foreignSellShares": 907300  
    },  
    {  
      "bid": 1610,  
      "low": 1575,  
      "date": "2026-07-30",  
      "high": 1610,  
      "open": 1605,  
      "close": 1610,  
      "offer": 1615,  
      "value": 14342819000,  
      "change": 25,  
      "volume": 9012100,  
      "previous": 1585,  
      "frequency": 2335,  
      "listedShares": 4705249440,  
      "foreignBuyValue": 3586597000,  
      "netForeignValue": 2784173000,  
      "foreignBuyShares": 2227700,  
      "foreignSellValue": 802424000,  
      "netForeignShares": 1729300,  
      "foreignSellShares": 498400  
    },  
    {  
      "bid": 1580,  
      "low": 1555,  
      "date": "2026-07-29",  
      "high": 1655,  
      "open": 1605,  
      "close": 1585,  
      "offer": 1585,  
      "value": 21078841000,  
      "change": \-20,  
      "volume": 13196700,  
      "previous": 1605,  
      "frequency": 4871,  
      "listedShares": 4705249440,  
      "foreignBuyValue": 3144323000,  
      "netForeignValue": \-2024996000,  
      "foreignBuyShares": 1983800,  
      "foreignSellValue": 5169319000,  
      "netForeignShares": \-1277600,  
      "foreignSellShares": 3261400  
    }  
  \],  
  "dataset": "stock-history",  
  "provider": "idx",  
  "valueBasis": "close"  
}  
\`\`\`

\---

\#\#\# Company Profile

Profil lengkap satu emiten: sektor, papan pencatatan, kegiatan usaha, sekretaris perusahaan, direksi, komisaris, komite audit, pemegang saham, anak perusahaan, riwayat dividen, dan obligasi yang diterbitkan.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/company-profile\`  
\- \*\*Cache TTL:\*\* 21600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`code\` | string | query | yes | Stock code. Required. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/company-profile?code=BBCA" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/company-profile?code=BBCA", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/company-profile?code=BBCA",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "fax": "021-23588300",  
  "code": "BBCA",  
  "logo": "https://www.idx.co.id/Portals/0/StaticData/ListedCompanies/LogoEmiten/BBCA.jpg",  
  "name": "PT Bank Central Asia Tbk.",  
  "bonds": \[  
    {  
      "isin": "IDA0000918A5",  
      "name": "Obligasi Subordinasi Berkelanjutan I Bank Central Asia Tahap I Tahun 2018 Seri A",  
      "rating": "AA",  
      "nominal": 435000000000,  
      "trustee": "PT Bank Rakyat Indonesia (Persero) Tbk.",  
      "listingDate": "2018-07-06",  
      "maturityDate": "2025-07-05"  
    },  
    {  
      "isin": "IDA0000918B3",  
      "name": "Obligasi Subordinasi Berkelanjutan I Bank Central Asia Tahap I Tahun 2018 Seri B",  
      "rating": "AA",  
      "nominal": 65000000000,  
      "trustee": "PT Bank Rakyat Indonesia (Persero) Tbk.",  
      "listingDate": "2018-07-06",  
      "maturityDate": "2030-07-05"  
    }  
  \],  
  "email": "investor\_relations@bca.co.id",  
  "phone": "021-23588000",  
  "sector": "Keuangan",  
  "address": "Menara BCA, Grand Indonesia\\r\\nJalan MH Thamrin No. 1\\r\\nJakarta 10310",  
  "dataset": "company-profile",  
  "website": "www.bca.co.id",  
  "industry": "Bank",  
  "provider": "idx",  
  "directors": \[  
    {  
      "name": "Gregory Hendra Lembong",  
      "title": "PRESIDEN DIREKTUR"  
    },  
    {  
      "name": "Armand Wahyudi Hartono",  
      "title": "WAKIL PRESIDEN DIREKTUR"  
    },  
    {  
      "name": "John Kosasih",  
      "title": "WAKIL PRESIDEN DIREKTUR"  
    },  
    {  
      "name": "Tan Ho Hien/Subur atau dipanggil Subur Tan",  
      "title": "DIREKTUR"  
    },  
    {  
      "name": "Lianawaty Suwono",  
      "title": "DIREKTUR"  
    },  
    {  
      "name": "Santoso",  
      "title": "DIREKTUR"  
    },  
    {  
      "name": "Vera Eve Lim",  
      "title": "DIREKTUR"  
    },  
    {  
      "name": "Haryanto Tiara Budiman",  
      "title": "DIREKTUR"  
    }  
  \],  
  "dividends": \[  
    {  
      "type": "dti",  
      "exDate": "2026-06-17",  
      "cumDate": "2026-06-15",  
      "bookYear": "2026",  
      "cashTotal": 0,  
      "recordDate": "2026-06-18",  
      "bonusShares": 0,  
      "paymentDate": "2026-06-26",  
      "cashPerShare": 20  
    }  
  \],  
  "subSector": "Bank",  
  "listingDate": "2000-05-31",  
  "subIndustry": "Bank",  
  "listingBoard": "Utama",  
  "mainBusiness": "Jasa Perbankan",  
  "shareholders": \[  
    {  
      "name": "PT Dwimuria Investama Andalan",  
      "shares": 67729950000,  
      "category": "Lebih dari 5%",  
      "sharePct": 54.942  
    },  
    {  
      "name": "Saham Treasury",  
      "shares": 433298700,  
      "category": "Saham Treasury",  
      "sharePct": 0.351  
    },  
    {  
      "name": "Masyarakat Warkat",  
      "shares": 3091408880,  
      "category": "Masyarakat Warkat",  
      "sharePct": 2.508  
    },  
    {  
      "name": "Masyarakat Non Warkat",  
      "shares": 51940016778,  
      "category": "Masyarakat Non Warkat",  
      "sharePct": 42.134  
    },  
    {  
      "name": "Antonius Widodo Mulyono",  
      "shares": 681407,  
      "category": "Direksi",  
      "sharePct": 0.001  
    },  
    {  
      "name": "Jahja Setiaatmadja",  
      "shares": 35802700,  
      "category": "Komisaris",  
      "sharePct": 0.03  
    },  
    {  
      "name": "Armand Wahyudi Hartono",  
      "shares": 4256065,  
      "category": "Direksi",  
      "sharePct": 0.003  
    },  
    {  
      "name": "Tan Ho Hien/Subur disebut juga Subur Tan",  
      "shares": 11788002,  
      "category": "Direksi",  
      "sharePct": 0.01  
    }  
  \],  
  "subsidiaries": \[  
    {  
      "name": "PT Asuransi Jiwa BCA",  
      "unit": "JUTAAN",  
      "business": "Asuransi Jiwa",  
      "currency": "IDR",  
      "location": "Jakarta",  
      "totalAssets": 4676146,  
      "ownershipPct": 90,  
      "commercialYear": "2014",  
      "operatingStatus": "Beroperasi"  
    },  
    {  
      "name": "PT Asuransi Umum BCA",  
      "unit": "JUTAAN",  
      "business": "Asuransi umum atau\\r\\nkerugian",  
      "currency": "IDR",  
      "location": "Jakarta",  
      "totalAssets": 3454384,  
      "ownershipPct": 100,  
      "commercialYear": "1989",  
      "operatingStatus": "Beroperasi"  
    },  
    {  
      "name": "PT Bank BCA Syariah",  
      "unit": "JUTAAN",  
      "business": "perbankan syariah",  
      "currency": "IDR",  
      "location": "Jakarta",  
      "totalAssets": 19207364,  
      "ownershipPct": 100,  
      "commercialYear": "1992",  
      "operatingStatus": "Beroperasi"  
    },  
    {  
      "name": "PT Bank Digital BCA",  
      "unit": "JUTAAN",  
      "business": "Perbankan",  
      "currency": "IDR",  
      "location": "Jakarta",  
      "totalAssets": 18923844,  
      "ownershipPct": 100,  
      "commercialYear": "1965",  
      "operatingStatus": "Beroperasi"  
    },  
    {  
      "name": "PT BCA Finance",  
      "unit": "JUTAAN",  
      "business": "Pembiayaan investasi, modal\\r\\nkerja, pembiayaan\\r\\nmultiguna, sewa\\r\\noperasi, keg\\r\\npembiayaan lain\\r\\nbrdsrkn\\r\\npersetujuan instansi\\r\\nyg berwenang",  
      "currency": "IDR",  
      "location": "Jakarta",  
      "totalAssets": 10371197,  
      "ownershipPct": 100,  
      "commercialYear": "1981",  
      "operatingStatus": "Beroperasi"  
    },  
    {  
      "name": "PT BCA Sekuritas",  
      "unit": "JUTAAN",  
      "business": "Perantara perdagangan efek dan penjamin emisi efek",  
      "currency": "IDR",  
      "location": "Jakarta",  
      "totalAssets": 2518673,  
      "ownershipPct": 90,  
      "commercialYear": "1992",  
      "operatingStatus": "Beroperasi"  
    },  
    {  
      "name": "PT Central Capital Ventura",  
      "unit": "JUTAAN",  
      "business": "Modal ventura",  
      "currency": "IDR",  
      "location": "Jakarta",  
      "totalAssets": 468985,  
      "ownershipPct": 100,  
      "commercialYear": "2017",  
      "operatingStatus": "Beroperasi"  
    }  
  \],  
  "commissioners": \[  
    {  
      "name": "Sumantri Slamet",  
      "title": "KOMISARIS"  
    },  
    {  
      "name": "Jahja Setiaatmadja",  
      "title": "PRESIDEN KOMISARIS"  
    },  
    {  
      "name": "Tonny Kusnadi",  
      "title": "KOMISARIS"  
    },  
    {  
      "name": "Raden Pardede",  
      "title": "KOMISARIS"  
    }  
  \],  
  "auditCommittee": \[  
    {  
      "name": "Sumantri Slamet",  
      "title": "KETUA"  
    },  
    {  
      "name": "Rallyati A. Wibowo",  
      "title": "ANGGOTA"  
    },  
    {  
      "name": "Prabowo",  
      "title": "ANGGOTA"  
    }  
  \],  
  "corporateSecretary": \[  
    {  
      "name": "Rudy Budiardjo",  
      "email": "corporate\_secretary@bca.co.id",  
      "phone": "021-23588000"  
    }  
  \]  
}  
\`\`\`

\---

\#\#\# Corporate Calendar

Kalender emiten: RUPS, jadwal dividen, dan jatuh tempo obligasi. \`range=m\` untuk sebulan penuh di sekitar tanggal, \`range=d\` untuk satu hari.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/calendar\`  
\- \*\*Cache TTL:\*\* 3600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`date\` | string | query | no | Anchor date (YYYY-MM-DD or YYYYMMDD). Defaults to today. |  
| \`range\` | enum(m|d) | query | no | \`m\` for the whole month around the date (default), \`d\` for that single day. |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/calendar?date=2026-08-08\&range=m" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/calendar?date=2026-08-08\&range=m", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/calendar?date=2026-08-08\&range=m",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "date": "2026-08-08",  
  "count": 155,  
  "items": \[  
    {  
      "id": 216022,  
      "code": "PPLN",  
      "date": "2026-08-01",  
      "type": "obligasiJatuhTempo",  
      "description": "Jatuh Tempo Obligasi / Sukuk Korporasi emisi Sukuk Ijarah Berkelanjutan III PLN Tahap IV Tahun 2019 seri Sukuk Ijarah Berkelanjutan III PLN Tahap IV Tahun 2019 Seri B"  
    },  
    {  
      "id": 216023,  
      "code": "PPLN",  
      "date": "2026-08-01",  
      "type": "obligasiJatuhTempo",  
      "description": "Jatuh Tempo Obligasi / Sukuk Korporasi emisi Obligasi Berkelanjutan III PLN Tahap IV Tahun 2019 seri Obligasi Berkelanjutan III PLN Tahap IV Tahun 2019 Seri B"  
    },  
    {  
      "id": 215852,  
      "code": "AKRA",  
      "date": "2026-08-03",  
      "description": "tanggal ex Dividen Tunai Interim PT AKR Corporindo Tbk."  
    },  
    {  
      "id": 214565,  
      "code": "NASI",  
      "date": "2026-08-03",  
      "step": "rencana",  
      "type": "Rencana",  
      "location": "Akan ditentukan kemudian",  
      "description": "Pemberitahuan RUPS Rencana  PT Wahana Inti Makmur Tbk"  
    },  
    {  
      "id": 216052,  
      "code": "INTP",  
      "date": "2026-08-03",  
      "description": "Laporan Pembelian Kembali Saham (Buyback)"  
    },  
    {  
      "id": 216053,  
      "code": "AYAM",  
      "date": "2026-08-03",  
      "type": "Tahunan",  
      "location": "Cyber 2 Tower Lantai 17, Jl. H.R. Rasuna Said, Blok X-5, Jakarta Selatan, Daerah Khusus Ibukota Jakarta 12950 serta melalui aplikasi Zoom.",  
      "description": "Hasil RUPS Tahunan 31-12-2025 PT Janu Putra Sejahtera Tbk."  
    },  
    {  
      "id": 216055,  
      "code": "TAMU",  
      "date": "2026-08-03",  
      "type": "Tahunan",  
      "location": "Jl. Balikpapan no.5D, Gambir, Jakarta Pusat",  
      "description": "Hasil RUPS Tahunan 31-12-2025 PT Pelayaran Tamarin Samudra Tbk."  
    },  
    {  
      "id": 216046,  
      "code": "ERAA",  
      "date": "2026-08-03",  
      "description": "Laporan Pembelian Kembali Saham (Buyback)"  
    }  
  \],  
  "range": "m",  
  "dataset": "calendar",  
  "provider": "idx"  
}  
\`\`\`

\---

\#\#\# IPO & Relisting

Perusahaan yang baru tercatat dan relisting, terbaru dulu. Filter \`year\` untuk satu tahun pencatatan.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:idx/ipo\`  
\- \*\*Cache TTL:\*\* 21600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`year\` | number | query | no | Filter by listing year. |  
| \`length\` | number | query | no | Rows to return (default 20, max 200\) |  
| \`start\` | number | query | no | Row offset (default 0\) |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:idx/ipo?year=2026\&length=20\&start=0" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:idx/ipo?year=2026\&length=20\&start=0", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:idx/ipo?year=2026\&length=20\&start=0",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "items": \[  
    {  
      "code": "RANS",  
      "name": "PT Rans Entertainmen Indonesia Tbk",  
      "listingDate": "2026-07-10",  
      "listingType": "baru",  
      "listingBoard": "Pengembangan",  
      "securityType": "saham",  
      "sharesOffered": 12609250000  
    },  
    {  
      "code": "PRDL",  
      "name": "PT Prodia Diagnostic Line Tbk",  
      "listingDate": "2026-07-09",  
      "listingType": "baru",  
      "listingBoard": "Pengembangan",  
      "securityType": "saham",  
      "sharesOffered": 1742900000  
    },  
    {  
      "code": "BACH",  
      "name": "PT Bach Multi Global Tbk",  
      "listingDate": "2026-07-08",  
      "listingType": "baru",  
      "listingBoard": "Utama",  
      "securityType": "saham",  
      "sharesOffered": 4084430000  
    },  
    {  
      "code": "EMMI",  
      "name": "PT Esa Medika Mandiri Tbk",  
      "listingDate": "2026-07-08",  
      "listingType": "baru",  
      "listingBoard": "Pengembangan",  
      "securityType": "saham",  
      "sharesOffered": 1742857000  
    },  
    {  
      "code": "JECX",  
      "name": "PT Nitrasanata Dharma Tbk",  
      "listingDate": "2026-07-07",  
      "listingType": "baru",  
      "listingBoard": "Utama",  
      "securityType": "saham",  
      "sharesOffered": 3253222300  
    },  
    {  
      "code": "JELI",  
      "name": "PT Niramas Utama Tbk",  
      "listingDate": "2026-07-07",  
      "listingType": "baru",  
      "listingBoard": "Pengembangan",  
      "securityType": "saham",  
      "sharesOffered": 1266000000  
    },  
    {  
      "code": "WBSA",  
      "name": "PT BSA Logistics Indonesia Tbk",  
      "listingDate": "2026-04-10",  
      "listingType": "baru",  
      "listingBoard": "Pengembangan",  
      "securityType": "saham",  
      "sharesOffered": 8675000000  
    }  
  \],  
  "start": 0,  
  "total": 7,  
  "length": 8,  
  "dataset": "ipo",  
  "provider": "idx"  
}  
\`\`\`

\---

\_Generated: 2026-08-09T03:00:39.433Z\_  
