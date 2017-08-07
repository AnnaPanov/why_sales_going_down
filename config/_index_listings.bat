cd "C:\Program Files\CompBoard\sandbox\"
set TIMESTAMP=%DATE:~-4%%DATE:~-7,-5%%DATE:~-10,-8%_%time:~-11,2%%time:~-8,2%%time:~-5,2%
set LOGFILE=availability_scraper_%TIMESTAMP%.log
echo started at %TIMESTAMP% > %LOGFILE%

python ..\app\availability_scraper.py --product_config ..\config\out_of_stock.xlsx > %LOGFILE% 2>&1
