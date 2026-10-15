@echo off
setlocal
title Aegis Guard Wazuh Event Test
cd /d "%~dp0"

echo Writing demo Aegis Guard event to Wazuh Indexer...
echo.

curl.exe -s -X POST "http://localhost:8002/events/test"
echo.
echo.
echo Recent ai-soc-events indices:
curl.exe -s -k -u admin:CHANGE_ME_INDEXER_PASSWORD "https://localhost:9200/_cat/indices/ai-soc-events-*?h=index,docs.count&s=index"
echo.
echo.
echo Open Wazuh Dashboard / OpenSearch Discover and use index pattern:
echo   ai-soc-events-*
echo.
pause
