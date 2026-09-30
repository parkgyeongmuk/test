@echo off
rem 작업 스케줄러가 매일 이 파일을 실행한다.
cd /d "%~dp0"
python record.py
