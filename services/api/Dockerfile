FROM python:3.14.2

# The path within my container (the linux environment)
WORKDIR /app

# Install the application dependencies
# Copying the file you have now into the container so it will be inside /app i.e. (/app/requirements.txt)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copying the source code
COPY main.py ./main.py
EXPOSE 8000 

# Creates a new user named app in the container
RUN useradd app

# changes ownership of /app and all it's contents to be app (the user)
# app:app follows a user:group structure, linux typically makes a matching group with the same name hence app:app
RUN chown -R app:app /app

USER app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]