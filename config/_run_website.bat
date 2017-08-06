cd "C:\Program Files\CompBoard\sandbox\"
set TIMESTAMP=%DATE:~-4%%DATE:~-7,-5%%DATE:~-10,-8%_%time:~-11,2%%time:~-8,2%%time:~-5,2%
set LOGFILE=website_%TIMESTAMP%.log
rem echo started at %TIMESTAMP% > %LOGFILE%

python ..\app\simple_web_server.py --product_config bestsellers.csv
