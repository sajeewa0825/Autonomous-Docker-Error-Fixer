## ⚙️ Installation Guide

This guide explains how to set up and run the project locally using **Python**, **uv**, and **FastAPI**.


##### 1. Check if Python is installed
python --version

##### 2. Install uv Package
pip install uv

##### 3. Create a Virtual Environment
uv venv

##### 4. Activate the Virtual Environment
.venv\Scripts\activate

##### 5.Sync Dependencies
uv sync

##### 6. Start Project
uvicorn app.main:app --reload