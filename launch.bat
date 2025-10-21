@echo off
cd  backend 
start cmd /k uvicorn server_minimal:app --host localhost --port 8000 --reload
cd ..
cd frontend
start cmd /k npm start
cd ..
