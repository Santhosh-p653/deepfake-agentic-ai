# ASGI and Execution Model in FastAPI

## 1. Introduction

Modern backend systems require the ability to handle a large number of concurrent requests efficiently. Traditional synchronous models often become bottlenecks under high I/O workloads. To address this, asynchronous execution models have become a standard approach in modern web frameworks.

FastAPI is built on top of the ASGI (Asynchronous Server Gateway Interface) specification, which enables non-blocking request handling and high concurrency.

---

## 2. Problem Definition

Traditional Python web applications relied on WSGI (Web Server Gateway Interface), which follows a synchronous execution model.

Limitations of WSGI:

- Blocking request handling
- Poor performance under I/O-bound workloads
- Limited scalability for real-time systems

This creates challenges when building:

- AI inference APIs
- agent-based systems
- streaming or real-time applications

---

## 3. Core Concept: ASGI

ASGI is a specification that defines how web servers communicate with Python applications asynchronously.

An ASGI application operates using three core components:

- scope → metadata about the request (type, headers, path)
- receive → channel to receive incoming data
- send → channel to send responses

---

## 4. ASGI Execution Flow

sequenceDiagram
    participant Client
    participant Uvicorn (ASGI Server)
    participant FastAPI App

    Client->>Uvicorn (ASGI Server): HTTP Request
    Uvicorn (ASGI Server)->>FastAPI App: scope
    FastAPI App->>Uvicorn (ASGI Server): receive()
    FastAPI App->>Uvicorn (ASGI Server): send(response)
    Uvicorn (ASGI Server)->>Client: HTTP Response

## Figure: Interaction between client, ASGI server, and FastAPI application.

---

## 5. FastAPI System Perspective

FastAPI does not operate in isolation. It is part of a layered architecture:

flowchart LR
    A[Client] --> B[Uvicorn ASGI Server]
    B --> C[FastAPI Application]
    C --> D[Starlette (Routing & Middleware)]
    C --> E[Pydantic (Validation)]

Components:

- Uvicorn → ASGI server handling network communication
- FastAPI → API layer defining endpoints
- Starlette → routing, middleware, background tasks
- Pydantic → data validation and parsing

---

## 6. Request Handling Model

FastAPI leverages Python’s "async" / "await" syntax:

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

Key Idea:

- The function is non-blocking
- While waiting (e.g., DB call), other requests can be processed

---

## 7. Trade-offs and Limitations

While ASGI provides significant advantages, it introduces complexity:

Advantages:

- High concurrency
- Efficient I/O handling
- Suitable for AI/ML inference APIs

Limitations:

- Increased conceptual complexity
- Debugging async code is harder
- Not always beneficial for CPU-bound tasks

---

## 8. Key Takeaways

- FastAPI is built on the ASGI specification
- ASGI enables asynchronous, non-blocking execution
- The execution model revolves around:
  - "scope", "receive", "send"
- FastAPI acts as a system boundary layer between clients and backend logic

---

## 9. Next

→ Request-Response Lifecycle in FastAPI
