# SEC 13F Institutional Fund Flow Tracker

An elegant and data-dense web dashboard for parsing, tracking, and analyzing institutional hedge fund filings (SEC Form 13F).

<!-- TODO: 請手動啟動本專案網頁，並截圖儲存為 screenshot.png 放至此目錄下 -->

## 📌 Executive Summary
"Follow the smart money." This application automates the tedious process of parsing quarterly SEC Edgar database filings. It tracks top hedge fund allocations, computes sector rotations, and identifies highly correlated institutional buying/selling behaviors across the S&P 500.

### Core Analytics
* **Fund Allocation Pie**: Visualizes sector exposure changes quarter-over-quarter.
* **Heatmap of Smart Money**: Displays concentrated buying/selling clusters among top-tier funds.
* **Automated Parsing**: Direct Edgar API integration eliminates manual XML processing.

## 🛠️ Technical Implementation
* **Pipeline**: SEC Edgar API querying, XML/JSON parsing, text extraction.
* **Frontend**: Highly responsive grid layout with hover analytics and data tables.
