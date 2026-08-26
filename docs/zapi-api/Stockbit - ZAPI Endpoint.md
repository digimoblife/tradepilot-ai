\# Stockbit — Zapi reference

\> Data saham IDX dari Stockbit: harga, chart intraday, profil emiten, diskusi komunitas, dan kamus investasi.

\*\*Base URL:\*\* \`https://api.zpi.web.id\`  
\*\*Auth:\*\* Send \`x-api-key: YOUR\_KEY\` header on every request. Get a free key at https://zpi.web.id/dashboard/keys.  
\*\*Response envelope:\*\* \`{ status, message, content }\`  
\*\*Rate limit:\*\* 60 req/min on free tier.

\*\*Related:\*\*  
\- Detail page: https://zpi.web.id/api/finance/stockbit  
\- Endpoint catalog: https://zpi.web.id/category/finance  
\- Concise index: https://zpi.web.id/llms.txt  
\- Full reference: https://zpi.web.id/llms-full.txt

\---

\#\# Stockbit

\*\*Category:\*\* finance · \*\*Slug:\*\* \`stockbit\`  
\*\*Detail page:\*\* https://zpi.web.id/api/finance/stockbit

Data saham IDX dari Stockbit: harga, chart intraday, profil emiten, diskusi komunitas, dan kamus investasi.

\*\*Tags:\*\* stockbit, saham, idx, indonesia, bursa, investasi

\#\#\# Symbol

Harga terkini satu saham IDX: last, previous close, perubahan, volume, dan bid/offer terbaik.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:stockbit/symbol\`  
\- \*\*Cache TTL:\*\* 60s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`symbol\` | string | query | yes | IDX ticker, e.g. BBCA |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:stockbit/symbol?symbol=BBCA" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:stockbit/symbol?symbol=BBCA", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:stockbit/symbol?symbol=BBCA",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "last": 6325,  
  "name": "Bank Central Asia Tbk.",  
  "type": "Saham",  
  "change": \-125,  
  "sector": "Keuangan",  
  "symbol": "BBCA",  
  "volume": 153174800,  
  "bestBid": {  
    "price": 6350,  
    "volume": 2925000  
  },  
  "country": "ID",  
  "iconUrl": "https://assets.stockbit.com/logos/companies/BBCA.png",  
  "indexes": \[  
    "TRADINGLIMIT",  
    "IDXVESTA28",  
    "ECONOMIC30",  
    "DAYTRADE",  
    "PRIMBANK10",  
    "IDXLQ45LCL"  
  \],  
  "exchange": "IDX",  
  "provider": "stockbit",  
  "bestOffer": {  
    "price": 6375,  
    "volume": 548800  
  },  
  "followers": 3303290,  
  "subSector": "Bank",  
  "tradeable": true,  
  "updatedAt": "2026-07-31T08:00:03+07:00",  
  "tradingDate": "31 Jul 2026",  
  "tradingTime": "Fri 16:14",  
  "averageValue": 284796460,  
  "marketStatus": "close",  
  "changePercent": \-1.94,  
  "previousClose": 6450,  
  "unusualMarketActivity": false  
}  
\`\`\`

\---

\#\#\# Chart

Deret harga intraday satu saham, satu titik per menit perdagangan.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:stockbit/chart\`  
\- \*\*Cache TTL:\*\* 60s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`symbol\` | string | query | yes | IDX ticker, e.g. BBCA |  
| \`count\` | number | query | no | Keep only the last N points. Default: the whole session |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:stockbit/chart?symbol=BBCA\&count=100" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:stockbit/chart?symbol=BBCA\&count=100", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:stockbit/chart?symbol=BBCA\&count=100",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "count": 5,  
  "items": \[  
    {  
      "time": "2026-07-31 16:09:00",  
      "price": 6325,  
      "change": \-125,  
      "changePercent": \-1.94  
    },  
    {  
      "time": "2026-07-31 16:10:00",  
      "price": 6325,  
      "change": \-125,  
      "changePercent": \-1.94  
    },  
    {  
      "time": "2026-07-31 16:11:00",  
      "price": 6325,  
      "change": \-125,  
      "changePercent": \-1.94  
    },  
    {  
      "time": "2026-07-31 16:12:00",  
      "price": 6325,  
      "change": \-125,  
      "changePercent": \-1.94  
    },  
    {  
      "time": "2026-07-31 16:14:00",  
      "price": 6325,  
      "change": \-125,  
      "changePercent": \-1.94  
    }  
  \],  
  "change": \-125,  
  "symbol": "BBCA",  
  "interval": "intraday",  
  "provider": "stockbit",  
  "timeframe": "today",  
  "tradingDate": "31 Jul 2026",  
  "changePercent": \-1.94,  
  "previousClose": 6450  
}  
\`\`\`

\---

\#\#\# Stream

Postingan komunitas terbaru tentang satu saham.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:stockbit/stream\`  
\- \*\*Cache TTL:\*\* 120s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`symbol\` | string | query | yes | IDX ticker, e.g. BBCA |  
| \`count\` | number | query | no | Cap the list. Default: every post the page carries |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:stockbit/stream?symbol=BBCA\&count=10" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:stockbit/stream?symbol=BBCA\&count=10", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:stockbit/stream?symbol=BBCA\&count=10",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "count": 5,  
  "items": \[  
    {  
      "id": 34411610,  
      "isPro": false,  
      "likes": 0,  
      "images": \[  
        "https://stream-asset.stockbit.com/283bb801-4e10-4e88-aba7-d8b862a61c45\_stream.jpg"  
      \],  
      "content": "$IHSG $BTC $BBCA",  
      "replies": 0,  
      "dislikes": 0,  
      "fullName": "Ryusuf Ivan",  
      "isPinned": false,  
      "username": "RahardianYusufIvandyaz",  
      "createdAt": "2026-08-02 17:45:44",  
      "isOfficial": false  
    },  
    {  
      "id": 34411604,  
      "isPro": false,  
      "likes": 0,  
      "images": \[  
        "https://stream-asset.stockbit.com/9364d3c0-b966-4b65-830b-64d6390969a9\_stream.jpg"  
      \],  
      "content": "@NurseTyaaa Artinya Indonesia cerah 🚀😂. \\n\\n\\nRT $IHSG $BBCA $BBRI",  
      "replies": 0,  
      "dislikes": 0,  
      "fullName": "Ovick",  
      "isPinned": false,  
      "username": "Taufik230295",  
      "createdAt": "2026-08-02 17:45:05",  
      "isOfficial": false  
    },  
    {  
      "id": 34411461,  
      "isPro": false,  
      "likes": 0,  
      "images": \[  
        "https://stream-asset.stockbit.com/6c824ce3-a4d8-4de9-b0ed-dbfe3c695c76\_stream.jpg"  
      \],  
      "content": "Dengan FL portofolio sudah stabil di bawah 10%, strategi di bulan Agustus ini kemungkinan timbun cash dulu di deposito bank digital $BBSI , antisipasi koreksi harga $BBRI dan $BBCA atau untuk menghadapi volatilitas harga menjelang bulan November nanti",  
      "replies": 0,  
      "dislikes": 0,  
      "fullName": "Yaih",  
      "isPinned": false,  
      "username": "herwindyowarihkusumo",  
      "createdAt": "2026-08-02 17:28:02",  
      "isOfficial": false  
    },  
    {  
      "id": 34411341,  
      "isPro": false,  
      "likes": 0,  
      "images": \[  
        "https://stream-asset.stockbit.com/0b190f1b-c369-435a-96f2-c98607643e87\_stream.jpg",  
        "https://stream-asset.stockbit.com/2d818ffe-0fd2-4842-a673-66b07f7f919c\_stream.jpg",  
        "https://stream-asset.stockbit.com/e7a1aa89-dbec-4887-a58e-97997e374146\_stream.jpg"  
      \],  
      "content": "platform sebelah bagus juga ya ngasih summary ini , sama flow dll\\n.\\nsemoga stockbit bisa nyusul 🤣\\n.\\ncapek Gonta ganti apps buat validasi move investasi\\n.\\n$BMRI $BBCA $BBRI",  
      "replies": 0,  
      "dislikes": 0,  
      "fullName": "Rama Abdurachman",  
      "isPinned": false,  
      "username": "ramaabd",  
      "createdAt": "2026-08-02 17:16:19",  
      "isOfficial": false  
    },  
    {  
      "id": 34411322,  
      "isPro": false,  
      "likes": 0,  
      "content": "Gemes lihat orang2 nulisnya laporan Q2, padahal laporan bulan Juni itu disebutnya semester 1, atau TW2, bukan Q2. Gimana sih ya... kan beda triwulanan ama kuartalan. $BBRI $BMRI $BBCA",  
      "replies": 0,  
      "dislikes": 0,  
      "fullName": "bunbun",  
      "isPinned": false,  
      "username": "bundagendis",  
      "createdAt": "2026-08-02 17:10:35",  
      "isOfficial": false  
    }  
  \],  
  "symbol": "BBCA",  
  "provider": "stockbit"  
}  
\`\`\`

\---

\#\#\# Profile

Profil emiten: deskripsi usaha, sektor, sub-sektor, dan indeks yang diikuti.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:stockbit/profile\`  
\- \*\*Cache TTL:\*\* 3600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`symbol\` | string | query | yes | IDX ticker, e.g. BBCA |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:stockbit/profile?symbol=BBCA" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:stockbit/profile?symbol=BBCA", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:stockbit/profile?symbol=BBCA",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "name": "Bank Central Asia Tbk.",  
  "type": "Saham",  
  "sector": "Keuangan",  
  "symbol": "BBCA",  
  "country": "ID",  
  "iconUrl": "https://assets.stockbit.com/logos/companies/BBCA.png",  
  "indexes": \[  
    "TRADINGLIMIT",  
    "IDXVESTA28",  
    "ECONOMIC30",  
    "DAYTRADE",  
    "PRIMBANK10",  
    "IDXLQ45LCL"  
  \],  
  "exchange": "IDX",  
  "provider": "stockbit",  
  "followers": 3303290,  
  "subSector": "Bank",  
  "tradeable": true,  
  "background": "PT Bank Central Asia Tbk. atau BBCA dalam bidang usaha bank umum. Anak perusahaan diantaranya: PT BCA Finance (Pembiayaan Konsumen, Sewa Guna Usaha dan Anjak Piutang), BCA Finance Limited (Money Lending- Jasa Pengiriman Uang), PT Bank BCA Syariah (Perbankan Syariah), PT BCA Sekuritas (Penjamin Emisi Efek dan Pialang Perdagangan Saham), dan PT Asuransi Umum BCA (Asuransi Umum atau Asuransi Kerugian).Pada 2017 BCA mendirikan PT Central Capital Ventura (CCV) guna mengikuti inovasi layanan keuangan berbasis digital. Produk dan layanan Perseroan yaitu: produk simpanan, layanan transaksi perbankan, perbankan elektronik, layanan cash management, kartu kredit, bancassurance, produk investasi, fasilitas kredit, Bank garansi, fasilitas ekspor impor dan fasilitas valuta asing. Pada 2017 Jumlah kantor wilayah ada 12 terdiri dari (146 kantor cabang utama, 856 kantor cabang pembantu dan 244 kantor kas) tersebar di seluruh Indonesia, kantor non wilayah (1 kantor cabang utama) dan satu kantor perwakilan di Jakarta pusat.",  
  "listingStatus": "STATUS\_ACTIVE"  
}  
\`\`\`

\---

\#\#\# Glossary

Kamus istilah investasi: definisi, rumus, dan penjelasan. Bisa disaring per huruf atau kata kunci.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:stockbit/glossary\`  
\- \*\*Cache TTL:\*\* 86400s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`letter\` | enum(a|b|c|d|e|f|g|h|i|j|k|l|m|n|o|p|q|r|s|t|u|v|w|x|y|z) | query | no | Fetch one initial letter only. Default: every letter |  
| \`q\` | string | query | no | Keep only terms whose name or definition contains this |  
| \`count\` | number | query | no | Cap the list. Default: everything found |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:stockbit/glossary?letter=a\&q=rasio\&count=20" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:stockbit/glossary?letter=a\&q=rasio\&count=20", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:stockbit/glossary?letter=a\&q=rasio\&count=20",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "count": 16,  
  "items": \[  
    {  
      "id": 360,  
      "slug": "absolute-valuation-",  
      "term": "Absolute Valuation",  
      "letter": "a",  
      "definition": "Absolute valuation merupakan salah satu metode valuasi yang digunakan oleh investor untuk menaksir nilai intrinsik saham dengan menghitung akumulasi nilai aset ataupun potensi arus kas perusahaan. \\n\\nSebagai contoh jika kita ingin membeli ruko, kita bisa menaksir nilai intrinsik ruko dengan menghitung harga seluruh komponen ruko tersebut, mulai dari harga tanah, perabotan, serta komponen lainnya. \\n\\nSelain dengan menghitung total aset, kita juga bisa memperkirakan nilai intrinsik ruko tersebut dengan memproyeksikan kemampuannya dalam menghasilkan cash flow ke depannya. Cash flow bisa didapatkan dengan menyewakan ruko, menggunakannya sebagai tempat usaha atau modal kerja, dan lain-lain. \\n\\nDalam saham, metode yang paling sering digunakan dalam menghitung absolute valuation adalah discounted cash flow (DCF)."  
    },  
    {  
      "id": 176,  
      "slug": "accrued-expenses",  
      "term": "Accrued Expense",  
      "letter": "a",  
      "definition": "Accrued expenses adalah biaya yang telah dikeluarkan perusahaan, tetapi belum dibayar tunai. Biaya ini umumnya termasuk dalam kewajiban lancar dalam neraca perusahaan."  
    },  
    {  
      "id": 253,  
      "slug": "agio-saham",  
      "term": "Agio Saham",  
      "letter": "a",  
      "definition": "Selisih antara nilai nominal (par) saham dan harga yang dibayar investor untuk itu, biasanya akibat IPO atau rights issue."  
    },  
    {  
      "id": 321,  
      "slug": "akuisisi",  
      "term": "Akuisisi",  
      "letter": "a",  
      "definition": "Akuisisi adalah pengambilalihan kepemilikan perusahaan atau aset. Berbeda dengan pembelian saham biasa, akuisisi umumnya merujuk kepada aksi pembelian saham mayoritas atau lebih dari 50%. Ketika suatu entitas membeli lebih dari 50% saham suatu perusahaan, ia akan memiliki kontrol di perusahaan tersebut."  
    },  
    {  
      "id": 63,  
      "slug": "altman-z-score-modified",  
      "term": "Altman Z-Score (modified)",  
      "letter": "a",  
      "formula": "Altman Z-Score (Modified) dihitung menggunakan formula:\\n\\nZ-Score \= 6.56A \+ 3.26B \+ 6.72C \+ 1.05D\\n\\nDimana:\\n\\nA \= Working Capital / Total Assets\\n\\nB \= Retained Earnings / Total Assets\\n\\nC \= EBIT / Total Assets\\n\\nD \= (Total Ekuitas \- kepentingan non pengendali) / Total liabilities",  
      "definition": "Altman Z-Score adalah model probabilistik yang digunakan untuk menentukan resiko kebangkrutan. Altman Z-Score (Modified) didesain agar dapat diterapkan pada perusahaan di emerging market (negara berkembang).\\n\\nAdapun kategori hasil Z-Score adalah sebagai berikut:\\n\\n Z-Score \< 1.1 mengindikasikan kemungkinan perusahaan sedang menuju kebangkrutan.\\n Z-Score antara 1.1 dan 2.6 mengindikasikan perusahaan masuk kedalam zona \\"hati-hati.\\"\\n\\nZ-Score diatas 2.6 mengindikasikan perusahaan berada dalam zona aman.",  
      "explanation": "Z-Score Result:\\n\\nZ-Score \< 1.1 mengindikasikan kemungkinan perusahaan sedang menuju kebangkrutan.\\nZ-Score antara 1.1 dan 2.6 mengindikasikan perusahaan masuk kedalam zona \\"hati-hati.\\"\\nZ-Score diatas 2.6 mengindikasikan perusahaan berada dalam zona aman."  
    },  
    {  
      "id": 66,  
      "slug": "altman-z-score-original",  
      "term": "Altman Z-Score (Original)",  
      "letter": "a",  
      "formula": "Altman Z-Score (Original) dihitung menggunakan formula:\\n\\nZ-Score \= 1.2A \+ 1.4B \+ 3.3C \+ 0.6D \+ 1E\\n\\nDimana:\\n\\nA \= Working Capital / Total Assets\\n\\nB \= Retained Earnings / Total Assets\\n\\nC \= EBIT / Total Assets\\n\\nD \= Market value of equity / Total Liabilities\\n\\nE \= Sales / Total Assets",  
      "definition": "Altman Z-Score menggabungkan beberapa rasio penting dalam metrik tunggal yang menyediakan informasi berharga tentang kesehatan keuangan perusahaan. Secara khusus, Altman Z-Score adalah model probabilistik yang digunakan untuk menentukan resiko kebangkrutan perusahaan.\\n\\nAltman Z-Score (Original) ini didesain agar dapat digunakan pada perusahaan manufaktur.",  
      "explanation": "Z-Score Result:\\n\\nZ-Score \<1.81 mengindikasikan kemungkinan perusahaan sedang menuju kebangkrutan\\nZ-Score antara 1.81 dan 2.99 mengindikasikan perusahaan masuk kedalam zona \\"hati-hati\\"\\nZ-Score diatas 3.00 mengindikasikan perusahaan berada dalam zona aman"  
    }  
  \],  
  "letter": "a",  
  "provider": "stockbit",  
  "lettersFetched": 1  
}  
\`\`\`

\---

\#\#\# User

Profil publik anggota: nama, avatar, jumlah follower, following, dan ide.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:stockbit/user\`  
\- \*\*Cache TTL:\*\* 900s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`username\` | string | query | yes | Member handle, without the @ |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:stockbit/user?username=ramaabd" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:stockbit/user?username=ramaabd", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:stockbit/user?username=ramaabd",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "ideas": 105,  
  "fullName": "Rama Abdurachman",  
  "joinedAt": "2023-02-20T13:16:45Z",  
  "provider": "stockbit",  
  "username": "ramaabd",  
  "avatarUrl": "https://avatar.stockbit.com/1875309/2699292a-c1a3-4d7a-b366-85194701f22c-stockbit\_image1768074830129.jpeg",  
  "followers": 12,  
  "following": 13,  
  "isVerified": false,  
  "avatarThumbnailUrl": "https://avatar.stockbit.com/thumb/1875309/2699292a-c1a3-4d7a-b366-85194701f22c-stockbit\_image1768074830129.jpeg"  
}  
\`\`\`

\---

\#\#\# Post

Satu postingan berdasarkan id permalink-nya.

\- \*\*Method:\*\* \`GET\`  
\- \*\*Endpoint:\*\* \`https://api.zpi.web.id/v1/finance:stockbit/post\`  
\- \*\*Cache TTL:\*\* 600s

\*\*Parameters:\*\*

| Name | Type | Location | Required | Description |  
|------|------|----------|----------|-------------|  
| \`id\` | string | query | yes | Numeric post id |

\*\*cURL:\*\*  
\`\`\`bash  
curl "https://api.zpi.web.id/v1/finance:stockbit/post?id=34411341" \\  
  \-H "x-api-key: YOUR\_API\_KEY"  
\`\`\`

\*\*JavaScript / TypeScript:\*\*  
\`\`\`javascript  
const res \= await fetch("https://api.zpi.web.id/v1/finance:stockbit/post?id=34411341", {  
  headers: { "x-api-key": process.env.ZAPI\_KEY }  
});  
const data \= await res.json();  
\`\`\`

\*\*Python:\*\*  
\`\`\`python  
import requests  
r \= requests.get("https://api.zpi.web.id/v1/finance:stockbit/post?id=34411341",  
  headers={"x-api-key": "YOUR\_API\_KEY"})  
data \= r.json()  
\`\`\`

\*\*Example response:\*\*  
\`\`\`json  
{  
  "id": 34411341,  
  "url": "https://stockbit.com/post/34411341",  
  "isPro": false,  
  "likes": 0,  
  "images": \[  
    "https://stream-asset.stockbit.com/0b190f1b-c369-435a-96f2-c98607643e87\_stream.jpg",  
    "https://stream-asset.stockbit.com/2d818ffe-0fd2-4842-a673-66b07f7f919c\_stream.jpg",  
    "https://stream-asset.stockbit.com/e7a1aa89-dbec-4887-a58e-97997e374146\_stream.jpg"  
  \],  
  "content": "platform sebelah bagus juga ya ngasih summary ini , sama flow dll\\n.\\nsemoga stockbit bisa nyusul 🤣\\n.\\ncapek Gonta ganti apps buat validasi move investasi\\n.\\n$BMRI $BBCA $BBRI",  
  "country": "ID",  
  "replies": 0,  
  "reposts": 0,  
  "dislikes": 0,  
  "fullName": "Rama Abdurachman",  
  "provider": "stockbit",  
  "username": "ramaabd",  
  "createdAt": "2026-08-02 17:16:19",  
  "isOfficial": false  
}  
\`\`\`

\---

\_Generated: 2026-08-09T03:00:35.751Z\_  
