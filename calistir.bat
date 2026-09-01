@echo off
REM Dijital Defterim - tek tikla calistirma dosyasi.
REM Bu dosyayi proje klasorune koy, cift tikla ya da terminalden "calistir.bat" yaz.

cd /d "%~dp0"

if not exist C:\ddenv\Scripts\activate.bat (
    echo Sanal ortam bulunamadi, olusturuluyor...
    python -m venv C:\ddenv
    call C:\ddenv\Scripts\activate.bat
    echo Paketler kuruluyor, bu ilk seferde biraz surebilir...
    pip install -r requirements.txt
) else (
    call C:\ddenv\Scripts\activate.bat
)

echo.
echo Dijital Defterim baslatiliyor...
echo Durdurmak icin bu pencerede Ctrl+C yap.
echo.

streamlit run app.py

pause
