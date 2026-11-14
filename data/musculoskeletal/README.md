# data/musculoskeletal/ 資料說明

## 真實文獻參考值（新增，不會影響現有程式）

| 檔案 | 內容 |
|---|---|
| `iss_published_reference.csv` | 87 筆已發表的統計值（平均、標準差、範圍），每筆附來源與網址。長表格式，可直接用 pandas 讀取並畫對照圖 |
| `literature_reference.json` | 同一批數值的結構化版本，另含 NASA 標準、可下載數據集說明 |

這兩個檔案只含已發表的群體統計值，不含任何個別太空人的原始數據。

欄位 `source_type`：`NASA`＝NASA 官方網站或文件；`ISS_study`＝已發表的太空站研究；`other_literature`＝其他文獻。
欄位 `verified`：`fetched`＝已讀原文；`excerpt`＝讀到原文摘錄，引用前請點開網址核對；`user_pasted`＝由組員貼上原文。

## 模擬數據（原有檔案，未更動）

| 檔案 | 內容 |
|---|---|
| `preflight_baseline.json` | 虛構組員的發射前基準值 |
| `e4d_sets.csv` | 模擬的 E4D 訓練紀錄 |
| `measurements_long.csv` | 模擬的長期追蹤數值 |

以上三個檔案是模擬數據，並非真實太空人測量值。

## 真實數據集（不在本資料夾）

`data/shared_real/OSD-575_cmp.csv`：NASA OSDR 的 Inspiration4 血清代謝檢查，由 Role 1 下載放入。
該任務只有 3 天，只能當血液基本值參考。
